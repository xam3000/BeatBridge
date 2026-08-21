"""Frozen, audio-SHA keyed split authority for Dataset Format 2."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path

from .dataset_export import SPLIT_NAMES, SplitConfig, assign_track_disjoint_splits


VARIABLE_SPLIT_AUTHORITY_FORMAT_VERSION = 1


@dataclass(frozen=True)
class VariableSplitAuthority:
    assignments: dict
    mapping_sha256: str
    source_manifest_sha256: str | None
    source: str
    policy: dict

    def to_dict(self):
        return {
            "format_version": VARIABLE_SPLIT_AUTHORITY_FORMAT_VERSION,
            "source": self.source,
            "source_manifest_sha256": self.source_manifest_sha256,
            "mapping_sha256": self.mapping_sha256,
            "policy": dict(self.policy),
            "track_assignments": [
                {"sha256": key, "split": self.assignments[key]}
                for key in sorted(self.assignments)
            ],
        }


def canonical_mapping_sha256(assignments):
    mapping = {
        str(key).lower(): str(value)
        for key, value in assignments.items()
    }
    canonical = json.dumps(mapping, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def build_variable_split_authority(
    track_hashes,
    pair_weights,
    *,
    split_config=None,
    source_manifest_sha256=None,
    source="generated_from_length_union",
):
    """Assign the complete union exactly once, before any length filtering."""
    split_config = split_config or SplitConfig()
    assignments = assign_track_disjoint_splits(
        tuple(track_hashes),
        pair_weights,
        config=split_config,
    )
    return _authority_from_mapping(
        assignments,
        source_manifest_sha256=source_manifest_sha256,
        source=source,
        policy=split_config.to_dict(),
    )


def load_variable_split_authority(
    path,
    required_track_hashes,
    *,
    source_manifest_sha256=None,
):
    """Read and validate a frozen mapping without modifying its file."""
    path = Path(path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    entries = payload.get("track_assignments")
    if not isinstance(entries, list):
        raise ValueError("Split authority must contain a track_assignments list")
    assignments = _entries_to_mapping(entries)
    declared_mapping = payload.get("mapping_sha256")
    computed_mapping = canonical_mapping_sha256(assignments)
    if (
        declared_mapping is not None
        and str(declared_mapping).lower() != computed_mapping
    ):
        raise ValueError("Frozen split authority mapping hash differs")
    declared_source = payload.get("source_manifest_sha256")
    if (
        source_manifest_sha256 is not None
        and declared_source is not None
        and str(declared_source).lower() != str(source_manifest_sha256).lower()
    ):
        raise ValueError("Frozen split authority source manifest hash differs")
    _require_tracks(assignments, required_track_hashes)
    return _authority_from_mapping(
        assignments,
        source_manifest_sha256=declared_source or source_manifest_sha256,
        source=str(payload.get("source", "provided")),
        policy=payload.get("policy", {}),
    )


def authority_from_mapping(
    assignments,
    required_track_hashes,
    *,
    source_manifest_sha256=None,
    source="provided_mapping",
    policy=None,
):
    """Validate an in-memory frozen mapping for synthetic and API callers."""
    normalized = {
        str(key).lower(): str(value)
        for key, value in dict(assignments).items()
    }
    _require_tracks(normalized, required_track_hashes)
    return _authority_from_mapping(
        normalized,
        source_manifest_sha256=source_manifest_sha256,
        source=source,
        policy=policy or {},
    )


def _authority_from_mapping(assignments, *, source_manifest_sha256, source, policy):
    invalid = sorted(set(assignments.values()) - set(SPLIT_NAMES))
    if invalid:
        raise ValueError(f"Unknown split names in authority: {invalid}")
    return VariableSplitAuthority(
        assignments=dict(assignments),
        mapping_sha256=canonical_mapping_sha256(assignments),
        source_manifest_sha256=source_manifest_sha256,
        source=str(source),
        policy=dict(policy),
    )


def _entries_to_mapping(entries):
    assignments = {}
    for entry in entries:
        if not isinstance(entry, dict) or "sha256" not in entry or "split" not in entry:
            raise ValueError("Every split assignment needs sha256 and split")
        key = str(entry["sha256"]).lower()
        if key in assignments:
            raise ValueError(f"Duplicate audio SHA in split authority: {key}")
        assignments[key] = str(entry["split"])
    return assignments


def _require_tracks(assignments, required_track_hashes):
    required = {str(value).lower() for value in required_track_hashes}
    missing = sorted(required - set(assignments))
    if missing:
        raise ValueError("Frozen split authority lacks audio SHAs: " + ", ".join(missing))
