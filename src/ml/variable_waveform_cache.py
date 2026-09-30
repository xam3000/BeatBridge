"""Immutable waveform cache for the variable-length ML contract.

The historical bridge caches deliberately keep their own semantics.  This
module implements the additive ``local_grid_target_to_source_v1`` contract:
the source grid owns the output duration, while the target window is stretched
with Rubber Band before the common training-rate resample.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
import time
import uuid

import librosa
import numpy as np
import soundfile as sf

from src.features.variable_contract import (
    SUPPORTED_VARIABLE_LENGTHS,
    VariableTransitionGeometry,
    geometry_for_length,
)
from src.pipeline import PROJECT_ROOT
from src.tempo.time_stretch import TimeStretch, TimeStretchBackendError


VARIABLE_WAVEFORM_CACHE_FORMAT_VERSION = 2
VARIABLE_WAVEFORM_CACHE_EXTRACTOR_VERSION = 1
VARIABLE_WAVEFORM_ALIGNMENT_CONTRACT = "local_grid_target_to_source_v1"
VARIABLE_WAVEFORM_CACHE_ROOT = Path("output") / "ml_cache" / "variable_bridge_waveform_v2"
VARIABLE_WAVEFORM_CHANNEL_ORDER = ("left", "right")
VARIABLE_WAVEFORM_DTYPE = "float32"
VARIABLE_WAVEFORM_SAMPLE_RATE = 11_025
VARIABLE_WAVEFORM_RENDER_SAMPLE_RATE = 44_100
VARIABLE_WAVEFORM_ROUNDING_TOLERANCE_SAMPLES = 2
VARIABLE_WAVEFORM_ROUNDING_CORRECTION_VERSION = 1
VARIABLE_WAVEFORM_TEMPO_BACKEND_VERSION = "rubberband_backend_protocol_v1"
VARIABLE_WAVEFORM_CACHE_INDEX_FORMAT_VERSION = 1
VARIABLE_WAVEFORM_CACHE_INDEX_NAME = "index.json"


class VariableWaveformAlignmentReject(ValueError):
    """A candidate cannot satisfy the versioned alignment contract."""

    def __init__(self, reason, diagnostics):
        self.reason = str(reason)
        self.diagnostics = dict(diagnostics)
        super().__init__(f"{self.reason}: {json.dumps(self.diagnostics, sort_keys=True)}")


@dataclass(frozen=True)
class VariableWaveformCacheArtifact:
    """One validated, immutable four-waveform cache entry."""

    cache_directory: Path
    manifest: dict
    source_audio: np.ndarray
    target_audio: np.ndarray
    source_vocal_audio: np.ndarray
    target_vocal_audio: np.ndarray
    cache_hit: bool


def load_or_create_variable_waveform_cache(
    example,
    geometry: VariableTransitionGeometry | None = None,
    *,
    dataset_id,
    dataset_manifest_sha256,
    cache_root=VARIABLE_WAVEFORM_CACHE_ROOT,
    feature_cache_root=None,
    training_sample_rate=VARIABLE_WAVEFORM_SAMPLE_RATE,
    render_sample_rate=VARIABLE_WAVEFORM_RENDER_SAMPLE_RATE,
    build_missing=True,
    verify_audio_hashes=True,
    time_stretch=None,
    audio_loader=None,
    vocal_loader=None,
    resampler=None,
    rounding_tolerance_samples=VARIABLE_WAVEFORM_ROUNDING_TOLERANCE_SAMPLES,
    supported_lengths=None,
):
    """Load or publish one immutable variable-v2 waveform entry.

    ``build_missing=False`` is the normal training-loader mode.  An existing
    directory is never repaired in place: a missing, corrupt, or contradictory
    entry is rejected so provenance cannot be silently changed.
    """

    geometry = geometry or geometry_for_length(example.get("transition_length_bars"))
    geometry = geometry_for_length(
        geometry.transition_length_bars,
        sequence_length=geometry.sequence_length,
        transition_length_beats=geometry.transition_length_beats,
    )
    training_sample_rate = int(training_sample_rate)
    render_sample_rate = int(render_sample_rate)
    tolerance = int(rounding_tolerance_samples)
    if training_sample_rate <= 0 or render_sample_rate <= 0:
        raise ValueError("Sample rates must be greater than 0")
    if tolerance < 0:
        raise ValueError("rounding_tolerance_samples must be non-negative")
    _validate_example(example, geometry)
    dataset_manifest_sha256 = str(dataset_manifest_sha256).lower()
    if not _is_sha256(dataset_manifest_sha256):
        raise ValueError("dataset_manifest_sha256 must be a SHA-256 digest")
    cache_config = _cache_config(
        example,
        geometry,
        dataset_id=str(dataset_id),
        dataset_manifest_sha256=dataset_manifest_sha256,
        training_sample_rate=training_sample_rate,
        render_sample_rate=render_sample_rate,
        rounding_tolerance_samples=tolerance,
    )
    cache_id = _cache_id(cache_config)
    cache_directory = (
        Path(cache_root) / "entries" / str(example["example_id"]) / cache_id
    )
    _ensure_root_manifest(
        Path(cache_root),
        dataset_id=str(dataset_id),
        dataset_manifest_sha256=dataset_manifest_sha256,
        training_sample_rate=training_sample_rate,
        render_sample_rate=render_sample_rate,
        rounding_tolerance_samples=tolerance,
        supported_lengths=supported_lengths or (geometry.transition_length_bars,),
    )
    cached = _load_cached_entry(cache_directory, cache_config)
    if cached is not None:
        return cached
    if cache_directory.exists():
        raise ValueError(f"Existing variable-v2 cache entry is invalid: {cache_directory}")
    if not build_missing:
        raise FileNotFoundError(f"Variable-v2 waveform cache is missing: {cache_directory}")

    if audio_loader is None or vocal_loader is None:
        prepared = _load_real_window_inputs(
            example,
            geometry,
            feature_cache_root=feature_cache_root,
            render_sample_rate=render_sample_rate,
            verify_audio_hashes=verify_audio_hashes,
            time_stretch=time_stretch or TimeStretch(),
            tolerance=tolerance,
        )
    else:
        prepared = _load_injected_window_inputs(
            example,
            geometry,
            audio_loader=audio_loader,
            vocal_loader=vocal_loader,
        )

    aligned = align_variable_waveform_windows(
        prepared["source_mix"],
        prepared["target_mix"],
        prepared["source_vocal"],
        prepared["target_vocal"],
        source_window=prepared["source_window"],
        target_window=prepared["target_window"],
        source_bpm=float(example["source_bpm"]),
        target_bpm=float(example["target_bpm"]),
        render_sample_rate=render_sample_rate,
        training_sample_rate=training_sample_rate,
        time_stretch=time_stretch or TimeStretch(),
        resampler=resampler,
        rounding_tolerance_samples=tolerance,
        provenance=prepared["provenance"],
        target_stretch_context=prepared.get("target_stretch_context"),
    )
    arrays = {
        "source_audio": aligned.source_audio,
        "target_audio": aligned.target_audio,
        "source_vocal_audio": aligned.source_vocal_audio,
        "target_vocal_audio": aligned.target_vocal_audio,
    }
    manifest = {
        **cache_config,
        "cache_id": cache_id,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "alignment": aligned.provenance,
        "waveforms": {
            "path": "waveforms.npz",
            "dtype": VARIABLE_WAVEFORM_DTYPE,
            "sample_rate": training_sample_rate,
            "channel_order": list(VARIABLE_WAVEFORM_CHANNEL_ORDER),
            "shape": list(aligned.source_audio.shape),
            "array_sha256": {
                name: _array_sha256(value) for name, value in arrays.items()
            },
        },
    }
    _publish_entry(cache_directory, manifest, arrays)
    return VariableWaveformCacheArtifact(
        cache_directory=cache_directory,
        manifest=manifest,
        source_audio=aligned.source_audio,
        target_audio=aligned.target_audio,
        source_vocal_audio=aligned.source_vocal_audio,
        target_vocal_audio=aligned.target_vocal_audio,
        cache_hit=False,
    )


def load_variable_waveform_cache(
    example,
    geometry: VariableTransitionGeometry | None = None,
    *,
    dataset_id,
    dataset_manifest_sha256,
    cache_root=VARIABLE_WAVEFORM_CACHE_ROOT,
    training_sample_rate=VARIABLE_WAVEFORM_SAMPLE_RATE,
    render_sample_rate=VARIABLE_WAVEFORM_RENDER_SAMPLE_RATE,
    rounding_tolerance_samples=VARIABLE_WAVEFORM_ROUNDING_TOLERANCE_SAMPLES,
    supported_lengths=None,
):
    """Read one cache entry without opening audio, feature, or test artifacts."""

    return load_or_create_variable_waveform_cache(
        example,
        geometry,
        dataset_id=dataset_id,
        dataset_manifest_sha256=dataset_manifest_sha256,
        cache_root=cache_root,
        training_sample_rate=training_sample_rate,
        render_sample_rate=render_sample_rate,
        build_missing=False,
        rounding_tolerance_samples=rounding_tolerance_samples,
        supported_lengths=supported_lengths,
    )


@dataclass(frozen=True)
class VariableWaveformAlignment:
    source_audio: np.ndarray
    target_audio: np.ndarray
    source_vocal_audio: np.ndarray
    target_vocal_audio: np.ndarray
    provenance: dict


def align_variable_waveform_windows(
    source_mix,
    target_mix,
    source_vocal,
    target_vocal,
    *,
    source_window,
    target_window,
    source_bpm,
    target_bpm,
    render_sample_rate,
    training_sample_rate,
    time_stretch,
    resampler=None,
    rounding_tolerance_samples=VARIABLE_WAVEFORM_ROUNDING_TOLERANCE_SAMPLES,
    provenance=None,
    stretch_pair=None,
    target_stretch_context=None,
):
    """Align already sliced source/target windows under the v2 contract.

    ``source_window`` and ``target_window`` contain the raw grid boundaries at
    ``render_sample_rate``.  ``stretch_pair`` is an injectable test seam and
    must return ``(target_mix, target_vocal, diagnostic_mapping)``.
    """

    source_mix = _stereo_float32(source_mix, "source_mix")
    target_mix = _stereo_float32(target_mix, "target_mix")
    source_vocal = _stereo_float32(source_vocal, "source_vocal")
    target_vocal = _stereo_float32(target_vocal, "target_vocal")
    source_window = _window_tuple(source_window, "source_window")
    target_window = _window_tuple(target_window, "target_window")
    source_raw_length = source_window[1] - source_window[0]
    target_raw_length = target_window[1] - target_window[0]
    if source_raw_length != source_mix.shape[-1] or source_raw_length != source_vocal.shape[-1]:
        raise VariableWaveformAlignmentReject(
            "source_window_payload_length_mismatch",
            {"source_window": list(source_window), "source_mix": list(source_mix.shape), "source_vocal": list(source_vocal.shape)},
        )
    if target_raw_length != target_mix.shape[-1] or target_raw_length != target_vocal.shape[-1]:
        raise VariableWaveformAlignmentReject(
            "target_window_payload_length_mismatch",
            {"target_window": list(target_window), "target_mix": list(target_mix.shape), "target_vocal": list(target_vocal.shape)},
        )
    if source_raw_length <= 0 or target_raw_length <= 0:
        raise VariableWaveformAlignmentReject(
            "empty_grid_window",
            {"source_window": list(source_window), "target_window": list(target_window)},
        )

    local_duration_ratio = float(source_raw_length) / float(target_raw_length)
    target_tempo_factor = float(target_raw_length) / float(source_raw_length)
    global_bpm_ratio = float(target_bpm) / float(source_bpm)
    global_duration_ratio = 1.0 / global_bpm_ratio
    ratio_deviation = local_duration_ratio - global_duration_ratio
    tolerance = int(round(rounding_tolerance_samples))
    if stretch_pair is None:
        stretched_target_mix, stretched_target_vocal, stretch_diagnostic = _strict_stretch_pair(
            target_mix,
            target_vocal,
            render_sample_rate=int(render_sample_rate),
            tempo_factor=target_tempo_factor,
            expected_samples=source_raw_length,
            time_stretch=time_stretch,
            correction_side="start",
            tolerance=tolerance,
            context_pair=target_stretch_context,
        )
    else:
        stretched_target_mix, stretched_target_vocal, stretch_diagnostic = stretch_pair(
            target_mix,
            target_vocal,
            tempo_factor=target_tempo_factor,
            expected_samples=source_raw_length,
            rounding_tolerance_samples=tolerance,
        )
        stretched_target_mix = _stereo_float32(stretched_target_mix, "stretched_target_mix")
        stretched_target_vocal = _stereo_float32(stretched_target_vocal, "stretched_target_vocal")
        if stretched_target_mix.shape != stretched_target_vocal.shape:
            raise VariableWaveformAlignmentReject(
                "target_mix_vocal_shape_mismatch_after_stretch",
                {"target_mix": list(stretched_target_mix.shape), "target_vocal": list(stretched_target_vocal.shape)},
            )
        if stretched_target_mix.shape[-1] != source_raw_length:
            raise VariableWaveformAlignmentReject(
                "target_stretch_output_length_mismatch",
                {"expected": source_raw_length, "actual": int(stretched_target_mix.shape[-1])},
            )

    source_mix, source_resample = _resample_and_correct_pair(
        source_mix,
        source_vocal,
        render_sample_rate=int(render_sample_rate),
        training_sample_rate=int(training_sample_rate),
        expected_samples=int(round(source_raw_length * training_sample_rate / render_sample_rate)),
        correction_side="end",
        tolerance=tolerance,
        resampler=resampler,
    )
    target_mix, target_resample = _resample_and_correct_pair(
        stretched_target_mix,
        stretched_target_vocal,
        render_sample_rate=int(render_sample_rate),
        training_sample_rate=int(training_sample_rate),
        expected_samples=int(round(source_raw_length * training_sample_rate / render_sample_rate)),
        correction_side="start",
        tolerance=tolerance,
        resampler=resampler,
    )
    if source_mix.shape != target_mix.shape or list(source_mix.shape) != source_resample["vocal_shape"]:
        raise VariableWaveformAlignmentReject(
            "final_source_target_shape_mismatch",
            {"source": list(source_mix.shape), "target": list(target_mix.shape), "source_vocal": source_resample["vocal_shape"]},
        )
    source_vocal = source_resample.pop("vocal")
    target_vocal = target_resample.pop("vocal")
    if not (source_mix.shape == target_mix.shape == source_vocal.shape == target_vocal.shape):
        raise VariableWaveformAlignmentReject(
            "final_four_way_shape_mismatch",
            {name: list(value.shape) for name, value in (("source_mix", source_mix), ("target_mix", target_mix), ("source_vocal", source_vocal), ("target_vocal", target_vocal))},
        )
    if not all(np.isfinite(value).all() for value in (source_mix, target_mix, source_vocal, target_vocal)):
        raise VariableWaveformAlignmentReject("non_finite_waveform", {})

    alignment_provenance = {
        **(provenance or {}),
        "alignment_contract": VARIABLE_WAVEFORM_ALIGNMENT_CONTRACT,
        "raw_windows": {
            "source": {"start_sample": source_window[0], "end_sample": source_window[1], "sample_length": source_raw_length},
            "target": {"start_sample": target_window[0], "end_sample": target_window[1], "sample_length": target_raw_length},
            "declared_beats": int(source_window[2] if len(source_window) > 2 else target_window[2] if len(target_window) > 2 else 0),
        },
        "ratios": {
            "local_stretch_ratio_output_over_input": local_duration_ratio,
            "target_tempo_factor": target_tempo_factor,
            "global_bpm_ratio_target_over_source": global_bpm_ratio,
            "global_duration_ratio_source_over_target": global_duration_ratio,
            "local_minus_global_duration_ratio": ratio_deviation,
        },
        "tempo_backend": stretch_diagnostic,
        "canonical_output_length": int(source_mix.shape[-1]),
        "rounding_correction": {
            "version": VARIABLE_WAVEFORM_ROUNDING_CORRECTION_VERSION,
            "tolerance_samples_at_render_rate": tolerance,
            "target_stretch": stretch_diagnostic.get("rounding_correction", {}),
            "source_resample": source_resample,
            "target_resample": target_resample,
        },
    }
    alignment_provenance["raw_windows"]["declared_beats"] = int(
        (source_window[2] if len(source_window) > 2 else target_window[2] if len(target_window) > 2 else 0)
    )
    return VariableWaveformAlignment(
        source_audio=np.ascontiguousarray(source_mix, dtype=np.float32),
        target_audio=np.ascontiguousarray(target_mix, dtype=np.float32),
        source_vocal_audio=np.ascontiguousarray(source_vocal, dtype=np.float32),
        target_vocal_audio=np.ascontiguousarray(target_vocal, dtype=np.float32),
        provenance=alignment_provenance,
    )


def materialize_variable_waveform_cache(
    dataset_directory,
    *,
    cache_root=VARIABLE_WAVEFORM_CACHE_ROOT,
    feature_cache_root=None,
    splits=("train", "validation"),
    transition_lengths=SUPPORTED_VARIABLE_LENGTHS,
    limit=None,
    training_sample_rate=VARIABLE_WAVEFORM_SAMPLE_RATE,
    render_sample_rate=VARIABLE_WAVEFORM_RENDER_SAMPLE_RATE,
    rounding_tolerance_samples=VARIABLE_WAVEFORM_ROUNDING_TOLERANCE_SAMPLES,
):
    """Materialize only explicitly requested non-test Dataset-2 splits."""

    from .variable_data import VariableFeatureDataset

    dataset_directory = Path(dataset_directory)
    dataset_manifest_path = dataset_directory / "manifest.json"
    dataset_manifest = _read_json(dataset_manifest_path)
    if int(dataset_manifest.get("format_version", 0)) != 2:
        raise ValueError("Variable waveform materialization requires Dataset Format 2")
    requested_splits = tuple(str(value) for value in splits)
    if not requested_splits or any(value not in {"train", "validation"} for value in requested_splits):
        raise ValueError("Variable-v2 materialization permits only train and validation")
    lengths = tuple(sorted({geometry_for_length(value).transition_length_bars for value in transition_lengths}))
    if not lengths:
        raise ValueError("At least one transition length is required")
    if limit is not None and int(limit) < 1:
        raise ValueError("limit must be at least 1 when provided")
    report = {
        "format_version": VARIABLE_WAVEFORM_CACHE_FORMAT_VERSION,
        "alignment_contract": VARIABLE_WAVEFORM_ALIGNMENT_CONTRACT,
        "dataset_directory": str(dataset_directory),
        "dataset_id": str(dataset_manifest["dataset_id"]),
        "dataset_manifest_sha256": _file_sha256(dataset_manifest_path),
        "splits": list(requested_splits),
        "lengths": list(lengths),
        "counts": {split: {str(length): {"requested": 0, "cache_hits": 0, "cache_misses": 0, "rejected": 0} for length in lengths} for split in requested_splits},
        "rejections": [],
        "ratio_statistics": {},
    }
    ratios = {length: [] for length in lengths}
    indexed_artifacts = []
    for split in requested_splits:
        for length in lengths:
            dataset = VariableFeatureDataset(dataset_directory, length, split)
            examples = dataset.examples[: int(limit)] if limit is not None else dataset.examples
            for example in examples:
                bucket = report["counts"][split][str(length)]
                bucket["requested"] += 1
                try:
                    artifact = load_or_create_variable_waveform_cache(
                        example,
                        dataset_id=dataset_manifest["dataset_id"],
                        dataset_manifest_sha256=report["dataset_manifest_sha256"],
                        cache_root=cache_root,
                        feature_cache_root=feature_cache_root,
                        training_sample_rate=training_sample_rate,
                        render_sample_rate=render_sample_rate,
                        build_missing=True,
                        rounding_tolerance_samples=rounding_tolerance_samples,
                        supported_lengths=lengths,
                    )
                    bucket["cache_hits" if artifact.cache_hit else "cache_misses"] += 1
                    ratios[length].append(float(artifact.manifest["alignment"]["ratios"]["local_stretch_ratio_output_over_input"]))
                    indexed_artifacts.append((split, length, example, artifact))
                except VariableWaveformAlignmentReject as error:
                    bucket["rejected"] += 1
                    report["rejections"].append({"split": split, "length": length, "example_id": example["example_id"], "reason": error.reason, "diagnostics": error.diagnostics})
    for length, values in ratios.items():
        if values:
            report["ratio_statistics"][str(length)] = {
                "count": len(values), "minimum": min(values), "maximum": max(values), "mean": float(np.mean(values)), "median": float(np.median(values)),
            }
    report_path = Path(cache_root) / "materialization_report.json"
    _write_json_atomic(report_path, report, allow_overwrite=True)
    index = write_variable_waveform_cache_index(
        cache_root,
        dataset_manifest_path=dataset_manifest_path,
        artifacts=indexed_artifacts,
        splits=requested_splits,
        transition_lengths=lengths,
    )
    report["cache_index"] = {
        "path": str(Path(cache_root) / VARIABLE_WAVEFORM_CACHE_INDEX_NAME),
        "file_sha256": _file_sha256(Path(cache_root) / VARIABLE_WAVEFORM_CACHE_INDEX_NAME),
        "payload_sha256": index["payload_sha256"],
        "entry_count": len(index["entries"]),
    }
    _write_json_atomic(report_path, report, allow_overwrite=True)
    return report


def write_variable_waveform_cache_index(
    cache_root,
    *,
    dataset_manifest_path,
    artifacts,
    splits,
    transition_lengths,
):
    """Seal exactly the materialized cache entries in a deterministic index."""

    cache_root = Path(cache_root)
    root_manifest_path = cache_root / "manifest.json"
    if not root_manifest_path.is_file():
        raise FileNotFoundError(f"Variable-v2 cache root manifest is missing: {root_manifest_path}")
    dataset_manifest_path = Path(dataset_manifest_path)
    dataset_manifest_sha256 = _file_sha256(dataset_manifest_path)
    root_manifest = _read_json(root_manifest_path)
    if str(root_manifest.get("dataset_manifest_sha256", "")).lower() != dataset_manifest_sha256:
        raise ValueError("Variable waveform cache root and dataset manifest hashes differ")
    rows = []
    seen = set()
    for split, length, example, artifact in artifacts:
        key = str(example["example_id"])
        if key in seen:
            raise ValueError(f"Duplicate example in waveform cache index: {key}")
        seen.add(key)
        entry_manifest_path = artifact.cache_directory / "manifest.json"
        waveform_path = artifact.cache_directory / "waveforms.npz"
        rows.append({
            "example_id": key,
            "split": str(split),
            "transition_length_bars": int(length),
            "cache_id": str(artifact.manifest["cache_id"]),
            "directory": str(artifact.cache_directory.resolve().relative_to(cache_root.resolve())),
            "manifest_sha256": _file_sha256(entry_manifest_path),
            "waveforms_sha256": _file_sha256(waveform_path),
        })
    payload = {
        "format_version": VARIABLE_WAVEFORM_CACHE_INDEX_FORMAT_VERSION,
        "dataset_manifest_sha256": dataset_manifest_sha256,
        "cache_root_manifest_sha256": _file_sha256(root_manifest_path),
        "splits": sorted({str(value) for value in splits}),
        "transition_lengths_bars": sorted({int(value) for value in transition_lengths}),
        "entries": sorted(rows, key=lambda item: item["example_id"]),
    }
    payload["payload_sha256"] = _canonical_json_sha256(payload)
    _write_json_atomic(cache_root / VARIABLE_WAVEFORM_CACHE_INDEX_NAME, payload)
    return payload


def load_variable_waveform_cache_index(
    cache_root,
    *,
    dataset_manifest_sha256,
    required_splits=("train", "validation"),
    required_lengths=SUPPORTED_VARIABLE_LENGTHS,
):
    """Validate the sealed cache index and every referenced immutable payload."""

    cache_root = Path(cache_root)
    index_path = cache_root / VARIABLE_WAVEFORM_CACHE_INDEX_NAME
    payload = _read_json(index_path)
    if int(payload.get("format_version", 0)) != VARIABLE_WAVEFORM_CACHE_INDEX_FORMAT_VERSION:
        raise ValueError("Unsupported variable waveform cache index format")
    declared_payload_sha = payload.get("payload_sha256")
    unsigned = {key: value for key, value in payload.items() if key != "payload_sha256"}
    if declared_payload_sha != _canonical_json_sha256(unsigned):
        raise ValueError("Variable waveform cache index payload hash differs")
    if str(payload.get("dataset_manifest_sha256", "")).lower() != str(dataset_manifest_sha256).lower():
        raise ValueError("Variable waveform cache index dataset hash differs")
    root_manifest_path = cache_root / "manifest.json"
    if payload.get("cache_root_manifest_sha256") != _file_sha256(root_manifest_path):
        raise ValueError("Variable waveform cache root manifest hash differs")
    if str(_read_json(root_manifest_path).get("dataset_manifest_sha256", "")).lower() != str(dataset_manifest_sha256).lower():
        raise ValueError("Variable waveform cache root dataset hash differs")
    if set(required_splits) - set(payload.get("splits", ())):
        raise ValueError("Variable waveform cache index lacks required splits")
    if {int(value) for value in required_lengths} - {int(value) for value in payload.get("transition_lengths_bars", ())}:
        raise ValueError("Variable waveform cache index lacks required transition lengths")
    entries = {}
    for row in payload.get("entries", ()):
        example_id = str(row["example_id"])
        if example_id in entries:
            raise ValueError(f"Duplicate example in waveform cache index: {example_id}")
        directory = cache_root / row["directory"]
        if _file_sha256(directory / "manifest.json") != row.get("manifest_sha256"):
            raise ValueError(f"Variable waveform entry manifest hash differs: {example_id}")
        if _file_sha256(directory / "waveforms.npz") != row.get("waveforms_sha256"):
            raise ValueError(f"Variable waveform payload hash differs: {example_id}")
        entries[example_id] = row
    return {
        "path": index_path,
        "file_sha256": _file_sha256(index_path),
        "payload": payload,
        "entries": entries,
    }


def build_variable_cache_loader(
    dataset_directory,
    *,
    cache_root=VARIABLE_WAVEFORM_CACHE_ROOT,
    training_sample_rate=VARIABLE_WAVEFORM_SAMPLE_RATE,
    render_sample_rate=VARIABLE_WAVEFORM_RENDER_SAMPLE_RATE,
    require_index=False,
    required_splits=("train", "validation"),
    required_lengths=SUPPORTED_VARIABLE_LENGTHS,
):
    """Return a strict cache-hit-only loader for Dataset-2 train/validation."""

    dataset_directory = Path(dataset_directory)
    manifest_path = dataset_directory / "manifest.json"
    manifest = _read_json(manifest_path)
    dataset_id = manifest["dataset_id"]
    dataset_manifest_sha256 = _file_sha256(manifest_path)
    index = None
    if require_index:
        index = load_variable_waveform_cache_index(
            cache_root,
            dataset_manifest_sha256=dataset_manifest_sha256,
            required_splits=required_splits,
            required_lengths=required_lengths,
        )

    def loader(example, geometry):
        if example.get("split") not in {"train", "validation"}:
            raise ValueError("Variable-v2 cache loader refuses the test split")
        if index is not None and str(example["example_id"]) not in index["entries"]:
            raise FileNotFoundError(
                f"Variable-v2 waveform cache index lacks example: {example['example_id']}"
            )
        artifact = load_variable_waveform_cache(
            example,
            geometry,
            dataset_id=dataset_id,
            dataset_manifest_sha256=dataset_manifest_sha256,
            cache_root=cache_root,
            training_sample_rate=training_sample_rate,
            render_sample_rate=render_sample_rate,
            supported_lengths=tuple(_read_json(Path(cache_root) / "manifest.json").get("supported_lengths", (example.get("transition_length_bars"),))),
        )
        if not artifact.cache_hit:
            raise RuntimeError("Variable-v2 training loader received a non-hit cache entry")
        return {
            "source_audio": artifact.source_audio,
            "target_audio": artifact.target_audio,
            "source_vocal_audio": artifact.source_vocal_audio,
            "target_vocal_audio": artifact.target_vocal_audio,
            "waveform_cache_hit": True,
            "waveform_cache_directory": str(artifact.cache_directory),
            "waveform_manifest": artifact.manifest,
        }

    return loader


def _load_real_window_inputs(example, geometry, *, feature_cache_root, render_sample_rate, verify_audio_hashes, time_stretch, tolerance):
    if feature_cache_root is not None:
        feature_cache_root = Path(feature_cache_root)
    source = _load_feature_window(
        example,
        "source",
        geometry,
        feature_cache_root=feature_cache_root,
        render_sample_rate=render_sample_rate,
        verify_audio_hashes=verify_audio_hashes,
        time_stretch=time_stretch,
        tolerance=tolerance,
    )
    target = _load_feature_window(
        example,
        "target",
        geometry,
        feature_cache_root=feature_cache_root,
        render_sample_rate=render_sample_rate,
        verify_audio_hashes=verify_audio_hashes,
        time_stretch=time_stretch,
        tolerance=tolerance,
    )
    return {
        "source_mix": source["mix"],
        "target_mix": target["mix"],
        "source_vocal": source["vocal"],
        "target_vocal": target["vocal"],
        "source_window": source["window"],
        "target_window": target["window"],
        "provenance": {"source": source["provenance"], "target": target["provenance"]},
        "target_stretch_context": target.get("stretch_context"),
    }


def _load_injected_window_inputs(example, geometry, *, audio_loader, vocal_loader):
    source = audio_loader(example, "source", geometry)
    target = audio_loader(example, "target", geometry)
    source_vocal = vocal_loader(example, "source", geometry)
    target_vocal = vocal_loader(example, "target", geometry)
    source_window = (0, int(np.asarray(source).shape[-1]), geometry.transition_length_beats)
    target_window = (0, int(np.asarray(target).shape[-1]), geometry.transition_length_beats)
    return {"source_mix": source, "target_mix": target, "source_vocal": source_vocal, "target_vocal": target_vocal, "source_window": source_window, "target_window": target_window, "provenance": {}}


def _load_feature_window(example, role, geometry, *, feature_cache_root, render_sample_rate, verify_audio_hashes, time_stretch, tolerance):
    info = example[f"{role}_feature_cache"]
    cache_directory = _resolve_path(info["directory"])
    manifest_path = cache_directory / "manifest.json"
    manifest = _read_json(manifest_path)
    expected_sha = str(example[f"{role}_track"]["sha256"]).lower()
    if str(manifest.get("source_sha256", "")).lower() != expected_sha:
        raise VariableWaveformAlignmentReject("feature_audio_provenance_mismatch", {"role": role, "expected": expected_sha, "actual": manifest.get("source_sha256")})
    grid = example[f"{role}_grid"]
    if manifest.get("beat_grid_sha256") != grid.get("beat_grid_sha256") or manifest.get("beat_grid_metadata", {}).get("beat_grid_sha256") != grid.get("beat_grid_sha256"):
        raise VariableWaveformAlignmentReject("feature_grid_provenance_mismatch", {"role": role, "example_grid": grid.get("beat_grid_sha256"), "feature_grid": manifest.get("beat_grid_sha256")})
    if grid.get("fallback_used") is not False or int(grid.get("format_version", 0)) != 1:
        raise VariableWaveformAlignmentReject("unreliable_grid_provenance", {"role": role, "grid": grid})
    if int(manifest.get("sample_rate", 0)) != int(render_sample_rate):
        raise VariableWaveformAlignmentReject("unsupported_feature_sample_rate", {"role": role, "expected": render_sample_rate, "actual": manifest.get("sample_rate")})
    data_path = cache_directory / manifest["data_file"]
    with np.load(data_path, allow_pickle=False) as payload:
        boundaries = np.asarray(payload["bin_boundaries"], dtype=np.int64)
    if boundaries.ndim != 1 or boundaries.size < geometry.sequence_length + 1 or np.any(np.diff(boundaries) <= 0):
        raise VariableWaveformAlignmentReject("invalid_feature_grid_boundaries", {"role": role, "shape": list(boundaries.shape)})
    cue = int(example[f"aligned_{role}_cue_sample"])
    cue_index = int(np.argmin(np.abs(boundaries - cue)))
    cue_delta = int(boundaries[cue_index] - cue)
    boundary_tolerance = max(2, int(np.median(np.diff(boundaries)) // 2))
    if abs(cue_delta) > boundary_tolerance:
        raise VariableWaveformAlignmentReject("cue_not_on_cached_grid", {"role": role, "cue": cue, "nearest_boundary": int(boundaries[cue_index]), "delta": cue_delta, "tolerance": boundary_tolerance})
    if role == "source":
        start_index, end_index = cue_index, cue_index + geometry.sequence_length
    else:
        start_index, end_index = cue_index - geometry.sequence_length, cue_index
    if start_index < 0 or end_index >= boundaries.size:
        raise VariableWaveformAlignmentReject("insufficient_cached_grid_context", {"role": role, "cue_index": cue_index, "sequence_length": geometry.sequence_length, "boundary_count": int(boundaries.size)})
    start_sample, end_sample = int(boundaries[start_index]), int(boundaries[end_index])
    audio_path = _resolve_path(manifest["source_path"])
    if verify_audio_hashes and _file_sha256(audio_path) != expected_sha:
        raise ValueError(f"{role} audio hash differs from feature cache: {audio_path}")
    mix, source_rate = _read_stereo(audio_path)
    vocal, vocal_manifest = _read_vocal_artifact(manifest, expected_sha)
    mix, vocal, prep = _prepare_aligned_audio_pair(
        mix, source_rate, vocal, int(vocal_manifest["sample_rate"]), manifest, render_sample_rate, time_stretch, tolerance
    )
    if end_sample > mix.shape[-1] or end_sample > vocal.shape[-1]:
        raise VariableWaveformAlignmentReject("audio_shorter_than_feature_grid", {"role": role, "end_sample": end_sample, "mix_samples": int(mix.shape[-1]), "vocal_samples": int(vocal.shape[-1])})
    result = {
        "mix": mix[..., start_sample:end_sample].astype(np.float32, copy=False),
        "vocal": vocal[..., start_sample:end_sample].astype(np.float32, copy=False),
        "window": (start_sample, end_sample, geometry.transition_length_beats),
        "provenance": {"feature_cache_manifest_sha256": _file_sha256(manifest_path), "feature_cache_directory": str(cache_directory), "grid_hash": grid["beat_grid_sha256"], "grid_boundaries": {"start_index": start_index, "end_index": end_index, "cue_index": cue_index, "cue_sample_requested": cue, "cue_sample_used": int(boundaries[cue_index])}, "audio_sha256": expected_sha, "stem_payload_sha256": vocal_manifest["artifact_sha256"], "preparation": prep},
    }
    if role == "target":
        context_samples = min(int(render_sample_rate), start_sample, int(mix.shape[-1]) - end_sample)
        if context_samples > 0:
            context_start = start_sample - context_samples
            context_end = end_sample + context_samples
            result["stretch_context"] = {
                "mix": mix[..., context_start:context_end],
                "vocal": vocal[..., context_start:context_end],
                "left_samples": context_samples,
                "window_length": end_sample - start_sample,
                "context_samples_each_side": context_samples,
            }
        else:
            result["stretch_context"] = None
    return result


def _prepare_aligned_audio_pair(mix, mix_sr, vocal, vocal_sr, manifest, render_sr, time_stretch, tolerance):
    original_mix_samples = int(np.asarray(mix).shape[-1])
    mix = _resample_array(mix, int(mix_sr), int(render_sr), None)
    vocal = _resample_array(vocal, int(vocal_sr), int(render_sr), None)
    expected = int(round(original_mix_samples * render_sr / int(mix_sr)))
    mix, vocal = _match_pair_boundary(mix, vocal, expected, "end", tolerance)
    original_bpm = float(manifest.get("original_bpm") or manifest.get("aligned_bpm"))
    aligned_bpm = float(manifest.get("aligned_bpm") or original_bpm)
    if not np.isclose(original_bpm, aligned_bpm, rtol=0.0, atol=1e-9):
        factor = aligned_bpm / original_bpm
        mix, vocal, diagnostic = _strict_stretch_pair(mix, vocal, render_sr, factor, int(round(mix.shape[-1] / factor)), time_stretch, "end", tolerance)
    else:
        diagnostic = {"backend": "not_needed", "backend_version": VARIABLE_WAVEFORM_TEMPO_BACKEND_VERSION, "rounding_correction": {"count": 0, "side": None}}
    return mix, vocal, {"original_bpm": original_bpm, "aligned_bpm": aligned_bpm, "tempo": diagnostic}


def _strict_stretch_pair(mix, vocal, render_sample_rate, tempo_factor, expected_samples, time_stretch, correction_side, tolerance, context_pair=None):
    mix = _stereo_float32(mix, "target_mix")
    vocal = _stereo_float32(vocal, "target_vocal")
    if mix.shape[-1] != vocal.shape[-1]:
        raise VariableWaveformAlignmentReject("mix_vocal_input_length_mismatch", {"mix": int(mix.shape[-1]), "vocal": int(vocal.shape[-1])})
    if np.isclose(float(tempo_factor), 1.0, rtol=0.0, atol=1e-12):
        mix, vocal = _match_pair_boundary(mix, vocal, int(expected_samples), correction_side, tolerance)
        return mix, vocal, {"backend": "not_needed", "backend_version": VARIABLE_WAVEFORM_TEMPO_BACKEND_VERSION, "tempo_factor": float(tempo_factor), "raw_output_samples": int(mix.shape[-1]), "expected_samples": int(expected_samples), "rounding_correction": {"count": abs(int(expected_samples) - int(mix.shape[-1])), "side": correction_side}}
    failures = []
    for backend in ("ffmpeg_librubberband", "rubberband_cli_r3"):
        try:
            transform_mix, transform_vocal = mix, vocal
            context_left = 0
            context_window_length = int(expected_samples if context_pair is None else context_pair["window_length"])
            if context_pair is not None:
                transform_mix = _stereo_float32(context_pair["mix"], "target_stretch_context_mix")
                transform_vocal = _stereo_float32(context_pair["vocal"], "target_stretch_context_vocal")
                context_left = int(context_pair["left_samples"])
                if transform_mix.shape != transform_vocal.shape:
                    raise VariableWaveformAlignmentReject("target_stretch_context_shape_mismatch", {"mix": list(transform_mix.shape), "vocal": list(transform_vocal.shape)})
            raw_mix = _run_raw_backend(transform_mix, render_sample_rate, tempo_factor, time_stretch, backend)
            raw_vocal = _run_raw_backend(transform_vocal, render_sample_rate, tempo_factor, time_stretch, backend)
            if context_pair is not None:
                local_start = int(round(context_left / float(tempo_factor)))
                local_end = int(round((context_left + context_window_length) / float(tempo_factor)))
                if local_start < 0 or local_end > raw_mix.shape[-1] or local_end > raw_vocal.shape[-1]:
                    raise VariableWaveformAlignmentReject("target_context_backend_output_does_not_cover_window", {"backend": backend, "local_start": local_start, "local_end": local_end, "mix_output": int(raw_mix.shape[-1]), "vocal_output": int(raw_vocal.shape[-1])})
                raw_mix = raw_mix[..., local_start:local_end]
                raw_vocal = raw_vocal[..., local_start:local_end]
            mix_delta = int(raw_mix.shape[-1]) - int(expected_samples)
            vocal_delta = int(raw_vocal.shape[-1]) - int(expected_samples)
            if abs(mix_delta) > tolerance or abs(vocal_delta) > tolerance or mix_delta != vocal_delta:
                failures.append({"backend": backend, "mix_delta": mix_delta, "vocal_delta": vocal_delta})
                continue
            corrected_mix, corrected_vocal = _match_pair_boundary(raw_mix, raw_vocal, int(expected_samples), correction_side, tolerance)
            return corrected_mix, corrected_vocal, {"backend": backend, "backend_version": VARIABLE_WAVEFORM_TEMPO_BACKEND_VERSION, "tempo_factor": float(tempo_factor), "raw_output_samples": int(raw_mix.shape[-1]), "expected_samples": int(expected_samples), "context_used": context_pair is not None, "rounding_correction": {"count": abs(mix_delta), "side": correction_side}}
        except (OSError, RuntimeError, TimeStretchBackendError, ValueError) as error:
            failures.append({"backend": backend, "error": f"{type(error).__name__}: {error}"})
    raise VariableWaveformAlignmentReject("backend_rounding_residual_exceeds_tolerance", {"expected_samples": int(expected_samples), "tolerance_samples": int(tolerance), "tempo_factor": float(tempo_factor), "attempts": failures})


def _run_raw_backend(audio, sample_rate, tempo_factor, time_stretch, backend):
    audio = _stereo_float32(audio, "stretch_audio")
    with tempfile.TemporaryDirectory(prefix="beatbridge_variable_stretch_") as temp_dir:
        temp_dir = Path(temp_dir)
        input_path = temp_dir / "input.wav"
        output_path = temp_dir / "output.wav"
        sf.write(str(input_path), audio.T, int(sample_rate), format="WAV", subtype="FLOAT")
        if backend == "ffmpeg_librubberband":
            time_stretch._run_ffmpeg(input_path, output_path, sample_rate=int(sample_rate), channels=2, tempo_factor=float(tempo_factor))
        elif backend == "rubberband_cli_r3":
            time_stretch._run_rubberband_cli(input_path, output_path, tempo_factor=float(tempo_factor))
        else:
            raise ValueError(f"Unknown strict time-stretch backend: {backend}")
        return _stereo_float32(time_stretch._read_backend_output(output_path, sample_rate=int(sample_rate), channels=2, mono=False), "stretched_audio")


def _resample_and_correct_pair(mix, vocal, *, render_sample_rate, training_sample_rate, expected_samples, correction_side, tolerance, resampler):
    mix_out = _resample_array(mix, render_sample_rate, training_sample_rate, resampler)
    vocal_out = _resample_array(vocal, render_sample_rate, training_sample_rate, resampler)
    raw_shapes = {"mix": list(mix_out.shape), "vocal": list(vocal_out.shape)}
    mix_out, vocal_out = _match_pair_boundary(mix_out, vocal_out, expected_samples, correction_side, tolerance)
    return mix_out, {"vocal": vocal_out, "vocal_shape": list(vocal_out.shape), "raw_shapes": raw_shapes, "expected_samples": int(expected_samples), "corrected_samples": int(vocal_out.shape[-1]), "correction_count": abs(int(expected_samples) - int(vocal_out.shape[-1])), "correction_side": correction_side}


def _match_pair_boundary(mix, vocal, expected_samples, correction_side, tolerance):
    mix = _stereo_float32(mix, "mix")
    vocal = _stereo_float32(vocal, "vocal")
    if mix.shape[-1] != vocal.shape[-1]:
        raise VariableWaveformAlignmentReject("mix_vocal_resample_length_mismatch", {"mix": int(mix.shape[-1]), "vocal": int(vocal.shape[-1])})
    delta = int(expected_samples) - int(mix.shape[-1])
    if abs(delta) > int(tolerance):
        raise VariableWaveformAlignmentReject("rounding_residual_exceeds_tolerance", {"expected_samples": int(expected_samples), "actual_samples": int(mix.shape[-1]), "delta": delta, "tolerance_samples": int(tolerance), "correction_side": correction_side})
    if delta == 0:
        return mix.astype(np.float32, copy=False), vocal.astype(np.float32, copy=False)
    if correction_side not in {"start", "end"}:
        raise ValueError("correction_side must be 'start' or 'end'")
    if delta < 0:
        trim = -delta
        if correction_side == "start":
            return mix[..., trim:], vocal[..., trim:]
        return mix[..., :-trim], vocal[..., :-trim]
    pad_mix = np.repeat(mix[..., -1:] if correction_side == "end" else mix[..., :1], delta, axis=-1)
    pad_vocal = np.repeat(vocal[..., -1:] if correction_side == "end" else vocal[..., :1], delta, axis=-1)
    if correction_side == "end":
        return np.concatenate((mix, pad_mix), axis=-1), np.concatenate((vocal, pad_vocal), axis=-1)
    return np.concatenate((pad_mix, mix), axis=-1), np.concatenate((pad_vocal, vocal), axis=-1)


def _resample_array(audio, original_rate, target_rate, resampler):
    audio = _stereo_float32(audio, "resample_audio")
    if int(original_rate) == int(target_rate):
        return audio.copy()
    if resampler is not None:
        output = resampler(audio, int(original_rate), int(target_rate))
    else:
        output = librosa.resample(audio, orig_sr=int(original_rate), target_sr=int(target_rate), axis=-1, res_type="soxr_hq")
    return _stereo_float32(output, "resampled_audio")


def _read_stereo(path):
    audio, sample_rate = sf.read(str(path), dtype="float32", always_2d=True)
    return _stereo_float32(np.asarray(audio).T, "mix_audio"), int(sample_rate)


def _read_vocal_artifact(feature_manifest, expected_audio_sha):
    info = feature_manifest.get("vocal_artifact")
    if not isinstance(info, dict) or not info.get("cache_directory"):
        raise VariableWaveformAlignmentReject("missing_vocal_provenance", {"source_sha256": expected_audio_sha})
    directory = _resolve_path(info["cache_directory"])
    manifest_path = directory / "manifest.json"
    manifest = _read_json(manifest_path)
    if str(manifest.get("source_sha256", "")).lower() != str(expected_audio_sha).lower() or manifest.get("artifact_sha256") != info.get("artifact_sha256"):
        raise VariableWaveformAlignmentReject("vocal_provenance_mismatch", {"expected_audio_sha256": expected_audio_sha, "stem_source_sha256": manifest.get("source_sha256"), "expected_artifact_sha256": info.get("artifact_sha256"), "actual_artifact_sha256": manifest.get("artifact_sha256")})
    data_path = directory / manifest["data_file"]
    if _file_sha256(data_path) != manifest["artifact_sha256"]:
        raise ValueError(f"Vocal stem payload hash differs: {data_path}")
    with np.load(data_path, allow_pickle=False) as payload:
        audio = np.asarray(payload["audio"], dtype=np.float32)
    if audio.ndim != 1 or audio.shape[0] != int(manifest["sample_count"]) or not np.isfinite(audio).all():
        raise ValueError(f"Invalid vocal stem payload: {data_path}")
    return _stereo_float32(audio, "vocal_audio"), manifest


def _publish_entry(cache_directory, manifest, arrays):
    temporary_directory = cache_directory.with_name(f".{cache_directory.name}.{uuid.uuid4().hex}.tmp")
    temporary_directory.mkdir(parents=True)
    try:
        waveform_path = temporary_directory / "waveforms.npz"
        with waveform_path.open("wb") as output:
            np.savez_compressed(output, **arrays)
        manifest["waveforms"]["file_sha256"] = _file_sha256(waveform_path)
        (temporary_directory / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        cache_directory.parent.mkdir(parents=True, exist_ok=True)
        try:
            os.replace(temporary_directory, cache_directory)
        except (FileExistsError, PermissionError) as error:
            cache_config = {key: manifest[key] for key in _cache_identity_keys()}
            if _load_cached_entry(cache_directory, cache_config) is not None:
                shutil.rmtree(temporary_directory, ignore_errors=True)
            elif isinstance(error, FileExistsError) or cache_directory.exists():
                raise
            else:
                # Managed Windows folders may briefly deny the atomic rename
                # while the just-written NPZ/manifest is being scanned. Retry
                # only when the destination is still absent; persistent ACL or
                # provenance errors remain fail-closed.
                for delay in (0.05, 0.1, 0.25, 0.5):
                    time.sleep(delay)
                    try:
                        os.replace(temporary_directory, cache_directory)
                        break
                    except PermissionError:
                        if _load_cached_entry(cache_directory, cache_config) is not None:
                            shutil.rmtree(temporary_directory, ignore_errors=True)
                            break
                        if cache_directory.exists() or not temporary_directory.exists():
                            raise
                else:
                    raise error
    except Exception:
        shutil.rmtree(temporary_directory, ignore_errors=True)
        raise


def _load_cached_entry(cache_directory, cache_config):
    manifest_path = cache_directory / "manifest.json"
    waveform_path = cache_directory / "waveforms.npz"
    if not manifest_path.is_file() or not waveform_path.is_file():
        return None
    try:
        manifest = _read_json(manifest_path)
        if any(manifest.get(key) != value for key, value in cache_config.items()):
            return None
        if _file_sha256(waveform_path) != manifest.get("waveforms", {}).get("file_sha256"):
            return None
        with np.load(waveform_path, allow_pickle=False) as payload:
            arrays = {name: np.asarray(payload[name]) for name in ("source_audio", "target_audio", "source_vocal_audio", "target_vocal_audio")}
        if any(value.dtype != np.dtype(np.float32) for value in arrays.values()):
            return None
        waveforms = manifest["waveforms"]
        if waveforms.get("dtype") != VARIABLE_WAVEFORM_DTYPE or int(waveforms.get("sample_rate", -1)) != int(cache_config["training_sample_rate"]):
            return None
        arrays = {name: _stereo_float32(value, name) for name, value in arrays.items()}
        shape = arrays["source_audio"].shape
        if any(value.shape != shape for value in arrays.values()) or list(shape) != manifest["waveforms"]["shape"]:
            return None
        if any(_array_sha256(arrays[name]) != manifest["waveforms"]["array_sha256"][name] for name in arrays):
            return None
        return VariableWaveformCacheArtifact(cache_directory=cache_directory, manifest=manifest, source_audio=arrays["source_audio"], target_audio=arrays["target_audio"], source_vocal_audio=arrays["source_vocal_audio"], target_vocal_audio=arrays["target_vocal_audio"], cache_hit=True)
    except Exception:
        return None


def _cache_config(example, geometry, *, dataset_id, dataset_manifest_sha256, training_sample_rate, render_sample_rate, rounding_tolerance_samples):
    return {"format_version": VARIABLE_WAVEFORM_CACHE_FORMAT_VERSION, "extractor_version": VARIABLE_WAVEFORM_CACHE_EXTRACTOR_VERSION, "alignment_contract": VARIABLE_WAVEFORM_ALIGNMENT_CONTRACT, "dataset_id": str(dataset_id), "dataset_manifest_sha256": str(dataset_manifest_sha256).lower(), "example_id": str(example["example_id"]), "candidate_id": str(example["candidate_id"]), "transition_length_bars": int(geometry.transition_length_bars), "transition_length_beats": int(geometry.transition_length_beats), "sequence_length": int(geometry.sequence_length), "source_audio_sha256": str(example["source_track"]["sha256"]).lower(), "target_audio_sha256": str(example["target_track"]["sha256"]).lower(), "training_sample_rate": int(training_sample_rate), "render_sample_rate": int(render_sample_rate), "channels": 2, "channel_order": list(VARIABLE_WAVEFORM_CHANNEL_ORDER), "rounding_tolerance_samples": int(rounding_tolerance_samples)}


def _cache_id(config):
    return hashlib.sha256(json.dumps(config, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()[:20]


def _cache_identity_keys():
    return ("format_version", "extractor_version", "alignment_contract", "dataset_id", "dataset_manifest_sha256", "example_id", "candidate_id", "transition_length_bars", "transition_length_beats", "sequence_length", "source_audio_sha256", "target_audio_sha256", "training_sample_rate", "render_sample_rate", "channels", "channel_order", "rounding_tolerance_samples")


def _ensure_root_manifest(cache_root, *, dataset_id, dataset_manifest_sha256, supported_lengths, training_sample_rate, render_sample_rate, rounding_tolerance_samples):
    cache_root = Path(cache_root)
    cache_root.mkdir(parents=True, exist_ok=True)
    path = cache_root / "manifest.json"
    expected = {"format_version": VARIABLE_WAVEFORM_CACHE_FORMAT_VERSION, "extractor_version": VARIABLE_WAVEFORM_CACHE_EXTRACTOR_VERSION, "alignment_contract": VARIABLE_WAVEFORM_ALIGNMENT_CONTRACT, "dataset_id": str(dataset_id), "dataset_manifest_sha256": str(dataset_manifest_sha256).lower(), "supported_lengths": sorted({int(value) for value in supported_lengths}), "training_sample_rate": int(training_sample_rate), "render_sample_rate": int(render_sample_rate), "channels": 2, "channel_order": list(VARIABLE_WAVEFORM_CHANNEL_ORDER), "rounding_correction_version": VARIABLE_WAVEFORM_ROUNDING_CORRECTION_VERSION, "rounding_tolerance_samples": int(rounding_tolerance_samples)}
    if path.is_file():
        actual = _read_json(path)
        if any(actual.get(key) != value for key, value in expected.items()):
            raise ValueError(f"Variable-v2 cache root provenance differs: {path}")
        return actual
    _write_json_atomic(path, {**expected, "created_at_utc": datetime.now(timezone.utc).isoformat()})
    return expected


def _validate_example(example, geometry):
    if example.get("split") not in {"train", "validation"}:
        raise ValueError("Variable-v2 waveform cache accepts only train and validation examples")
    if int(example.get("dataset_format_version", 0)) != 2 or int(example.get("feature_protocol_version", 0)) != 2:
        raise ValueError("Example is not Dataset/Feature Protocol 2")
    geometry_for_length(example.get("transition_length_bars"), sequence_length=example.get("sequence_length"), transition_length_beats=example.get("transition_length_beats"))
    if int(example["transition_length_bars"]) != geometry.transition_length_bars:
        raise ValueError("Example geometry differs from requested geometry")
    for role in ("source", "target"):
        if not _is_sha256(str(example[f"{role}_track"]["sha256"]).lower()):
            raise ValueError(f"{role} audio SHA is invalid")
        grid = example.get(f"{role}_grid", {})
        if grid.get("fallback_used") is not False:
            raise VariableWaveformAlignmentReject("unreliable_grid_provenance", {"role": role, "grid": grid})


def _window_tuple(value, name):
    values = tuple(int(item) for item in value)
    if len(values) not in {2, 3} or values[1] <= values[0]:
        raise ValueError(f"{name} must contain start, end, and optional declared beats")
    return values


def _stereo_float32(value, name):
    array = np.asarray(value, dtype=np.float32)
    if array.ndim == 1:
        array = np.stack((array, array), axis=0)
    elif array.ndim == 2 and array.shape[0] == 1:
        array = np.repeat(array, 2, axis=0)
    if array.ndim != 2 or array.shape[0] != 2 or array.shape[-1] <= 0:
        raise ValueError(f"{name} must have shape (2, samples)")
    if not np.isfinite(array).all():
        raise ValueError(f"{name} must contain only finite samples")
    return np.ascontiguousarray(array, dtype=np.float32)


def _resolve_path(value):
    path = Path(value)
    return path if path.is_absolute() else PROJECT_ROOT / path


def _read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _write_json_atomic(path, payload, *, allow_overwrite=False):
    path = Path(path)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        if path.exists() and not allow_overwrite:
            existing = _read_json(path)
            if existing != payload:
                raise ValueError(f"Refusing to overwrite immutable JSON artifact: {path}")
            return
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _file_sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_json_sha256(value):
    canonical = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _array_sha256(array):
    digest = hashlib.sha256()
    array = np.ascontiguousarray(array)
    digest.update(str(array.dtype).encode("ascii"))
    digest.update(json.dumps(list(array.shape)).encode("ascii"))
    digest.update(array.tobytes())
    return digest.hexdigest()


def _is_sha256(value):
    value = str(value).lower()
    return len(value) == 64 and all(character in "0123456789abcdef" for character in value)
