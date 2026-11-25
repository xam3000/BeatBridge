"""Unmaintained proxy-teacher labels for the historical Cue-Ranker Dataset Format 3.

The scorer is deliberately separate from the ranker and accepts only the
already sampled train/validation universe.  It never offers a test split.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
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
from src.ranking.rendered_transition import (
    RenderedTransitionInput,
    RenderedTransitionMetricConfig,
    rank_rendered_transitions,
)
from .variable_model import VariableTCNBiLSTMControlConfig, VariableTCNBiLSTMTransitionControl
from .variable_runner import (
    VARIABLE_TEMPORAL_TRAINING_RUNNER_NAME,
    VARIABLE_TRAINING_RUN_FORMAT_VERSION,
)
from .cue_ranker_teacher_resolver import (
    CueRankerCandidateResolver,
    DEFAULT_CUE_RANKER_TEACHER_WAVEFORM_CACHE_ROOT,
)


TEACHER_RELEASE_FORMAT_VERSION = 2
TEACHER_LABEL_FORMAT_VERSION = 2
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
    guard_rejected: bool = False


@dataclass(frozen=True)
class TeacherLabelingConfig:
    """Explicit failure and resource limits for an interruptible label run."""

    guard_threshold: float = 0.50
    max_candidates: int | None = None
    max_technical_failures: int | None = None
    max_technical_failure_rate: float | None = None

    def __post_init__(self):
        if not 0.0 <= float(self.guard_threshold) <= 1.0:
            raise ValueError("guard_threshold must be in [0, 1]")
        if self.max_candidates is not None and int(self.max_candidates) < 1:
            raise ValueError("max_candidates must be at least one")
        if self.max_technical_failures is not None and int(self.max_technical_failures) < 0:
            raise ValueError("max_technical_failures must be non-negative")
        if self.max_technical_failure_rate is not None and not 0.0 <= float(self.max_technical_failure_rate) <= 1.0:
            raise ValueError("max_technical_failure_rate must be in [0, 1]")


@dataclass(frozen=True)
class CueRankerTeacherLabelResult:
    output_directory: Path
    manifest_path: Path
    counts: dict[str, dict[str, int]]
    cache_hits: int = 0
    cache_misses: int = 0


def seal_teacher_release(run_manifest_path, checkpoint_path, output_path, *, renderer_config=None, objective_config=None, normalizer_sha256=None, normalizer_path=None, backend_provenance=None, device="cpu", gpu_tolerance=None):
    """Seal one explicit completed Variable-TCN run's declared best checkpoint.

    This function performs no discovery or scientific model selection.  The
    selected checkpoint must already be the run manifest's hash-bound best
    checkpoint; the sole deserialisation is ``weights_only=True``.
    """
    import torch

    run_manifest_path, checkpoint_path, output_path = map(Path, (run_manifest_path, checkpoint_path, output_path))
    if output_path.exists(): raise FileExistsError(f"Teacher release already exists: {output_path}")
    run_manifest = _validate_teacher_run_manifest(run_manifest_path, checkpoint_path)
    checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=True)
    _validate_teacher_checkpoint(checkpoint, run_manifest)
    state = checkpoint.get("model_state_dict")
    if not isinstance(state, dict): raise ValueError("teacher_checkpoint_model_state_dict_missing")
    state_schema = {key: {"shape": list(value.shape), "dtype": str(value.dtype)} for key, value in sorted(state.items())}
    renderer_config = dict(renderer_config or run_manifest["contract"].get("renderer", {}))
    renderer_config.pop("name", None)
    if not renderer_config:
        raise ValueError("teacher_renderer_contract_missing")
    objective_config = dict(objective_config or asdict(VocalAwareTransitionObjectiveConfig()))
    normalizer = _normalizer_release_record(normalizer_path, normalizer_sha256)
    backend_provenance = _backend_provenance(backend_provenance)
    code_provenance = _teacher_code_provenance()
    renderer = {"name": "DifferentiableVocalAwareRenderer", "config": renderer_config}
    objective = {"name": TEACHER_OBJECTIVE, "config": dict(objective_config)}
    payload = {
        "format_version": TEACHER_RELEASE_FORMAT_VERSION,
        "model_name": TEACHER_MODEL_NAME,
        "model_format_version": run_manifest["contract"].get("model_format_version"),
        "model_config": dict(run_manifest["contract"].get("model", {}).get("config", {})),
        "model_contract_sha256": _canonical_sha(run_manifest["contract"]),
        "checkpoint": {"path": str(checkpoint_path.resolve()), "sha256": _file_sha256(checkpoint_path), "bytes": checkpoint_path.stat().st_size, "kind": "torch_checkpoint"},
        "run_manifest": {"path": str(run_manifest_path.resolve()), "sha256": _file_sha256(run_manifest_path), "bytes": run_manifest_path.stat().st_size, "kind": "json"},
        "state_dict_schema_sha256": _canonical_sha(state_schema),
        "alignment_contract": TEACHER_ALIGNMENT_CONTRACT,
        "renderer": renderer,
        "renderer_contract_sha256": _canonical_sha(renderer),
        "objective": objective,
        "objective_contract_sha256": _canonical_sha(objective),
        "guard": {"name": TEACHER_GUARD, "config": RenderedTransitionMetricConfig().to_dict()},
        "alignment_contract_sha256": code_provenance["waveform_alignment"],
        "normalizer_sha256": normalizer["sha256"],
        "normalizer": normalizer,
        "backend_provenance": backend_provenance,
        "code_provenance": code_provenance,
        "environment": _environment_record(device, gpu_tolerance),
    }
    payload["teacher_contract_sha256"] = _canonical_sha(payload)
    _atomic_json_write(output_path, payload)
    return output_path


def verify_teacher_release(release_path):
    """Validate all fixed release artifacts before any checkpoint use."""
    release_path = Path(release_path)
    release = _read_json(release_path)
    if int(release.get("format_version", -1)) not in {1, TEACHER_RELEASE_FORMAT_VERSION}: raise ValueError("teacher_release_format_unsupported")
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
    _sha(release.get("normalizer_sha256"), "teacher_release_normalizer_sha256")
    normalizer = release.get("normalizer")
    if isinstance(normalizer, dict) and normalizer.get("path"):
        normalizer_path = _resolve_release_path(release_path, normalizer["path"])
        _verify_file(normalizer_path, _sha(normalizer.get("sha256"), "teacher_release_normalizer_sha256"))
        if normalizer.get("sha256") != release["normalizer_sha256"]:
            raise ValueError("teacher_release_normalizer_sha_mismatch")
        _normalizer_stats(_read_json(normalizer_path))
    if int(release.get("format_version", 1)) >= 2:
        _backend_provenance(release.get("backend_provenance"))
        expected_code = _teacher_code_provenance()
        if release.get("code_provenance") != expected_code:
            raise ValueError("teacher_release_code_sha_mismatch")
        if release.get("model_contract_sha256") != _canonical_sha(_read_json(resolved["run_manifest"])["contract"]):
            raise ValueError("teacher_release_model_contract_sha_mismatch")
        if release.get("renderer_contract_sha256") != _canonical_sha(release.get("renderer")):
            raise ValueError("teacher_release_renderer_contract_sha_mismatch")
        if release.get("objective_contract_sha256") != _canonical_sha(release.get("objective")):
            raise ValueError("teacher_release_objective_contract_sha_mismatch")
        if release.get("alignment_contract_sha256") != expected_code["waveform_alignment"]:
            raise ValueError("teacher_release_alignment_sha_mismatch")
    contract = dict(release); contract.pop("teacher_contract_sha256", None)
    if release.get("teacher_contract_sha256") != _canonical_sha(contract): raise ValueError("teacher_release_contract_sha256_mismatch")
    return release, _file_sha256(release_path)


def load_frozen_teacher(release_path):
    """Load the fixed variable controller in evaluation mode with no optimizer."""
    import torch

    release, release_sha = verify_teacher_release(release_path)
    checkpoint_item = release["checkpoint"]
    checkpoint_path = _resolve_release_path(release_path, checkpoint_item["path"])
    run_item = release["run_manifest"]
    run_manifest_path = _resolve_release_path(release_path, run_item["path"])
    run_manifest = _validate_teacher_run_manifest(run_manifest_path, checkpoint_path)
    checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=True)
    _validate_teacher_checkpoint(checkpoint, run_manifest)
    state_schema = {key: {"shape": list(value.shape), "dtype": str(value.dtype)} for key, value in sorted(checkpoint["model_state_dict"].items())}
    if _canonical_sha(state_schema) != release["state_dict_schema_sha256"]:
        raise ValueError("teacher_checkpoint_state_schema_mismatch")
    model = VariableTCNBiLSTMTransitionControl(
        VariableTCNBiLSTMControlConfig(**dict(release.get("model_config") or {}))
    )
    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()
    return model, release, release_sha


def score_prepared_candidate(model, record, prepared, release, *, guard_scorer=None, guard_threshold=0.50):
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
        provenance = dict(prepared["provenance"])
    except Exception as error:
        return TeacherEvaluation(None, None, dict(prepared.get("provenance", {})) if isinstance(prepared, dict) else {}, _canonical_error(error))

    try:
        scorer = guard_scorer or _production_guard_scorer
        guard_score = float(scorer(record, prepared, rendered) if guard_scorer else scorer(record, prepared, rendered, release))
        if not math.isfinite(guard_score): raise ValueError("teacher_nonfinite_guard_score")
    except Exception as error:
        # Controller and Objective were valid.  A missing or failed external
        # guard is therefore a documented relative negative anchor, not a
        # fabricated objective score and not a technical model failure.
        return TeacherEvaluation(-total, None, provenance, _canonical_error(error), guard_rejected=True)
    provenance["teacher_cache_key_sha256"] = cache_key
    return TeacherEvaluation(-total, guard_score, provenance, None)


def _production_guard_scorer(record, prepared, rendered, release):
    """Evaluate the actual v5 renderer output with the frozen v1 guard.

    The locally aligned source/target windows are the guard's immediate
    context around the rendered bridge.  This adds no waveform operation: all
    three blocks already have the exact common shape required by the
    ``local_grid_target_to_source_v1`` contract.
    """
    source = np.asarray(prepared["source_audio"], dtype=np.float32)
    target = np.asarray(prepared["target_audio"], dtype=np.float32)
    bridge = rendered.audio.detach().cpu().numpy().astype(np.float32, copy=False)
    if source.ndim != 2 or target.shape != source.shape or bridge.shape != source.shape:
        raise ValueError("teacher_guard_four_waveform_shape_mismatch")
    samples = int(source.shape[-1])
    ranking = rank_rendered_transitions((RenderedTransitionInput(
        candidate_id=str(record["candidate_id"]),
        renderer="DifferentiableVocalAwareRenderer",
        audio=np.concatenate((source, bridge, target), axis=-1),
        sample_rate=int(release["renderer"]["config"]["sample_rate"]),
        transition_start_sample=samples,
        transition_end_sample=2 * samples,
        transition_length_beats=int(record["transition_length_beats"]),
        bpm=float(record["candidate"]["source_bpm"]),
    ),), config=RenderedTransitionMetricConfig(**release.get("guard", {}).get("config", {})))
    if ranking.failures or len(ranking.scores) != 1:
        raise ValueError("teacher_render_guard_failed")
    return float(ranking.scores[0].total_score)


def label_cue_ranker_teacher(universe_directory, release_path, output_directory, *, evaluator=None, guard_threshold=0.50, config=None, resume=False, split_map=None, resolver=None):
    """Persist labels candidate by candidate and resume only verified cache hits.

    Production mode is selected by omitting ``evaluator``.  Synthetic tests
    retain an explicit evaluator seam, while the production path accepts no
    test split and loads the fixed controller exactly once.
    """
    universe_directory, output_directory = Path(universe_directory), Path(output_directory)
    configuration = config or TeacherLabelingConfig(guard_threshold=float(guard_threshold))
    if not isinstance(configuration, TeacherLabelingConfig):
        raise TypeError("config must be TeacherLabelingConfig")
    release, release_sha = verify_teacher_release(release_path)
    active_resolver = None
    if evaluator is None:
        active_resolver = resolver or CueRankerCandidateResolver(release, release_sha)
    universe_manifest_path = universe_directory / "manifest.json"
    universe_manifest = _read_json(universe_manifest_path)
    _verify_teacher_universe(universe_directory, universe_manifest, split_map=split_map)
    binding = {
        "format_version": TEACHER_LABEL_FORMAT_VERSION,
        "universe_manifest_sha256": _file_sha256(universe_manifest_path),
        "teacher_release_sha256": release_sha,
        "teacher_contract_sha256": release["teacher_contract_sha256"],
        "guard": {"name": TEACHER_GUARD, "threshold": float(configuration.guard_threshold)},
        "alignment_contract": TEACHER_ALIGNMENT_CONTRACT,
        "waveform_cache_root": str(getattr(active_resolver, "waveform_cache_root", DEFAULT_CUE_RANKER_TEACHER_WAVEFORM_CACHE_ROOT)),
        "test": {"state": "sealed_not_materialized"},
    }
    _prepare_label_root(output_directory, binding, resume=resume)
    selected_rows = {
        split: [row for row in _load_teacher_universe_rows(universe_directory, split) if row["label_selected"]]
        for split in _ALLOWED_SPLITS
    }
    if evaluator is None:
        model, loaded_release, loaded_sha = load_frozen_teacher(release_path)
        if loaded_sha != release_sha or loaded_release["teacher_contract_sha256"] != release["teacher_contract_sha256"]:
            raise ValueError("teacher_release_changed_during_label_load")

        def evaluator(row, frozen_release):
            prepared = active_resolver.resolve(row)
            prepared["provenance"] = dict(prepared["provenance"], teacher_release_sha256=release_sha)
            return score_prepared_candidate(model, row, prepared, frozen_release, guard_threshold=float(configuration.guard_threshold))

    labels, cache_hits, cache_misses, attempted, technical_failures, new_evaluations = {split: [] for split in _ALLOWED_SPLITS}, 0, 0, 0, 0, 0
    for split in _ALLOWED_SPLITS:
        for row in selected_rows[split]:
            cache_key = _label_cache_key(row, release_sha)
            label = _read_label_cache(output_directory, row, release_sha, cache_key)
            if label is not None:
                cache_hits += 1
            else:
                if configuration.max_candidates is not None and new_evaluations >= int(configuration.max_candidates):
                    _atomic_json_write(output_directory / "progress.json", {**binding, "state": "aborted_candidate_budget", "attempted": attempted, "technical_failures": technical_failures, "new_evaluations": new_evaluations})
                    raise RuntimeError("teacher_candidate_budget_exceeded")
                cache_misses += 1
                new_evaluations += 1
                try:
                    result = evaluator(row, release)
                    if not isinstance(result, TeacherEvaluation): raise TypeError("teacher_evaluator_must_return_TeacherEvaluation")
                    label = _label_row(row, result, release_sha, float(configuration.guard_threshold))
                except Exception as error:
                    label = _label_row(row, TeacherEvaluation(None, None, {}, _canonical_error(error)), release_sha, float(configuration.guard_threshold))
                _write_label_cache(output_directory, row, release_sha, cache_key, label)
            labels[split].append(label)
            attempted += 1
            technical_failures += int(label["teacher_status"] == "failed")
            if _failure_budget_exceeded(configuration, attempted, technical_failures):
                _atomic_json_write(output_directory / "progress.json", {**binding, "state": "aborted_failure_budget", "attempted": attempted, "technical_failures": technical_failures})
                raise RuntimeError("teacher_failure_budget_exceeded")
    counts = {split: _status_counts(labels[split]) for split in _ALLOWED_SPLITS}
    _write_final_label_artifacts(output_directory, labels, binding, counts, configuration)
    return CueRankerTeacherLabelResult(output_directory, output_directory / "manifest.json", counts, cache_hits, cache_misses)


def teacher_cache_key(record, provenance, release, *, release_sha256=None):
    """Hash every cache-affecting contract field; no BPM-only alignment key."""
    required = ("source_feature_payload_sha256", "target_feature_payload_sha256", "source_feature_manifest_sha256", "target_feature_manifest_sha256", "source_grid_sha256", "target_grid_sha256", "source_audio_sha256", "target_audio_sha256", "source_stem_payload_sha256", "target_stem_payload_sha256", "rubberband_backend_sha256", "local_source_window_samples")
    missing = [key for key in required if key not in provenance or provenance[key] is None]
    if missing: raise ValueError("teacher_cache_provenance_missing:" + ",".join(missing))
    release_sha256 = release_sha256 or provenance.get("teacher_release_sha256") or release["teacher_contract_sha256"]
    return _canonical_sha({"candidate_identity_sha256": _sha(record["candidate_identity_sha256"], "candidate_identity_sha256"), "candidate_request_config_sha256": _sha(record["candidate_request_config_sha256"], "candidate_request_config_sha256"), "teacher_release_sha256": _sha(release_sha256, "teacher_release_sha256"), "alignment_contract": TEACHER_ALIGNMENT_CONTRACT, "teacher_contract_sha256": release["teacher_contract_sha256"], "renderer": release["renderer"], "objective": release["objective"], "guard": release.get("guard"), "normalizer_sha256": release["normalizer_sha256"], "backend_provenance": release["backend_provenance"], "provenance": provenance})


def _label_row(row, result, release_sha, threshold):
    status = "failed"
    if result.guard_rejected:
        status = "guard_rejected"
    elif result.error_code is None and result.utility is not None and math.isfinite(float(result.utility)) and result.guard_score is not None and math.isfinite(float(result.guard_score)):
        status = "scored" if float(result.guard_score) >= threshold else "guard_rejected"
    provenance = dict(result.provenance)
    return {"group_id": row["group_id"], "candidate_id": row["candidate_id"], "candidate_identity_sha256": row["candidate_identity_sha256"], "teacher_status": status, "label_status": "success" if status == "scored" else ("guard_rejected" if status == "guard_rejected" else "technical_failure"), "teacher_utility": None if result.utility is None else float(result.utility), "render_guard_score": None if result.guard_score is None else float(result.guard_score), "teacher_release_sha256": release_sha, "teacher_provenance_sha256": _canonical_sha(provenance), "teacher_provenance": provenance, "error_code": result.error_code}


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


def _normalizer_release_record(path, sha256):
    """Bind a training-only normalizer file when sealing production releases."""
    if path is None:
        # Compatibility for historical synthetic fixtures.  The production
        # resolver rejects this incomplete form before touching audio.
        return {"path": None, "sha256": _sha(sha256, "normalizer_sha256")}
    path = Path(path)
    digest = _file_sha256(path)
    if sha256 is not None and _sha(sha256, "normalizer_sha256") != digest:
        raise ValueError("teacher_normalizer_sha_mismatch")
    _normalizer_stats(_read_json(path))
    return {"path": str(path.resolve()), "sha256": digest, "bytes": path.stat().st_size, "kind": "json"}


def _normalizer_stats(payload):
    values = payload.get("statistics", payload) if isinstance(payload, dict) else None
    if not isinstance(values, dict) or values.get("fit_scope") != "training_tracks_only":
        raise ValueError("teacher_normalizer_not_training_only")
    for key in ("stats_id", "spectral_flux_log1p_p99", "onset_strength_log1p_p99"):
        if key not in values:
            raise ValueError("teacher_normalizer_invalid")
    if not all(math.isfinite(float(values[key])) for key in ("spectral_flux_log1p_p99", "onset_strength_log1p_p99")):
        raise ValueError("teacher_normalizer_nonfinite")
    return values


def _backend_provenance(value):
    if not isinstance(value, dict):
        raise ValueError("teacher_backend_provenance_missing")
    result = dict(value)
    result["rubberband_backend_sha256"] = _sha(result.get("rubberband_backend_sha256"), "rubberband_backend_sha256")
    return result


def _teacher_code_provenance():
    root = Path(__file__).resolve().parents[1]
    paths = {
        "teacher": Path(__file__),
        "resolver": root / "ml" / "cue_ranker_teacher_resolver.py",
        "variable_model": root / "ml" / "variable_model.py",
        "waveform_alignment": root / "ml" / "variable_waveform_cache.py",
        "renderer": root / "control" / "differentiable.py",
        "objective": root / "control" / "variable_differentiable.py",
        "guard": root / "ranking" / "rendered_transition.py",
    }
    return {name: _file_sha256(path) for name, path in paths.items()}


def _resolve_release_path(release_path, value):
    path = Path(str(value or ""))
    return path if path.is_absolute() else Path(release_path).parent / path


def _verify_teacher_universe(universe_directory, manifest, *, split_map):
    if int(manifest.get("format_version", -1)) != 1:
        raise ValueError("teacher_universe_format_unsupported")
    if manifest.get("test") != {"state": "sealed_not_materialized"}:
        raise ValueError("teacher_universe_not_test_sealed")
    # All materialised candidate shards are independently hash checked by the
    # loader.  If the caller supplies the external split authority, reject a
    # cross-split or test SHA before the resolver can inspect a track path.
    assignments = None if split_map is None else _normalise_split_map(split_map)
    if assignments is not None and manifest.get("split_map_sha256") != _canonical_sha(assignments):
        raise ValueError("teacher_universe_split_map_sha_mismatch")
    for split in _ALLOWED_SPLITS:
        for row in _load_teacher_universe_rows(universe_directory, split):
            if assignments is not None:
                if assignments.get(row.get("source_audio_sha256")) != split or assignments.get(row.get("target_audio_sha256")) != split:
                    raise ValueError("teacher_universe_cross_or_test_split_row")


def _load_teacher_universe_rows(universe_directory, split):
    """Use the SHA-verified shard selection as the split authority.

    Existing Universe-v1 rows predate a duplicated ``split`` column.  A
    present value must agree with the selected shard; an absent value is bound
    here exclusively from the already verified ``train``/``validation`` file.
    """
    rows = []
    for raw in load_cue_ranker_universe_rows(universe_directory, split):
        declared = raw.get("split")
        if declared is not None and declared != split:
            raise ValueError("teacher_universe_row_split_mismatch")
        rows.append(dict(raw, split=split))
    return rows


def _prepare_label_root(root, binding, *, resume):
    root = Path(root)
    marker = root / "teacher_binding.json"
    if root.exists():
        if not resume:
            raise FileExistsError(f"Teacher label output already exists: {root}")
        if not marker.is_file() or _read_json(marker) != binding:
            raise ValueError("teacher_label_resume_binding_mismatch")
        return
    root.mkdir(parents=True)
    _atomic_json_write(marker, binding)


def _label_cache_key(row, release_sha):
    return _canonical_sha({
        "format_version": 1,
        "teacher_release_sha256": _sha(release_sha, "teacher_release_sha256"),
        "candidate_identity_sha256": _sha(row["candidate_identity_sha256"], "candidate_identity_sha256"),
        "group_id": str(row["group_id"]),
        "candidate_id": str(row["candidate_id"]),
    })


def _label_cache_path(root, row, release_sha, cache_key):
    return Path(root) / "candidate_cache" / _sha(release_sha, "teacher_release_sha256") / _sha(row["candidate_identity_sha256"], "candidate_identity_sha256") / cache_key / "label.json"


def _read_label_cache(root, row, release_sha, cache_key):
    path = _label_cache_path(root, row, release_sha, cache_key)
    if not path.is_file():
        return None
    payload = _read_json(path)
    label = payload.get("label")
    if payload.get("format_version") != 2 or payload.get("cache_key_sha256") != cache_key or not isinstance(label, dict):
        raise ValueError("teacher_label_cache_contract_mismatch")
    if payload.get("label_sha256") != _canonical_sha(label):
        raise ValueError("teacher_label_cache_sha256_mismatch")
    if (label.get("group_id"), label.get("candidate_id"), label.get("candidate_identity_sha256"), label.get("teacher_release_sha256")) != (row["group_id"], row["candidate_id"], row["candidate_identity_sha256"], release_sha):
        raise ValueError("teacher_label_cache_identity_mismatch")
    if not isinstance(label.get("teacher_provenance"), dict) or label.get("teacher_provenance_sha256") != _canonical_sha(label["teacher_provenance"]):
        raise ValueError("teacher_label_cache_provenance_sha256_mismatch")
    return label


def _write_label_cache(root, row, release_sha, cache_key, label):
    path = _label_cache_path(root, row, release_sha, cache_key)
    payload = {"format_version": 2, "cache_key_sha256": cache_key, "label_sha256": _canonical_sha(label), "label": label}
    if path.exists():
        if _read_json(path) != payload:
            raise ValueError("teacher_label_cache_immutable_conflict")
        return
    _atomic_json_write(path, payload)


def _failure_budget_exceeded(config, attempted, failures):
    if config.max_technical_failures is not None and failures > int(config.max_technical_failures):
        return True
    return config.max_technical_failure_rate is not None and attempted > 0 and failures / attempted > float(config.max_technical_failure_rate)


def _write_final_label_artifacts(root, labels, binding, counts, configuration):
    root, files = Path(root), {}
    for split in _ALLOWED_SPLITS:
        path = root / "teacher" / f"{split}-labels-00000.npz"
        _write_labels_immutable(path, labels[split])
        files[f"{split}_teacher_labels"] = _file_record(path, root, "npz")
    manifest = {
        **binding,
        "counts": counts,
        "files": files,
        "failure_budget": asdict(configuration),
        "cache": {"candidate_cache_format_version": 2, "waveform_cache_root": binding["waveform_cache_root"]},
        "state": "completed",
    }
    path = root / "manifest.json"
    if path.exists() and _read_json(path) != manifest:
        raise ValueError("teacher_label_manifest_immutable_conflict")
    if not path.exists():
        _atomic_json_write(path, manifest)
    _atomic_json_write(root / "progress.json", {**binding, "state": "completed"})


def _write_labels_immutable(path, labels):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    values = np.asarray([json.dumps(row, sort_keys=True, separators=(",", ":")) for row in labels], dtype=str)
    if path.exists():
        with np.load(path, allow_pickle=False) as payload:
            if payload["row_json"].tolist() != values.tolist():
                raise ValueError("teacher_label_shard_immutable_conflict")
        return
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temporary.open("wb") as handle:
            np.savez_compressed(handle, row_json=values)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
