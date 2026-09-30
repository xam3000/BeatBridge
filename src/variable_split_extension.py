"""CLI for immutable recording-group-aware Dataset-v2 split extension."""

import argparse
import json
from pathlib import Path

from src.features.dataset_export import SplitConfig
from src.features.variable_split import (
    extend_variable_split_authority,
    load_variable_split_authority,
    write_variable_split_authority,
)


def _load_groups(path):
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    rows = payload.get("tracks") if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        raise ValueError("Recording-group input must be a list or contain a tracks list")
    groups = {}
    for row in rows:
        if not isinstance(row, dict) or "sha256" not in row or "recording_group_id" not in row:
            raise ValueError("Each recording-group row needs sha256 and recording_group_id")
        sha = str(row["sha256"]).lower()
        if sha in groups:
            raise ValueError(f"Duplicate recording-group SHA: {sha}")
        groups[sha] = str(row["recording_group_id"])
    return groups


def _base_hashes(path):
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return tuple(str(row["sha256"]).lower() for row in payload.get("track_assignments", ()))


def build_argument_parser():
    parser = argparse.ArgumentParser(description="Extend a frozen split map without changing existing assignments.")
    parser.add_argument("base_split_map")
    parser.add_argument("recording_groups")
    parser.add_argument("output_path")
    parser.add_argument("--source-manifest-sha256")
    parser.add_argument("--train-ratio", type=float, default=0.70)
    parser.add_argument("--validation-ratio", type=float, default=0.15)
    parser.add_argument("--test-ratio", type=float, default=0.15)
    parser.add_argument("--seed", type=int, default=20260923)
    return parser


def main(argv=None):
    args = build_argument_parser().parse_args(argv)
    base = load_variable_split_authority(args.base_split_map, _base_hashes(args.base_split_map))
    authority = extend_variable_split_authority(
        base,
        _load_groups(args.recording_groups),
        split_config=SplitConfig(
            train=args.train_ratio,
            validation=args.validation_ratio,
            test=args.test_ratio,
            seed=args.seed,
        ),
        source_manifest_sha256=args.source_manifest_sha256,
    )
    output = write_variable_split_authority(args.output_path, authority)
    print(json.dumps({"path": str(output), "mapping_sha256": authority.mapping_sha256, "track_count": len(authority.assignments)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
