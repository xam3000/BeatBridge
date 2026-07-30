"""Export real baseline/optimized WAV pairs from an existing batch."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import uuid

import librosa
import numpy as np
import soundfile as sf
import torch

from src.analysis.pre_analysis import PreAnalysis
from src.control import (
    CONTROL_PROTOCOL_VERSION,
    DifferentiableTransitionObjective,
    DifferentiableTwoBandRenderer,
    optimize_control_curves,
)
from src.cutting.equal_power_fade_cut import EqualPowerFadeCut
from src.dataset import (
    DEFAULT_TRACK_EXCLUSIONS_PATH,
    is_track_excluded,
    load_track_exclusions,
)
from src.pipeline import BeatBridgePipeline, DEFAULT_SAMPLE_RATE
from src.ranking import RenderedTransitionInput, rank_rendered_transitions
from src.tempo.time_stretch import TimeStretch


CONTROL_COMPARISON_MANIFEST_FORMAT_VERSION = 1
SELECTION_POLICY = "render_score_desc_unique_pairs_track_use_cap_v2"
DEFAULT_OPTIMIZATION_SAMPLE_RATE = 11_025
DEFAULT_CONTROL_POINTS = 32
DEFAULT_PREFIX_SECONDS = 5.0
DEFAULT_SUFFIX_SECONDS = 8.0


def select_probe_candidates(
    batch_directory,
    *,
    pair_count=4,
    transition_bars=4,
    track_exclusions_path=DEFAULT_TRACK_EXCLUSIONS_PATH,
    max_track_uses=1,
):
    """Select high-scoring candidates with unique pairs and bounded track reuse."""
    batch_directory = Path(batch_directory)
    if pair_count <= 0:
        raise ValueError("pair_count must be greater than 0")
    if transition_bars <= 0:
        raise ValueError("transition_bars must be greater than 0")
    if max_track_uses <= 0:
        raise ValueError("max_track_uses must be greater than 0")

    exclusions = load_track_exclusions(track_exclusions_path)
    candidates = []
    pairs_directory = batch_directory / "pairs"
    for metrics_path in sorted(pairs_directory.glob("*/transition_metrics.json")):
        pair_directory = metrics_path.parent
        manifest = _read_json(pair_directory / "manifest.json")
        metrics = _read_json(metrics_path)
        candidate_by_id = {
            candidate["candidate_id"]: candidate
            for candidate in manifest["candidate_generation"]["candidates"]
        }
        variant_by_id = {
            variant["variant_id"]: variant for variant in metrics.get("variants", ())
        }
        for score in metrics["ranking"]["scores"]:
            candidate = candidate_by_id.get(score["candidate_id"])
            if candidate is None:
                continue
            if int(candidate["transition_length_bars"]) != int(transition_bars):
                continue
            if is_track_excluded(
                candidate["source_track"]["path"],
                sha256=candidate["source_track"]["sha256"],
                scope="control_probe",
                exclusions=exclusions,
            ) or is_track_excluded(
                candidate["target_track"]["path"],
                sha256=candidate["target_track"]["sha256"],
                scope="control_probe",
                exclusions=exclusions,
            ):
                continue
            candidates.append(
                {
                    "pair_directory": pair_directory,
                    "pair_relative_directory": str(
                        pair_directory.relative_to(batch_directory)
                    ),
                    "candidate": candidate,
                    "historical_score": score,
                    "historical_variant": variant_by_id.get(score["variant_id"]),
                }
            )

    candidates.sort(
        key=lambda item: (
            -float(item["historical_score"]["total_score"]),
            item["pair_relative_directory"],
            item["candidate"]["candidate_id"],
        )
    )
    selected = []
    track_use_counts = {}
    used_pairs = set()
    for item in candidates:
        candidate = item["candidate"]
        source_hash = candidate["source_track"]["sha256"]
        target_hash = candidate["target_track"]["sha256"]
        pair_key = (source_hash, target_hash)
        if pair_key in used_pairs:
            continue
        if (
            track_use_counts.get(source_hash, 0) >= max_track_uses
            or track_use_counts.get(target_hash, 0) >= max_track_uses
        ):
            continue
        selected.append(item)
        used_pairs.add(pair_key)
        track_use_counts[source_hash] = track_use_counts.get(source_hash, 0) + 1
        track_use_counts[target_hash] = track_use_counts.get(target_hash, 0) + 1
        if len(selected) == pair_count:
            break

    if len(selected) < pair_count:
        raise ValueError(
            f"Only found {len(selected)} eligible unique pairs with max_track_uses="
            f"{max_track_uses}; requested {pair_count}"
        )
    return tuple(selected)


def export_control_comparisons(
    batch_directory,
    output_directory,
    *,
    analysis_location=Path("output") / "pre_analysis",
    pair_count=4,
    transition_bars=4,
    control_points=DEFAULT_CONTROL_POINTS,
    optimization_steps=60,
    optimization_learning_rate=0.08,
    optimization_sample_rate=DEFAULT_OPTIMIZATION_SAMPLE_RATE,
    prefix_seconds=DEFAULT_PREFIX_SECONDS,
    suffix_seconds=DEFAULT_SUFFIX_SECONDS,
    track_exclusions_path=DEFAULT_TRACK_EXCLUSIONS_PATH,
    max_track_uses=1,
):
    """Render baseline and directly optimized WAVs for selected real candidates."""
    batch_directory = Path(batch_directory)
    output_directory = Path(output_directory)
    manifest_path = output_directory / "manifest.json"
    if output_directory.exists():
        raise FileExistsError(
            f"Comparison output already exists; choose a new directory: {output_directory}"
        )
    if control_points < 3:
        raise ValueError("control_points must be at least 3")
    if optimization_steps < 1:
        raise ValueError("optimization_steps must be at least 1")
    if optimization_sample_rate <= 0:
        raise ValueError("optimization_sample_rate must be greater than 0")
    if prefix_seconds < 0 or suffix_seconds < 0:
        raise ValueError("Preview context durations must be greater than or equal to 0")

    selected = select_probe_candidates(
        batch_directory,
        pair_count=pair_count,
        transition_bars=transition_bars,
        track_exclusions_path=track_exclusions_path,
        max_track_uses=max_track_uses,
    )
    output_directory.mkdir(parents=True)
    payload = {
        "format_version": CONTROL_COMPARISON_MANIFEST_FORMAT_VERSION,
        "control_protocol_version": CONTROL_PROTOCOL_VERSION,
        "status": "running",
        "created_at_utc": _utc_now(),
        "completed_at_utc": None,
        "source_batch": str(batch_directory),
        "selection_policy": SELECTION_POLICY,
        "track_exclusions_path": str(track_exclusions_path),
        "config": {
            "pair_count": int(pair_count),
            "transition_bars": int(transition_bars),
            "control_points": int(control_points),
            "optimization_steps": int(optimization_steps),
            "optimization_learning_rate": float(optimization_learning_rate),
            "optimization_sample_rate": int(optimization_sample_rate),
            "render_sample_rate": DEFAULT_SAMPLE_RATE,
            "prefix_seconds": float(prefix_seconds),
            "suffix_seconds": float(suffix_seconds),
            "max_track_uses": int(max_track_uses),
        },
        "pairs": [],
        "failures": [],
    }
    _write_json_atomic(manifest_path, payload)

    analysis = PreAnalysis(str(Path(analysis_location)) + os.sep)
    for index, selection in enumerate(selected, start=1):
        candidate = selection["candidate"]
        pair_slug = _pair_slug(candidate)
        pair_directory = output_directory / f"{index:02d}__{pair_slug}"
        pair_directory.mkdir()
        try:
            result = _render_comparison_pair(
                candidate,
                selection,
                pair_directory,
                analysis=analysis,
                control_points=control_points,
                optimization_steps=optimization_steps,
                optimization_learning_rate=optimization_learning_rate,
                optimization_sample_rate=optimization_sample_rate,
                prefix_seconds=prefix_seconds,
                suffix_seconds=suffix_seconds,
            )
            result["index"] = index
            result["directory"] = str(pair_directory.relative_to(output_directory))
            payload["pairs"].append(result)
            print(
                f"[{index}/{len(selected)}] {pair_slug}: "
                f"{result['optimization']['initial_loss']:.4f} -> "
                f"{result['optimization']['final_loss']:.4f}",
                flush=True,
            )
        except Exception as error:
            payload["failures"].append(
                {
                    "index": index,
                    "candidate_id": candidate["candidate_id"],
                    "error_type": type(error).__name__,
                    "message": str(error),
                }
            )
            print(
                f"[{index}/{len(selected)}] failed {pair_slug}: {error}",
                flush=True,
            )
        _write_json_atomic(manifest_path, payload)

    payload["completed_at_utc"] = _utc_now()
    payload["status"] = "completed" if not payload["failures"] else "completed_with_failures"
    _write_json_atomic(manifest_path, payload)
    _write_readme(output_directory, payload)
    return manifest_path


def _render_comparison_pair(
    candidate,
    selection,
    pair_directory,
    *,
    analysis,
    control_points,
    optimization_steps,
    optimization_learning_rate,
    optimization_sample_rate,
    prefix_seconds,
    suffix_seconds,
):
    source, target, geometry = _extract_aligned_bridge(candidate, analysis)
    proxy_source = librosa.resample(
        source,
        orig_sr=DEFAULT_SAMPLE_RATE,
        target_sr=optimization_sample_rate,
        axis=-1,
        res_type="soxr_hq",
    ).astype(np.float32, copy=False)
    proxy_target = librosa.resample(
        target,
        orig_sr=DEFAULT_SAMPLE_RATE,
        target_sr=optimization_sample_rate,
        axis=-1,
        res_type="soxr_hq",
    ).astype(np.float32, copy=False)
    proxy_source_tensor = torch.from_numpy(proxy_source)
    proxy_target_tensor = torch.from_numpy(proxy_target)
    proxy_renderer = DifferentiableTwoBandRenderer(
        sample_rate=optimization_sample_rate,
        lowpass_cutoff_hz=180.0,
        lowpass_kernel_size=127,
    )
    objective = DifferentiableTransitionObjective(energy_frames=control_points)
    baseline_control = torch.linspace(0.0, 1.0, control_points)
    with torch.no_grad():
        proxy_baseline = proxy_renderer(
            proxy_source_tensor,
            proxy_target_tensor,
            baseline_control,
            baseline_control,
        )
        baseline_terms = objective(
            proxy_baseline,
            proxy_source_tensor,
            proxy_target_tensor,
        )

    optimization = optimize_control_curves(
        proxy_source_tensor,
        proxy_target_tensor,
        renderer=proxy_renderer,
        objective=objective,
        control_points=control_points,
        steps=optimization_steps,
        learning_rate=optimization_learning_rate,
    )
    with torch.no_grad():
        optimized_proxy_render = proxy_renderer(
            proxy_source_tensor,
            proxy_target_tensor,
            optimization.mix_position,
            optimization.low_end_position,
        )
        optimized_terms = objective(
            optimized_proxy_render,
            proxy_source_tensor,
            proxy_target_tensor,
        )

    full_renderer = DifferentiableTwoBandRenderer(
        sample_rate=DEFAULT_SAMPLE_RATE,
        lowpass_cutoff_hz=180.0,
        lowpass_kernel_size=511,
    )
    full_source_tensor = torch.from_numpy(source)
    full_target_tensor = torch.from_numpy(target)
    with torch.no_grad():
        baseline_transition = full_renderer(
            full_source_tensor,
            full_target_tensor,
            baseline_control,
            baseline_control,
        ).audio.cpu().numpy()
        optimized_transition = full_renderer(
            full_source_tensor,
            full_target_tensor,
            optimization.mix_position,
            optimization.low_end_position,
        ).audio.cpu().numpy()

    prefix = geometry["source_audio"][
        ...,
        max(
            0,
            geometry["source_cut_sample"]
            - int(round(prefix_seconds * DEFAULT_SAMPLE_RATE)),
        ) : geometry["source_cut_sample"],
    ]
    suffix = geometry["target_audio"][
        ...,
        geometry["target_cut_sample"] : min(
            geometry["target_audio"].shape[-1],
            geometry["target_cut_sample"]
            + int(round(suffix_seconds * DEFAULT_SAMPLE_RATE)),
        ),
    ]
    baseline_preview = np.concatenate(
        (prefix, baseline_transition, suffix),
        axis=-1,
    ).astype(np.float32, copy=False)
    optimized_preview = np.concatenate(
        (prefix, optimized_transition, suffix),
        axis=-1,
    ).astype(np.float32, copy=False)
    raw_peak = max(
        float(np.max(np.abs(baseline_preview))),
        float(np.max(np.abs(optimized_preview))),
    )
    shared_gain = min(1.0, 0.98 / max(raw_peak, 1e-8))
    baseline_preview = baseline_preview * shared_gain
    optimized_preview = optimized_preview * shared_gain

    baseline_path = pair_directory / "01_baseline_equal_power.wav"
    optimized_path = pair_directory / "02_optimized_proxy.wav"
    _write_audio_atomic(baseline_path, baseline_preview, DEFAULT_SAMPLE_RATE)
    _write_audio_atomic(optimized_path, optimized_preview, DEFAULT_SAMPLE_RATE)

    transition_start = prefix.shape[-1]
    transition_end = transition_start + source.shape[-1]
    historical_comparison = rank_rendered_transitions(
        (
            RenderedTransitionInput(
                candidate_id=candidate["candidate_id"],
                renderer="control_baseline",
                audio=baseline_preview,
                sample_rate=DEFAULT_SAMPLE_RATE,
                transition_start_sample=transition_start,
                transition_end_sample=transition_end,
                transition_length_beats=candidate["transition_length_beats"],
                bpm=candidate["source_bpm"],
            ),
            RenderedTransitionInput(
                candidate_id=candidate["candidate_id"],
                renderer="control_optimized",
                audio=optimized_preview,
                sample_rate=DEFAULT_SAMPLE_RATE,
                transition_start_sample=transition_start,
                transition_end_sample=transition_end,
                transition_length_beats=candidate["transition_length_beats"],
                bpm=candidate["source_bpm"],
            ),
        )
    )

    return {
        "candidate": candidate,
        "source_pair_directory": selection["pair_relative_directory"],
        "historical_render_score": selection["historical_score"],
        "historical_variant": selection["historical_variant"],
        "geometry": {
            key: value
            for key, value in geometry.items()
            if key not in {"source_audio", "target_audio"}
        },
        "optimization": {
            "initial_loss": float(baseline_terms["loss"].cpu()),
            "final_loss": float(optimized_terms["loss"].cpu()),
            "relative_improvement": float(
                1.0
                - float(optimized_terms["loss"].cpu())
                / max(float(baseline_terms["loss"].cpu()), 1e-12)
            ),
            "baseline_components": _tensor_terms_to_float(baseline_terms),
            "optimized_components": _tensor_terms_to_float(optimized_terms),
            "mix_position": [
                float(value) for value in optimization.mix_position.cpu()
            ],
            "low_end_position": [
                float(value) for value in optimization.low_end_position.cpu()
            ],
        },
        "exports": {
            "baseline": _audio_metadata(
                baseline_path,
                baseline_preview,
                DEFAULT_SAMPLE_RATE,
            ),
            "optimized": _audio_metadata(
                optimized_path,
                optimized_preview,
                DEFAULT_SAMPLE_RATE,
            ),
            "shared_peak_gain": float(shared_gain),
            "raw_joint_peak": float(raw_peak),
            "transition_start_sample": int(transition_start),
            "transition_end_sample": int(transition_end),
        },
        "historical_metric_comparison": historical_comparison.to_dict(),
    }


def _extract_aligned_bridge(candidate, analysis):
    transition_beats = int(candidate["transition_length_beats"])
    cutter = EqualPowerFadeCut(fade_beats=transition_beats)
    pipeline = BeatBridgePipeline(
        candidate["source_track"]["path"],
        candidate["target_track"]["path"],
        analysis,
        TimeStretch(),
        cutter,
        target_sample_rate=DEFAULT_SAMPLE_RATE,
        bpm1=candidate["source_bpm"],
        bpm2=candidate["target_bpm"],
    )
    source_audio, target_audio = pipeline.adjust_tempo()
    source_cut = int(candidate["source_cutpoint"]["sample"])
    target_cut = int(
        round(
            int(candidate["target_cutpoint"]["sample"])
            * pipeline.adjusted_sample_scale2
        )
    )
    source_cut, target_cut = cutter.resolve_cut_samples(
        source_audio,
        target_audio,
        source_cut,
        target_cut,
        pipeline.beat_frames1,
        pipeline.adjusted_beat_frames2,
    )
    source_end = cutter._find_beat_offset_sample(
        pipeline.beat_frames1,
        source_cut,
        transition_beats,
        source_audio.shape[-1],
    )
    target_start = cutter._find_beat_offset_sample(
        pipeline.adjusted_beat_frames2,
        target_cut,
        -transition_beats,
        target_audio.shape[-1],
    )
    transition_samples = min(source_end - source_cut, target_cut - target_start)
    if transition_samples <= 0:
        raise ValueError("Candidate has no complete aligned transition window")
    source = source_audio[..., source_cut : source_cut + transition_samples]
    target = target_audio[..., target_cut - transition_samples : target_cut]
    return (
        np.asarray(source, dtype=np.float32),
        np.asarray(target, dtype=np.float32),
        {
            "source_cut_sample": int(source_cut),
            "target_cut_sample": int(target_cut),
            "transition_samples": int(transition_samples),
            "transition_seconds": float(transition_samples / DEFAULT_SAMPLE_RATE),
            "source_audio": source_audio,
            "target_audio": target_audio,
        },
    )


def _pair_slug(candidate):
    source = Path(candidate["source_track"]["path"]).stem
    target = Path(candidate["target_track"]["path"]).stem
    return f"{_safe_name(source)}__to__{_safe_name(target)}"


def _safe_name(value):
    cleaned = "".join(character if character.isalnum() else "_" for character in value)
    return "_".join(part for part in cleaned.split("_") if part)


def _tensor_terms_to_float(terms):
    return {
        key: float(value.detach().cpu())
        for key, value in terms.items()
    }


def _audio_metadata(path, audio, sample_rate):
    return {
        "path": path.name,
        "sample_rate": int(sample_rate),
        "channels": int(audio.shape[0]),
        "sample_count": int(audio.shape[-1]),
        "duration_seconds": float(audio.shape[-1] / sample_rate),
        "peak": float(np.max(np.abs(audio))),
    }


def _write_audio_atomic(path, audio, sample_rate):
    temporary_path = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        sf.write(
            str(temporary_path),
            np.asarray(audio).T,
            int(sample_rate),
            format="WAV",
            subtype="FLOAT",
        )
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)


def _write_json_atomic(path, payload):
    temporary_path = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        temporary_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)


def _write_readme(output_directory, payload):
    lines = [
        "# Control-Vergleich",
        "",
        "Jeder Unterordner enthält dieselbe Transition mit identischem Kontext:",
        "",
        "- `01_baseline_equal_power.wav`: feste Equal-Power- und Low-End-Kurve",
        "- `02_optimized_proxy.wav`: direkt gegen das differenzierbare Proxy-Objective optimiert",
        "",
        "Bitte zuerst blind bzw. ohne Blick auf die Metrikwerte anhören. Achte auf",
        "Energieverlauf, Grenzglätte, Low-End-Übergabe, Rhythmus und Artefakte.",
        "",
        f"Status: `{payload['status']}`; Paare: {len(payload['pairs'])}; "
        f"Fehler: {len(payload['failures'])}.",
        "",
        "Alle Cutpoints, Controls, Loss-Komponenten und technischen Metadaten stehen",
        "in `manifest.json`.",
        "",
    ]
    readme_path = output_directory / "README.md"
    temporary_path = readme_path.with_name(f".{readme_path.name}.{uuid.uuid4().hex}.tmp")
    try:
        temporary_path.write_text("\n".join(lines), encoding="utf-8")
        os.replace(temporary_path, readme_path)
    finally:
        temporary_path.unlink(missing_ok=True)


def _read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def build_argument_parser():
    parser = argparse.ArgumentParser(
        description="Export baseline/optimized control WAV pairs from a historical batch.",
    )
    parser.add_argument("batch_directory")
    parser.add_argument("output_directory")
    parser.add_argument("--analysis-location", default=str(Path("output") / "pre_analysis"))
    parser.add_argument("--pair-count", type=int, default=4)
    parser.add_argument("--transition-bars", type=int, default=4)
    parser.add_argument("--control-points", type=int, default=DEFAULT_CONTROL_POINTS)
    parser.add_argument("--optimization-steps", type=int, default=60)
    parser.add_argument("--learning-rate", type=float, default=0.08)
    parser.add_argument(
        "--optimization-sample-rate",
        type=int,
        default=DEFAULT_OPTIMIZATION_SAMPLE_RATE,
    )
    parser.add_argument("--prefix-seconds", type=float, default=DEFAULT_PREFIX_SECONDS)
    parser.add_argument("--suffix-seconds", type=float, default=DEFAULT_SUFFIX_SECONDS)
    parser.add_argument(
        "--track-exclusions",
        default=str(DEFAULT_TRACK_EXCLUSIONS_PATH),
    )
    parser.add_argument("--max-track-uses", type=int, default=1)
    return parser


def main():
    args = build_argument_parser().parse_args()
    manifest_path = export_control_comparisons(
        args.batch_directory,
        args.output_directory,
        analysis_location=args.analysis_location,
        pair_count=args.pair_count,
        transition_bars=args.transition_bars,
        control_points=args.control_points,
        optimization_steps=args.optimization_steps,
        optimization_learning_rate=args.learning_rate,
        optimization_sample_rate=args.optimization_sample_rate,
        prefix_seconds=args.prefix_seconds,
        suffix_seconds=args.suffix_seconds,
        track_exclusions_path=args.track_exclusions,
        max_track_uses=args.max_track_uses,
    )
    payload = _read_json(manifest_path)
    print(
        f"Exported {len(payload['pairs']) * 2} WAVs across {len(payload['pairs'])} "
        f"pairs; failures: {len(payload['failures'])}"
    )
    print(manifest_path)
    return 0 if payload["status"] == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
