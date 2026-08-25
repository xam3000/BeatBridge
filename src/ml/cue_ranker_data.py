"""Grouped, ragged Dataset Format 3 view for the Cue-Ranker."""

from __future__ import annotations

import hashlib
import inspect
import json
from pathlib import Path
from typing import Callable, Mapping

import numpy as np
import torch
from torch.utils.data import Dataset

from src.features.variable_contract import geometry_for_length, validate_length_condition, validate_variable_feature_array
from .cue_ranker_context import build_candidate_context
from .cue_ranker_model import CUE_RANKER_CONTEXT_DIMENSION, CUE_RANKER_GRID_SOURCE_VOCAB_SIZE
from src.features.cue_ranker_universe import _ALLOWED_SPLITS


class CueRankerGroupedDataset(Dataset):
    """Read one sealed train/validation split as complete ragged groups.

    Format 3 deliberately stores metadata separately from feature payloads.
    ``feature_loader`` is therefore explicit and must return the already
    resolved feature tensors for one row; the dataset never discovers pair
    manifests, opens audio, or accepts a test split.
    """

    def __init__(self, dataset_directory, split, *, feature_loader: Callable | Mapping | None = None):
        self.dataset_directory = Path(dataset_directory)
        self.split = str(split)
        if self.split not in _ALLOWED_SPLITS:
            raise ValueError("Cue-Ranker dataset exposes only train and validation")
        self.feature_loader = feature_loader
        self.manifest_path = self.dataset_directory / "manifest.json"
        self.manifest = _read_verified_json(self.manifest_path)
        if int(self.manifest.get("format_version", -1)) != 3:
            raise ValueError("CueRankerGroupedDataset requires Dataset Format 3")
        if self.manifest.get("test") != {"state": "sealed_not_materialized"}:
            raise ValueError("Cue-Ranker dataset is not sealed against test materialization")
        self.manifest_sha256 = _sha256(self.manifest_path)
        self.rows = _load_rows(self.dataset_directory, self.manifest, self.split)
        self.groups = _load_groups(self.dataset_directory, self.manifest, self.split)
        _validate_ragged_index(self.dataset_directory, self.manifest, self.split, self.rows, self.groups)
        row_by_id = {int(row["row_id"]): row for row in self.rows}
        self._groups = []
        for group in self.groups:
            # The on-disk ragged index remains a complete universe audit.
            # Training/evaluation must however see exactly the frozen labeled
            # sample: unselected universe rows have p_inclusion=0 and cannot
            # enter the IPW softmax.
            members = tuple(
                row_by_id[int(row_id)]
                for row_id in group.get("member_row_ids", ())
                if bool(row_by_id[int(row_id)].get("label_selected", False))
            )
            if not members:
                raise ValueError("Cue-Ranker group has no frozen label sample")
            self._groups.append({"group_id": group["group_id"], "split": self.split, "members": members, "group": group})

    def __len__(self):
        return len(self._groups)

    def __getitem__(self, index):
        group = self._groups[int(index)]
        sampled_members = group["members"]
        # The label sample may be much smaller than its complete candidate
        # universe.  Candidate-context density must match inference, which
        # sees the complete accepted group rather than just the labeled rows.
        universe_size = int(group["group"].get("universe_size", len(sampled_members)))
        if universe_size < len(sampled_members):
            raise ValueError("Cue-Ranker group universe_size is smaller than its label sample")
        members = tuple(self._materialise_row(row, universe_size) for row in sampled_members)
        return {"group_id": group["group_id"], "split": self.split, "members": members, "group": group["group"]}

    def _materialise_row(self, row, group_size):
        payload = _resolve_features(self.feature_loader, row)
        candidate_context = payload.get("candidate_context")
        grid_source_ids = payload.get("grid_source_ids")
        if candidate_context is None or grid_source_ids is None:
            built_context, built_grid_ids = build_candidate_context(row, group_size=group_size)
            candidate_context = built_context if candidate_context is None else candidate_context
            grid_source_ids = built_grid_ids if grid_source_ids is None else grid_source_ids
        length = geometry_for_length(row["transition_length_bars"], sequence_length=row["sequence_length"])
        features_a = _feature_tensor(payload.get("features_a"), "features_a")
        features_b = _feature_tensor(payload.get("features_b"), "features_b")
        global_features = _vector_tensor(payload.get("global_features"), 16, "global_features")
        length_condition = _vector_tensor(payload.get("length_condition", [length.length_condition]), 1, "length_condition")
        validate_variable_feature_array(features_a.detach().cpu().numpy(), transition_length_bars=length.transition_length_bars, sequence_length=length.sequence_length, name="features_a")
        validate_variable_feature_array(features_b.detach().cpu().numpy(), transition_length_bars=length.transition_length_bars, sequence_length=length.sequence_length, name="features_b")
        validate_length_condition(length_condition.detach().cpu().numpy(), transition_length_bars=length.transition_length_bars)
        context = _vector_tensor(candidate_context, CUE_RANKER_CONTEXT_DIMENSION, "candidate_context")
        grid_ids = torch.as_tensor(grid_source_ids, dtype=torch.long)
        if grid_ids.shape != (2,) or torch.any(grid_ids < 0) or torch.any(grid_ids >= CUE_RANKER_GRID_SOURCE_VOCAB_SIZE):
            raise ValueError("grid_source_ids must have shape (2,) and valid categories")
        item = dict(row)
        item.update({
            "features_a": features_a,
            "features_b": features_b,
            "global_features": global_features,
            "length_condition": length_condition,
            "candidate_context": context,
            "grid_source_ids": grid_ids,
        })
        return item


