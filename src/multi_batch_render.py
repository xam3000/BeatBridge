"""Render the best transition batches for the best target songs per source."""

import argparse
import glob
import json
import os
from pathlib import Path
import re
import uuid

from src.analysis.pre_analysis import PreAnalysis
from src.batch_render import DEFAULT_RENDERERS, generate_and_render_batch
from src.ranking.song_compatibility import rank_song_targets


MULTI_BATCH_MANIFEST_FORMAT_VERSION = 1


def generate_multi_song_batch(
    songs,
    output_directory,
    *,
    top_targets=3,
    top_transitions=3,
    renderers=("equal_power",),
    target_sample_rate=44_100,
    analysis_location=None,
):
    """Rank targets per source, then render the best transition candidates.

    Each selected song pair gets its own regular batch directory and manifest.
    The parent manifest records the song-level selection and keeps a stable
    index of all pair-level results.
    """
    song_paths = _expand_song_paths(songs)
    _validate_request(song_paths, top_targets, top_transitions, renderers)

    output_directory = Path(output_directory)
    _preflight_output_directory(output_directory)
    output_directory.mkdir(parents=True, exist_ok=True)

    cache_path = (
        Path("output") / "pre_analysis"
        if analysis_location is None
        else Path(analysis_location)
    )
    analysis = PreAnalysis(str(cache_path) + os.sep)
    manifest_path = output_directory / "manifest.json"
    manifest = {
        "format_version": MULTI_BATCH_MANIFEST_FORMAT_VERSION,
        "songs": list(song_paths),
        "top_targets_per_source": int(top_targets),
        "top_transitions_per_pair": int(top_transitions),
        "renderers": list(renderers),
        "target_sample_rate": int(target_sample_rate),
        "sources": [],
        "failures": [],
    }

    for source_index, source_song in enumerate(song_paths, start=1):
        source_entry = {"source_path": source_song, "status": "running", "pairs": []}
        manifest["sources"].append(source_entry)
        try:
            target_songs = tuple(song for song in song_paths if song != source_song)
            song_ranking = rank_song_targets(
                source_song,
                target_songs,
                analysis=analysis,
                target_sample_rate=target_sample_rate,
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
                    "target_rank": score.rank,
                    "target_score": score.total_score,
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
                        top_k=top_transitions,
                    )
                    pair_entry.update(
                        {
                            "status": "completed",
                            "manifest_path": str(
                                result.manifest_path.relative_to(output_directory)
                            ),
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


def _expand_song_paths(songs):
    expanded_paths = []
    for song in songs:
        matches = sorted(glob.glob(str(song)))
        expanded_paths.extend(matches if matches else (song,))
    return tuple(str(Path(song)) for song in expanded_paths)


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
    return parser


def main():
    args = build_argument_parser().parse_args()
    manifest_path = generate_multi_song_batch(
        args.songs,
        args.output_dir,
        top_targets=args.top_targets,
        top_transitions=args.top_transitions,
        renderers=tuple(args.renderers),
        target_sample_rate=args.target_sample_rate,
        analysis_location=args.analysis_location,
    )
    print(manifest_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
