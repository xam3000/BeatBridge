"""Bind a frozen split mapping to an immutable producer manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from src.features.variable_split import (
    bind_variable_split_authority,
    load_variable_split_authority,
    write_variable_split_authority,
)


def _file_sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _authority_hashes(path):
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return tuple(str(row["sha256"]).lower() for row in payload["track_assignments"])


def bind_split_authority(base_split_map, producer_manifest, output_path):
    base_split_map = Path(base_split_map)
    producer_manifest = Path(producer_manifest)
    authority = load_variable_split_authority(
        base_split_map,
        _authority_hashes(base_split_map),
    )
    bound = bind_variable_split_authority(
        authority,
        source_manifest_sha256=_file_sha256(producer_manifest),
        parent_authority_sha256=_file_sha256(base_split_map),
    )
    return write_variable_split_authority(output_path, bound)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("base_split_map")
    parser.add_argument("producer_manifest")
    parser.add_argument("output_path")
    args = parser.parse_args(argv)
    output = bind_split_authority(
        args.base_split_map,
        args.producer_manifest,
        args.output_path,
    )
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
