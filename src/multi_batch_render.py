"""Render the best transition batches for the best target songs per source."""

import argparse
from concurrent.futures import ThreadPoolExecutor
import glob
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sys
import uuid

from src.analysis.pre_analysis import PreAnalysis
from src.batch_render import DEFAULT_RENDERERS, RANKING_METHODS, generate_and_render_batch
from src.ranking import load_learned_cue_ranker
from src.candidates import CandidateGenerationConfig, VariableCandidateGenerationConfig
from src.dataset import (
    DEFAULT_TRACK_EXCLUSIONS_PATH,
    filter_excluded_tracks,
    load_track_exclusions,
)
from src.ranking.song_compatibility import rank_song_targets


MULTI_BATCH_MANIFEST_FORMAT_VERSION = 1
AUDIO_EXTENSIONS = {".flac", ".mp3", ".ogg", ".wav"}
DEFAULT_TRANSITION_LENGTHS_BARS = (2, 4)


def generate_multi_song_batch(
    songs,
    output_directory,
    *,
    top_targets=3,
    top_transitions=3,
    renderers=("equal_power",),
    target_sample_rate=44_100,
    analysis_location=None,
    track_exclusions_path=DEFAULT_TRACK_EXCLUSIONS_PATH,
    minimum_bpm=None,
    maximum_bpm=None,
    analysis_workers=1,
    approximate_grid_policy="reject",
    transition_lengths_bars=DEFAULT_TRANSITION_LENGTHS_BARS,
    ranking_method="feature_baseline_v3",
    cue_ranker_run=None,
    cue_ranker_dataset=None,
    cue_ranker_feature_cache_root="output/feature_cache",
    cue_ranker_vocal_backend="disabled",
):
    """Rank targets per source, then render the best transition candidates.

    Each selected song pair gets its own regular batch directory and manifest.
    The parent manifest records the song-level selection and keeps a stable
    index of all pair-level results.
    """
    expanded_song_paths = _expand_song_paths(songs)
    track_exclusions = load_track_exclusions(track_exclusions_path)
    song_paths, excluded_tracks = filter_excluded_tracks(
        expanded_song_paths,
        scope="multi_batch",
        exclusions=track_exclusions,
    )
    song_paths, duplicate_tracks = _deduplicate_tracks_by_sha256(song_paths)
    _validate_bpm_bounds(minimum_bpm, maximum_bpm)
    if int(analysis_workers) <= 0:
        raise ValueError("analysis_workers must be greater than 0")
    transition_lengths_bars = _normalise_transition_lengths(transition_lengths_bars)
    ranking_method = _validate_ranking_method(ranking_method)
    learned_ranker = None
    if ranking_method == "learned_cue_ranker_v1":
        # Fail before creating the output root: a missing/corrupt checkpoint
        # must never turn into a set of per-pair silent fallbacks.
        learned_ranker = load_learned_cue_ranker(
            cue_ranker_run,
            dataset_manifest_path=cue_ranker_dataset,
        )

    output_directory = Path(output_directory)
    _preflight_output_directory(output_directory)

    cache_path = (
        Path("output") / "pre_analysis"
        if analysis_location is None
        else Path(analysis_location)
    )
    analysis = PreAnalysis(str(cache_path) + os.sep)
    song_paths, bpm_excluded_tracks, bpm_analysis_failures = _filter_tracks_by_bpm(
        song_paths,
        analysis,
        minimum_bpm=minimum_bpm,
        maximum_bpm=maximum_bpm,
        workers=int(analysis_workers),
        analysis_location=cache_path,
    )
    _validate_request(song_paths, top_targets, top_transitions, renderers)
    candidate_config = _candidate_generation_config(
        transition_lengths_bars,
        approximate_grid_policy=approximate_grid_policy,
        ranking_method=ranking_method,
    )
    candidate_request_config = _candidate_request_config(candidate_config)
    output_directory.mkdir(parents=True, exist_ok=True)
    manifest_path = output_directory / "manifest.json"
    manifest = {
        "format_version": MULTI_BATCH_MANIFEST_FORMAT_VERSION,
        "songs": list(song_paths),
        "excluded_tracks": list(excluded_tracks),
        "duplicate_tracks": duplicate_tracks,
        "bpm_filter": {
            "minimum_bpm": None if minimum_bpm is None else float(minimum_bpm),
            "maximum_bpm": None if maximum_bpm is None else float(maximum_bpm),
            "bounds_inclusive": True,
            "excluded_tracks": bpm_excluded_tracks,
            "analysis_failures": bpm_analysis_failures,
            "analysis_workers": int(analysis_workers),
        },
        "track_exclusions_path": str(track_exclusions_path),
        "top_targets_per_source": int(top_targets),
        "top_transitions_per_pair": int(top_transitions),
        "renderers": list(renderers),
        "ranking_method": ranking_method,
        "cue_ranker_run": (
            None if learned_ranker is None else learned_ranker.provenance
        ),
        "target_sample_rate": int(target_sample_rate),
        "approximate_grid_policy": approximate_grid_policy,
        "transition_lengths_bars": list(transition_lengths_bars),
        "candidate_request_config": candidate_request_config,
        "candidate_request_config_sha256": _canonical_json_sha256(candidate_request_config),
        "sources": [],
        "failures": [],
    }
    compatibility_feature_cache = {}

    for source_index, source_song in enumerate(song_paths, start=1):
        source_entry = {
            "source_path": source_song,
            "source_audio_sha256": _file_sha256(source_song),
            "status": "running",
            "pairs": [],
        }
        manifest["sources"].append(source_entry)
        try:
            target_songs = tuple(song for song in song_paths if song != source_song)
            song_ranking = rank_song_targets(
                source_song,
                target_songs,
                analysis=analysis,
                target_sample_rate=target_sample_rate,
                feature_cache=compatibility_feature_cache,
            )
            selected_scores = song_ranking.scores[: int(top_targets)]
            source_entry["song_ranking"] = song_ranking.to_dict()
            source_entry["selected_target_paths"] = [
                score.target_path for score in selected_scores
            ]

            for score in selected_scores:
                pair_directory = output_directory / "pairs" / _pair_directory_name(
                    source_index,
                    source_song,
                    score.rank,
                    score.target_path,
                )
                pair_entry = {
                    "target_path": score.target_path,
                    "source_audio_sha256": source_entry["source_audio_sha256"],
                    "target_audio_sha256": _file_sha256(score.target_path),
                    "target_rank": score.rank,
                    "target_score": score.total_score,
                    "candidate_generator": _candidate_generator_name(candidate_config),
                    "candidate_request_config": candidate_request_config,
                    "candidate_request_config_sha256": _canonical_json_sha256(candidate_request_config),
                    "output_directory": str(pair_directory.relative_to(output_directory)),
                    "status": "running",
                }
                source_entry["pairs"].append(pair_entry)
                _write_manifest_atomic(manifest_path, manifest)
                try:
                    result = generate_and_render_batch(
                        source_song,
                        score.target_path,
                        pair_directory,
                        renderers=renderers,
                        target_sample_rate=target_sample_rate,
                        analysis=analysis,
                        candidate_config=candidate_config,
                        top_k=top_transitions,
                        ranking_method=ranking_method,
                        cue_ranker=learned_ranker,
                        cue_ranker_run=cue_ranker_run,
                        cue_ranker_dataset=cue_ranker_dataset,
                        cue_ranker_feature_cache_root=cue_ranker_feature_cache_root,
                        cue_ranker_analysis_root=str(cache_path),
                        cue_ranker_vocal_backend=cue_ranker_vocal_backend,
                    )
                    pair_entry.update(
                        {
                            "status": "completed",
                            "manifest_path": str(
                                result.manifest_path.relative_to(output_directory)
                            ),
                            "pair_manifest_path": str(
                                result.manifest_path.relative_to(output_directory)
                            ),
                            "pair_manifest_sha256": _file_sha256(result.manifest_path),
                            "candidate_count": len(result.candidate_generation.candidates),
                            "ranked_candidate_count": len(result.candidate_ranking.scores),
                            "rendered_variant_count": len(result.rendered_variants),
                            "render_failure_count": len(result.failures),
                            "transition_metric_failure_count": len(
                                result.rendered_transition_ranking.failures
                            ),
                        }
                    )
                except Exception as error:  # Continue the independent song pairs.
                    failure = _failure("pair", source_song, score.target_path, error)
                    pair_entry.update({"status": "failed", "failure": failure})
                    manifest["failures"].append(failure)
                _write_manifest_atomic(manifest_path, manifest)
            source_entry["status"] = "completed"
        except Exception as error:  # Continue with the next independent source song.
            failure = _failure("source", source_song, None, error)
            source_entry.update({"status": "failed", "failure": failure})
            manifest["failures"].append(failure)
        _write_manifest_atomic(manifest_path, manifest)

    return manifest_path


