"""Frozen, audio-SHA keyed split authority for Dataset Format 2."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import os
import uuid

from .dataset_export import SPLIT_NAMES, SplitConfig, assign_track_disjoint_splits


VARIABLE_SPLIT_AUTHORITY_FORMAT_VERSION = 1


@dataclass(frozen=True)
class VariableSplitAuthority:
    assignments: dict
    mapping_sha256: str
    source_manifest_sha256: str | None
    source: str
    policy: dict
    recording_groups: dict | None = None

    def to_dict(self):
        payload = {
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
        if self.recording_groups is not None:
            payload["recording_groups"] = [
                {"sha256": key, "recording_group_id": self.recording_groups[key]}
                for key in sorted(self.recording_groups)
            ]
        return payload


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


def bind_variable_split_authority(
    authority,
    *,
    source_manifest_sha256,
    source="bound_to_producer_manifest_v1",
    parent_authority_sha256=None,
):
    """Bind an unchanged frozen mapping to one concrete producer manifest."""

    if not isinstance(authority, VariableSplitAuthority):
        raise TypeError("authority must be VariableSplitAuthority")
    source_manifest_sha256 = str(source_manifest_sha256).lower()
    if len(source_manifest_sha256) != 64 or any(
        character not in "0123456789abcdef" for character in source_manifest_sha256
    ):
        raise ValueError("source_manifest_sha256 must be a lowercase SHA-256")
    policy = {
        **authority.policy,
        "binding_policy": "unchanged_mapping_to_producer_manifest_v1",
        "parent_mapping_sha256": authority.mapping_sha256,
        "parent_source_manifest_sha256": authority.source_manifest_sha256,
    }
    if parent_authority_sha256 is not None:
        policy["parent_authority_sha256"] = str(parent_authority_sha256).lower()
    return _authority_from_mapping(
        authority.assignments,
        source_manifest_sha256=source_manifest_sha256,
        source=source,
        policy=policy,
        recording_groups=authority.recording_groups,
    )


def extend_variable_split_authority(
    base_authority,
    recording_groups,
    *,
    split_config=None,
    source_manifest_sha256=None,
    source="extended_recording_groups_v1",
):
    """Preserve frozen assignments and assign each new recording group once.

    ``recording_groups`` maps an audio SHA to a stable recording-group id.
    Alternate/radio/master versions must share that id.  A group touching an
    existing assignment inherits it; conflicting inherited splits are refused.
    New groups use a deterministic SHA roulette keyed by the split seed.
    """

    split_config = split_config or SplitConfig()
    if isinstance(base_authority, VariableSplitAuthority):
        assignments = dict(base_authority.assignments)
        base_mapping_sha256 = base_authority.mapping_sha256
    else:
        assignments = {str(key).lower(): str(value) for key, value in dict(base_authority).items()}
        base_mapping_sha256 = canonical_mapping_sha256(assignments)
    groups = {}
    for track_sha, group_id in dict(recording_groups).items():
        track_sha = str(track_sha).lower()
        if len(track_sha) != 64 or any(character not in "0123456789abcdef" for character in track_sha):
            raise ValueError(f"Invalid audio SHA in recording groups: {track_sha}")
        group_id = str(group_id).strip()
        if not group_id:
            raise ValueError("recording_group_id must not be empty")
        groups.setdefault(group_id, []).append(track_sha)
    ratios = (
        ("train", float(split_config.train)),
        ("validation", float(split_config.validation)),
        ("test", float(split_config.test)),
    )
    ratio_total = sum(value for _name, value in ratios)
    if ratio_total <= 0:
        raise ValueError("Split ratios must sum to a positive value")
    for group_id in sorted(groups):
        tracks = sorted(set(groups[group_id]))
        inherited = {assignments[track] for track in tracks if track in assignments}
        if len(inherited) > 1:
            raise ValueError(f"Recording group spans frozen splits: {group_id}")
        split = next(iter(inherited), None)
        if split is None:
            token = hashlib.sha256(f"{int(split_config.seed)}:{group_id}".encode("utf-8")).digest()
            point = int.from_bytes(token[:8], "big") / float(2**64)
            cumulative = 0.0
            split = ratios[-1][0]
            for candidate, weight in ratios:
                cumulative += weight / ratio_total
                if point < cumulative:
                    split = candidate
                    break
        for track in tracks:
            previous = assignments.get(track)
            if previous is not None and previous != split:
                raise ValueError(f"Frozen split assignment would change: {track}")
            assignments[track] = split
    group_mapping = {
        track: group_id
        for group_id, tracks in groups.items()
        for track in sorted(set(tracks))
    }
    policy = {
        **split_config.to_dict(),
        "extension_policy": "recording_group_sha_roulette_v1",
        "base_mapping_sha256": base_mapping_sha256,
        "recording_group_mapping_sha256": canonical_mapping_sha256(group_mapping),
    }
    return _authority_from_mapping(
        assignments,
        source_manifest_sha256=source_manifest_sha256,
        source=source,
        policy=policy,
        recording_groups=group_mapping,
    )


def write_variable_split_authority(path, authority):
    """Publish a frozen split authority without ever replacing different bytes."""

    if not isinstance(authority, VariableSplitAuthority):
        raise TypeError("authority must be VariableSplitAuthority")
    path = Path(path)
    payload = authority.to_dict()
    encoded = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if path.exists():
        if path.read_text(encoding="utf-8") != encoded:
            raise ValueError(f"Refusing to overwrite frozen split authority: {path}")
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        temporary.write_text(encoded, encoding="utf-8")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
    return path


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
    recording_groups = _recording_group_entries_to_mapping(payload.get("recording_groups"))
    declared_mapping = payload.get("mapping_sha256")
    computed_mapping = canonical_mapping_sha256(assignments)
    if (
        declared_mapping is not None
        and str(declared_mapping).lower() != computed_mapping
    ):
        raise ValueError("Frozen split authority mapping hash differs")
    declared_group_mapping = payload.get("policy", {}).get("recording_group_mapping_sha256")
    if declared_group_mapping is not None:
        if recording_groups is None or str(declared_group_mapping).lower() != canonical_mapping_sha256(recording_groups):
            raise ValueError("Frozen recording-group mapping hash differs")
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
        recording_groups=recording_groups,
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


def _authority_from_mapping(assignments, *, source_manifest_sha256, source, policy, recording_groups=None):
    invalid = sorted(set(assignments.values()) - set(SPLIT_NAMES))
    if invalid:
        raise ValueError(f"Unknown split names in authority: {invalid}")
    return VariableSplitAuthority(
        assignments=dict(assignments),
        mapping_sha256=canonical_mapping_sha256(assignments),
        source_manifest_sha256=source_manifest_sha256,
        source=str(source),
        policy=dict(policy),
        recording_groups=None if recording_groups is None else dict(recording_groups),
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


def _recording_group_entries_to_mapping(entries):
    if entries is None:
        return None
    if not isinstance(entries, list):
        raise ValueError("recording_groups must be a list")
    mapping = {}
    for entry in entries:
        if not isinstance(entry, dict) or "sha256" not in entry or "recording_group_id" not in entry:
            raise ValueError("Every recording-group entry needs sha256 and recording_group_id")
        key = str(entry["sha256"]).lower()
        if key in mapping:
            raise ValueError(f"Duplicate audio SHA in recording groups: {key}")
        mapping[key] = str(entry["recording_group_id"])
    return mapping


def _require_tracks(assignments, required_track_hashes):
    required = {str(value).lower() for value in required_track_hashes}
    missing = sorted(required - set(assignments))
    if missing:
        raise ValueError("Frozen split authority lacks audio SHAs: " + ", ".join(missing))
