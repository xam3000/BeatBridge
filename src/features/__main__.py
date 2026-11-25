"""Inspect the schema or populate a reusable full-track feature cache."""

import argparse
import json

from .contract import feature_schema
from .vocal import DEFAULT_ROFORMER_MODEL, DEFAULT_VOCAL_BACKEND


def build_argument_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser("schema", help="Print the active feature schema.")
    cache_parser = subparsers.add_parser(
        "cache-track",
        help="Extract or reuse one full-track feature cache.",
    )
    cache_parser.add_argument("song")
    cache_parser.add_argument("--cache-root", default="output/feature_cache")
    cache_parser.add_argument("--analysis-root", default="output/pre_analysis")
    cache_parser.add_argument("--sample-rate", type=int, default=44_100)
    cache_parser.add_argument("--target-bpm", type=float)
    cache_parser.add_argument(
        "--vocal-backend",
        choices=("disabled", "demucs", "roformer"),
        default=DEFAULT_VOCAL_BACKEND,
    )
    cache_parser.add_argument("--vocal-model", default=DEFAULT_ROFORMER_MODEL)
    export_parser = subparsers.add_parser(
        "export-dataset",
        help="Export four-bar feature examples with track-disjoint splits.",
    )
    export_parser.add_argument("source_manifest")
    export_parser.add_argument("output_directory")
    export_parser.add_argument("--cache-root", default="output/feature_cache")
    export_parser.add_argument("--analysis-root", default="output/pre_analysis")
    export_parser.add_argument("--sample-rate", type=int, default=44_100)
    export_parser.add_argument("--top-k-per-pair", type=int, default=3)
    export_parser.add_argument("--transition-bars", type=int, default=4)
    export_parser.add_argument("--train-ratio", type=float, default=0.70)
    export_parser.add_argument("--validation-ratio", type=float, default=0.15)
    export_parser.add_argument("--test-ratio", type=float, default=0.15)
    export_parser.add_argument("--split-seed", type=int, default=20260731)
    export_parser.add_argument("--split-search-attempts", type=int, default=4096)
    export_parser.add_argument("--max-pairs", type=int)
    export_parser.add_argument("--min-bpm", type=float)
    export_parser.add_argument("--max-bpm", type=float)
    export_parser.add_argument(
        "--vocal-backend",
        choices=("disabled", "demucs", "roformer"),
        default=DEFAULT_VOCAL_BACKEND,
    )
    export_parser.add_argument("--vocal-model", default=DEFAULT_ROFORMER_MODEL)
    export_parser.add_argument(
        "--track-exclusions",
        default="config/track_exclusions.json",
    )
    variable_parser = subparsers.add_parser(
        "export-dataset-v2",
        help="Export homogeneous variable-length Feature Protocol 2 shards.",
    )
    variable_parser.add_argument("source_manifest")
    variable_parser.add_argument("output_directory")
    variable_parser.add_argument("--cache-root", default="output/feature_cache")
    variable_parser.add_argument("--analysis-root", default="output/pre_analysis")
    variable_parser.add_argument("--sample-rate", type=int, default=44_100)
    variable_parser.add_argument("--top-k-per-pair", type=int, default=3)
    variable_parser.add_argument("--transition-bars", nargs="+", type=int, default=(2, 4, 6, 8))
    variable_parser.add_argument("--split-map")
    variable_parser.add_argument("--train-ratio", type=float, default=0.70)
    variable_parser.add_argument("--validation-ratio", type=float, default=0.15)
    variable_parser.add_argument("--test-ratio", type=float, default=0.15)
    variable_parser.add_argument("--split-seed", type=int, default=20260731)
    variable_parser.add_argument("--split-search-attempts", type=int, default=4096)
    variable_parser.add_argument("--max-pairs", type=int)
    variable_parser.add_argument("--min-bpm", type=float)
    variable_parser.add_argument("--max-bpm", type=float)
    variable_parser.add_argument(
        "--vocal-backend",
        choices=("disabled", "demucs", "roformer"),
        default=DEFAULT_VOCAL_BACKEND,
    )
    variable_parser.add_argument("--vocal-model", default=DEFAULT_ROFORMER_MODEL)
    variable_parser.add_argument("--track-exclusions", default="config/track_exclusions.json")
    cue_universe_parser = subparsers.add_parser(
        "build-cue-ranker-universe",
        help="Build a sealed Candidate-v2 universe for the retired proxy cue ranker.",
    )
    cue_universe_parser.add_argument("pair_index")
    cue_universe_parser.add_argument("output_directory")
    cue_universe_parser.add_argument("--split-map", required=True)
    cue_universe_parser.add_argument("--sampling-seed", type=int, default=20260825)
    cue_pair_index_parser = subparsers.add_parser(
        "build-cue-ranker-pair-index",
        help="Build a sealed pair index for the retired proxy cue ranker.",
    )
    cue_pair_index_parser.add_argument(
        "source_manifest",
        help="Batch manifest containing complete producer-recorded pair provenance.",
    )
    cue_pair_index_parser.add_argument(
        "output_path",
        help="New pair_index.json path; existing files are never overwritten.",
    )
    cue_pair_index_parser.add_argument("--split-map", required=True)
    cue_pair_index_parser.add_argument(
        "--dataset-manifest",
        help="Optional Dataset-v2 manifest whose source-manifest SHA is also bound.",
    )
    cue_dataset_parser = subparsers.add_parser(
        "export-cue-ranker-dataset",
        help="Publish a historical Dataset-3 for the retired proxy cue ranker.",
    )
    cue_dataset_parser.add_argument("universe_directory")
    cue_dataset_parser.add_argument("label_directory")
    cue_dataset_parser.add_argument("output_directory")
    cue_dataset_parser.add_argument("--train-only-normalizer", required=True)
    return parser


