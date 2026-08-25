"""Frozen offline Teacher labels for Cue-Ranker Dataset Format 3.

The scorer is deliberately separate from the ranker and accepts only the
already sampled train/validation universe.  It never offers a test split.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import shutil
import uuid

import numpy as np

from src.control import DifferentiableVocalAwareRenderer, VariableVocalAwareTransitionObjective
from src.control.differentiable import VocalAwareTransitionObjectiveConfig
from src.features.cue_ranker_universe import (
    _ALLOWED_SPLITS,
    _atomic_json_write,
    _file_record,
    _file_sha256,
    _read_json,
    _verify_file,
    load_cue_ranker_universe_rows,
)
from src.features.variable_contract import geometry_for_length
from .variable_model import VariableTCNBiLSTMControlConfig, VariableTCNBiLSTMTransitionControl
from .variable_runner import (
    VARIABLE_TEMPORAL_TRAINING_RUNNER_NAME,
    VARIABLE_TRAINING_RUN_FORMAT_VERSION,
)


TEACHER_RELEASE_FORMAT_VERSION = 1
TEACHER_LABEL_FORMAT_VERSION = 1
TEACHER_MODEL_NAME = "variable_tcn_bilstm_transition_control_v1"
TEACHER_ALIGNMENT_CONTRACT = "local_grid_target_to_source_v1"
TEACHER_OBJECTIVE = "VariableVocalAwareTransitionObjective_v5_time_normalized"
TEACHER_GUARD = "rendered_transition_baseline_v1"


@dataclass(frozen=True)
class TeacherEvaluation:
    """An auditable result for exactly one sampled Candidate identity."""

    utility: float | None
    guard_score: float | None
    provenance: dict
    error_code: str | None = None


@dataclass(frozen=True)
class CueRankerTeacherLabelResult:
    output_directory: Path
    manifest_path: Path
    counts: dict[str, dict[str, int]]


def seal_teacher_release(run_manifest_path, checkpoint_path, output_path, *, renderer_config, objective_config, normalizer_sha256, backend_provenance, device="cpu", gpu_tolerance=None):
    """Create a SHA-bound release; checkpoint loading is `weights_only=True`."""
    import torch

    run_manifest_path, checkpoint_path, output_path = map(Path, (run_manifest_path, checkpoint_path, output_path))
    if output_path.exists(): raise FileExistsError(f"Teacher release already exists: {output_path}")
    run_manifest = _validate_teacher_run_manifest(run_manifest_path, checkpoint_path)
    checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=True)
    _validate_teacher_checkpoint(checkpoint, run_manifest)
    state = checkpoint.get("model_state_dict")
    if not isinstance(state, dict): raise ValueError("teacher_checkpoint_model_state_dict_missing")
    state_schema = {key: list(value.shape) for key, value in sorted(state.items())}
    payload = {
        "format_version": TEACHER_RELEASE_FORMAT_VERSION,
        "model_name": TEACHER_MODEL_NAME,
        "checkpoint": {"path": str(checkpoint_path.resolve()), "sha256": _file_sha256(checkpoint_path), "bytes": checkpoint_path.stat().st_size, "kind": "torch_checkpoint"},
        "run_manifest": {"path": str(run_manifest_path.resolve()), "sha256": _file_sha256(run_manifest_path), "bytes": run_manifest_path.stat().st_size, "kind": "json"},
        "state_dict_schema_sha256": _canonical_sha(state_schema),
        "alignment_contract": TEACHER_ALIGNMENT_CONTRACT,
        "renderer": {"name": "DifferentiableVocalAwareRenderer", "config": dict(renderer_config)},
        "objective": {"name": TEACHER_OBJECTIVE, "config": dict(objective_config)},
        "normalizer_sha256": _sha(normalizer_sha256, "normalizer_sha256"),
        "backend_provenance": dict(backend_provenance),
        "environment": _environment_record(device, gpu_tolerance),
    }
    payload["teacher_contract_sha256"] = _canonical_sha(payload)
    _atomic_json_write(output_path, payload)
    return output_path


def verify_teacher_release(release_path):
    """Validate all fixed release artifacts before any checkpoint use."""
    release_path = Path(release_path)
    release = _read_json(release_path)
    if int(release.get("format_version", -1)) != TEACHER_RELEASE_FORMAT_VERSION: raise ValueError("teacher_release_format_unsupported")
    if release.get("model_name") != TEACHER_MODEL_NAME: raise ValueError("teacher_release_model_mismatch")
    if release.get("alignment_contract") != TEACHER_ALIGNMENT_CONTRACT: raise ValueError("teacher_release_alignment_mismatch")
    if release.get("objective", {}).get("name") != TEACHER_OBJECTIVE: raise ValueError("teacher_release_objective_mismatch")
    resolved = {}
    for key in ("checkpoint", "run_manifest"):
        item = release.get(key, {})
        path = Path(item.get("path", ""))
        # Absolute references are intentional release provenance. Relative paths
        # are resolved against the release file for portable synthetic fixtures.
        if not path.is_absolute(): path = release_path.parent / path
        _verify_file(path, _sha(item.get("sha256"), f"teacher_release_{key}_sha256"))
        resolved[key] = path
    _validate_teacher_run_manifest(resolved["run_manifest"], resolved["checkpoint"])
    contract = dict(release); contract.pop("teacher_contract_sha256", None)
    if release.get("teacher_contract_sha256") != _canonical_sha(contract): raise ValueError("teacher_release_contract_sha256_mismatch")
    return release, _file_sha256(release_path)


def load_frozen_teacher(release_path):
    """Load the fixed variable controller in evaluation mode with no optimizer."""
    import torch

    release, release_sha = verify_teacher_release(release_path)
    checkpoint_item = release["checkpoint"]
    checkpoint_path = Path(checkpoint_item["path"])
    if not checkpoint_path.is_absolute(): checkpoint_path = Path(release_path).parent / checkpoint_path
    run_item = release["run_manifest"]
    run_manifest_path = Path(run_item["path"])
    if not run_manifest_path.is_absolute(): run_manifest_path = Path(release_path).parent / run_manifest_path
    run_manifest = _validate_teacher_run_manifest(run_manifest_path, checkpoint_path)
    checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=True)
    _validate_teacher_checkpoint(checkpoint, run_manifest)
    model = VariableTCNBiLSTMTransitionControl(VariableTCNBiLSTMControlConfig())
    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()
    return model, release, release_sha


def score_prepared_candidate(model, record, prepared, release, *, guard_scorer, guard_threshold=0.50):
    """Score one prepared candidate through frozen Controller → v5 → Guard.

    ``prepared`` is a resolver-owned payload containing the existing feature
    windows and four locally aligned waveforms.  This keeps raw-data/cache I/O
    outside the sealed label loop and makes all provenance explicit.
    """
    import torch

    try:
        _validate_prepared(record, prepared, release)
        cache_key = teacher_cache_key(record, prepared["provenance"], release)
        geometry = geometry_for_length(record["transition_length_bars"], sequence_length=record["sequence_length"])
        device = next(model.parameters()).device
        dtype = next(model.parameters()).dtype
        def tensor(name): return torch.as_tensor(prepared[name], device=device, dtype=dtype)
        features_a, features_b, global_features, length_condition = tensor("features_a"), tensor("features_b"), tensor("global_features"), tensor("length_condition")
        if features_a.ndim == 2: features_a = features_a.unsqueeze(0); features_b = features_b.unsqueeze(0); global_features = global_features.unsqueeze(0); length_condition = length_condition.reshape(1, 1)
        renderer = DifferentiableVocalAwareRenderer(**release["renderer"]["config"]).to(device=device, dtype=dtype)
        objective = VariableVocalAwareTransitionObjective(
            config=VocalAwareTransitionObjectiveConfig(**release["objective"]["config"])
        ).to(device=device)
        with torch.no_grad():
            controls = model(features_a, features_b, global_features, transition_length_bars=geometry.transition_length_bars, length_condition=length_condition)
            audio = {name: tensor(name) for name in ("source_audio", "target_audio", "source_vocal_audio", "target_vocal_audio")}
            rendered = renderer(audio["source_audio"], audio["target_audio"], audio["source_vocal_audio"], audio["target_vocal_audio"], controls.mix_position[0], controls.low_end_position[0], controls.vocal_position[0], controls.vocal_duck_a[0], controls.vocal_duck_b[0])
            terms = objective(rendered, audio["source_audio"], audio["target_audio"], audio["source_vocal_audio"], audio["target_vocal_audio"], features_a[0], features_b[0], transition_length_bars=geometry.transition_length_bars)
            total = float(terms["loss"].detach().cpu())
        if not math.isfinite(total): raise ValueError("teacher_nonfinite_total_loss")
        guard_score = float(guard_scorer(record, prepared, rendered))
        if not math.isfinite(guard_score): raise ValueError("teacher_nonfinite_guard_score")
        provenance = dict(prepared["provenance"])
        provenance["teacher_cache_key_sha256"] = cache_key
        return TeacherEvaluation(-total, guard_score, provenance, None)
    except Exception as error:
        return TeacherEvaluation(None, None, dict(prepared.get("provenance", {})) if isinstance(prepared, dict) else {}, _canonical_error(error))


def label_cue_ranker_teacher(universe_directory, release_path, output_directory, *, evaluator, guard_threshold=0.50):
    """Label every sampled row, isolating technical failures by candidate."""
    universe_directory, output_directory = Path(universe_directory), Path(output_directory)
    if output_directory.exists(): raise FileExistsError(f"Teacher label output already exists: {output_directory}")
    if not 0.0 <= float(guard_threshold) <= 1.0: raise ValueError("guard_threshold must be in [0, 1]")
    release, release_sha = verify_teacher_release(release_path)
    universe_manifest_path = universe_directory / "manifest.json"
    universe_manifest = _read_json(universe_manifest_path)
    if universe_manifest.get("test", {}).get("state") != "sealed_not_materialized": raise ValueError("teacher_universe_not_test_sealed")
    labels, counts = {}, {}
    for split in _ALLOWED_SPLITS:
        rows = load_cue_ranker_universe_rows(universe_directory, split)
        split_labels = []
        for row in rows:
            if not row["label_selected"]: continue
            try:
                result = evaluator(row, release)
                if not isinstance(result, TeacherEvaluation): raise TypeError("teacher_evaluator_must_return_TeacherEvaluation")
                label = _label_row(row, result, release_sha, float(guard_threshold))
            except Exception as error:
                label = _label_row(row, TeacherEvaluation(None, None, {}, _canonical_error(error)), release_sha, float(guard_threshold))
            split_labels.append(label)
        labels[split] = split_labels
        counts[split] = _status_counts(split_labels)
    temporary = output_directory.with_name(f".{output_directory.name}.{uuid.uuid4().hex}.tmp")
    temporary.mkdir(parents=True)
    try:
        files = {}
        for split in _ALLOWED_SPLITS:
            path = temporary / "teacher" / f"{split}-labels-00000.npz"
            _write_labels(path, labels[split])
            files[f"{split}_teacher_labels"] = _file_record(path, temporary, "npz")
        manifest = {"format_version": TEACHER_LABEL_FORMAT_VERSION, "universe_manifest_sha256": _file_sha256(universe_manifest_path), "teacher_release_sha256": release_sha, "teacher_contract_sha256": release["teacher_contract_sha256"], "guard": {"name": TEACHER_GUARD, "threshold": float(guard_threshold)}, "alignment_contract": TEACHER_ALIGNMENT_CONTRACT, "counts": counts, "files": files, "test": {"state": "sealed_not_materialized"}}
        _atomic_json_write(temporary / "manifest.json", manifest)
        os.replace(temporary, output_directory)
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True); raise
    return CueRankerTeacherLabelResult(output_directory, output_directory / "manifest.json", counts)


def teacher_cache_key(record, provenance, release):
    """Hash every cache-affecting contract field; no BPM-only alignment key."""
    required = ("source_feature_payload_sha256", "target_feature_payload_sha256", "source_feature_manifest_sha256", "target_feature_manifest_sha256", "source_grid_sha256", "target_grid_sha256", "source_audio_sha256", "target_audio_sha256", "source_stem_payload_sha256", "target_stem_payload_sha256", "rubberband_backend_sha256", "local_source_window_samples")
    missing = [key for key in required if key not in provenance]
    if missing: raise ValueError("teacher_cache_provenance_missing:" + ",".join(missing))
    return _canonical_sha({"candidate_identity_sha256": record["candidate_identity_sha256"], "candidate_request_config_sha256": record["candidate_request_config_sha256"], "alignment_contract": TEACHER_ALIGNMENT_CONTRACT, "teacher_contract_sha256": release["teacher_contract_sha256"], "renderer": release["renderer"], "objective": release["objective"], "normalizer_sha256": release["normalizer_sha256"], "provenance": provenance})


def _label_row(row, result, release_sha, threshold):
    status = "failed"
    if result.error_code is None and result.utility is not None and math.isfinite(float(result.utility)) and result.guard_score is not None and math.isfinite(float(result.guard_score)):
        status = "scored" if float(result.guard_score) >= threshold else "guard_rejected"
    provenance = dict(result.provenance)
    return {"group_id": row["group_id"], "candidate_id": row["candidate_id"], "candidate_identity_sha256": row["candidate_identity_sha256"], "teacher_status": status, "teacher_utility": None if result.utility is None else float(result.utility), "render_guard_score": None if result.guard_score is None else float(result.guard_score), "teacher_release_sha256": release_sha, "teacher_provenance_sha256": _canonical_sha(provenance), "teacher_provenance": provenance, "error_code": result.error_code}


def _validate_prepared(record, prepared, release):
    if not isinstance(prepared, dict) or not isinstance(prepared.get("provenance"), dict): raise ValueError("teacher_prepared_inputs_missing_provenance")
    if prepared["provenance"].get("alignment_contract") != TEACHER_ALIGNMENT_CONTRACT: raise ValueError("teacher_alignment_contract_mismatch")
    if prepared["provenance"].get("normalizer_sha256") != release["normalizer_sha256"]: raise ValueError("teacher_normalizer_sha_mismatch")
    for name in ("features_a", "features_b", "global_features", "length_condition", "source_audio", "target_audio", "source_vocal_audio", "target_vocal_audio"):
        if name not in prepared: raise ValueError(f"teacher_prepared_{name}_missing")


def _validate_teacher_run_manifest(run_manifest_path, checkpoint_path):
    run_manifest_path, checkpoint_path = Path(run_manifest_path), Path(checkpoint_path)
    run = _read_json(run_manifest_path)
    if run.get("format_version") != VARIABLE_TRAINING_RUN_FORMAT_VERSION:
        raise ValueError("teacher_run_format_unsupported")
    if run.get("runner_name") != VARIABLE_TEMPORAL_TRAINING_RUNNER_NAME:
        raise ValueError("teacher_run_runner_mismatch")
    if run.get("status") != "completed":
        raise ValueError("teacher_run_not_completed")
    contract = run.get("contract")
    if not isinstance(contract, dict) or contract.get("model_name") != TEACHER_MODEL_NAME:
        raise ValueError("teacher_run_model_mismatch")
    record = run.get("files", {}).get("best_checkpoint")
    if not isinstance(record, dict):
        raise ValueError("teacher_run_best_checkpoint_missing")
    declared = Path(str(record.get("path", "")))
    if not declared.is_absolute(): declared = run_manifest_path.parent / declared
    if declared.resolve() != checkpoint_path.resolve():
        raise ValueError("teacher_run_best_checkpoint_path_mismatch")
    _verify_file(checkpoint_path, _sha(record.get("sha256"), "teacher_run_best_checkpoint_sha256"))
    return run


def _validate_teacher_checkpoint(checkpoint, run):
    if not isinstance(checkpoint, dict):
        raise ValueError("teacher_checkpoint_invalid")
    if checkpoint.get("format_version") != VARIABLE_TRAINING_RUN_FORMAT_VERSION:
        raise ValueError("teacher_checkpoint_format_mismatch")
    if checkpoint.get("runner_name") != VARIABLE_TEMPORAL_TRAINING_RUNNER_NAME:
        raise ValueError("teacher_checkpoint_runner_mismatch")
    if checkpoint.get("model_name") != TEACHER_MODEL_NAME:
        raise ValueError("teacher_checkpoint_model_mismatch")
    if checkpoint.get("run_id") != run.get("run_id") or checkpoint.get("contract") != run.get("contract"):
        raise ValueError("teacher_checkpoint_contract_mismatch")
    if not isinstance(checkpoint.get("model_state_dict"), dict):
        raise ValueError("teacher_checkpoint_model_state_dict_missing")


def _write_labels(path, labels):
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(path, row_json=np.asarray([json.dumps(row, sort_keys=True, separators=(",", ":")) for row in labels], dtype=str))


def _status_counts(labels):
    result = {"selected": len(labels), "scored": 0, "guard_rejected": 0, "failed": 0}
    for label in labels: result[label["teacher_status"]] += 1
    return result


def _environment_record(device, tolerance):
    import torch
    return {"python": platform.python_version(), "torch": torch.__version__, "numpy": np.__version__, "device": str(device), "cuda": torch.version.cuda, "cudnn": torch.backends.cudnn.version(), "deterministic_algorithms": bool(torch.are_deterministic_algorithms_enabled()), "gpu_tolerance": tolerance}
def _canonical_sha(value): return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
def _sha(value, name):
    value = str(value or "").lower()
    if len(value) != 64 or any(char not in "0123456789abcdef" for char in value): raise ValueError(f"{name} must be a SHA-256 hex digest")
    return value
def _canonical_error(error): return f"{type(error).__name__}:{str(error).splitlines()[0][:240]}"
