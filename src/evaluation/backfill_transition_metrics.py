"""Score rendered WAVs from an existing multi-song batch without rewriting it."""

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import uuid

import numpy as np
import soundfile as sf

from src.analysis.pre_analysis import (
    ANALYSIS_CACHE_FILENAME,
    ANALYSIS_CACHE_FORMAT_VERSION,
    ANALYSIS_CACHE_NAMESPACE,
)

from src.ranking import RenderedTransitionInput, rank_rendered_transitions


TRANSITION_METRICS_SIDECAR_FORMAT_VERSION = 1
TRANSITION_METRICS_FILENAME = "transition_metrics.json"
GEOMETRY_RECONSTRUCTION = "candidate_beat_grid_v1"


def score_existing_multi_batch(
    batch_directory,
    *,
    analysis_location=Path("output") / "pre_analysis",
    overwrite=False,
):
    """Score every rendered pair in a historical multi-song batch.

    Existing manifests and WAV files remain read-only. One metric sidecar is
    written beside every pair manifest and one progress/summary sidecar is
    written at the multi-batch root.
    """
    batch_directory = Path(batch_directory)
    root_manifest_path = batch_directory / "manifest.json"
    root_manifest = _read_json(root_manifest_path)
    pair_entries = _pair_entries(root_manifest)
    root_metrics_path = batch_directory / TRANSITION_METRICS_FILENAME
    pair_metrics_paths = [
        batch_directory / Path(entry["manifest_path"]).parent / TRANSITION_METRICS_FILENAME
        for entry in pair_entries
    ]
    _preflight_sidecars([root_metrics_path, *pair_metrics_paths], overwrite=overwrite)

    analysis_cache = _ReadOnlyBeatGridCache(analysis_location)
    started_at = _utc_now()
    root_payload = {
        "format_version": TRANSITION_METRICS_SIDECAR_FORMAT_VERSION,
        "source_manifest": "manifest.json",
        "metric": "rendered_transition_baseline_v1",
        "geometry_reconstruction": GEOMETRY_RECONSTRUCTION,
        "started_at_utc": started_at,
        "completed_at_utc": None,
        "status": "running",
        "pair_count": len(pair_entries),
        "completed_pair_count": 0,
        "scored_variant_count": 0,
        "failure_count": 0,
        "pairs": [],
        "score_summary": None,
    }
    _write_json_atomic(root_metrics_path, root_payload)

    all_scores = []
    for pair_index, pair_entry in enumerate(pair_entries, start=1):
        pair_manifest_path = batch_directory / pair_entry["manifest_path"]
        pair_directory = pair_manifest_path.parent
        metrics_path = pair_directory / TRANSITION_METRICS_FILENAME
        summary = {
            "pair_index": pair_index,
            "manifest_path": str(pair_manifest_path.relative_to(batch_directory)),
            "metrics_path": str(metrics_path.relative_to(batch_directory)),
            "status": "running",
        }
        root_payload["pairs"].append(summary)
        _write_json_atomic(root_metrics_path, root_payload)
        try:
            pair_payload = score_existing_pair_batch(
                pair_directory,
                analysis_cache=analysis_cache,
            )
            _write_json_atomic(metrics_path, pair_payload)
            pair_scores = pair_payload["ranking"]["scores"]
            all_scores.extend(score["total_score"] for score in pair_scores)
            summary.update(
                {
                    "status": "completed",
                    "rendered_variant_count": pair_payload["rendered_variant_count"],
                    "scored_variant_count": pair_payload["scored_variant_count"],
                    "failure_count": pair_payload["failure_count"],
                }
            )
            root_payload["scored_variant_count"] += pair_payload["scored_variant_count"]
            root_payload["failure_count"] += pair_payload["failure_count"]
        except Exception as error:
            summary.update(
                {
                    "status": "failed",
                    "error_type": type(error).__name__,
                    "message": str(error),
                }
            )
            root_payload["failure_count"] += 1
        root_payload["completed_pair_count"] = pair_index
        root_payload["score_summary"] = _score_summary(all_scores)
        _write_json_atomic(root_metrics_path, root_payload)
        print(
            f"[{pair_index}/{len(pair_entries)}] {summary['status']}: "
            f"{pair_entry['manifest_path']}",
            flush=True,
        )

    root_payload["completed_at_utc"] = _utc_now()
    root_payload["status"] = (
        "completed" if all(pair["status"] == "completed" for pair in root_payload["pairs"])
        else "completed_with_failures"
    )
    root_payload["score_summary"] = _score_summary(all_scores)
    _write_json_atomic(root_metrics_path, root_payload)
    return root_metrics_path