def main(argv=None):
    args = build_argument_parser().parse_args(argv)
    if args.command in {None, "schema"}:
        print(json.dumps(feature_schema(), ensure_ascii=False, indent=2))
        return 0

    if args.command == "export-dataset":
        from .dataset_export import SplitConfig, export_feature_dataset

        result = export_feature_dataset(
            args.source_manifest,
            args.output_directory,
            cache_root=args.cache_root,
            analysis_root=args.analysis_root,
            sample_rate=args.sample_rate,
            top_k_per_pair=args.top_k_per_pair,
            transition_bars=args.transition_bars,
            split_config=SplitConfig(
                train=args.train_ratio,
                validation=args.validation_ratio,
                test=args.test_ratio,
                seed=args.split_seed,
                search_attempts=args.split_search_attempts,
            ),
            vocal_backend=args.vocal_backend,
            vocal_model=args.vocal_model,
            track_exclusions_path=args.track_exclusions,
            minimum_bpm=args.min_bpm,
            maximum_bpm=args.max_bpm,
            max_pairs=args.max_pairs,
        )
        print(
            json.dumps(
                {
                    "output_directory": str(result.output_directory),
                    "manifest_path": str(result.manifest_path),
                    "example_count": result.example_count,
                    "split_counts": result.split_counts,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    if args.command == "export-dataset-v2":
        from .dataset_export import SplitConfig
        from .variable_dataset_export import export_variable_feature_dataset

        result = export_variable_feature_dataset(
            args.source_manifest,
            args.output_directory,
            cache_root=args.cache_root,
            analysis_root=args.analysis_root,
            sample_rate=args.sample_rate,
            top_k_per_pair=args.top_k_per_pair,
            transition_lengths_bars=tuple(args.transition_bars),
            split_map_path=args.split_map,
            split_config=SplitConfig(
                train=args.train_ratio,
                validation=args.validation_ratio,
                test=args.test_ratio,
                seed=args.split_seed,
                search_attempts=args.split_search_attempts,
            ),
            vocal_backend=args.vocal_backend,
            vocal_model=args.vocal_model,
            track_exclusions_path=args.track_exclusions,
            minimum_bpm=args.min_bpm,
            maximum_bpm=args.max_bpm,
            max_pairs=args.max_pairs,
        )
        print(json.dumps({
            "output_directory": str(result.output_directory),
            "manifest_path": str(result.manifest_path),
            "example_count": result.example_count,
            "split_counts": result.split_counts,
        }, ensure_ascii=False, indent=2))
        return 0

    if args.command == "build-cue-ranker-universe":
        from .cue_ranker_universe import build_cue_ranker_universe
        result = build_cue_ranker_universe(
            args.pair_index,
            args.output_directory,
            split_map=args.split_map,
            sampling_seed=args.sampling_seed,
        )
        print(json.dumps({"output_directory": str(result.output_directory), "group_counts": result.group_counts, "candidate_counts": result.candidate_counts}, ensure_ascii=False, indent=2))
        return 0

    if args.command == "build-cue-ranker-pair-index":
        from .cue_ranker_universe import build_cue_ranker_pair_index

        output_path = build_cue_ranker_pair_index(
            args.source_manifest,
            args.output_path,
            split_map=args.split_map,
            dataset_manifest=args.dataset_manifest,
        )
        print(json.dumps({"pair_index_path": str(output_path)}, ensure_ascii=False, indent=2))
        return 0

    if args.command == "export-cue-ranker-dataset":
        from .cue_ranker_dataset import export_cue_ranker_dataset
        result = export_cue_ranker_dataset(
            args.universe_directory,
            args.label_directory,
            args.output_directory,
            train_only_normalizer=args.train_only_normalizer,
        )
        print(json.dumps({"output_directory": str(result.output_directory), "group_counts": result.group_counts, "candidate_counts": result.candidate_counts}, ensure_ascii=False, indent=2))
        return 0

    from .extract_track import extract_or_load_track_features

    artifact = extract_or_load_track_features(
        args.song,
        cache_root=args.cache_root,
        analysis_root=args.analysis_root,
        sample_rate=args.sample_rate,
        target_bpm=args.target_bpm,
        vocal_backend=args.vocal_backend,
        vocal_model=args.vocal_model,
    )
    print(
        json.dumps(
            {
                "cache_hit": artifact.cache_hit,
                "cache_directory": str(artifact.cache_directory),
                "bin_count": artifact.bin_count,
                "feature_dimension": int(artifact.base_features.shape[-1]),
                "tempo_backend": artifact.manifest["tempo_backend"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
