"""Publish the additive, grouped Cue-Ranker Dataset Format 3."""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import shutil
import uuid

import numpy as np

from .cue_ranker_universe import (
    CUE_RANKER_DATASET_FORMAT_VERSION,
    CUE_RANKER_UNIVERSE_FORMAT_VERSION,
    _ALLOWED_SPLITS,
    _atomic_json_write,
    _file_record,
    _file_sha256,
    _read_json,
    _verify_file,
    _write_jsonl,
    _write_ragged_npz,
    _write_record_npz,
    canonical_json_sha256,
    load_cue_ranker_universe_rows,
)


@dataclass(frozen=True)
class CueRankerDatasetExportResult:
    output_directory: Path
    manifest_path: Path
    candidate_counts: dict[str, int]
    group_counts: dict[str, int]


def export_cue_ranker_dataset(universe_directory, label_directory, output_directory, *, train_only_normalizer):
    """Merge a SHA-verified universe and frozen teacher labels.

    No feature tensors, waveform caches, pair manifests, or any test artefact
    are opened here.  The normalizer is an explicit training-only artifact,
    never silently fitted from validation.
    """
    universe_directory, label_directory, output_directory = map(Path, (universe_directory, label_directory, output_directory))
    if output_directory.exists():
        raise FileExistsError(f"Dataset output already exists: {output_directory}")
    universe_manifest = _read_json(universe_directory / "manifest.json")
    if universe_manifest.get("format_version") != CUE_RANKER_UNIVERSE_FORMAT_VERSION:
        raise ValueError("Unsupported Cue-Ranker universe format")
    label_manifest = _read_json(label_directory / "manifest.json")
    universe_sha = _file_sha256(universe_directory / "manifest.json")
    if label_manifest.get("universe_manifest_sha256") != universe_sha:
        raise ValueError("teacher_labels_universe_manifest_sha256_mismatch")
    normalizer = _normalizer_record(train_only_normalizer)
    labels = {split: _load_labels(label_directory, label_manifest, split) for split in _ALLOWED_SPLITS}
    records = {split: load_cue_ranker_universe_rows(universe_directory, split) for split in _ALLOWED_SPLITS}
    groups = {split: _load_groups(universe_directory, universe_manifest, split) for split in _ALLOWED_SPLITS}
    for split in _ALLOWED_SPLITS:
        _merge_labels(records[split], labels[split])
        _mark_group_teacher_support(groups[split], records[split])
    temporary = output_directory.with_name(f".{output_directory.name}.{uuid.uuid4().hex}.tmp")
    temporary.mkdir(parents=True)
    try:
        files = {}
        for split in _ALLOWED_SPLITS:
            group_path = temporary / "groups" / f"{split}.jsonl"
            candidate_path = temporary / "index" / f"{split}-candidates-00000.npz"
            ragged_path = temporary / "index" / f"{split}-ragged-groups.npz"
            label_path = temporary / "teacher" / f"{split}-labels-00000.npz"
            _write_jsonl(group_path, groups[split])
            _write_record_npz(candidate_path, records[split])
            _write_ragged(groups[split], records[split], ragged_path)
            _write_label_npz(label_path, labels[split])
            for name, path, kind in (
                (f"{split}_groups", group_path, "jsonl"),
                (f"{split}_candidates", candidate_path, "npz"),
                (f"{split}_ragged_groups", ragged_path, "npz"),
                (f"{split}_teacher_labels", label_path, "npz"),
            ):
                files[name] = _file_record(path, temporary, kind)
        normalizer_path = temporary / "normalization" / "train_only_stats.json"
        _atomic_json_write(normalizer_path, normalizer)
        files["train_only_normalizer"] = _file_record(normalizer_path, temporary, "json")
        manifest = {
            "format_version": CUE_RANKER_DATASET_FORMAT_VERSION,
            "universe_manifest_sha256": universe_sha,
            "teacher_manifest_sha256": _file_sha256(label_directory / "manifest.json"),
            "teacher_release_sha256": label_manifest["teacher_release_sha256"],
            "teacher_contract_sha256": label_manifest.get("teacher_contract_sha256"),
            "teacher_alignment_contract": label_manifest.get("alignment_contract"),
            "split_map_sha256": universe_manifest["split_map_sha256"],
            "normalization": {"fit_scope": "training_tracks_only", "sha256": files["train_only_normalizer"]["sha256"], "source_sha256": normalizer["sha256"]},
            "counts": {split: {"candidates": len(records[split]), "groups": len(groups[split]), "loss_eligible_groups": sum(group["group_status"] == "teacher_supported" for group in groups[split])} for split in _ALLOWED_SPLITS},
            "files": files,
            "sampling": universe_manifest["sampling"],
            "test": {"state": "sealed_not_materialized"},
        }
        _atomic_json_write(temporary / "manifest.json", manifest)
        os.replace(temporary, output_directory)
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise
    return CueRankerDatasetExportResult(output_directory, output_directory / "manifest.json", {s: len(records[s]) for s in _ALLOWED_SPLITS}, {s: len(groups[s]) for s in _ALLOWED_SPLITS})