def collate_cue_ranker_groups(groups):
    """Keep complete ragged groups intact; no time/candidate padding."""

    groups = tuple(groups)
    if not groups:
        raise ValueError("Cannot collate an empty Cue-Ranker group batch")
    if any(not isinstance(group, Mapping) or not group.get("members") for group in groups):
        raise ValueError("Cue-Ranker batches must contain non-empty groups")
    return groups


class CueRankerGroupLoader:
    """Small deterministic iterable used by callers that already have groups."""

    def __init__(self, groups, *, batch_size=1, shuffle=False, seed=0):
        self.groups = tuple(groups)
        self.batch_size = int(batch_size)
        self.shuffle = bool(shuffle)
        self.seed = int(seed)
        if self.batch_size < 1:
            raise ValueError("batch_size must be at least one")

    def __iter__(self):
        order = np.arange(len(self.groups), dtype=np.int64)
        if self.shuffle and len(order):
            rng = np.random.default_rng(self.seed)
            rng.shuffle(order)
        for start in range(0, len(order), self.batch_size):
            yield [self.groups[int(index)] for index in order[start : start + self.batch_size]]

    def __len__(self):
        return (len(self.groups) + self.batch_size - 1) // self.batch_size


def _resolve_features(loader, row):
    embedded = {key: row[key] for key in ("features_a", "features_b", "global_features", "length_condition") if key in row}
    if loader is None:
        if len(embedded) < 3:
            raise ValueError("CueRankerGroupedDataset requires an explicit feature_loader or embedded feature tensors")
        return embedded
    if isinstance(loader, Mapping):
        key = (row["group_id"], row["candidate_id"], row["candidate_identity_sha256"])
        payload = loader.get(key, loader.get(row["candidate_id"]))
        if payload is None:
            raise KeyError(f"No feature payload for candidate {row['candidate_id']}")
        return dict(payload)
    if not callable(loader):
        raise TypeError("feature_loader must be callable or a mapping")
    try:
        signature = inspect.signature(loader)
        payload = loader(row) if len(signature.parameters) == 1 else loader(row, geometry_for_length(row["transition_length_bars"]))
    except (TypeError, ValueError):
        payload = loader(row)
    if not isinstance(payload, Mapping):
        raise TypeError("feature_loader must return a mapping")
    return dict(payload)


def _load_rows(root, manifest, split):
    info = manifest["files"][f"{split}_candidates"]
    path = root / info["path"]
    _verify_file(path, info["sha256"])
    with np.load(path, allow_pickle=False) as payload:
        return [json.loads(value) for value in payload["row_json"].tolist()]


def _load_groups(root, manifest, split):
    info = manifest["files"][f"{split}_groups"]
    path = root / info["path"]
    _verify_file(path, info["sha256"])
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _validate_ragged_index(root, manifest, split, rows, groups):
    info = manifest["files"][f"{split}_ragged_groups"]
    path = root / info["path"]
    _verify_file(path, info["sha256"])
    with np.load(path, allow_pickle=False) as payload:
        ids = [str(value) for value in payload["group_ids"].tolist()]
        offsets = payload["group_offsets"].tolist()
        members = payload["member_row_ids"].tolist()
    if ids != [str(group["group_id"]) for group in groups] or len(offsets) != len(groups) + 1:
        raise ValueError("Cue-Ranker ragged group index disagrees with groups JSONL")
    if members != [int(row_id) for group in groups for row_id in group.get("member_row_ids", ())]:
        raise ValueError("Cue-Ranker ragged member index disagrees with groups JSONL")
    if offsets != [sum(len(group.get("member_row_ids", ())) for group in groups[:index]) for index in range(len(groups) + 1)]:
        raise ValueError("Cue-Ranker ragged offsets are invalid")
    if {int(row["row_id"]) for row in rows} != set(members):
        raise ValueError("Cue-Ranker ragged index does not cover candidate rows")


def _feature_tensor(value, name):
    if value is None:
        raise ValueError(f"{name} is missing")
    value = torch.as_tensor(value)
    if value.ndim != 2 or value.shape[-1] != 54 or not value.is_floating_point():
        raise ValueError(f"{name} must have shape (T, 54) and floating dtype")
    value = value.to(dtype=torch.float32)
    if not torch.isfinite(value).all():
        raise ValueError(f"{name} must contain finite values")
    return value.contiguous()


def _vector_tensor(value, dimension, name):
    if value is None:
        raise ValueError(f"{name} is missing")
    value = torch.as_tensor(value)
    if value.numel() != dimension or not value.is_floating_point():
        raise ValueError(f"{name} must contain {dimension} floating values")
    value = value.reshape(dimension).to(dtype=torch.float32)
    if not torch.isfinite(value).all():
        raise ValueError(f"{name} must contain finite values")
    return value.contiguous()


def _read_verified_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _verify_file(path, expected):
    if not Path(path).is_file():
        raise FileNotFoundError(path)
    if _sha256(path) != expected:
        raise ValueError(f"Cue-Ranker dataset SHA-256 mismatch: {path}")


def _sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()