def _validate_request(song_paths, top_targets, top_transitions, renderers):
    if len(song_paths) < 2:
        raise ValueError("At least two songs are required")
    if len(set(song_paths)) != len(song_paths):
        raise ValueError("Songs must not contain duplicates")
    if int(top_targets) <= 0:
        raise ValueError("top_targets must be greater than 0")
    if int(top_transitions) <= 0:
        raise ValueError("top_transitions must be greater than 0")
    if not renderers:
        raise ValueError("At least one renderer must be requested")
    unknown_renderers = set(renderers).difference(DEFAULT_RENDERERS)
    if unknown_renderers:
        raise ValueError(f"Unknown renderer(s): {', '.join(sorted(unknown_renderers))}")


def _normalise_transition_lengths(transition_lengths_bars):
    """Validate requested lengths through the additive variable-length contract."""
    variable_config = VariableCandidateGenerationConfig(
        transition_lengths_bars=tuple(transition_lengths_bars),
    )
    return variable_config.transition_lengths_bars


def _candidate_generation_config(
    transition_lengths_bars,
    *,
    approximate_grid_policy,
    ranking_method="feature_baseline_v3",
):
    """Keep the historical v1 default while enabling v2 lengths additively."""
    if (
        tuple(transition_lengths_bars) == DEFAULT_TRANSITION_LENGTHS_BARS
        and ranking_method == "feature_baseline_v3"
    ):
        return CandidateGenerationConfig(
            transition_lengths_bars=tuple(transition_lengths_bars),
            approximate_grid_policy=approximate_grid_policy,
        )
    return VariableCandidateGenerationConfig(
        transition_lengths_bars=tuple(transition_lengths_bars),
        approximate_grid_policy=approximate_grid_policy,
    )