def _normalizer_record(value):
    if isinstance(value, (str, Path)):
        path = Path(value)
        payload = _read_json(path)
        source_sha = _file_sha256(path)
    elif isinstance(value, dict):
        payload = dict(value)
        source_sha = canonical_json_sha256(payload)
    else:
        raise ValueError("train_only_normalizer is required")
    if payload.get("fit_scope") != "training_tracks_only":
        raise ValueError("Cue-Ranker normalizer must be training_tracks_only")
    return {"format_version": 1, "fit_scope": "training_tracks_only", "sha256": source_sha, "statistics": payload}


def _load_labels(root, manifest, split):
    info = manifest.get("files", {}).get(f"{split}_teacher_labels")
    if not info: raise ValueError("teacher_label_shard_missing")
    path = root / info["path"]
    _verify_file(path, info["sha256"])
    with np.load(path, allow_pickle=False) as payload:
        labels = [json.loads(value) for value in payload["row_json"].tolist()]
    return labels


def _load_groups(root, manifest, split):
    info = manifest["files"][f"{split}_groups"]
    path = root / info["path"]
    _verify_file(path, info["sha256"])
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def _merge_labels(records, labels):
    by_key = {(row["group_id"], row["candidate_id"], row["candidate_identity_sha256"]): row for row in records}
    for label in labels:
        key = (label["group_id"], label["candidate_id"], label["candidate_identity_sha256"])
        if key not in by_key: raise ValueError("teacher_label_not_in_universe")
        row = by_key[key]
        if not row["label_selected"]: raise ValueError("teacher_label_for_unsampled_candidate")
        if not 0.0 < float(row["p_inclusion"]) <= 1.0: raise ValueError("teacher_label_invalid_inclusion_probability")
        row.update({key: value for key, value in label.items() if key not in {"group_id", "candidate_id", "candidate_identity_sha256"}})
    for row in records:
        if row["label_selected"] and row.get("teacher_status") == "unlabeled":
            raise ValueError("teacher_label_missing_for_selected_candidate")


def _mark_group_teacher_support(groups, records):
    by_group = {}
    for row in records: by_group.setdefault(row["group_id"], []).append(row)
    for group in groups:
        members = by_group.get(group["group_id"], [])
        finite = [float(row["teacher_utility"]) for row in members if row.get("teacher_status") == "scored" and isinstance(row.get("teacher_utility"), (int, float)) and np.isfinite(row["teacher_utility"])]
        rejected = sum(row.get("teacher_status") == "guard_rejected" for row in members)
        failed = sum(row.get("teacher_status") == "failed" for row in members)
        group["teacher_failure_count"] = failed
        group["teacher_guard_rejection_count"] = rejected
        group["teacher_finite_count"] = len(finite)
        group["group_status"] = "teacher_supported" if len(finite) + rejected >= 2 and finite else "insufficient_teacher_support"


def _write_ragged(groups, records, path):
    by_group = {}
    for row in records: by_group.setdefault(row["group_id"], []).append(int(row["row_id"]))
    offsets, members = [0], []
    for group in groups:
        ids = sorted(by_group[group["group_id"]])
        group["member_row_ids"] = ids
        members.extend(ids); offsets.append(len(members))
    _write_ragged_npz(path, groups, offsets, members)


def _write_label_npz(path, labels):
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(path, row_json=np.asarray([json.dumps(row, sort_keys=True, separators=(",", ":")) for row in labels], dtype=str))
