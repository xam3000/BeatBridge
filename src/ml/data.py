"""Feature dataset loading and immutable aligned-bridge waveform caching."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import uuid

import librosa
import numpy as np
import torch
from torch.utils.data import Dataset

from src.analysis.pre_analysis import PreAnalysis
from src.bridge import (
    DEFAULT_FEATURE_CACHE_ROOT,
    extract_aligned_bridge,
    extract_aligned_vocal_bridge,
)
from src.features import (
    FEATURE_DIMENSION,
    GLOBAL_FEATURE_DIMENSION,
    SEQUENCE_LENGTH,
    validate_feature_array,
    validate_global_feature_array,
)
from src.features.vocal import DEFAULT_DEMUCS_MODEL, extract_or_load_vocal_stem
from src.pipeline import DEFAULT_SAMPLE_RATE, PROJECT_ROOT, RENDER_RESULT_FORMAT_VERSION


BRIDGE_WAVEFORM_CACHE_FORMAT_VERSION = 1
BRIDGE_WAVEFORM_EXTRACTOR_VERSION = 1
DEFAULT_TRAINING_SAMPLE_RATE = 11_025
DEFAULT_BRIDGE_WAVEFORM_CACHE_ROOT = Path("output") / "ml_cache" / "bridge_waveform_v1"
VOCAL_BRIDGE_WAVEFORM_CACHE_FORMAT_VERSION = 2
VOCAL_BRIDGE_WAVEFORM_EXTRACTOR_VERSION = 2
DEFAULT_VOCAL_BRIDGE_WAVEFORM_CACHE_ROOT = (
    Path("output") / "ml_cache" / "bridge_waveform_v2_vocal"
)
TIME_STRETCH_POLICY = "ffmpeg_librubberband_then_cli_r3"


@dataclass(frozen=True)
class BridgeWaveformArtifact:
    """One immutable pair of aligned training waveforms."""

    cache_directory: Path
    manifest: dict
    source_audio: np.ndarray
    target_audio: np.ndarray
    cache_hit: bool


@dataclass(frozen=True)
class VocalBridgeWaveformArtifact(BridgeWaveformArtifact):
    """Aligned mix and vocal-stem waveforms for objective-v5 training."""

    source_vocal_audio: np.ndarray
    target_vocal_audio: np.ndarray


def load_or_create_bridge_waveforms(
    example,
    candidate,
    *,
    cache_root=DEFAULT_BRIDGE_WAVEFORM_CACHE_ROOT,
    training_sample_rate=DEFAULT_TRAINING_SAMPLE_RATE,
    render_sample_rate=DEFAULT_SAMPLE_RATE,
    analysis=None,
    analysis_root=Path("output") / "pre_analysis",
    bridge_extractor=extract_aligned_bridge,
    build_missing=True,
    verify_audio_hashes=True,
):
    """Load an immutable bridge cache entry or render and store it once."""
    training_sample_rate = int(training_sample_rate)
    render_sample_rate = int(render_sample_rate)
    if training_sample_rate <= 0 or render_sample_rate <= 0:
        raise ValueError("Sample rates must be greater than 0")
    _validate_example_candidate_identity(example, candidate)
    cache_config = _bridge_cache_config(
        example,
        candidate,
        training_sample_rate=training_sample_rate,
        render_sample_rate=render_sample_rate,
    )
    cache_id = hashlib.sha256(
        json.dumps(cache_config, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()[:20]
    cache_directory = (
        Path(cache_root)
        / str(example["example_id"])
        / cache_id
    )
    cached = _load_cached_bridge(cache_directory, cache_config)
    if cached is not None:
        return cached
    if cache_directory.exists():
        raise ValueError(f"Existing bridge cache is invalid: {cache_directory}")
    if not build_missing:
        raise FileNotFoundError(f"Bridge waveform cache is missing: {cache_directory}")
    if verify_audio_hashes:
        _verify_candidate_audio_hashes(candidate)

    analysis = analysis or PreAnalysis(str(Path(analysis_root)) + os.sep)
    source_audio, target_audio, geometry = bridge_extractor(
        candidate,
        analysis,
        sample_rate=render_sample_rate,
        include_context_audio=False,
    )
    if training_sample_rate != render_sample_rate:
        source_audio = librosa.resample(
            source_audio,
            orig_sr=render_sample_rate,
            target_sr=training_sample_rate,
            axis=-1,
            res_type="soxr_hq",
        )
        target_audio = librosa.resample(
            target_audio,
            orig_sr=render_sample_rate,
            target_sr=training_sample_rate,
            axis=-1,
            res_type="soxr_hq",
        )
    source_audio, target_audio = _validate_waveforms(source_audio, target_audio)
    geometry = {
        key: value
        for key, value in geometry.items()
        if key not in {"source_audio", "target_audio"}
    }
    manifest = {
        **cache_config,
        "cache_id": cache_id,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "geometry": geometry,
        "tempo_backend": geometry.get("tempo_backend"),
        "waveforms": {
            "path": "bridge_waveforms.npz",
            "source_shape": list(source_audio.shape),
            "target_shape": list(target_audio.shape),
            "dtype": "float32",
            "source_array_sha256": _array_sha256(source_audio),
            "target_array_sha256": _array_sha256(target_audio),
        },
    }
    temporary_directory = cache_directory.with_name(
        f".{cache_directory.name}.{uuid.uuid4().hex}.tmp"
    )
    temporary_directory.mkdir(parents=True)
    try:
        waveform_path = temporary_directory / "bridge_waveforms.npz"
        np.savez_compressed(
            waveform_path,
            source_audio=source_audio,
            target_audio=target_audio,
        )
        manifest["waveforms"]["file_sha256"] = _file_sha256(waveform_path)
        (temporary_directory / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        cache_directory.parent.mkdir(parents=True, exist_ok=True)
        try:
            os.replace(temporary_directory, cache_directory)
        except (FileExistsError, PermissionError):
            # Two cache builders may finish the same immutable entry at once.
            # Windows reports the already-published destination as WinError 5
            # instead of consistently using FileExistsError for directories.
            concurrently_published = _load_cached_bridge(cache_directory, cache_config)
            if concurrently_published is None:
                raise
            shutil.rmtree(temporary_directory, ignore_errors=True)
            return concurrently_published
    except Exception:
        shutil.rmtree(temporary_directory, ignore_errors=True)
        raise
    return BridgeWaveformArtifact(
        cache_directory=cache_directory,
        manifest=manifest,
        source_audio=source_audio,
        target_audio=target_audio,
        cache_hit=False,
    )


def load_or_create_vocal_bridge_waveforms(
    example,
    candidate,
    *,
    cache_root=DEFAULT_VOCAL_BRIDGE_WAVEFORM_CACHE_ROOT,
    feature_cache_root=DEFAULT_FEATURE_CACHE_ROOT,
    training_sample_rate=DEFAULT_TRAINING_SAMPLE_RATE,
    render_sample_rate=DEFAULT_SAMPLE_RATE,
    analysis=None,
    analysis_root=Path("output") / "pre_analysis",
    bridge_extractor=extract_aligned_vocal_bridge,
    vocal_stem_loader=extract_or_load_vocal_stem,
    vocal_model=DEFAULT_DEMUCS_MODEL,
    build_missing=True,
    verify_audio_hashes=True,
):
    """Load or atomically build one immutable mix-plus-vocal bridge cache."""
    training_sample_rate = int(training_sample_rate)
    render_sample_rate = int(render_sample_rate)
    if training_sample_rate <= 0 or render_sample_rate <= 0:
        raise ValueError("Sample rates must be greater than 0")
    _validate_example_candidate_identity(example, candidate)
    if verify_audio_hashes:
        _verify_candidate_audio_hashes(candidate)
    vocal_artifacts = {}
    for role in ("source", "target"):
        track = candidate[f"{role}_track"]
        path = Path(track["path"])
        if not path.is_absolute():
            path = PROJECT_ROOT / path
        vocal_artifacts[role] = vocal_stem_loader(
            path,
            cache_root=feature_cache_root,
            source_sha256=track["sha256"],
            model_name=vocal_model,
        )
    cache_config = _vocal_bridge_cache_config(
        example,
        candidate,
        vocal_artifacts,
        training_sample_rate=training_sample_rate,
        render_sample_rate=render_sample_rate,
        vocal_model=vocal_model,
    )
    cache_id = hashlib.sha256(
        json.dumps(cache_config, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()[:20]
    cache_directory = Path(cache_root) / str(example["example_id"]) / cache_id
    cached = _load_cached_vocal_bridge(cache_directory, cache_config)
    if cached is not None:
        return cached
    if cache_directory.exists():
        raise ValueError(f"Existing vocal bridge cache is invalid: {cache_directory}")
    if not build_missing:
        raise FileNotFoundError(f"Vocal bridge waveform cache is missing: {cache_directory}")

    analysis = analysis or PreAnalysis(str(Path(analysis_root)) + os.sep)
    source, target, source_vocal, target_vocal, geometry = bridge_extractor(
        candidate,
        analysis,
        sample_rate=render_sample_rate,
        include_context_audio=False,
        feature_cache_root=feature_cache_root,
        vocal_model=vocal_model,
        source_vocal_artifact=vocal_artifacts["source"],
        target_vocal_artifact=vocal_artifacts["target"],
    )
    if training_sample_rate != render_sample_rate:
        arrays = [
            librosa.resample(
                value,
                orig_sr=render_sample_rate,
                target_sr=training_sample_rate,
                axis=-1,
                res_type="soxr_hq",
            ).astype(np.float32, copy=False)
            for value in (source, target, source_vocal, target_vocal)
        ]
        source, target, source_vocal, target_vocal = arrays
    source, target = _validate_waveforms(source, target)
    source_vocal, target_vocal = _validate_waveforms(source_vocal, target_vocal)
    if source.shape != source_vocal.shape:
        raise ValueError("Mix and vocal bridge waveforms must have identical shapes")
    arrays = {
        "source_audio": source,
        "target_audio": target,
        "source_vocal_audio": source_vocal,
        "target_vocal_audio": target_vocal,
    }
    manifest = {
        **cache_config,
        "cache_id": cache_id,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "geometry": {
            key: value
            for key, value in geometry.items()
            if key not in {
                "source_audio",
                "target_audio",
                "source_vocal_audio",
                "target_vocal_audio",
            }
        },
        "tempo_backend": geometry.get("tempo_backend"),
        "vocal_tempo_backend": geometry.get("vocal_tempo_backend"),
        "waveforms": {
            "path": "bridge_waveforms.npz",
            "dtype": "float32",
            "shape": list(source.shape),
            "array_sha256": {name: _array_sha256(value) for name, value in arrays.items()},
        },
    }
    temporary_directory = cache_directory.with_name(
        f".{cache_directory.name}.{uuid.uuid4().hex}.tmp"
    )
    temporary_directory.mkdir(parents=True)
    try:
        waveform_path = temporary_directory / "bridge_waveforms.npz"
        np.savez_compressed(waveform_path, **arrays)
        manifest["waveforms"]["file_sha256"] = _file_sha256(waveform_path)
        (temporary_directory / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        cache_directory.parent.mkdir(parents=True, exist_ok=True)
        try:
            os.replace(temporary_directory, cache_directory)
        except (FileExistsError, PermissionError):
            concurrently_published = _load_cached_vocal_bridge(cache_directory, cache_config)
            if concurrently_published is None:
                raise
            shutil.rmtree(temporary_directory, ignore_errors=True)
            return concurrently_published
    except Exception:
        shutil.rmtree(temporary_directory, ignore_errors=True)
        raise
    return VocalBridgeWaveformArtifact(
        cache_directory=cache_directory,
        manifest=manifest,
        source_audio=source,
        target_audio=target,
        source_vocal_audio=source_vocal,
        target_vocal_audio=target_vocal,
        cache_hit=False,
    )


class FeatureControlDataset(Dataset):
    """Join one feature split with its cached variable-length bridge audio."""

    def __init__(
        self,
        dataset_directory,
        split,
        *,
        waveform_cache_root=DEFAULT_BRIDGE_WAVEFORM_CACHE_ROOT,
        training_sample_rate=DEFAULT_TRAINING_SAMPLE_RATE,
        render_sample_rate=DEFAULT_SAMPLE_RATE,
        build_missing_waveforms=False,
        analysis=None,
        bridge_extractor=extract_aligned_bridge,
        verify_audio_hashes=True,
    ):
        self.dataset_directory = Path(dataset_directory)
        self.split = str(split)
        if self.split not in {"train", "validation", "test"}:
            raise ValueError("split must be train, validation, or test")
        self.waveform_cache_root = Path(waveform_cache_root)
        self.training_sample_rate = int(training_sample_rate)
        self.render_sample_rate = int(render_sample_rate)
        self.build_missing_waveforms = bool(build_missing_waveforms)
        self.analysis = analysis
        self.bridge_extractor = bridge_extractor
        self.verify_audio_hashes = bool(verify_audio_hashes)

        self.manifest = _read_json(self.dataset_directory / "manifest.json")
        split_path = self.dataset_directory / f"{self.split}.npz"
        _verify_declared_file(self.manifest, self.split, split_path)
        examples_path = self.dataset_directory / "examples.jsonl"
        _verify_declared_file(self.manifest, "examples", examples_path)
        with np.load(split_path, allow_pickle=False) as payload:
            self.example_ids = tuple(str(value) for value in payload["example_ids"])
            self.features_a = np.asarray(payload["features_a"], dtype=np.float32)
            self.features_b = np.asarray(payload["features_b"], dtype=np.float32)
            self.global_features = np.asarray(
                payload["global_features"],
                dtype=np.float32,
            )
        _validate_split_arrays(
            self.example_ids,
            self.features_a,
            self.features_b,
            self.global_features,
        )
        metadata = [
            json.loads(line)
            for line in examples_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        metadata_by_id = {item["example_id"]: item for item in metadata}
        if len(metadata_by_id) != len(metadata):
            raise ValueError("examples.jsonl contains duplicate example IDs")
        self.examples = tuple(metadata_by_id[example_id] for example_id in self.example_ids)
        if any(item["split"] != self.split for item in self.examples):
            raise ValueError("Split NPZ contains metadata assigned to another split")
        self._candidate_cache = {}

    def __len__(self):
        return len(self.example_ids)

    def __getitem__(self, index):
        index = int(index)
        example = self.examples[index]
        candidate = self._candidate_for_example(example)
        waveform = load_or_create_bridge_waveforms(
            example,
            candidate,
            cache_root=self.waveform_cache_root,
            training_sample_rate=self.training_sample_rate,
            render_sample_rate=self.render_sample_rate,
            analysis=self.analysis,
            bridge_extractor=self.bridge_extractor,
            build_missing=self.build_missing_waveforms,
            verify_audio_hashes=self.verify_audio_hashes,
        )
        return {
            "example_id": example["example_id"],
            "split": self.split,
            "features_a": torch.from_numpy(self.features_a[index]),
            "features_b": torch.from_numpy(self.features_b[index]),
            "global_features": torch.from_numpy(self.global_features[index]),
            "source_audio": torch.from_numpy(waveform.source_audio),
            "target_audio": torch.from_numpy(waveform.target_audio),
            "waveform_cache_hit": waveform.cache_hit,
            "waveform_cache_directory": str(waveform.cache_directory),
            "tempo_backend": waveform.manifest.get("tempo_backend"),
        }

    def _candidate_for_example(self, example):
        manifest_path = Path(example["pair_manifest_path"])
        key = str(manifest_path)
        if key not in self._candidate_cache:
            if _file_sha256(manifest_path) != example["pair_manifest_sha256"]:
                raise ValueError(f"Pair manifest hash differs from dataset: {manifest_path}")
            pair_manifest = _read_json(manifest_path)
            self._candidate_cache[key] = {
                item["candidate_id"]: item
                for item in pair_manifest["candidate_generation"]["candidates"]
            }
        try:
            return self._candidate_cache[key][example["candidate_id"]]
        except KeyError as error:
            raise ValueError(
                f"Candidate {example['candidate_id']} is missing from {manifest_path}"
            ) from error


class VocalFeatureControlDataset(FeatureControlDataset):
    """Feature split joined with aligned mix and Demucs-vocal waveforms."""

    def __init__(
        self,
        dataset_directory,
        split,
        *,
        waveform_cache_root=DEFAULT_VOCAL_BRIDGE_WAVEFORM_CACHE_ROOT,
        feature_cache_root=DEFAULT_FEATURE_CACHE_ROOT,
        training_sample_rate=DEFAULT_TRAINING_SAMPLE_RATE,
        render_sample_rate=DEFAULT_SAMPLE_RATE,
        build_missing_waveforms=False,
        analysis=None,
        bridge_extractor=extract_aligned_vocal_bridge,
        vocal_stem_loader=extract_or_load_vocal_stem,
        vocal_model=DEFAULT_DEMUCS_MODEL,
        verify_audio_hashes=True,
    ):
        super().__init__(
            dataset_directory,
            split,
            waveform_cache_root=waveform_cache_root,
            training_sample_rate=training_sample_rate,
            render_sample_rate=render_sample_rate,
            build_missing_waveforms=build_missing_waveforms,
            analysis=analysis,
            bridge_extractor=bridge_extractor,
            verify_audio_hashes=verify_audio_hashes,
        )
        self.feature_cache_root = Path(feature_cache_root)
        self.vocal_stem_loader = vocal_stem_loader
        self.vocal_model = str(vocal_model)

    def __getitem__(self, index):
        index = int(index)
        example = self.examples[index]
        candidate = self._candidate_for_example(example)
        waveform = load_or_create_vocal_bridge_waveforms(
            example,
            candidate,
            cache_root=self.waveform_cache_root,
            feature_cache_root=self.feature_cache_root,
            training_sample_rate=self.training_sample_rate,
            render_sample_rate=self.render_sample_rate,
            analysis=self.analysis,
            bridge_extractor=self.bridge_extractor,
            vocal_stem_loader=self.vocal_stem_loader,
            vocal_model=self.vocal_model,
            build_missing=self.build_missing_waveforms,
            verify_audio_hashes=self.verify_audio_hashes,
        )
        return {
            "example_id": example["example_id"],
            "split": self.split,
            "features_a": torch.from_numpy(self.features_a[index]),
            "features_b": torch.from_numpy(self.features_b[index]),
            "global_features": torch.from_numpy(self.global_features[index]),
            "source_audio": torch.from_numpy(waveform.source_audio),
            "target_audio": torch.from_numpy(waveform.target_audio),
            "source_vocal_audio": torch.from_numpy(waveform.source_vocal_audio),
            "target_vocal_audio": torch.from_numpy(waveform.target_vocal_audio),
            "waveform_cache_hit": waveform.cache_hit,
            "waveform_cache_directory": str(waveform.cache_directory),
            "tempo_backend": waveform.manifest.get("tempo_backend"),
            "vocal_tempo_backend": waveform.manifest.get("vocal_tempo_backend"),
        }


def collate_feature_control_examples(examples):
    """Stack fixed-size features while preserving variable-length audio tensors."""
    examples = tuple(examples)
    if not examples:
        raise ValueError("Cannot collate an empty batch")
    result = {
        "example_ids": tuple(item["example_id"] for item in examples),
        "features_a": torch.stack([item["features_a"] for item in examples]),
        "features_b": torch.stack([item["features_b"] for item in examples]),
        "global_features": torch.stack(
            [item["global_features"] for item in examples]
        ),
        "source_audio": tuple(item["source_audio"] for item in examples),
        "target_audio": tuple(item["target_audio"] for item in examples),
        "waveform_cache_hits": tuple(
            bool(item["waveform_cache_hit"]) for item in examples
        ),
    }
    vocal_keys = ("source_vocal_audio", "target_vocal_audio")
    vocal_presence = [all(key in item for key in vocal_keys) for item in examples]
    if any(vocal_presence) and not all(vocal_presence):
        raise ValueError("Either every example or no example must contain vocal waveforms")
    if all(vocal_presence):
        for key in vocal_keys:
            result[key] = tuple(item[key] for item in examples)
    return result


def _bridge_cache_config(example, candidate, *, training_sample_rate, render_sample_rate):
    return {
        "format_version": BRIDGE_WAVEFORM_CACHE_FORMAT_VERSION,
        "extractor_version": BRIDGE_WAVEFORM_EXTRACTOR_VERSION,
        "rendering_protocol_version": RENDER_RESULT_FORMAT_VERSION,
        "example_id": str(example["example_id"]),
        "candidate_id": str(candidate["candidate_id"]),
        "source_sha256": str(candidate["source_track"]["sha256"]).lower(),
        "target_sha256": str(candidate["target_track"]["sha256"]).lower(),
        "source_cue_sample_44100": int(candidate["source_cutpoint"]["sample"]),
        "target_cue_sample_44100": int(candidate["target_cutpoint"]["sample"]),
        "source_bpm": float(candidate["source_bpm"]),
        "target_bpm": float(candidate["target_bpm"]),
        "transition_length_beats": int(candidate["transition_length_beats"]),
        "training_sample_rate": int(training_sample_rate),
        "render_sample_rate": int(render_sample_rate),
        "channels": 2,
        "time_stretch_policy": TIME_STRETCH_POLICY,
    }


def _vocal_bridge_cache_config(
    example,
    candidate,
    vocal_artifacts,
    *,
    training_sample_rate,
    render_sample_rate,
    vocal_model,
):
    base = _bridge_cache_config(
        example,
        candidate,
        training_sample_rate=training_sample_rate,
        render_sample_rate=render_sample_rate,
    )
    return {
        **base,
        "format_version": VOCAL_BRIDGE_WAVEFORM_CACHE_FORMAT_VERSION,
        "extractor_version": VOCAL_BRIDGE_WAVEFORM_EXTRACTOR_VERSION,
        "vocal_model": str(vocal_model),
        "source_vocal_artifact_sha256": vocal_artifacts["source"].manifest["artifact_sha256"],
        "target_vocal_artifact_sha256": vocal_artifacts["target"].manifest["artifact_sha256"],
    }


def _load_cached_bridge(cache_directory, expected_config):
    manifest_path = cache_directory / "manifest.json"
    waveform_path = cache_directory / "bridge_waveforms.npz"
    if not manifest_path.is_file() or not waveform_path.is_file():
        return None
    manifest = _read_json(manifest_path)
    for key, value in expected_config.items():
        if manifest.get(key) != value:
            return None
    if _file_sha256(waveform_path) != manifest["waveforms"]["file_sha256"]:
        return None
    with np.load(waveform_path, allow_pickle=False) as payload:
        source_audio = np.asarray(payload["source_audio"], dtype=np.float32)
        target_audio = np.asarray(payload["target_audio"], dtype=np.float32)
    source_audio, target_audio = _validate_waveforms(source_audio, target_audio)
    if _array_sha256(source_audio) != manifest["waveforms"]["source_array_sha256"]:
        return None
    if _array_sha256(target_audio) != manifest["waveforms"]["target_array_sha256"]:
        return None
    return BridgeWaveformArtifact(
        cache_directory=cache_directory,
        manifest=manifest,
        source_audio=source_audio,
        target_audio=target_audio,
        cache_hit=True,
    )


def _load_cached_vocal_bridge(cache_directory, expected_config):
    manifest_path = cache_directory / "manifest.json"
    waveform_path = cache_directory / "bridge_waveforms.npz"
    if not manifest_path.is_file() or not waveform_path.is_file():
        return None
    manifest = _read_json(manifest_path)
    if any(manifest.get(key) != value for key, value in expected_config.items()):
        return None
    if _file_sha256(waveform_path) != manifest["waveforms"]["file_sha256"]:
        return None
    names = (
        "source_audio",
        "target_audio",
        "source_vocal_audio",
        "target_vocal_audio",
    )
    with np.load(waveform_path, allow_pickle=False) as payload:
        arrays = {name: np.asarray(payload[name], dtype=np.float32) for name in names}
    source, target = _validate_waveforms(arrays["source_audio"], arrays["target_audio"])
    source_vocal, target_vocal = _validate_waveforms(
        arrays["source_vocal_audio"],
        arrays["target_vocal_audio"],
    )
    if source.shape != source_vocal.shape:
        return None
    if any(
        _array_sha256(arrays[name]) != manifest["waveforms"]["array_sha256"][name]
        for name in names
    ):
        return None
    return VocalBridgeWaveformArtifact(
        cache_directory=cache_directory,
        manifest=manifest,
        source_audio=source,
        target_audio=target,
        source_vocal_audio=source_vocal,
        target_vocal_audio=target_vocal,
        cache_hit=True,
    )


def _validate_waveforms(source_audio, target_audio):
    source_audio = np.ascontiguousarray(source_audio, dtype=np.float32)
    target_audio = np.ascontiguousarray(target_audio, dtype=np.float32)
    if source_audio.ndim != 2 or target_audio.ndim != 2:
        raise ValueError("Bridge waveforms must have shape (channels, samples)")
    if source_audio.shape != target_audio.shape:
        raise ValueError("Source and target bridge waveforms must have identical shapes")
    if source_audio.shape[0] != 2 or source_audio.shape[-1] == 0:
        raise ValueError("Bridge waveforms must be non-empty stereo audio")
    if not np.isfinite(source_audio).all() or not np.isfinite(target_audio).all():
        raise ValueError("Bridge waveforms must contain only finite values")
    return source_audio, target_audio


def _validate_split_arrays(example_ids, features_a, features_b, global_features):
    count = len(example_ids)
    if len(set(example_ids)) != count:
        raise ValueError("Split NPZ contains duplicate example IDs")
    if features_a.shape != (count, SEQUENCE_LENGTH, FEATURE_DIMENSION):
        raise ValueError(f"Invalid features_a shape: {features_a.shape}")
    if features_b.shape != (count, SEQUENCE_LENGTH, FEATURE_DIMENSION):
        raise ValueError(f"Invalid features_b shape: {features_b.shape}")
    if global_features.shape != (count, GLOBAL_FEATURE_DIMENSION):
        raise ValueError(f"Invalid global_features shape: {global_features.shape}")
    validate_feature_array(features_a, name="features_a")
    validate_feature_array(features_b, name="features_b")
    validate_global_feature_array(global_features, name="global_features")


def _validate_example_candidate_identity(example, candidate):
    checks = (
        ("candidate_id", candidate["candidate_id"], example["candidate_id"]),
        ("source hash", candidate["source_track"]["sha256"], example["source_track"]["sha256"]),
        ("target hash", candidate["target_track"]["sha256"], example["target_track"]["sha256"]),
        ("source cue", candidate["source_cutpoint"]["sample"], example["source_cutpoint"]["sample"]),
        ("target cue", candidate["target_cutpoint"]["sample"], example["target_cutpoint"]["sample"]),
    )
    for name, actual, expected in checks:
        if str(actual).lower() != str(expected).lower():
            raise ValueError(f"Dataset/candidate {name} mismatch: {actual} != {expected}")


def _verify_candidate_audio_hashes(candidate):
    for role in ("source", "target"):
        track = candidate[f"{role}_track"]
        path = Path(track["path"])
        if not path.is_absolute():
            path = PROJECT_ROOT / path
        if _file_sha256(path) != str(track["sha256"]).lower():
            raise ValueError(f"{role} audio hash differs from candidate: {path}")


def _verify_declared_file(manifest, name, path):
    declared = manifest.get("files", {}).get(name)
    if declared is None:
        raise ValueError(f"Dataset manifest does not declare {name}")
    if _file_sha256(path) != declared["sha256"]:
        raise ValueError(f"Dataset file hash mismatch: {path}")


def _read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _array_sha256(array):
    digest = hashlib.sha256()
    digest.update(str(array.dtype).encode("ascii"))
    digest.update(json.dumps(list(array.shape)).encode("ascii"))
    digest.update(np.ascontiguousarray(array).tobytes())
    return digest.hexdigest()


def _file_sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