def _candidate_generator_name(candidate_config):
    return (
        "bar_grid_v2_length_specific"
        if int(getattr(candidate_config, "format_version", 1)) == 2
        else "bar_grid_v1"
    )


def _candidate_request_config(candidate_config):
    return {
        "format_version": int(getattr(candidate_config, "format_version", 1)),
        "candidate_generator": _candidate_generator_name(candidate_config),
        "transition_lengths_bars": [int(value) for value in candidate_config.transition_lengths_bars],
        "source_boundary_count": getattr(candidate_config, "source_boundary_count", None),
        "target_boundary_count": getattr(candidate_config, "target_boundary_count", None),
        "max_tempo_relative_difference": float(candidate_config.max_tempo_relative_difference),
        "approximate_grid_policy": str(candidate_config.approximate_grid_policy),
    }


def _canonical_json_sha256(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _validate_ranking_method(ranking_method):
    ranking_method = str(ranking_method)
    if ranking_method not in RANKING_METHODS:
        raise ValueError(
            f"Unknown ranking method {ranking_method!r}; choose one of {', '.join(RANKING_METHODS)}"
        )
    return ranking_method


def _expand_song_paths(songs):
    expanded_paths = []
    for song in songs:
        song_path = Path(song)
        if song_path.is_dir():
            expanded_paths.extend(
                str(path)
                for path in sorted(song_path.rglob("*"))
                if path.is_file() and path.suffix.lower() in AUDIO_EXTENSIONS
            )
            continue
        matches = sorted(glob.glob(str(song)))
        expanded_paths.extend(matches if matches else (song,))
    return tuple(str(Path(song)) for song in expanded_paths)


def _deduplicate_tracks_by_sha256(song_paths):
    unique = []
    duplicates = []
    first_path_by_hash = {}
    for song_path in song_paths:
        digest = _file_sha256(song_path)
        first_path = first_path_by_hash.get(digest)
        if first_path is None:
            first_path_by_hash[digest] = str(song_path)
            unique.append(song_path)
        else:
            duplicates.append(
                {
                    "path": str(song_path),
                    "sha256": digest,
                    "same_audio_as": first_path,
                }
            )
    return tuple(unique), duplicates


def _file_sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _validate_bpm_bounds(minimum_bpm, maximum_bpm):
    for name, value in (("minimum_bpm", minimum_bpm), ("maximum_bpm", maximum_bpm)):
        if value is not None and (not math.isfinite(float(value)) or float(value) <= 0):
            raise ValueError(f"{name} must be finite and greater than 0")
    if (
        minimum_bpm is not None
        and maximum_bpm is not None
        and float(minimum_bpm) > float(maximum_bpm)
    ):
        raise ValueError("minimum_bpm must be less than or equal to maximum_bpm")


def _filter_tracks_by_bpm(
    song_paths,
    analysis,
    *,
    minimum_bpm=None,
    maximum_bpm=None,
    workers=1,
    analysis_location=None,
):
    included = []
    excluded = []
    failures = []
    if int(workers) <= 1:
        analysed = [(song_path, _analyse_bpm(analysis, song_path)) for song_path in song_paths]
    else:
        if analysis_location is None:
            raise ValueError("analysis_location is required with multiple analysis workers")

        def analyse_independently(song_path):
            worker_analysis = PreAnalysis(str(Path(analysis_location)) + os.sep)
            return song_path, _analyse_bpm(worker_analysis, song_path)

        with ThreadPoolExecutor(max_workers=int(workers)) as executor:
            analysed = list(executor.map(analyse_independently, song_paths))

    for song_path, result in analysed:
        if isinstance(result, Exception):
            failures.append(
                {
                    "path": str(song_path),
                    "error_type": type(result).__name__,
                    "message": str(result),
                }
            )
            continue
        bpm = result
        reason = None
        if minimum_bpm is not None and bpm < float(minimum_bpm):
            reason = "below_minimum_bpm"
        elif maximum_bpm is not None and bpm > float(maximum_bpm):
            reason = "above_maximum_bpm"
        if reason is None:
            included.append(song_path)
        else:
            excluded.append({"path": str(song_path), "bpm": bpm, "reason": reason})
    return tuple(included), excluded, failures


def _analyse_bpm(analysis, song_path):
    try:
        bpm, _ = analysis(song_path)
        bpm = float(bpm)
        if not math.isfinite(bpm) or bpm <= 0:
            raise ValueError("analysed BPM must be finite and greater than 0")
        return bpm
    except Exception as error:
        return error


def _preflight_output_directory(output_directory):
    if output_directory.exists() and any(output_directory.iterdir()):
        raise FileExistsError(
            "Multi-batch output already exists. Choose a new empty output directory: "
            f"{output_directory}"
        )


def _pair_directory_name(source_index, source_song, target_rank, target_song):
    return (
        f"{source_index:02d}__{_safe_name(source_song)}"
        f"__target-{target_rank:02d}__{_safe_name(target_song)}"
    )


def _safe_name(song_path):
    stem = Path(song_path).stem
    return re.sub(r"[^A-Za-z0-9]+", "_", stem).strip("_")[:80] or "track"


def _failure(stage, source_path, target_path, error):
    return {
        "stage": stage,
        "source_path": source_path,
        "target_path": target_path,
        "error_type": type(error).__name__,
        "message": str(error),
    }


def _write_manifest_atomic(path, payload):
    temporary_path = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        temporary_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)