def score_existing_pair_batch(pair_directory, *, analysis_cache):
    """Return a sidecar payload for one historical pair batch."""
    pair_directory = Path(pair_directory)
    manifest = _read_json(pair_directory / "manifest.json")
    candidates = {
        candidate["candidate_id"]: candidate
        for candidate in manifest["candidate_generation"]["candidates"]
    }
    rendered_inputs = []
    preparation_failures = []
    geometry_by_variant = {}

    for variant in manifest["rendered_variants"]:
        candidate_id = variant["candidate_id"]
        renderer = variant["renderer"]
        variant_id = f"{candidate_id}::{renderer}"
        try:
            candidate = candidates[candidate_id]
            audio_path = pair_directory / variant["output_file"]
            audio, sample_rate = sf.read(
                str(audio_path),
                always_2d=True,
                dtype="float32",
            )
            audio = np.asarray(audio.T, dtype=np.float32)
            if int(variant["sample_rate"]) != int(sample_rate):
                raise ValueError(
                    f"Manifest/WAV sample-rate mismatch for {variant_id}: "
                    f"{variant['sample_rate']} != {sample_rate}"
                )
            transition_start, transition_end = _rendered_transition_bounds(
                candidate,
                renderer,
                manifest.get("render_preview"),
                int(sample_rate),
                audio.shape[-1],
                analysis_cache,
            )
            geometry_by_variant[variant_id] = {
                "variant_id": variant_id,
                "candidate_id": candidate_id,
                "renderer": renderer,
                "output_file": variant["output_file"],
                "transition_start_sample": transition_start,
                "transition_end_sample": transition_end,
            }
            rendered_inputs.append(
                RenderedTransitionInput(
                    candidate_id=candidate_id,
                    renderer=renderer,
                    audio=audio,
                    sample_rate=int(sample_rate),
                    transition_start_sample=transition_start,
                    transition_end_sample=transition_end,
                    transition_length_beats=int(candidate["transition_length_beats"]),
                    bpm=float(candidate["source_bpm"]),
                )
            )
        except Exception as error:
            preparation_failures.append(
                {
                    "variant_id": variant_id,
                    "candidate_id": candidate_id,
                    "renderer": renderer,
                    "stage": "prepare_rendered_audio",
                    "error_type": type(error).__name__,
                    "message": str(error),
                }
            )

    ranking = rank_rendered_transitions(rendered_inputs)
    ranking_payload = ranking.to_dict()
    ranking_payload["failures"] = [
        {
            **failure,
            "stage": "score_rendered_audio",
        }
        for failure in ranking_payload["failures"]
    ]
    ranking_payload["failures"].extend(preparation_failures)
    score_by_variant = {
        score["variant_id"]: score for score in ranking_payload["scores"]
    }
    variants = []
    for variant in manifest["rendered_variants"]:
        variant_id = f"{variant['candidate_id']}::{variant['renderer']}"
        geometry = geometry_by_variant.get(
            variant_id,
            {
                "variant_id": variant_id,
                "candidate_id": variant["candidate_id"],
                "renderer": variant["renderer"],
                "output_file": variant["output_file"],
                "transition_start_sample": None,
                "transition_end_sample": None,
            },
        )
        score = score_by_variant.get(variant_id)
        variants.append(
            {
                **geometry,
                "transition_rank": None if score is None else score["rank"],
                "transition_score": None if score is None else score["total_score"],
            }
        )

    return {
        "format_version": TRANSITION_METRICS_SIDECAR_FORMAT_VERSION,
        "source_manifest": "manifest.json",
        "source_manifest_format_version": manifest.get("format_version"),
        "metric": ranking.metric,
        "geometry_reconstruction": GEOMETRY_RECONSTRUCTION,
        "created_at_utc": _utc_now(),
        "rendered_variant_count": len(manifest["rendered_variants"]),
        "scored_variant_count": len(ranking_payload["scores"]),
        "failure_count": len(ranking_payload["failures"]),
        "ranking": ranking_payload,
        "variants": variants,
    }


