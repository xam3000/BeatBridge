"""Split-aware, candidate-only multi-song producer for Dataset Format 2."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import glob
import hashlib
import json
import os
from pathlib import Path
import re
import uuid

from src.analysis.pre_analysis import PartialPreAnalysis
from src.candidates.variable import VariableCandidateGenerationConfig
from src.dataset import DEFAULT_TRACK_EXCLUSIONS_PATH, filter_excluded_tracks, load_track_exclusions
from src.features.variable_split import load_variable_split_authority
from src.pipeline import generate_transition_candidates
from src.ranking.feature_baseline import rank_candidates
from src.ranking.song_compatibility import rank_song_targets


VARIABLE_PRODUCER_FORMAT_VERSION = 1
AUDIO_EXTENSIONS = {".flac", ".mp3", ".ogg", ".wav"}


def generate_variable_candidate_producer(
    songs,
    output_directory,
    *,
    split_map,
    top_targets=1,
    top_candidates_per_length=3,
    transition_lengths_bars=(2, 4, 6, 8),
    target_sample_rate=44_100,
    analysis_location="output/pre_analysis",
    track_exclusions_path=DEFAULT_TRACK_EXCLUSIONS_PATH,
    minimum_bpm=None,
    maximum_bpm=None,
    corpus_manifest_path=None,
    analysis_workers=1,
    source_workers=1,
):
    """Write compact Candidate-v2 manifests without rendering any audio."""

    output_directory = Path(output_directory)
    if output_directory.exists() and any(output_directory.iterdir()):
        raise FileExistsError(f"Producer output must be new or empty: {output_directory}")
    if int(top_targets) < 1 or int(top_candidates_per_length) < 1:
        raise ValueError("top_targets and top_candidates_per_length must be positive")
    lengths = VariableCandidateGenerationConfig(
        transition_lengths_bars=tuple(transition_lengths_bars),
        approximate_grid_policy="reject",
    ).transition_lengths_bars
    paths = _expand_song_paths(songs)
    exclusions = load_track_exclusions(track_exclusions_path)
    paths, excluded = filter_excluded_tracks(paths, scope="multi_batch", exclusions=exclusions)
    authority_probe = load_variable_split_authority(split_map, ())
    closed_split_exclusions = []
    if corpus_manifest_path is not None:
        corpus_payload = json.loads(Path(corpus_manifest_path).read_text(encoding="utf-8"))
        manifest_hashes = {
            os.path.normcase(os.path.abspath(str(row["path"]))): str(row["sha256"]).lower()
            for row in corpus_payload.get("tracks", ())
        }
        eligible_paths = []
        for path in paths:
            key = os.path.normcase(os.path.abspath(path))
            audio_sha = manifest_hashes.get(key)
            if audio_sha is None:
                raise ValueError(
                    "Closed-test production requires every input path to be declared "
                    "in the corpus manifest; refusing to inspect undeclared audio"
                )
            split = authority_probe.assignments.get(audio_sha)
            if split == "test":
                closed_split_exclusions.append(
                    {"path": path, "sha256": audio_sha, "split": split, "reason": "closed_split"}
                )
            elif split is None:
                raise ValueError(f"Corpus manifest audio SHA is absent from split authority: {audio_sha}")
            else:
                eligible_paths.append(path)
        paths = tuple(eligible_paths)
    elif any(split == "test" for split in authority_probe.assignments.values()):
        raise ValueError(
            "A corpus manifest is required to exclude the closed test split before audio hashing"
        )

    paths, duplicates, hashes = _deduplicate(paths)
    if corpus_manifest_path is not None:
        for path, audio_sha in hashes.items():
            key = os.path.normcase(os.path.abspath(path))
            if manifest_hashes[key] != audio_sha:
                raise ValueError(f"Corpus manifest audio SHA differs from input file: {path}")
    authority = load_variable_split_authority(split_map, hashes.values())
    analysis = PartialPreAnalysis(str(Path(analysis_location)) + os.sep)
    if int(analysis_workers) < 1:
        raise ValueError("analysis_workers must be greater than 0")
    if int(source_workers) < 1:
        raise ValueError("source_workers must be greater than 0")
    paths, bpm_excluded, analysis_failures = _filter_bpm(
        paths,
        analysis,
        minimum_bpm=minimum_bpm,
        maximum_bpm=maximum_bpm,
        workers=int(analysis_workers),
        analysis_location=analysis_location,
    )
    if len(paths) < 2:
        raise ValueError("At least two eligible unique tracks are required")
    request_config = {
        "format_version": 1,
        "analysis_contract": "partial_merge_v2",
        "candidate_format_version": 2,
        "candidate_generator": "bar_grid_v2_length_specific",
        "approximate_grid_policy": "reject",
        "feature_ranker": "feature_baseline_v3",
        "transition_lengths_bars": list(lengths),
        "top_targets_per_source": int(top_targets),
        "top_candidates_per_pair_and_length": int(top_candidates_per_length),
        "target_sample_rate": int(target_sample_rate),
        "minimum_bpm": minimum_bpm,
        "maximum_bpm": maximum_bpm,
        "analysis_workers": int(analysis_workers),
        "source_workers": int(source_workers),
        "closed_split_names": ["test"],
    }
    request_sha256 = _canonical_json_sha256(request_config)
    output_directory.mkdir(parents=True, exist_ok=True)
    root_path = output_directory / "manifest.json"
    root = {
        "format_version": VARIABLE_PRODUCER_FORMAT_VERSION,
        "producer": "split_aware_candidate_only_variable_v1",
        "candidate_format_version": 2,
        "feature_ranking": "feature_baseline_v3",
        "analysis_contract": "partial_merge_v2",
        "renderers": [],
        "audio_materialized": False,
        "split_authority_path": str(Path(split_map).resolve()),
        "split_authority_file_sha256": _file_sha256(split_map),
        "split_mapping_sha256": authority.mapping_sha256,
        "corpus_manifest_path": None if corpus_manifest_path is None else str(Path(corpus_manifest_path).resolve()),
        "corpus_manifest_sha256": None if corpus_manifest_path is None else _file_sha256(corpus_manifest_path),
        "transition_lengths_bars": list(lengths),
        "top_targets_per_source": int(top_targets),
        "top_candidates_per_pair_and_length": int(top_candidates_per_length),
        "target_sample_rate": int(target_sample_rate),
        "producer_request_config": request_config,
        "producer_request_config_sha256": request_sha256,
        "track_exclusions_path": str(track_exclusions_path),
        "excluded_tracks": list(excluded),
        "closed_split_exclusions": closed_split_exclusions,
        "duplicate_tracks": duplicates,
        "bpm_filter": {
            "minimum_bpm": minimum_bpm,
            "maximum_bpm": maximum_bpm,
            "excluded_tracks": bpm_excluded,
            "analysis_failures": analysis_failures,
        },
        "sources": [],
        "failures": [],
        "status": "running",
    }
    root["sources"] = [
        {
            "source_path": source,
            "source_audio_sha256": hashes[source],
            "split": authority.assignments[hashes[source]],
            "status": "running",
            "pairs": [],
        }
        for source in paths
    ]
    _write_json_atomic(root_path, root, overwrite=True)
    compatibility_cache = {}

    def produce(item):
        source_index, source = item
        worker_analysis = (
            analysis
            if int(source_workers) == 1
            else PartialPreAnalysis(str(Path(analysis_location)) + os.sep)
        )
        return _produce_source_row(
            source_index,
            source,
            paths=paths,
            hashes=hashes,
            authority=authority,
            analysis=worker_analysis,
            compatibility_cache=compatibility_cache,
            output_directory=output_directory,
            lengths=lengths,
            top_targets=top_targets,
            top_candidates_per_length=top_candidates_per_length,
            target_sample_rate=target_sample_rate,
            request_config=request_config,
            request_sha256=request_sha256,
        )

    items = tuple(enumerate(paths, start=1))
    if int(source_workers) == 1:
        results = map(produce, items)
        executor = None
    else:
        executor = ThreadPoolExecutor(max_workers=int(source_workers))
        results = executor.map(produce, items)
    try:
        for source_index, (source_row, failure) in enumerate(results, start=1):
            root["sources"][source_index - 1] = source_row
            if failure is not None:
                root["failures"].append(failure)
            _write_json_atomic(root_path, root, overwrite=True)
    finally:
        if executor is not None:
            executor.shutdown(wait=True, cancel_futures=False)
    root["status"] = (
        "completed"
        if not root["failures"] and all(source.get("status") == "completed" for source in root["sources"])
        else "completed_with_failures"
    )
    _write_json_atomic(root_path, root, overwrite=True)
    return root_path


def _produce_source_row(
    source_index,
    source,
    *,
    paths,
    hashes,
    authority,
    analysis,
    compatibility_cache,
    output_directory,
    lengths,
    top_targets,
    top_candidates_per_length,
    target_sample_rate,
    request_config,
    request_sha256,
):
        source_sha = hashes[source]
        split = authority.assignments[source_sha]
        source_row = {
            "source_path": source,
            "source_audio_sha256": source_sha,
            "split": split,
            "status": "running",
            "pairs": [],
        }
        try:
            targets = tuple(
                path for path in paths
                if path != source and authority.assignments[hashes[path]] == split
            )
            if not targets:
                source_row.update({"status": "completed", "song_ranking": None})
                return source_row, None
            song_ranking = rank_song_targets(
                source,
                targets,
                analysis=analysis,
                target_sample_rate=target_sample_rate,
                feature_cache=compatibility_cache,
            )
            source_row["song_ranking"] = song_ranking.to_dict()
            for target_score in song_ranking.scores[: int(top_targets)]:
                target = target_score.target_path
                target_sha = hashes[target]
                pair_directory = output_directory / "pairs" / _pair_name(
                    source_index, source, target_score.rank, target
                )
                pair_directory.mkdir(parents=True, exist_ok=False)
                pair_manifest_path = pair_directory / "manifest.json"
                selected_candidates = []
                selected_scores = []
                rejections = []
                ranking_failures = []
                generated_counts = {}
                for length in lengths:
                    generation = generate_transition_candidates(
                        source,
                        target,
                        analysis=analysis,
                        target_sample_rate=target_sample_rate,
                        config=VariableCandidateGenerationConfig(
                            transition_lengths_bars=(length,),
                            approximate_grid_policy="reject",
                        ),
                    )
                    generated_counts[str(length)] = len(generation.candidates)
                    rejections.extend(item.to_dict() for item in generation.rejections)
                    ranking = rank_candidates(
                        generation.candidates,
                        target_sample_rate=target_sample_rate,
                    )
                    candidates_by_id = {
                        candidate.candidate_id: candidate for candidate in generation.candidates
                    }
                    top_scores = ranking.scores[: int(top_candidates_per_length)]
                    selected_scores.extend(score.to_dict() for score in top_scores)
                    selected_candidates.extend(
                        candidates_by_id[score.candidate_id].to_dict() for score in top_scores
                    )
                    ranking_failures.extend(item.to_dict() for item in ranking.failures)
                pair_payload = {
                    "format_version": 2,
                    "render_protocol_version": None,
                    "renderers": [],
                    "ranking_method": "feature_baseline_v3",
                    "source_audio_sha256": source_sha,
                    "target_audio_sha256": target_sha,
                    "split": split,
                    "producer_request_config": request_config,
                    "producer_request_config_sha256": request_sha256,
                    "candidate_generation": {
                        "format_version": 2,
                        "approximate_grid_policy": "reject",
                        "candidates": selected_candidates,
                        "rejections": rejections,
                        "generated_candidate_counts_by_length": generated_counts,
                        "storage_policy": "top_k_per_pair_and_length_only_v1",
                    },
                    "candidate_ranking": {
                        "format_version": 1,
                        "ranker": "feature_baseline_v3",
                        "scores": selected_scores,
                        "failures": ranking_failures,
                    },
                    "rendered_variants": [],
                    "failures": [],
                }
                _write_json_atomic(pair_manifest_path, pair_payload)
                source_row["pairs"].append({
                    "target_path": target,
                    "source_audio_sha256": source_sha,
                    "target_audio_sha256": target_sha,
                    "split": split,
                    "target_rank": int(target_score.rank),
                    "target_score": float(target_score.total_score),
                    "status": "completed",
                    "manifest_path": str(pair_manifest_path.relative_to(output_directory)),
                    "pair_manifest_sha256": _file_sha256(pair_manifest_path),
                    "selected_candidate_count": len(selected_candidates),
                    "generated_candidate_counts_by_length": generated_counts,
                    "ranking_failure_count": len(ranking_failures),
                })
            source_row["status"] = (
                "completed"
                if all(pair.get("ranking_failure_count", 0) == 0 for pair in source_row["pairs"])
                else "completed_with_failures"
            )
        except Exception as error:
            failure = {
                "stage": "source",
                "source_path": source,
                "error_type": type(error).__name__,
                "message": str(error),
            }
            source_row.update({"status": "failed", "failure": failure})
            return source_row, failure
        return source_row, None


def _expand_song_paths(songs):
    paths = []
    for value in songs:
        path = Path(value)
        if path.is_dir():
            paths.extend(str(item) for item in sorted(path.rglob("*")) if item.is_file() and item.suffix.lower() in AUDIO_EXTENSIONS)
        else:
            matches = sorted(glob.glob(str(value)))
            paths.extend(matches if matches else (str(path),))
    return tuple(paths)


def _deduplicate(paths):
    unique, duplicates, hashes, first = [], [], {}, {}
    for path in paths:
        digest = _file_sha256(path)
        if digest in first:
            duplicates.append({"path": path, "sha256": digest, "same_audio_as": first[digest]})
        else:
            first[digest] = path
            hashes[path] = digest
            unique.append(path)
    return tuple(unique), duplicates, hashes


def _filter_bpm(
    paths,
    analysis,
    *,
    minimum_bpm,
    maximum_bpm,
    workers=1,
    analysis_location=None,
):
    included, excluded, failures = [], [], []
    if int(workers) <= 1:
        analysed = [(path, _analyse_bpm(analysis, path)) for path in paths]
    else:
        if analysis_location is None:
            raise ValueError("analysis_location is required with multiple analysis workers")

        def analyse_independently(path):
            worker_analysis = PartialPreAnalysis(str(Path(analysis_location)) + os.sep)
            return path, _analyse_bpm(worker_analysis, path)

        with ThreadPoolExecutor(max_workers=int(workers)) as executor:
            analysed = list(executor.map(analyse_independently, paths))

    for path, result in analysed:
        if isinstance(result, Exception):
            failures.append(
                {"path": path, "error_type": type(result).__name__, "message": str(result)}
            )
            continue
        bpm = result
        reason = None
        if minimum_bpm is not None and bpm < float(minimum_bpm):
            reason = "below_minimum_bpm"
        elif maximum_bpm is not None and bpm > float(maximum_bpm):
            reason = "above_maximum_bpm"
        if reason:
            excluded.append({"path": path, "bpm": bpm, "reason": reason})
        else:
            included.append(path)
    return tuple(included), excluded, failures


def _analyse_bpm(analysis, path):
    try:
        bpm, _beats = analysis(path)
        bpm = float(bpm)
        if not (bpm > 0):
            raise ValueError("analysed BPM must be greater than 0")
        return bpm
    except Exception as error:
        return error


def _pair_name(source_index, source, target_rank, target):
    safe = lambda value: re.sub(r"[^A-Za-z0-9]+", "_", Path(value).stem).strip("_")[:60]
    return f"{source_index:04d}__{safe(source)}__target-{int(target_rank):02d}__{safe(target)}"


def _file_sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_json_sha256(value):
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _write_json_atomic(path, payload, *, overwrite=False):
    path = Path(path)
    if path.exists() and not overwrite:
        raise FileExistsError(f"Refusing to overwrite immutable artifact: {path}")
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def build_argument_parser():
    parser = argparse.ArgumentParser(description="Build compact split-aware Candidate-v2 pair manifests without rendering audio.")
    parser.add_argument("songs", nargs="*")
    parser.add_argument("--corpus-manifest")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--split-map", required=True)
    parser.add_argument("--analysis-location", required=True)
    parser.add_argument("--top-targets", type=int, default=1)
    parser.add_argument("--top-candidates-per-length", type=int, default=3)
    parser.add_argument("--transition-bars", nargs="+", type=int, default=(2, 4, 6, 8))
    parser.add_argument("--target-sample-rate", type=int, default=44_100)
    parser.add_argument("--min-bpm", type=float)
    parser.add_argument("--max-bpm", type=float)
    parser.add_argument("--analysis-workers", type=int, default=1)
    parser.add_argument("--source-workers", type=int, default=1)
    parser.add_argument("--track-exclusions", default=str(DEFAULT_TRACK_EXCLUSIONS_PATH))
    return parser


def main(argv=None):
    args = build_argument_parser().parse_args(argv)
    songs = tuple(args.songs)
    if args.corpus_manifest:
        payload = json.loads(Path(args.corpus_manifest).read_text(encoding="utf-8"))
        manifest_songs = tuple(str(row["path"]) for row in payload.get("tracks", ()))
        songs = songs + manifest_songs
    if not songs:
        raise ValueError("Supply songs or --corpus-manifest")
    result = generate_variable_candidate_producer(
        songs,
        args.output_dir,
        split_map=args.split_map,
        top_targets=args.top_targets,
        top_candidates_per_length=args.top_candidates_per_length,
        transition_lengths_bars=tuple(args.transition_bars),
        target_sample_rate=args.target_sample_rate,
        analysis_location=args.analysis_location,
        track_exclusions_path=args.track_exclusions,
        minimum_bpm=args.min_bpm,
        maximum_bpm=args.max_bpm,
        corpus_manifest_path=args.corpus_manifest,
        analysis_workers=args.analysis_workers,
        source_workers=args.source_workers,
    )
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