def build_argument_parser():
    parser = argparse.ArgumentParser(
        description="For every source track, render top transitions to its best target tracks.",
    )
    parser.add_argument("songs", nargs="+", help="Source and target tracks; every track is a source.")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument(
        "--ranking-method",
        choices=RANKING_METHODS,
        default="feature_baseline_v3",
        help="Candidate selection method (default: feature_baseline_v3).",
    )
    parser.add_argument(
        "--cue-ranker-run",
        help="Completed learned_cue_ranker_v1 run directory or best checkpoint.",
    )
    parser.add_argument(
        "--cue-ranker-dataset",
        help="SHA-bound Cue-Ranker Dataset-3 manifest required for learned inference.",
    )
    parser.add_argument("--cue-ranker-feature-cache-root", default="output/feature_cache")
    parser.add_argument(
        "--cue-ranker-vocal-backend",
        choices=("disabled", "demucs", "roformer"),
        default="disabled",
    )
    parser.add_argument("--top-targets", type=int, default=3)
    parser.add_argument("--top-transitions", type=int, default=3)
    parser.add_argument(
        "--renderers",
        nargs="+",
        choices=DEFAULT_RENDERERS,
        default=("equal_power",),
    )
    parser.add_argument("--target-sample-rate", type=int, default=44_100)
    parser.add_argument("--analysis-location")
    parser.add_argument("--min-bpm", type=float)
    parser.add_argument("--max-bpm", type=float)
    parser.add_argument("--analysis-workers", type=int, default=1)
    parser.add_argument(
        "--transition-bars",
        nargs="+",
        type=int,
        choices=(2, 4, 6, 8),
        default=DEFAULT_TRANSITION_LENGTHS_BARS,
        help="Candidate transition lengths in bars (default: 2 4).",
    )
    parser.add_argument(
        "--approximate-grid-policy",
        choices=("reject", "allow"),
        default="reject",
    )
    parser.add_argument(
        "--track-exclusions",
        default=str(DEFAULT_TRACK_EXCLUSIONS_PATH),
    )
    return parser