def _rendered_transition_bounds(
    candidate,
    renderer,
    preview,
    sample_rate,
    rendered_sample_count,
    analysis_cache,
):
    source_cutpoint = int(candidate["source_cutpoint"]["sample"])
    preview_before = None if preview is None else preview.get(
        "seconds_before_source_cutpoint"
    )
    if preview_before is None:
        preview_start = 0
    else:
        preview_start = max(
            0,
            int(round(source_cutpoint - float(preview_before) * sample_rate)),
        )
    transition_start = source_cutpoint - preview_start

    if renderer == "simple":
        transition_samples = 0
    else:
        transition_samples = _bridge_transition_samples(
            candidate,
            sample_rate,
            analysis_cache,
        )
    transition_end = transition_start + transition_samples
    if transition_start < 0 or transition_start >= rendered_sample_count:
        raise ValueError("Reconstructed transition start is outside the rendered WAV")
    if transition_end < transition_start or transition_end > rendered_sample_count:
        raise ValueError("Reconstructed transition end is outside the rendered WAV")
    return transition_start, transition_end


def _bridge_transition_samples(candidate, sample_rate, analysis_cache):
    transition_beats = int(candidate["transition_length_beats"])
    if transition_beats <= 0:
        raise ValueError("transition_length_beats must be greater than 0")

    source_beats = analysis_cache.normalised_beats(
        candidate["source_track"]["path"],
        candidate["source_track"]["sha256"],
        sample_rate,
        expected_grid_metadata=candidate.get("source_grid"),
    )
    target_beats = analysis_cache.normalised_beats(
        candidate["target_track"]["path"],
        candidate["target_track"]["sha256"],
        sample_rate,
        expected_grid_metadata=candidate.get("target_grid"),
    )
    source_index = int(candidate["source_cutpoint"]["beat_index"])
    target_index = int(candidate["target_cutpoint"]["beat_index"])
    if source_index + transition_beats >= len(source_beats):
        raise ValueError("Source beat grid has no complete transition post-roll")
    if target_index - transition_beats < 0:
        raise ValueError("Target beat grid has no complete transition pre-roll")

    source_cutpoint = int(candidate["source_cutpoint"]["sample"])
    source_transition_end = int(source_beats[source_index + transition_beats][0])
    source_samples = source_transition_end - source_cutpoint

    tempo_scale = float(candidate["target_bpm"]) / float(candidate["source_bpm"])
    target_cutpoint = int(round(int(candidate["target_cutpoint"]["sample"]) * tempo_scale))
    target_transition_start = int(
        round(int(target_beats[target_index - transition_beats][0]) * tempo_scale)
    )
    target_samples = target_cutpoint - target_transition_start
    transition_samples = min(source_samples, target_samples)
    if transition_samples <= 0:
        raise ValueError("Reconstructed bridge transition has no samples")
    return transition_samples


