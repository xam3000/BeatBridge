"""Inspect the schema or populate a reusable full-track feature cache."""

import argparse
import json

from .contract import feature_schema


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
        choices=("disabled", "demucs"),
        default="demucs",
    )
    cache_parser.add_argument("--vocal-model", default="htdemucs")
    return parser


def main():
    args = build_argument_parser().parse_args()
    if args.command in {None, "schema"}:
        print(json.dumps(feature_schema(), ensure_ascii=False, indent=2))
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
