"""Fail-closed Feature Protocol 2 loader for Cue-Ranker Dataset Format 3.

Format 3 intentionally contains no feature tensors.  This module is the one
offline training resolver: it follows the dataset -> universe -> teacher-label
hash chain and opens only existing, immutable Feature Protocol 2 cache files.
It never discovers pair manifests, builds caches, or accepts a test split.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np

from src.features.extract_track import FeatureNormalizationStats, TrackFeatureArtifact
from src.features.variable_contract import geometry_for_length, validate_length_condition, validate_variable_feature_array
from src.features.variable_extract import extract_variable_track_window
from src.features.variable_global_pair import build_variable_global_pair_features


class CueRankerFeatureLoader:
    """Resolve a Format-3 row using only sealed metadata and feature caches."""

    def __init__(self, dataset_directory, *, feature_cache_root="output/feature_cache"):
        self.dataset_directory = Path(dataset_directory).resolve()
        self.feature_cache_root = Path(feature_cache_root).resolve()
        self.manifest_path = self.dataset_directory / "manifest.json"
        self.manifest = _read_json(self.manifest_path)
        if int(self.manifest.get("format_version", -1)) != 3:
            raise ValueError("cue_ranker_feature_loader_requires_format_3")
        if self.manifest.get("test") != {"state": "sealed_not_materialized"}:
            raise ValueError("cue_ranker_feature_loader_test_split_rejected")
        self.normalization = self._load_normalizer()
        self._universe_rows, self._teacher_labels = self._verify_input_chain()
        self._validate_normalizer_scope()
        self._artifacts = {}

    def __call__(self, row):
        return self.resolve(row)

    def resolve(self, row):
        if row.get("split") not in {"train", "validation"}:
            raise ValueError("cue_ranker_feature_loader_test_split_rejected")
        key = _row_key(row)
        universe = self._universe_rows.get(key)
        label = self._teacher_labels.get(key)
        if universe is None or label is None:
            raise ValueError("cue_ranker_feature_loader_universe_or_teacher_reference_missing")
        # Do not trust the duplicated Dataset row over the externally sealed
        # sources.  Its full candidate identity must be identical.
        for name in ("group_id", "candidate_id", "candidate_identity_sha256", "source_audio_sha256", "target_audio_sha256", "transition_length_bars", "sequence_length"):
            if row.get(name) != universe.get(name):
                raise ValueError("cue_ranker_feature_loader_dataset_universe_mismatch")
        if row.get("teacher_status") != label.get("teacher_status") or row.get("teacher_utility") != label.get("teacher_utility"):
            raise ValueError("cue_ranker_feature_loader_dataset_teacher_mismatch")
        provenance = label.get("teacher_provenance", {})
        if not isinstance(provenance, dict):
            raise ValueError("cue_ranker_feature_loader_teacher_provenance_missing")
        if provenance.get("normalizer_sha256") != self.normalizer_sha256:
            raise ValueError("cue_ranker_feature_loader_normalizer_teacher_mismatch")
        geometry = geometry_for_length(
            row["transition_length_bars"], sequence_length=row["sequence_length"],
            transition_length_beats=row.get("transition_length_beats"),
        )
        candidate = universe.get("candidate")
        if not isinstance(candidate, dict):
            raise ValueError("cue_ranker_feature_loader_candidate_missing")
        source = self._artifact(candidate, "source", None, provenance)
        target = self._artifact(candidate, "target", float(candidate["source_bpm"]), provenance)
        source_cue = int(candidate["source_cutpoint"]["sample"])
        target_cue = int(round(int(candidate["target_cutpoint"]["sample"]) * float(candidate["target_bpm"]) / float(candidate["source_bpm"])))
        features_a = extract_variable_track_window(source, source_cue, role="source", normalization=self.normalization, transition_length_bars=geometry.transition_length_bars, sequence_length=geometry.sequence_length)
        features_b = extract_variable_track_window(target, target_cue, role="target", normalization=self.normalization, transition_length_bars=geometry.transition_length_bars, sequence_length=geometry.sequence_length)
        global_features = build_variable_global_pair_features(features_a, features_b, transition_length_bars=geometry.transition_length_bars, sequence_length=geometry.sequence_length, bpm_a=float(candidate["source_bpm"]), bpm_b=float(candidate["target_bpm"]), artifact_a=source, artifact_b=target, cue_sample_a=source_cue, cue_sample_b=target_cue)
        length_condition = np.asarray([geometry.length_condition], dtype=np.float32)
        validate_variable_feature_array(features_a, transition_length_bars=geometry.transition_length_bars, sequence_length=geometry.sequence_length, name="cue_ranker_features_a")
        validate_variable_feature_array(features_b, transition_length_bars=geometry.transition_length_bars, sequence_length=geometry.sequence_length, name="cue_ranker_features_b")
        validate_length_condition(length_condition, transition_length_bars=geometry.transition_length_bars)
        for value in (features_a, features_b, global_features, length_condition):
            if value.dtype != np.float32 or not np.isfinite(value).all():
                raise ValueError("cue_ranker_feature_loader_nonfinite_or_non_float32")
        return {"features_a": features_a, "features_b": features_b, "global_features": global_features, "length_condition": length_condition}

    def _load_normalizer(self):
        info = self.manifest.get("files", {}).get("train_only_normalizer")
        if not isinstance(info, dict):
            raise ValueError("cue_ranker_feature_loader_normalizer_missing")
        path = self.dataset_directory / str(info.get("path", ""))
        _verify(path, info.get("sha256"), "dataset_normalizer")
        payload = _read_json(path)
        if payload.get("fit_scope") != "training_tracks_only":
            raise ValueError("cue_ranker_feature_loader_normalizer_not_training_only")
        if payload.get("input_universe_manifest_sha256") != self.manifest.get("universe_manifest_sha256"):
            raise ValueError("cue_ranker_feature_loader_normalizer_universe_mismatch")
        if self.manifest.get("normalization", {}).get("sha256") != info.get("sha256"):
            raise ValueError("cue_ranker_feature_loader_normalizer_manifest_mismatch")
        try:
            normalization = FeatureNormalizationStats(
                spectral_flux_log1p_p99=float(payload["spectral_flux_log1p_p99"]),
                onset_strength_log1p_p99=float(payload["onset_strength_log1p_p99"]),
                stats_id=str(payload["stats_id"]),
            )
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError("cue_ranker_feature_loader_normalizer_invalid") from error
        self.normalizer_sha256 = str(payload.get("source_sha256", "")).lower()
        if not _is_sha(self.normalizer_sha256):
            raise ValueError("cue_ranker_feature_loader_normalizer_source_sha_invalid")
        source = self.manifest.get("inputs", {}).get("train_only_normalizer_source", {})
        if not isinstance(source, dict) or source.get("sha256") != self.normalizer_sha256:
            raise ValueError("cue_ranker_feature_loader_normalizer_source_reference_mismatch")
        if source.get("path"):
            _verify(Path(source["path"]), source.get("sha256"), "normalizer_source")
        self._normalizer_payload = payload
        return normalization

    def _validate_normalizer_scope(self):
        declared = self._normalizer_payload.get("training_audio_sha256")
        if not isinstance(declared, list) or not declared or any(not _is_sha(value) for value in declared):
            raise ValueError("cue_ranker_feature_loader_normalizer_training_scope_missing")
        train_tracks = {
            str(row[name]).lower()
            for row in self._universe_rows.values()
            if row.get("split") == "train"
            for name in ("source_audio_sha256", "target_audio_sha256")
        }
        if set(declared) != train_tracks:
            raise ValueError("cue_ranker_feature_loader_normalizer_leakage_or_scope_mismatch")

    def _verify_input_chain(self):
        inputs = self.manifest.get("inputs", {})
        universe_info, labels_info = inputs.get("universe_manifest"), inputs.get("teacher_manifest")
        if not isinstance(universe_info, dict) or not isinstance(labels_info, dict):
            raise ValueError("cue_ranker_feature_loader_input_references_missing")
        universe_path, labels_path = Path(universe_info.get("path", "")), Path(labels_info.get("path", ""))
        _verify(universe_path, universe_info.get("sha256"), "universe_manifest")
        _verify(labels_path, labels_info.get("sha256"), "teacher_manifest")
        if _sha(universe_path) != self.manifest.get("universe_manifest_sha256") or _sha(labels_path) != self.manifest.get("teacher_manifest_sha256"):
            raise ValueError("cue_ranker_feature_loader_input_manifest_mismatch")
        universe, labels = _read_json(universe_path), _read_json(labels_path)
        if universe.get("test") != {"state": "sealed_not_materialized"} or labels.get("test") != {"state": "sealed_not_materialized"}:
            raise ValueError("cue_ranker_feature_loader_test_split_rejected")
        if labels.get("universe_manifest_sha256") != _sha(universe_path):
            raise ValueError("cue_ranker_feature_loader_teacher_universe_mismatch")
        universe_rows, teacher_rows = {}, {}
        for split in ("train", "validation"):
            for item in _load_record_shard(universe_path.parent, universe, f"{split}_candidates"):
                if item.get("split") not in (None, split):
                    raise ValueError("cue_ranker_feature_loader_universe_split_mismatch")
                item["split"] = split
                universe_rows[_row_key(item)] = item
            for item in _load_record_shard(labels_path.parent, labels, f"{split}_teacher_labels"):
                item["split"] = split
                teacher_rows[_row_key(item)] = item
        return universe_rows, teacher_rows

    def _artifact(self, candidate, role, target_bpm, provenance):
        track = candidate[f"{role}_track"]
        expected_audio = str(track.get("sha256", "")).lower()
        expected_payload = provenance.get(f"{role}_feature_payload_sha256")
        expected_manifest = provenance.get(f"{role}_feature_manifest_sha256")
        key = (expected_audio, target_bpm, expected_payload, expected_manifest)
        if key in self._artifacts:
            return self._artifacts[key]
        root = self.feature_cache_root / "feature_protocol_v2" / expected_audio[:16]
        if not root.is_dir():
            raise FileNotFoundError("cue_ranker_feature_cache_missing")
        for manifest_path in sorted(root.glob("*/manifest.json")):
            if _sha(manifest_path) != expected_manifest:
                continue
            manifest = _read_json(manifest_path)
            if str(manifest.get("source_sha256", "")).lower() != expected_audio:
                continue
            if int(manifest.get("sample_rate", -1)) != 44100:
                continue
            if target_bpm is None:
                if float(manifest.get("aligned_bpm", -1)) != float(candidate[f"{role}_bpm"]):
                    continue
            elif float(manifest.get("aligned_bpm", -1)) != float(target_bpm):
                continue
            data_path = manifest_path.parent / str(manifest.get("data_file", ""))
            if not data_path.is_file() or _sha(data_path) != expected_payload:
                continue
            with np.load(data_path, allow_pickle=False) as data:
                arrays = {name: np.asarray(data[name]) for name in ("base_features", "bin_boundaries", "spectral_flux_raw", "onset_strength_raw")}
            if arrays["base_features"].dtype != np.float32 or arrays["base_features"].ndim != 2 or arrays["base_features"].shape[1] != 54:
                raise ValueError("cue_ranker_feature_cache_shape_invalid")
            if not all(np.isfinite(value).all() for value in arrays.values() if np.issubdtype(value.dtype, np.floating)):
                raise ValueError("cue_ranker_feature_cache_nonfinite")
            artifact = TrackFeatureArtifact(cache_directory=manifest_path.parent, manifest=manifest, cache_hit=True, **arrays)
            self._artifacts[key] = artifact
            return artifact
        raise ValueError("cue_ranker_feature_cache_sha_reference_unresolved")


def _load_record_shard(root, manifest, name):
    info = manifest.get("files", {}).get(name)
    if not isinstance(info, dict):
        raise ValueError("cue_ranker_feature_loader_shard_missing")
    path = Path(root) / str(info.get("path", ""))
    _verify(path, info.get("sha256"), name)
    with np.load(path, allow_pickle=False) as payload:
        return [json.loads(value) for value in payload["row_json"].tolist()]


def _row_key(row):
    return (str(row.get("group_id")), str(row.get("candidate_id")), str(row.get("candidate_identity_sha256")))


def _read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _verify(path, expected, name):
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"cue_ranker_feature_loader_{name}_missing:{path}")
    if not _is_sha(expected) or _sha(path) != str(expected).lower():
        raise ValueError(f"cue_ranker_feature_loader_{name}_sha_mismatch")


def _is_sha(value):
    value = str(value or "").lower()
    return len(value) == 64 and all(character in "0123456789abcdef" for character in value)
