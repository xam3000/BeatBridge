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
    return parser


def main():
    args = build_argument_parser().parse_args()
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
