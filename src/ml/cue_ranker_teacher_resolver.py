"""Production Candidate-v2 resolver for the sealed Cue-Ranker Teacher.

This module deliberately reuses Feature Protocol 2 and the existing variable
waveform alignment implementation.  It does not recreate an alignment path,
and it never accepts a test row.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import uuid

import numpy as np

from src.analysis.models import AnalysisResult, BeatGridMetadata
from src.features.extract_track import (
    DEFAULT_ANALYSIS_ROOT,
    DEFAULT_FEATURE_CACHE_ROOT,
    FeatureNormalizationStats,
    extract_or_load_track_features,
)
from src.features.variable_contract import (
    geometry_for_length,
    validate_length_condition,
    validate_variable_feature_array,
)
from src.features.variable_extract import extract_variable_track_window
from src.features.variable_global_pair import build_variable_global_pair_features
from src.features.vocal import DEFAULT_ROFORMER_MODEL, DEFAULT_VOCAL_BACKEND
from src.ml.variable_waveform_cache import (
    VARIABLE_WAVEFORM_RENDER_SAMPLE_RATE,
    VARIABLE_WAVEFORM_ROUNDING_TOLERANCE_SAMPLES,
    VARIABLE_WAVEFORM_SAMPLE_RATE,
    _load_real_window_inputs,
    align_variable_waveform_windows,
)
from src.tempo.time_stretch import TimeStretch


CUE_RANKER_TEACHER_WAVEFORM_CACHE_FORMAT_VERSION = 1
DEFAULT_CUE_RANKER_TEACHER_WAVEFORM_CACHE_ROOT = (
    Path("output") / "ml_cache" / "cue_ranker_teacher_waveform_v1"
)
_REQUIRED_PROVENANCE = (
    "source_feature_payload_sha256",
    "target_feature_payload_sha256",
    "source_feature_manifest_sha256",
    "target_feature_manifest_sha256",
    "source_grid_sha256",
    "target_grid_sha256",
    "source_audio_sha256",
    "target_audio_sha256",
    "source_stem_payload_sha256",
    "target_stem_payload_sha256",
    "rubberband_backend_sha256",
    "local_source_window_samples",
)


class CueRankerCandidateResolver:
    """Resolve one train/validation Candidate-v2 identity to Teacher inputs."""

    def __init__(
        self,
        release,
        release_sha256,
        *,
        analysis_root=DEFAULT_ANALYSIS_ROOT,
        feature_cache_root=DEFAULT_FEATURE_CACHE_ROOT,
        waveform_cache_root=DEFAULT_CUE_RANKER_TEACHER_WAVEFORM_CACHE_ROOT,
        vocal_backend=DEFAULT_VOCAL_BACKEND,
        vocal_model=DEFAULT_ROFORMER_MODEL,
        feature_sample_rate=VARIABLE_WAVEFORM_RENDER_SAMPLE_RATE,
        training_sample_rate=VARIABLE_WAVEFORM_SAMPLE_RATE,
        rounding_tolerance_samples=VARIABLE_WAVEFORM_ROUNDING_TOLERANCE_SAMPLES,
    ):
        self.release = dict(release)
        self.release_sha256 = _sha(release_sha256, "teacher_release_sha256")
        self.analysis_root = Path(analysis_root)
        self.feature_cache_root = Path(feature_cache_root)
        self.waveform_cache_root = Path(waveform_cache_root)
        self.vocal_backend = str(vocal_backend)
        self.vocal_model = str(vocal_model)
        self.feature_sample_rate = int(feature_sample_rate)
        self.training_sample_rate = int(training_sample_rate)
        self.rounding_tolerance_samples = int(rounding_tolerance_samples)
        if self.feature_sample_rate != VARIABLE_WAVEFORM_RENDER_SAMPLE_RATE:
            raise ValueError("teacher_feature_sample_rate_contract_mismatch")
        if self.training_sample_rate != int(self.release["renderer"]["config"].get("sample_rate", -1)):
            raise ValueError("teacher_renderer_sample_rate_contract_mismatch")
        self.normalization = _normalization_from_release(self.release)

    def __call__(self, row):
        return self.resolve(row)

    def resolve(self, row):
        _validate_row(row)
        candidate = row["candidate"]
        geometry = geometry_for_length(
            row["transition_length_bars"],
            sequence_length=row["sequence_length"],
            transition_length_beats=row["transition_length_beats"],
        )
        source_artifact = self._feature_artifact(candidate, "source", target_bpm=None)
        target_artifact = self._feature_artifact(
            candidate, "target", target_bpm=float(candidate["source_bpm"])
        )
        source_cue = int(candidate["source_cutpoint"]["sample"])
        target_cue = int(round(
            int(candidate["target_cutpoint"]["sample"])
            * float(candidate["target_bpm"])
            / float(candidate["source_bpm"])
        ))
        features_a = extract_variable_track_window(
            source_artifact, source_cue, role="source", normalization=self.normalization,
            transition_length_bars=geometry.transition_length_bars,
            sequence_length=geometry.sequence_length,
        )
        features_b = extract_variable_track_window(
            target_artifact, target_cue, role="target", normalization=self.normalization,
            transition_length_bars=geometry.transition_length_bars,
            sequence_length=geometry.sequence_length,
        )
        global_features = build_variable_global_pair_features(
            features_a, features_b,
            transition_length_bars=geometry.transition_length_bars,
            sequence_length=geometry.sequence_length,
            bpm_a=float(candidate["source_bpm"]), bpm_b=float(candidate["target_bpm"]),
            artifact_a=source_artifact, artifact_b=target_artifact,
            cue_sample_a=source_cue, cue_sample_b=target_cue,
        )
        length_condition = np.asarray([geometry.length_condition], dtype=np.float32)
        validate_variable_feature_array(features_a, transition_length_bars=geometry.transition_length_bars, sequence_length=geometry.sequence_length, name="teacher_features_a")
        validate_variable_feature_array(features_b, transition_length_bars=geometry.transition_length_bars, sequence_length=geometry.sequence_length, name="teacher_features_b")
        validate_length_condition(length_condition, transition_length_bars=geometry.transition_length_bars)

        example = self._waveform_example(row, candidate, source_artifact, target_artifact, source_cue, target_cue)
        # The existing loader verifies source audio, grid and vocal payload
        # hashes before returning any material to the alignment function.
        windows = _load_real_window_inputs(
            example, geometry, feature_cache_root=self.feature_cache_root,
            render_sample_rate=self.feature_sample_rate, verify_audio_hashes=True,
            time_stretch=TimeStretch(), tolerance=self.rounding_tolerance_samples,
        )
        provenance = self._provenance(row, example, source_artifact, target_artifact, windows)
        cache_key = teacher_waveform_cache_key(row, provenance, self.release, self.release_sha256)
        cached = _load_cache(self.waveform_cache_root, row, cache_key, provenance)
        if cached is None:
            aligned = align_variable_waveform_windows(
                windows["source_mix"], windows["target_mix"],
                windows["source_vocal"], windows["target_vocal"],
                source_window=windows["source_window"], target_window=windows["target_window"],
                source_bpm=float(candidate["source_bpm"]), target_bpm=float(candidate["target_bpm"]),
                render_sample_rate=self.feature_sample_rate,
                training_sample_rate=self.training_sample_rate,
                time_stretch=TimeStretch(),
                rounding_tolerance_samples=self.rounding_tolerance_samples,
                provenance=provenance,
                target_stretch_context=windows.get("target_stretch_context"),
            )
            arrays = {
                "source_audio": aligned.source_audio,
                "target_audio": aligned.target_audio,
                "source_vocal_audio": aligned.source_vocal_audio,
                "target_vocal_audio": aligned.target_vocal_audio,
            }
            arrays, cache_manifest, cache_hit = _publish_cache(
                self.waveform_cache_root, row, cache_key, provenance, arrays,
                sample_rate=self.training_sample_rate, alignment=aligned.provenance,
            )
        else:
            arrays, cache_manifest, cache_hit = cached
        provenance = dict(cache_manifest["provenance"])
        provenance["alignment"] = dict(cache_manifest["alignment"])
        provenance["teacher_waveform_cache_key_sha256"] = cache_key
        provenance["teacher_waveform_cache_hit"] = bool(cache_hit)
        return {
            "features_a": np.asarray(features_a, dtype=np.float32),
            "features_b": np.asarray(features_b, dtype=np.float32),
            "global_features": np.asarray(global_features, dtype=np.float32),
            "length_condition": length_condition,
            **arrays,
            "provenance": provenance,
        }

    def _feature_artifact(self, candidate, role, *, target_bpm):
        track, grid = candidate[f"{role}_track"], candidate[f"{role}_grid"]
        expected_sha = _sha(track.get("sha256"), f"teacher_{role}_audio_sha256")
        analysis = _sealed_analysis(
            self.analysis_root, expected_sha, grid, float(candidate[f"{role}_bpm"])
        )
        artifact = extract_or_load_track_features(
            track["path"], cache_root=self.feature_cache_root, analysis=analysis,
            sample_rate=self.feature_sample_rate, target_bpm=target_bpm,
            vocal_backend=self.vocal_backend, vocal_model=self.vocal_model,
        )
        if str(artifact.manifest.get("source_sha256", "")).lower() != expected_sha:
            raise ValueError("teacher_feature_audio_sha_mismatch")
        return artifact

    def _waveform_example(self, row, candidate, source, target, source_cue, target_cue):
        return {
            "example_id": f"cue-ranker-{row['candidate_identity_sha256']}",
            "candidate_id": row["candidate_id"], "split": row["split"],
            "dataset_format_version": 2, "feature_protocol_version": 2,
            "source_track": candidate["source_track"], "target_track": candidate["target_track"],
            "source_grid": candidate["source_grid"], "target_grid": candidate["target_grid"],
            "source_bpm": float(candidate["source_bpm"]), "target_bpm": float(candidate["target_bpm"]),
            "transition_length_bars": int(row["transition_length_bars"]),
            "transition_length_beats": int(row["transition_length_beats"]),
            "sequence_length": int(row["sequence_length"]),
            "aligned_source_cue_sample": int(source_cue), "aligned_target_cue_sample": int(target_cue),
            "source_feature_cache": {"directory": str(source.cache_directory)},
            "target_feature_cache": {"directory": str(target.cache_directory)},
        }

    def _provenance(self, row, example, source, target, windows):
        source_payload, source_manifest, source_stem = _artifact_hashes(source)
        target_payload, target_manifest, target_stem = _artifact_hashes(target)
        return {
            "alignment_contract": "local_grid_target_to_source_v1",
            "teacher_release_sha256": self.release_sha256,
            "normalizer_sha256": self.release["normalizer_sha256"],
            "source_feature_payload_sha256": source_payload,
            "target_feature_payload_sha256": target_payload,
            "source_feature_manifest_sha256": source_manifest,
            "target_feature_manifest_sha256": target_manifest,
            "source_grid_sha256": _sha(example["source_grid"]["beat_grid_sha256"], "source_grid_sha256"),
            "target_grid_sha256": _sha(example["target_grid"]["beat_grid_sha256"], "target_grid_sha256"),
            "source_audio_sha256": _sha(example["source_track"]["sha256"], "source_audio_sha256"),
            "target_audio_sha256": _sha(example["target_track"]["sha256"], "target_audio_sha256"),
            "source_stem_payload_sha256": source_stem, "target_stem_payload_sha256": target_stem,
            "rubberband_backend_sha256": _backend_sha(self.release),
            "local_source_window_samples": int(windows["source_window"][1] - windows["source_window"][0]),
        }


def teacher_waveform_cache_key(row, provenance, release, release_sha256):
    missing = [key for key in _REQUIRED_PROVENANCE if provenance.get(key) is None]
    if missing:
        raise ValueError("teacher_cache_provenance_missing:" + ",".join(missing))
    return _canonical_sha({
        "candidate_identity_sha256": _sha(row["candidate_identity_sha256"], "candidate_identity_sha256"),
        "candidate_request_config_sha256": _sha(row["candidate_request_config_sha256"], "candidate_request_config_sha256"),
        "teacher_release_sha256": _sha(release_sha256, "teacher_release_sha256"),
        "teacher_contract_sha256": _sha(release["teacher_contract_sha256"], "teacher_contract_sha256"),
        "renderer": release["renderer"], "objective": release["objective"],
        "normalizer_sha256": release["normalizer_sha256"],
        "backend_provenance": release["backend_provenance"], "provenance": provenance,
    })


def _load_cache(root, row, key, provenance):
    directory = Path(root) / "entries" / row["candidate_identity_sha256"] / key
    manifest_path, waveforms_path = directory / "manifest.json", directory / "waveforms.npz"
    if not manifest_path.exists() and not waveforms_path.exists():
        return None
    if not manifest_path.is_file() or not waveforms_path.is_file():
        raise ValueError("teacher_waveform_cache_incomplete")
    manifest = _read_json(manifest_path)
    expected = {
        "format_version": CUE_RANKER_TEACHER_WAVEFORM_CACHE_FORMAT_VERSION,
        "cache_key_sha256": key, "candidate_identity_sha256": row["candidate_identity_sha256"],
        "provenance": provenance,
    }
    if any(manifest.get(name) != value for name, value in expected.items()):
        raise ValueError("teacher_waveform_cache_provenance_mismatch")
    alignment = manifest.get("alignment")
    if not isinstance(alignment, dict) or alignment.get("alignment_contract") != "local_grid_target_to_source_v1":
        raise ValueError("teacher_waveform_cache_alignment_mismatch")
    _verify_file(waveforms_path, _sha(manifest["waveforms"].get("file_sha256"), "teacher_waveform_cache_file_sha256"))
    with np.load(waveforms_path, allow_pickle=False) as payload:
        arrays = {name: np.asarray(payload[name], dtype=np.float32) for name in ("source_audio", "target_audio", "source_vocal_audio", "target_vocal_audio")}
    shape = arrays["source_audio"].shape
    if any(value.shape != shape or value.ndim != 2 or value.shape[0] != 2 or not np.isfinite(value).all() for value in arrays.values()):
        raise ValueError("teacher_waveform_cache_shape_mismatch")
    if any(_array_sha256(value) != manifest["waveforms"]["array_sha256"].get(name) for name, value in arrays.items()):
        raise ValueError("teacher_waveform_cache_array_sha_mismatch")
    return arrays, manifest, True


def _publish_cache(root, row, key, provenance, arrays, *, sample_rate, alignment):
    directory = Path(root) / "entries" / row["candidate_identity_sha256"] / key
    temporary = directory.with_name(f".{directory.name}.{uuid.uuid4().hex}.tmp")
    temporary.mkdir(parents=True)
    try:
        waveforms = temporary / "waveforms.npz"
        with waveforms.open("wb") as handle:
            np.savez_compressed(handle, **arrays)
        manifest = {
            "format_version": CUE_RANKER_TEACHER_WAVEFORM_CACHE_FORMAT_VERSION,
            "cache_key_sha256": key, "candidate_identity_sha256": row["candidate_identity_sha256"],
            "provenance": provenance,
            "alignment": alignment,
            "waveforms": {"path": "waveforms.npz", "file_sha256": _file_sha256(waveforms), "sample_rate": int(sample_rate), "array_sha256": {name: _array_sha256(value) for name, value in arrays.items()}},
        }
        _atomic_json_write(temporary / "manifest.json", manifest)
        directory.parent.mkdir(parents=True, exist_ok=True)
        try:
            os.replace(temporary, directory)
        except (FileExistsError, PermissionError):
            cached = _load_cache(root, row, key, provenance)
            if cached is None:
                raise
            shutil.rmtree(temporary, ignore_errors=True)
            return cached
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise
    return dict(arrays), manifest, False


def _artifact_hashes(artifact):
    directory, manifest = Path(artifact.cache_directory), artifact.manifest
    vocal = manifest.get("vocal_artifact") or {}
    if not vocal.get("artifact_sha256"):
        raise ValueError("teacher_vocal_stem_provenance_missing")
    return (
        _file_sha256(directory / manifest["data_file"]),
        _file_sha256(directory / "manifest.json"),
        _sha(vocal["artifact_sha256"], "teacher_stem_payload_sha256"),
    )


def _sealed_analysis(root, audio_sha, grid, expected_bpm):
    if not isinstance(grid, dict) or grid.get("fallback_used") is not False:
        raise ValueError("teacher_grid_provenance_rejected")
    analysis_id, grid_sha = _sha(grid.get("analysis_id"), "analysis_id"), _sha(grid.get("beat_grid_sha256"), "grid_sha")
    path = Path(root) / "v2" / audio_sha / analysis_id / "analysis.json"
    payload = _read_json(path)
    if int(payload.get("format_version", -1)) != 2 or payload.get("analysis_id") != analysis_id:
        raise ValueError("teacher_analysis_contract_mismatch")
    if _sha(payload.get("source_audio", {}).get("sha256"), "analysis_audio_sha") != audio_sha:
        raise ValueError("teacher_analysis_audio_sha_mismatch")
    result = payload.get("result", {})
    metadata = BeatGridMetadata.from_dict(result.get("grid_metadata"))
    if metadata.to_dict() != {key: grid.get(key) for key in metadata.to_dict()} or metadata.beat_grid_sha256 != grid_sha:
        raise ValueError("teacher_analysis_grid_provenance_mismatch")
    bpm = float(result.get("bpm"))
    if not math.isfinite(bpm) or not math.isclose(bpm, float(expected_bpm), rel_tol=0.0, abs_tol=1e-9):
        raise ValueError("teacher_analysis_bpm_mismatch")
    analysis = AnalysisResult(bpm=bpm, beat_frames=tuple(tuple(int(value) for value in frame) for frame in result.get("beat_frames", ())), grid_metadata=metadata)

    def frozen_analysis(song_path):
        if _file_sha256(song_path) != audio_sha:
            raise ValueError("teacher_audio_sha_mismatch_before_feature_processing")
        return analysis

    return frozen_analysis


def _normalization_from_release(release):
    info = release.get("normalizer")
    if not isinstance(info, dict) or not info.get("path"):
        raise ValueError("teacher_release_normalizer_path_required")
    path = Path(info["path"])
    _verify_file(path, _sha(info.get("sha256"), "teacher_normalizer_sha256"))
    payload = _read_json(path)
    values = payload.get("statistics", payload)
    if not isinstance(values, dict) or values.get("fit_scope") != "training_tracks_only":
        raise ValueError("teacher_normalizer_not_training_only")
    try:
        return FeatureNormalizationStats(
            spectral_flux_log1p_p99=float(values["spectral_flux_log1p_p99"]),
            onset_strength_log1p_p99=float(values["onset_strength_log1p_p99"]),
            stats_id=str(values["stats_id"]),
        )
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("teacher_normalizer_invalid") from error


def _validate_row(row):
    if row.get("split") not in {"train", "validation"}:
        raise ValueError("teacher_test_split_rejected")
    candidate = row.get("candidate")
    if not isinstance(candidate, dict) or candidate.get("generator") != "bar_grid_v2_length_specific" or int(candidate.get("format_version", -1)) != 2:
        raise ValueError("teacher_candidate_v2_required")
    for role in ("source", "target"):
        if _sha(candidate[f"{role}_track"].get("sha256"), f"{role}_candidate_sha") != _sha(row.get(f"{role}_audio_sha256"), f"{role}_row_sha"):
            raise ValueError("teacher_candidate_audio_sha_mismatch")
    geometry_for_length(row["transition_length_bars"], sequence_length=row["sequence_length"], transition_length_beats=row["transition_length_beats"])


def _backend_sha(release):
    return _sha(release.get("backend_provenance", {}).get("rubberband_backend_sha256"), "rubberband_backend_sha256")


def _array_sha256(array):
    array = np.ascontiguousarray(array)
    digest = hashlib.sha256()
    digest.update(str(array.dtype).encode("ascii")); digest.update(json.dumps(list(array.shape)).encode("ascii")); digest.update(array.tobytes())
    return digest.hexdigest()


def _atomic_json_write(path, payload):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        temporary.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _verify_file(path, expected):
    if _file_sha256(path) != expected:
        raise ValueError(f"sha256_mismatch:{path}")


def _file_sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _canonical_sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def _sha(value, name):
    value = str(value or "").lower()
    if len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
        raise ValueError(f"{name} must be a SHA-256 hex digest")
    return value
