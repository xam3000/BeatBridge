"""Read-only loader for homogeneous Dataset Format 2 feature shards."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Callable, Mapping

import numpy as np
import torch
from torch.utils.data import Dataset, Sampler

from src.features.variable_contract import (
    SUPPORTED_VARIABLE_LENGTHS,
    geometry_for_length,
    validate_length_condition,
    validate_variable_feature_batch,
)


class VariableFeatureDataset(Dataset):
    """Load exactly one length/split shard; no padding or mixed-T batches."""

    def __init__(
        self,
        dataset_directory,
        transition_length_bars,
        split,
        *,
        waveform_loader: Callable | None = None,
    ):
        self.dataset_directory = Path(dataset_directory)
        self.split = str(split)
        self.waveform_loader = waveform_loader
        if self.split not in {"train", "validation", "test"}:
            raise ValueError("split must be train, validation, or test")
        self.geometry = geometry_for_length(transition_length_bars)
        self.manifest = _read_json(self.dataset_directory / "manifest.json")
        if int(self.manifest.get("format_version", 0)) != 2:
            raise ValueError("VariableFeatureDataset requires Dataset Format 2")
        declared_lengths = tuple(int(value) for value in self.manifest.get("supported_lengths", ()))
        if self.geometry.transition_length_bars not in declared_lengths:
            raise ValueError("Requested length is not declared by the dataset")
        shard = self.manifest["shards"][str(self.geometry.transition_length_bars)][self.split]
        if int(shard["sequence_length"]) != self.geometry.sequence_length:
            raise ValueError("Shard sequence_length differs from requested geometry")
        self.shard = shard
        npz_path = self.dataset_directory / self.manifest["files"][shard["npz_file"]]["path"]
        metadata_path = self.dataset_directory / self.manifest["files"][shard["metadata_file"]]["path"]
        _verify_file(self.manifest, shard["npz_file"], npz_path)
        _verify_file(self.manifest, shard["metadata_file"], metadata_path)
        with np.load(npz_path, allow_pickle=False) as payload:
            self.example_ids = tuple(str(value) for value in payload["example_ids"])
            self.features_a = _require_float32(payload["features_a"], "features_a")
            self.features_b = _require_float32(payload["features_b"], "features_b")
            self.global_features = _require_float32(payload["global_features"], "global_features")
            self.length_condition = _require_float32(payload["length_condition"], "length_condition")
            self.transition_length_bars = _require_integer_array(
                payload["transition_length_bars"], "transition_length_bars"
            )
            self.sequence_lengths = _require_integer_array(
                payload["sequence_length"], "sequence_length"
            )
        count = len(self.example_ids)
        if int(self.shard["count"]) != count:
            raise ValueError("Variable shard count differs from its manifest")
        if len(set(self.example_ids)) != count:
            raise ValueError("Variable shard contains duplicate example IDs")
        if self.features_a.shape != (count, self.geometry.sequence_length, 54):
            raise ValueError(f"Invalid features_a shape: {self.features_a.shape}")
        if self.features_b.shape != (count, self.geometry.sequence_length, 54):
            raise ValueError(f"Invalid features_b shape: {self.features_b.shape}")
        if self.global_features.shape != (count, 16):
            raise ValueError(f"Invalid global_features shape: {self.global_features.shape}")
        if self.length_condition.shape != (count, 1):
            raise ValueError(f"Invalid length_condition shape: {self.length_condition.shape}")
        if self.transition_length_bars.shape != (count,):
            raise ValueError(f"Invalid transition_length_bars shape: {self.transition_length_bars.shape}")
        if self.sequence_lengths.shape != (count,):
            raise ValueError(f"Invalid sequence_length shape: {self.sequence_lengths.shape}")
        if np.any(self.transition_length_bars != self.geometry.transition_length_bars):
            raise ValueError("Shard transition_length_bars does not match its path")
        if np.any(self.sequence_lengths != self.geometry.sequence_length):
            raise ValueError("Shard sequence_length does not match its path")
        validate_variable_feature_batch(
            self.features_a,
            transition_length_bars=self.geometry.transition_length_bars,
            name="features_a",
        )
        validate_variable_feature_batch(
            self.features_b,
            transition_length_bars=self.geometry.transition_length_bars,
            name="features_b",
        )
        validate_length_condition(
            self.length_condition,
            transition_length_bars=self.geometry.transition_length_bars,
        )
        metadata = [
            json.loads(line)
            for line in metadata_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        metadata_by_id = {item["example_id"]: item for item in metadata}
        if len(metadata_by_id) != len(metadata) or set(metadata_by_id) != set(self.example_ids):
            raise ValueError("Variable shard metadata does not match example_ids")
        self.examples = tuple(metadata_by_id[example_id] for example_id in self.example_ids)
        if any(item.get("split") != self.split for item in self.examples):
            raise ValueError("Variable shard metadata contains another split")
        for item in self.examples:
            if int(item["transition_length_bars"]) != self.geometry.transition_length_bars:
                raise ValueError("Variable shard metadata contains another length")
            if int(item["sequence_length"]) != self.geometry.sequence_length:
                raise ValueError("Variable shard metadata contains another sequence length")

    def __len__(self):
        return len(self.example_ids)

    def __getitem__(self, index):
        index = int(index)
        item = {
            "example_id": self.example_ids[index],
            "split": self.split,
            "transition_length_bars": self.geometry.transition_length_bars,
            "sequence_length": self.geometry.sequence_length,
            "features_a": torch.from_numpy(self.features_a[index]),
            "features_b": torch.from_numpy(self.features_b[index]),
            "global_features": torch.from_numpy(self.global_features[index]),
            "length_condition": torch.from_numpy(self.length_condition[index]),
        }
        if self.waveform_loader is not None:
            item.update(
                _normalise_waveform_payload(
                    self.waveform_loader(self.examples[index], self.geometry),
                )
            )
        return item


class VariableFeatureDatasetCollection(Dataset):
    """Read all requested v2 length shards while retaining shard identity.

    A collection is intentionally not directly stackable by a default
    ``DataLoader``.  Use :class:`VariableLengthBatchSampler` so every batch
    contains one ``T``.  This keeps the base representation unpadded.
    """

    def __init__(
        self,
        dataset_directory,
        split,
        *,
        transition_length_bars=None,
        waveform_loader: Callable | None = None,
    ):
        requested = (
            tuple(
                geometry_for_length(value).transition_length_bars
                for value in transition_length_bars
            )
            if transition_length_bars is not None
            else tuple(
                geometry_for_length(value).transition_length_bars
                for value in SUPPORTED_VARIABLE_LENGTHS
            )
        )
        if not requested:
            raise ValueError("At least one transition length is required")
        if len(set(requested)) != len(requested):
            raise ValueError("transition_length_bars must not contain duplicates")
        self.lengths = tuple(sorted(requested))
        self.datasets = tuple(
            VariableFeatureDataset(
                dataset_directory,
                length,
                split,
                waveform_loader=waveform_loader,
            )
            for length in self.lengths
        )
        self._locations = tuple(
            (dataset_index, local_index)
            for dataset_index, dataset in enumerate(self.datasets)
            for local_index in range(len(dataset))
        )
        self._indices_by_length = {
            length: tuple(
                global_index
                for global_index, (dataset_index, _local_index) in enumerate(self._locations)
                if self.lengths[dataset_index] == length
            )
            for length in self.lengths
        }

    def __len__(self):
        return len(self._locations)

    def __getitem__(self, index):
        dataset_index, local_index = self._locations[int(index)]
        return self.datasets[dataset_index][local_index]

    def indices_by_length(self):
        """Return immutable global-index groups, including empty shards."""

        return {length: indices for length, indices in self._indices_by_length.items()}


class VariableFeatureControlDataset(VariableFeatureDatasetCollection):
    """Dataset-2 ML view with optional immutable, variable-length waveforms.

    ``waveform_loader(example_metadata, geometry)`` must return a mapping with
    ``source_audio`` and ``target_audio``.  Optional vocal keys are preserved.
    The callback is deliberately explicit so the v2 path cannot accidentally
    reuse the v1 cache's minimum-length truncation policy.
    """

    pass


class VariableLengthBatchSampler(Sampler[list[int]]):
    """Yield batches from one length group only; never pad across lengths."""

    def __init__(self, dataset, batch_size, *, shuffle=False, seed=0, drop_last=False):
        if not isinstance(dataset, VariableFeatureDatasetCollection):
            raise TypeError("dataset must be a VariableFeatureDatasetCollection")
        self.dataset = dataset
        self.batch_size = int(batch_size)
        self.shuffle = bool(shuffle)
        self.seed = int(seed)
        self.drop_last = bool(drop_last)
        if self.batch_size < 1:
            raise ValueError("batch_size must be at least 1")

    def __iter__(self):
        generator = torch.Generator()
        generator.manual_seed(self.seed)
        groups = []
        for length in self.dataset.lengths:
            indices = list(self.dataset.indices_by_length()[length])
            if self.shuffle and indices:
                order = torch.randperm(len(indices), generator=generator).tolist()
                indices = [indices[position] for position in order]
            groups.extend(
                indices[start : start + self.batch_size]
                for start in range(0, len(indices), self.batch_size)
                if not self.drop_last or len(indices[start : start + self.batch_size]) == self.batch_size
            )
        if self.shuffle and len(groups) > 1:
            order = torch.randperm(len(groups), generator=generator).tolist()
            groups = [groups[position] for position in order]
        yield from groups

    def __len__(self):
        total = 0
        for indices in self.dataset.indices_by_length().values():
            total += len(indices) // self.batch_size
            if not self.drop_last and len(indices) % self.batch_size:
                total += 1
        return total


def collate_variable_feature_examples(examples):
    """Stack one homogeneous shard and reject mixed lengths explicitly."""
    examples = tuple(examples)
    if not examples:
        raise ValueError("Cannot collate an empty batch")
    lengths = {int(item["transition_length_bars"]) for item in examples}
    sequences = {int(item["sequence_length"]) for item in examples}
    if len(lengths) != 1 or len(sequences) != 1:
        raise ValueError("Variable feature batches must be homogeneous in length")
    length = next(iter(lengths))
    sequence_length = next(iter(sequences))
    geometry = geometry_for_length(length, sequence_length=sequence_length)
    result = {
        "example_ids": tuple(item["example_id"] for item in examples),
        "transition_length_bars": length,
        "sequence_length": sequence_length,
        "features_a": torch.stack([item["features_a"] for item in examples]),
        "features_b": torch.stack([item["features_b"] for item in examples]),
        "global_features": torch.stack([item["global_features"] for item in examples]),
        "length_condition": torch.stack([item["length_condition"] for item in examples]),
    }
    waveform_keys = (
        "source_audio",
        "target_audio",
        "source_vocal_audio",
        "target_vocal_audio",
    )
    present = {key: [key in item for item in examples] for key in waveform_keys}
    for key, flags in present.items():
        if any(flags) and not all(flags):
            raise ValueError(f"Either every example or no example must contain {key}")
        if all(flags):
            result[key] = tuple(item[key] for item in examples)
    if "source_audio" in result:
        result["source_audio_lengths"] = tuple(
            int(audio.shape[-1]) for audio in result["source_audio"]
        )
        result["target_audio_lengths"] = tuple(
            int(audio.shape[-1]) for audio in result["target_audio"]
        )
    return result


def _normalise_waveform_payload(payload: Mapping):
    if not isinstance(payload, Mapping):
        raise TypeError("waveform_loader must return a mapping")
    required = ("source_audio", "target_audio")
    if any(key not in payload for key in required):
        raise ValueError("waveform_loader must return source_audio and target_audio")
    result = {}
    for key, value in payload.items():
        if key.endswith("_audio"):
            array = np.asarray(value, dtype=np.float32)
            if array.ndim not in (1, 2) or array.shape[-1] < 1:
                raise ValueError(f"{key} must be a non-empty mono or channel-first waveform")
            if not np.isfinite(array).all():
                raise ValueError(f"{key} must contain only finite values")
            result[key] = torch.from_numpy(np.ascontiguousarray(array))
        else:
            result[key] = value
    source = result["source_audio"]
    target = result["target_audio"]
    if source.shape[:-1] != target.shape[:-1] or source.shape[-1] != target.shape[-1]:
        raise ValueError("source_audio and target_audio must have identical shape per example")
    for vocal_name in ("source_vocal_audio", "target_vocal_audio"):
        if vocal_name in result and result[vocal_name].shape != source.shape:
            raise ValueError(
                f"{vocal_name} must have the same shape as source_audio"
            )
    return result


def _require_float32(value, name):
    array = np.asarray(value)
    if array.dtype != np.dtype(np.float32):
        raise TypeError(f"{name} must be stored as float32")
    return array


def _require_integer_array(value, name):
    array = np.asarray(value)
    if not np.issubdtype(array.dtype, np.integer):
        raise TypeError(f"{name} must use an integer dtype")
    return array


def _verify_file(manifest, key, path):
    if not path.is_file():
        raise FileNotFoundError(f"Declared dataset file does not exist: {path}")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != manifest["files"][key]["sha256"]:
        raise ValueError(f"Dataset file hash mismatch: {path}")


def _read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))
