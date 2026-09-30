"""Build the immutable corpus and recording-group inputs for Dataset v2."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import unicodedata
import uuid

from src.features.dataset_export import SplitConfig
from src.features.variable_split import (
    authority_from_mapping,
    extend_variable_split_authority,
    write_variable_split_authority,
)


AUDIO_EXTENSIONS = {".flac", ".mp3", ".ogg", ".wav"}
VERSION_MARKERS = re.compile(
    r"\b(?:radio|original|extended|special|club|album|single|festival|vip|dj)\s*"
    r"(?:edit|mix|version|remix|cut)?\b|\b(?:edit|mix|version|remix|remaster(?:ed)?)\b",
    re.IGNORECASE,
)


def build_variable_corpus_inventory(
    base_dataset_manifest,
    base_producer_manifest,
    added_directory,
    output_directory,
    *,
    split_seed=20260923,
):
    """Hash tracks, derive conservative recording groups, and freeze splits."""

    base_dataset_manifest = Path(base_dataset_manifest)
    base_producer_manifest = Path(base_producer_manifest)
    added_directory = Path(added_directory)
    output_directory = Path(output_directory)
    if output_directory.exists():
        raise FileExistsError(f"Corpus inventory output already exists: {output_directory}")
    base_dataset = _read_json(base_dataset_manifest)
    base_producer = _read_json(base_producer_manifest)
    base_assignments = {
        str(row["sha256"]).lower(): str(row["split"])
        for row in base_dataset["track_assignments"]
    }
    base_paths = tuple(str(Path(value)) for value in base_producer["songs"])
    added_paths = tuple(
        str(path)
        for path in sorted(added_directory.rglob("*"))
        if path.is_file() and path.suffix.lower() in AUDIO_EXTENSIONS
    )
    all_paths = base_paths + added_paths
    rows = []
    seen_hashes = {}
    for path_text in all_paths:
        path = Path(path_text)
        digest = _file_sha256(path)
        if digest in seen_hashes:
            continue
        tags = _ffprobe_tags(path)
        artist = tags.get("artist") or _fallback_artist(path)
        title = tags.get("title") or _fallback_title(path)
        group_key = _recording_group_key(artist, title)
        group_id = "recording-" + hashlib.sha256(group_key.encode("utf-8")).hexdigest()[:20]
        seen_hashes[digest] = str(path)
        rows.append({
            "sha256": digest,
            "path": str(path),
            "source": "base" if path_text in base_paths else "prive_scantraxx",
            "artist": artist,
            "title": title,
            "recording_group_id": group_id,
            "recording_group_key": group_key,
            "size_bytes": path.stat().st_size,
        })
    rows, conflict_exclusions = _exclude_frozen_split_recording_conflicts(
        rows, base_assignments
    )
    base_seen = {row["sha256"] for row in rows if row["source"] == "base"}
    excluded_base = {row["sha256"] for row in conflict_exclusions}
    missing_base = sorted(set(base_assignments) - base_seen - excluded_base)
    if missing_base:
        raise ValueError("Base producer does not resolve all frozen audio SHAs: " + ", ".join(missing_base))
    rows.sort(key=lambda row: row["sha256"])
    corpus = {
        "format_version": 1,
        "inventory": "variable_corpus_audio_sha_recording_groups_v1",
        "base_dataset_manifest": str(base_dataset_manifest),
        "base_dataset_manifest_sha256": _file_sha256(base_dataset_manifest),
        "base_producer_manifest": str(base_producer_manifest),
        "base_producer_manifest_sha256": _file_sha256(base_producer_manifest),
        "added_directory": str(added_directory),
        "track_count": len(rows),
        "base_track_count": sum(row["source"] == "base" for row in rows),
        "added_track_count": sum(row["source"] == "prive_scantraxx" for row in rows),
        "recording_group_count": len({row["recording_group_id"] for row in rows}),
        "recording_conflict_exclusions": conflict_exclusions,
        "tracks": rows,
    }
    output_directory.mkdir(parents=True)
    corpus_path = output_directory / "corpus_manifest.json"
    _write_json_atomic(corpus_path, corpus)
    groups_payload = {
        "format_version": 1,
        "source_corpus_manifest_sha256": _file_sha256(corpus_path),
        "tracks": [
            {"sha256": row["sha256"], "recording_group_id": row["recording_group_id"]}
            for row in rows
        ],
    }
    _write_json_atomic(output_directory / "recording_groups.json", groups_payload)
    base_authority = authority_from_mapping(
        base_assignments,
        base_assignments,
        source_manifest_sha256=base_dataset.get("source_manifest_sha256"),
        source="preserved_variable_v2_strict_20260820",
        policy=base_dataset.get("split", {}),
    )
    write_variable_split_authority(output_directory / "base_split_authority.json", base_authority)
    extended = extend_variable_split_authority(
        base_authority,
        {row["sha256"]: row["recording_group_id"] for row in rows},
        split_config=SplitConfig(seed=int(split_seed)),
        source_manifest_sha256=_file_sha256(corpus_path),
    )
    write_variable_split_authority(output_directory / "split_authority.json", extended)
    summary = {
        "format_version": 1,
        "corpus_manifest_sha256": _file_sha256(corpus_path),
        "recording_groups_sha256": _file_sha256(output_directory / "recording_groups.json"),
        "split_authority_sha256": _file_sha256(output_directory / "split_authority.json"),
        "split_mapping_sha256": extended.mapping_sha256,
        "track_count": len(rows),
        "recording_group_count": corpus["recording_group_count"],
        "split_counts": {
            split: sum(value == split for value in extended.assignments.values())
            for split in ("train", "validation", "test")
        },
    }
    _write_json_atomic(output_directory / "summary.json", summary)
    return summary


def _exclude_frozen_split_recording_conflicts(rows, base_assignments):
    """Keep the most protected split when an old recording already leaked."""

    priority = {"train": 0, "validation": 1, "test": 2}
    groups = {}
    for row in rows:
        groups.setdefault(row["recording_group_id"], []).append(row)
    excluded = []
    retained = []
    for group_id, members in groups.items():
        frozen = {
            base_assignments[row["sha256"]]
            for row in members
            if row["sha256"] in base_assignments
        }
        keep_split = max(frozen, key=priority.get) if len(frozen) > 1 else None
        for row in members:
            split = base_assignments.get(row["sha256"])
            if keep_split is not None and split is not None and split != keep_split:
                excluded.append({
                    **row,
                    "reason": "preexisting_recording_group_cross_split_conflict",
                    "kept_split": keep_split,
                    "excluded_split": split,
                })
            else:
                retained.append(row)
    retained.sort(key=lambda row: row["sha256"])
    excluded.sort(key=lambda row: row["sha256"])
    return retained, excluded


def _ffprobe_tags(path):
    completed = subprocess.run(
        [
            "ffprobe", "-v", "error", "-show_entries", "format_tags=artist,title",
            "-of", "json", str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    raw = _read_json_text(completed.stdout).get("format", {}).get("tags", {})
    return {str(key).lower(): str(value).strip() for key, value in raw.items()}


def _recording_group_key(artist, title):
    artist_key = _normalise_text(artist.replace(";", " & "))
    title = re.sub(
        r"\s*[\[(]([^\])]+)[\])]",
        lambda match: "" if VERSION_MARKERS.search(match.group(1)) else " " + match.group(0),
        title,
    )
    parts = [part.strip() for part in re.split(r"\s+-\s+", title) if part.strip()]
    while len(parts) > 1 and VERSION_MARKERS.search(parts[-1]):
        parts.pop()
    title_key = _normalise_text(" - ".join(parts))
    return f"{artist_key}|{title_key}"


def _normalise_text(value):
    value = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode("ascii")
    return " ".join(re.sub(r"[^a-z0-9]+", " ", value.casefold()).split()) or "unknown"


def _fallback_artist(path):
    parts = [part.strip() for part in path.stem.split(" - ") if part.strip()]
    return parts[-1] if len(parts) > 1 else "unknown"


def _fallback_title(path):
    parts = [part.strip() for part in path.stem.split(" - ") if part.strip()]
    return parts[0] if len(parts) > 1 else path.stem


def _file_sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _read_json_text(value):
    return json.loads(value)


def _write_json_atomic(path, payload):
    path = Path(path)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def build_argument_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("base_dataset_manifest")
    parser.add_argument("base_producer_manifest")
    parser.add_argument("added_directory")
    parser.add_argument("output_directory")
    parser.add_argument("--split-seed", type=int, default=20260923)
    return parser


def main(argv=None):
    args = build_argument_parser().parse_args(argv)
    result = build_variable_corpus_inventory(
        args.base_dataset_manifest,
        args.base_producer_manifest,
        args.added_directory,
        args.output_directory,
        split_seed=args.split_seed,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