def _recorded_failure_count(manifest):
    failure_count = len(manifest.get("failures", ())) + len(
        manifest.get("bpm_filter", {}).get("analysis_failures", ())
    )
    for source in manifest.get("sources", ()):
        for pair in source.get("pairs", ()):
            failure_count += int(pair.get("render_failure_count", 0))
            failure_count += int(pair.get("transition_metric_failure_count", 0))
    return failure_count


def main(argv=None):
    args = build_argument_parser().parse_args(argv)
    try:
        manifest_path = generate_multi_song_batch(
            args.songs,
            args.output_dir,
            top_targets=args.top_targets,
            top_transitions=args.top_transitions,
            renderers=tuple(args.renderers),
            target_sample_rate=args.target_sample_rate,
            analysis_location=args.analysis_location,
            track_exclusions_path=args.track_exclusions,
            minimum_bpm=args.min_bpm,
            maximum_bpm=args.max_bpm,
            analysis_workers=args.analysis_workers,
            approximate_grid_policy=args.approximate_grid_policy,
            transition_lengths_bars=tuple(args.transition_bars),
            ranking_method=args.ranking_method,
            cue_ranker_run=args.cue_ranker_run,
            cue_ranker_dataset=args.cue_ranker_dataset,
            cue_ranker_feature_cache_root=args.cue_ranker_feature_cache_root,
            cue_ranker_vocal_backend=args.cue_ranker_vocal_backend,
        )
    except (FileNotFoundError, ValueError) as error:
        if args.ranking_method != "learned_cue_ranker_v1":
            raise
        print(
            f"learned_cue_ranker_v1 preflight failed: {type(error).__name__}: {error}",
            file=sys.stderr,
        )
        return 1
    print(manifest_path)
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    failure_count = _recorded_failure_count(manifest)
    if failure_count:
        print(
            f"Multi-batch completed with {failure_count} recorded failure(s); "
            f"see {manifest_path}",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