class _ReadOnlyBeatGridCache:
    def __init__(self, analysis_location):
        self.analysis_location = Path(analysis_location)
        self._cache = {}

    def normalised_beats(
        self,
        track_path,
        expected_hash,
        sample_rate,
        *,
        expected_grid_metadata=None,
    ):
        analysis_id = (
            None
            if not expected_grid_metadata
            else expected_grid_metadata.get("analysis_id")
        )
        key = (
            str(Path(track_path)),
            str(expected_hash),
            int(sample_rate),
            analysis_id,
        )
        if key in self._cache:
            return self._cache[key]

        track_path = Path(track_path)
        legacy_path = self.analysis_location / track_path.stem / "00_pre_analysis.txt"
        if analysis_id is None and legacy_path.is_file():
            lines = legacy_path.read_text(encoding="utf-8").splitlines()
            if lines and lines[0].strip() == str(expected_hash):
                beats = self._legacy_beats(lines, legacy_path)
                self._cache[key] = self._scale_beats(beats, track_path, sample_rate)
                return self._cache[key]

        cache_path = self._current_cache_path(expected_hash, analysis_id)
        payload = json.loads(cache_path.read_text(encoding="utf-8"))
        if payload.get("format_version") != ANALYSIS_CACHE_FORMAT_VERSION:
            raise ValueError(f"Unsupported analysis cache format: {cache_path}")
        if analysis_id and payload.get("analysis_id") != str(analysis_id):
            raise ValueError(f"Analysis cache identity does not match candidate: {cache_path}")
        if payload["source_audio"]["sha256"] != str(expected_hash):
            raise ValueError(f"Analysis cache hash does not match candidate: {cache_path}")
        grid_metadata = payload["result"]["grid_metadata"]
        expected_grid_hash = (
            None
            if not expected_grid_metadata
            else expected_grid_metadata.get("beat_grid_sha256")
        )
        if (
            expected_grid_hash
            and grid_metadata.get("beat_grid_sha256") != expected_grid_hash
        ):
            raise ValueError(
                f"Analysis cache beat-grid hash does not match candidate: {cache_path}"
            )
        beats = [
            tuple(int(value) for value in frame)
            for frame in payload["result"]["beat_frames"]
        ]
        if not beats:
            raise ValueError(f"Analysis cache contains no beat positions: {cache_path}")
        self._cache[key] = self._scale_beats(beats, track_path, sample_rate)
        return self._cache[key]

    def _current_cache_path(self, expected_hash, analysis_id):
        hash_root = (
            self.analysis_location
            / ANALYSIS_CACHE_NAMESPACE
            / str(expected_hash)
        )
        if analysis_id:
            cache_path = hash_root / str(analysis_id) / ANALYSIS_CACHE_FILENAME
            if cache_path.is_file():
                return cache_path
            raise ValueError(f"Expected analysis cache is missing: {cache_path}")
        matches = sorted(hash_root.glob(f"*/{ANALYSIS_CACHE_FILENAME}"))
        if len(matches) == 1:
            return matches[0]
        if not matches:
            raise ValueError(f"No analysis cache found for audio hash {expected_hash}")
        raise ValueError(
            f"Multiple analysis caches exist for audio hash {expected_hash}; "
            "candidate provenance needs analysis_id"
        )

    @staticmethod
    def _legacy_beats(lines, cache_path):
        if len(lines) < 3:
            raise ValueError(f"Analysis cache is incomplete: {cache_path}")
        beats = []
        for line in lines[2:]:
            if not line.strip():
                continue
            parts = [part.strip() for part in line.split(",")]
            if len(parts) == 1:
                beat = (int(parts[0]), None, None)
            elif len(parts) == 3:
                beat = (
                    int(parts[0]),
                    int(parts[1]),
                    int(parts[2]),
                )
            else:
                raise ValueError(f"Invalid beat entry in analysis cache: {line}")
            beats.append(beat)
        if not beats:
            raise ValueError(f"Analysis cache contains no beat positions: {cache_path}")
        return beats

    @staticmethod
    def _scale_beats(beats, track_path, sample_rate):
        source_sample_rate = int(sf.info(str(track_path)).samplerate)
        scale = int(sample_rate) / float(source_sample_rate)
        return tuple(
            (int(round(int(beat[0]) * scale)), beat[1], beat[2]) for beat in beats
        )


def _pair_entries(root_manifest):
    entries = []
    for source in root_manifest.get("sources", []):
        for pair in source.get("pairs", []):
            if pair.get("status") == "completed" and pair.get("manifest_path"):
                entries.append(pair)
    if not entries:
        raise ValueError("Multi-batch manifest contains no completed pair manifests")
    return entries


def _score_summary(scores):
    if not scores:
        return None
    values = np.asarray(scores, dtype=np.float64)
    return {
        "minimum": round(float(np.min(values)), 6),
        "maximum": round(float(np.max(values)), 6),
        "mean": round(float(np.mean(values)), 6),
        "median": round(float(np.median(values)), 6),
    }


def _preflight_sidecars(paths, *, overwrite):
    if overwrite:
        return
    existing = [path for path in paths if path.exists()]
    if existing:
        raise FileExistsError(
            "Transition-metric sidecar already exists. Use --overwrite to replace it: "
            f"{existing[0]}"
        )


def _read_json(path):
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"Manifest not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json_atomic(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        temporary_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def build_argument_parser():
    parser = argparse.ArgumentParser(
        description="Score rendered WAVs in an existing multi-song batch.",
    )
    parser.add_argument("batch_directory")
    parser.add_argument(
        "--analysis-location",
        default=str(Path("output") / "pre_analysis"),
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace existing transition_metrics.json sidecars.",
    )
    return parser


def main():
    args = build_argument_parser().parse_args()
    metrics_path = score_existing_multi_batch(
        args.batch_directory,
        analysis_location=args.analysis_location,
        overwrite=args.overwrite,
    )
    payload = _read_json(metrics_path)
    print(
        f"Scored {payload['scored_variant_count']} variants across "
        f"{payload['completed_pair_count']} pair batches; "
        f"recorded {payload['failure_count']} failures."
    )
    print(metrics_path)
    return 0 if payload["status"] == "completed" and payload["failure_count"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
