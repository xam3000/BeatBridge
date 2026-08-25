"""Reproducible train/validation runner for ``learned_cue_ranker_v1``."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import math
import os
from pathlib import Path
import random
import shutil
import uuid

import numpy as np
import torch

from .cue_ranker_model import CUE_RANKER_CONTEXT_DIMENSION, CUE_RANKER_MODEL_FORMAT_VERSION, CUE_RANKER_MODEL_NAME, CueRankerTemporalConfig, CueRankerTemporalModel


CUE_RANKER_RUN_FORMAT_VERSION = 1
CUE_RANKER_RUNNER_NAME = "train_validation_learned_cue_ranker_v1"


@dataclass(frozen=True)
class CueRankerTrainingConfig:
    seed: int = 20260825
    max_epochs: int = 1
    learning_rate: float = 1e-3
    weight_decay: float = 1e-4
    gradient_clip_norm: float = 1.0
    patience: int = 6
    min_delta: float = 0.0
    tau_teacher: float = 1.0
    tau_model: float = 1.0
    guard_margin: float = 0.05
    evaluation_top_k: int = 3
    device: str = "cpu"

    def __post_init__(self):
        if self.max_epochs < 1 or self.learning_rate <= 0 or self.weight_decay < 0:
            raise ValueError("Invalid Cue-Ranker optimization configuration")
        if self.gradient_clip_norm <= 0 or self.patience < 1 or self.min_delta < 0:
            raise ValueError("Invalid Cue-Ranker stopping configuration")
        if self.tau_teacher <= 0 or self.tau_model <= 0 or self.guard_margin <= 0:
            raise ValueError("Cue-Ranker temperatures and guard_margin must be positive")
        if self.evaluation_top_k < 1:
            raise ValueError("evaluation_top_k must be at least one")

    def to_dict(self):
        return asdict(self)


@dataclass(frozen=True)
class CueRankerRunResult:
    output_directory: Path
    status: str
    last_epoch: int
    best_epoch: int
    best_validation_loss: float
    history: tuple[dict, ...]


def cue_ranker_listwise_loss(
    scores,
    teacher_utility,
    inclusion_probability,
    *,
    tau_teacher=1.0,
    tau_model=1.0,
    guard_margin=0.05,
    teacher_status=None,
    group_ids=None,
    valid_mask=None,
    return_details=False,
):
    """Compute the contract's masked, group-mean IPW listwise loss.

    The inputs may be flat with ``group_ids`` or rectangular padded tensors.
    Invalid/padded rows are never inspected for finite values and cannot
    affect a group's softmax.  Groups with zero or one eligible members are
    reported and contribute zero, as required by the dataset contract.
    """

    if tau_teacher <= 0 or tau_model <= 0 or guard_margin <= 0:
        raise ValueError("Loss temperatures and guard_margin must be positive")
    scores = torch.as_tensor(scores)
    if not scores.is_floating_point():
        scores = scores.to(dtype=torch.float32)
    utility = torch.as_tensor(teacher_utility, device=scores.device, dtype=scores.dtype)
    inclusion = torch.as_tensor(inclusion_probability, device=scores.device, dtype=scores.dtype)
    if scores.shape != utility.shape or scores.shape != inclusion.shape:
        raise ValueError("scores, teacher_utility and inclusion_probability must have the same shape")
    if scores.ndim == 1:
        if group_ids is None:
            groups = [torch.arange(scores.numel(), device=scores.device)]
        else:
            groups = _group_indices(torch.as_tensor(group_ids, device=scores.device), scores.numel())
        flat_mask = torch.ones_like(scores, dtype=torch.bool) if valid_mask is None else torch.as_tensor(valid_mask, device=scores.device, dtype=torch.bool)
        if flat_mask.shape != scores.shape:
            raise ValueError("valid_mask must have the same shape as scores")
        status = _normalise_status(teacher_status, scores.shape, scores.device)
    elif scores.ndim == 2:
        flat_mask = torch.ones_like(scores, dtype=torch.bool) if valid_mask is None else torch.as_tensor(valid_mask, device=scores.device, dtype=torch.bool)
        if flat_mask.shape != scores.shape:
            raise ValueError("valid_mask must have the same shape as scores")
        groups = [torch.arange(scores.shape[1], device=scores.device) + row * scores.shape[1] for row in range(scores.shape[0])]
        scores, utility, inclusion, flat_mask = (value.reshape(-1) for value in (scores, utility, inclusion, flat_mask))
        status = _normalise_status(teacher_status, flat_mask.shape, scores.device)
    else:
        raise ValueError("scores must be a flat or padded 2D tensor")
    if not torch.isfinite(inclusion[flat_mask]).all() or torch.any(inclusion[flat_mask] <= 0) or torch.any(inclusion[flat_mask] > 1):
        raise ValueError("valid inclusion probabilities must be in (0, 1]")
    losses = []
    supported = 0
    insufficient = 0
    for indices in groups:
        indices = indices.to(device=scores.device, dtype=torch.long)
        mask = flat_mask[indices]
        indices = indices[mask]
        if indices.numel() == 0:
            insufficient += 1
            continue
        current_status = np.asarray(status)[indices.detach().cpu().numpy()]
        scored = torch.as_tensor(current_status == "scored", device=scores.device, dtype=torch.bool)
        rejected = torch.as_tensor(current_status == "guard_rejected", device=scores.device, dtype=torch.bool)
        finite_utility = torch.isfinite(utility[indices])
        finite_scored = scored & finite_utility
        # A guard rejection is an explicit negative teacher anchor.  Its
        # differentiable utility is retained for audit, never for the target:
        # a high objective score must not override a failed render guard.
        if torch.any(rejected):
            finite_values = utility[indices][finite_scored]
            if finite_values.numel() == 0:
                insufficient += 1
                continue
            replacement = finite_values.min() - float(guard_margin)
            utility = utility.clone()
            utility[indices[rejected]] = replacement
            eligible = finite_scored | rejected
        else:
            eligible = finite_scored
        eligible_indices = indices[eligible]
        if eligible_indices.numel() == 0:
            insufficient += 1
            continue
        if eligible_indices.numel() < 2:
            insufficient += 1
            continue
        group_scores = scores[eligible_indices]
        group_utility = utility[eligible_indices]
        group_ipw = torch.log(inclusion[eligible_indices])
        target_logits = group_utility / float(tau_teacher) - group_ipw
        prediction_logits = group_scores / float(tau_model) - group_ipw
        target = torch.softmax(target_logits, dim=0)
        log_prediction = torch.log_softmax(prediction_logits, dim=0)
        losses.append(-(target * log_prediction).sum())
        supported += 1
    loss = torch.stack(losses).mean() if losses else scores[flat_mask].sum() * 0.0
    if not torch.isfinite(loss):
        raise FloatingPointError("Cue-Ranker listwise loss is non-finite")
    if return_details:
        return loss, {"supported_groups": supported, "insufficient_groups": insufficient}
    return loss


def masked_pairwise_logistic_loss(scores, teacher_utility, *, group_ids=None, valid_mask=None):
    """Optional diagnostic pairwise loss with the same ragged masking rules."""

    scores = torch.as_tensor(scores)
    utility = torch.as_tensor(teacher_utility, device=scores.device, dtype=scores.dtype)
    if scores.shape != utility.shape:
        raise ValueError("scores and teacher_utility must have the same shape")
    if scores.ndim != 1:
        raise ValueError("masked_pairwise_logistic_loss expects flat scores")
    mask = torch.ones_like(scores, dtype=torch.bool) if valid_mask is None else torch.as_tensor(valid_mask, device=scores.device, dtype=torch.bool)
    groups = [torch.arange(scores.numel(), device=scores.device)] if group_ids is None else _group_indices(torch.as_tensor(group_ids, device=scores.device), scores.numel())
    values = []
    for group in groups:
        group = group[mask[group] & torch.isfinite(utility[group])]
        for left in range(group.numel()):
            for right in range(left + 1, group.numel()):
                delta = utility[group[left]] - utility[group[right]]
                if delta == 0:
                    continue
                sign = torch.sign(delta)
                values.append(torch.nn.functional.softplus(-sign * (scores[group[left]] - scores[group[right]])))
    return torch.stack(values).mean() if values else scores[mask].sum() * 0.0


# Descriptive aliases used by callers that refer to the contract as a
# pairwise/listwise objective.  v1 training uses the listwise implementation.
grouped_soft_target_listwise_loss = cue_ranker_listwise_loss
pairwise_listwise_loss = cue_ranker_listwise_loss


def train_cue_ranker(
    train_loader,
    validation_loader,
    output_directory,
    *,
    dataset_manifest_sha256,
    config: CueRankerTrainingConfig | None = None,
    model_config: CueRankerTemporalConfig | None = None,
    resume=False,
    progress=print,
):
    """Train using only the explicitly supplied train and validation loaders."""

    config = config or CueRankerTrainingConfig()
    model_config = model_config or CueRankerTemporalConfig()
    dataset_manifest_sha256 = _require_sha(dataset_manifest_sha256, "dataset_manifest_sha256")
    train_batches, validation_batches = tuple(train_loader), tuple(validation_loader)
    if not train_batches or not validation_batches:
        raise ValueError("train_loader and validation_loader must both be non-empty")
    _seed_everything(config.seed)
    output_directory = Path(output_directory).resolve()
    manifest_path = output_directory / "manifest.json"
    manifest_sha_path = output_directory / "manifest.sha256"
    history_path = output_directory / "history.json"
    latest_path = output_directory / "latest.pt"
    best_path = output_directory / "best.pt"
    contract = _training_contract(dataset_manifest_sha256, config, model_config)
    run_id = hashlib.sha256(_canonical_json(contract)).hexdigest()[:20]
    device = torch.device(config.device)
    model = CueRankerTemporalModel(model_config).to(device=device, dtype=torch.float32)
    optimizer = torch.optim.AdamW(model.parameters(), lr=config.learning_rate, weight_decay=config.weight_decay)
    if resume:
        checkpoint, manifest = _load_resume(manifest_path, manifest_sha_path, latest_path, expected_contract=contract, expected_run_id=run_id)
        model.load_state_dict(checkpoint["model_state_dict"])
        optimizer.load_state_dict(checkpoint["optimizer_state_dict"])
        history = list(checkpoint.get("history", ()))
        start_epoch = int(checkpoint["epoch"]) + 1
        best_epoch = int(checkpoint.get("best_epoch", 0))
        best_loss = float(checkpoint.get("best_validation_loss", math.inf))
        if config.max_epochs < start_epoch:
            raise ValueError("max_epochs must extend beyond the latest checkpoint")
    else:
        if output_directory.exists():
            raise FileExistsError(f"Training output already exists; use resume=True: {output_directory}")
        output_directory.mkdir(parents=True)
        history, start_epoch, best_epoch, best_loss = [], 1, 0, math.inf
    stale_epochs = 0
    for epoch in range(start_epoch, config.max_epochs + 1):
        train_metrics = _run_deterministic_epoch(model, train_batches, optimizer, config, device, training=True)
        validation_metrics = _run_deterministic_epoch(model, validation_batches, None, config, device, training=False)
        validation_loss = float(validation_metrics["loss"])
        improved = validation_loss < best_loss - config.min_delta
        if improved:
            best_loss, best_epoch, stale_epochs = validation_loss, epoch, 0
        else:
            stale_epochs += 1
        history.append({"epoch": epoch, "train": train_metrics, "validation": validation_metrics})
        payload = {
            "format_version": CUE_RANKER_RUN_FORMAT_VERSION,
            "runner_name": CUE_RANKER_RUNNER_NAME,
            "model_name": CUE_RANKER_MODEL_NAME,
            "run_id": run_id,
            "epoch": epoch,
            "best_epoch": best_epoch,
            "best_validation_loss": best_loss,
            "model_state_dict": model.state_dict(),
            "optimizer_state_dict": optimizer.state_dict(),
            "history": history,
            "contract": contract,
        }
        _atomic_torch_save(latest_path, payload)
        if improved:
            _atomic_torch_save(best_path, payload)
        _write_run_files(manifest_path, manifest_sha_path, history_path, latest_path, best_path, run_id, contract, history, status="running")
        progress(f"epoch={epoch} train={train_metrics['loss']:.6f} validation={validation_loss:.6f}")
        if stale_epochs >= config.patience:
            break
    _write_run_files(manifest_path, manifest_sha_path, history_path, latest_path, best_path, run_id, contract, history, status="completed")
    return CueRankerRunResult(output_directory, "completed", int(history[-1]["epoch"]), best_epoch, best_loss, tuple(history))


def _run_epoch(model, batches, optimizer, config, device, *, training):
    model.train(training)
    group_losses, supported, insufficient = [], 0, 0
    evaluation_groups = []
    context = torch.enable_grad() if training else torch.no_grad()
    with context:
        for raw_batch in batches:
            groups = _normalise_batch(raw_batch)
            losses = []
            for group in groups:
                score_vector = _score_group(model, group, device)
                utility, inclusion, status = _labels(group, device, score_vector.dtype)
                loss, details = cue_ranker_listwise_loss(score_vector, utility, inclusion, teacher_status=status, valid_mask=torch.ones_like(score_vector, dtype=torch.bool), group_ids=None, tau_teacher=config.tau_teacher, tau_model=config.tau_model, guard_margin=config.guard_margin, return_details=True)
                if details["supported_groups"]:
                    losses.append(loss)
                    supported += details["supported_groups"]
                    # Detached scores are intentional: evaluation is strictly
                    # against the frozen label snapshot, never the teacher.
                    evaluation_groups.append(_evaluation_group(group, score_vector, config))
                insufficient += details["insufficient_groups"]
            if not losses:
                continue
            batch_loss = torch.stack(losses).mean()
            if training:
                optimizer.zero_grad(set_to_none=True)
                batch_loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), config.gradient_clip_norm)
                optimizer.step()
            group_losses.append(float(batch_loss.detach().cpu()))
    metrics = {"loss": float(np.mean(group_losses)) if group_losses else 0.0, "groups": len(group_losses), "supported_groups": supported, "insufficient_groups": insufficient}
    metrics.update(_aggregate_ranking_metrics(evaluation_groups, top_k=config.evaluation_top_k))
    return metrics


def _run_deterministic_epoch(model, batches, optimizer, config, device, *, training):
    """Enable strict deterministic algorithms only for this runner's epoch."""

    previous_enabled = torch.are_deterministic_algorithms_enabled()
    previous_warn_only = torch.is_deterministic_algorithms_warn_only_enabled()
    torch.use_deterministic_algorithms(True, warn_only=True)
    try:
        return _run_epoch(model, batches, optimizer, config, device, training=training)
    finally:
        torch.use_deterministic_algorithms(previous_enabled, warn_only=previous_warn_only)


def _evaluation_group(group, score_vector, config):
    """Create a CPU-only, frozen-label ranking snapshot for one group.

    This deliberately consumes only label fields and ranker scores.  It never
    calls the controller, renderer, cache resolver, or any audio path.
    """
    members = tuple(group.get("members", group.get("candidates", ())))
    utilities, _inclusion, statuses = _labels(group, torch.device("cpu"), torch.float64)
    finite = utilities.detach().cpu().numpy().astype(np.float64)
    statuses = np.asarray(statuses, dtype=object)
    scored = statuses == "scored"
    rejected = statuses == "guard_rejected"
    eligible = scored & np.isfinite(finite)
    scored_finite = finite[eligible]
    # Match the training target exactly: every guard rejection is a negative
    # anchor, even when the differentiable teacher utility is finite and high.
    if np.any(rejected) and scored_finite.size:
        finite[rejected] = scored_finite.min() - float(config.guard_margin)
        eligible |= rejected
    rows = []
    for index, row in enumerate(members):
        if not eligible[index]:
            continue
        rows.append({
            "candidate_id": str(row.get("candidate_id", index)),
            "length": int(row.get("transition_length_bars", int(row["features_a"].shape[0]) // 8)),
            "utility": float(finite[index]),
            "ranker_score": float(score_vector[index].detach().cpu()),
            "feature_baseline_v3": _finite_or_none(row.get("feature_baseline_v3_score")),
            "bpm": _bpm_baseline_score(row),
            "harmony": _harmony_baseline_score(row),
        })
    return rows


def _aggregate_ranking_metrics(groups, *, top_k):
    """Report agreement with the fixed Teacher, globally and for 2/4/6/8.

    ``top_1_agreement`` is an exact choice match; ``top_k_agreement`` is the
    overlap fraction of deterministic top-k sets.  NDCG uses teacher-derived
    ordinal gains, so it is meaningful across groups with differently scaled
    utilities.  Scores are correlated only with finite Teacher utilities.
    """
    buckets = {"all": list(groups)}
    for length in (2, 4, 6, 8):
        buckets[str(length)] = [[row for row in group if row["length"] == length] for group in groups]
    return {"ranking": {name: _metric_bucket(value, top_k=top_k) for name, value in buckets.items()}}


def _metric_bucket(groups, *, top_k):
    valid = [group for group in groups if len(group) >= 2]
    result = {"groups": len(valid), "top_k": int(top_k)}
    methods = {
        "ranker": lambda row: row["ranker_score"],
        "random_valid": None,
        "feature_baseline_v3": lambda row: row["feature_baseline_v3"],
        "bpm_only": lambda row: row["bpm"],
        "harmony_only": lambda row: row["harmony"],
        "teacher_oracle": lambda row: row["utility"],
    }
    for name, scorer in methods.items():
        per_group = []
        for group_index, group in enumerate(valid):
            if scorer is None:
                ordered = _deterministic_random_order(group, group_index)
            elif any(scorer(row) is None for row in group):
                # A baseline that is unavailable for one candidate is not a
                # valid comparison on this frozen snapshot; do not impute it.
                continue
            else:
                ordered = _ordered(group, scorer)
            teacher = _ordered(group, lambda row: row["utility"])
            k = min(int(top_k), len(group))
            selected, expected = ordered[:k], teacher[:k]
            selected_ids, expected_ids = {row["candidate_id"] for row in selected}, {row["candidate_id"] for row in expected}
            relevance = _ordinal_gains(group)
            dcg = sum(relevance[row["candidate_id"]] / math.log2(position + 2) for position, row in enumerate(selected[:k]))
            ideal = sum(relevance[row["candidate_id"]] / math.log2(position + 2) for position, row in enumerate(expected[:k]))
            per_group.append({
                "top_1_agreement": float(selected[0]["candidate_id"] == expected[0]["candidate_id"]),
                "top_k_agreement": len(selected_ids & expected_ids) / k,
                "ndcg": dcg / ideal if ideal else 0.0,
                "top_1_teacher_utility": selected[0]["utility"],
            })
        result[name] = _mean_metrics(per_group)
    ranker_rows = [row for group in valid for row in group]
    result["ranker_score_correlation"] = _pearson(
        [row["ranker_score"] for row in ranker_rows], [row["utility"] for row in ranker_rows]
    )
    return result


def _ordered(rows, scorer):
    return sorted(rows, key=lambda row: (-float(scorer(row)), row["candidate_id"]))


def _deterministic_random_order(rows, group_index):
    return sorted(rows, key=lambda row: (hashlib.sha256(f"cue_ranker_random_v1|{group_index}|{row['candidate_id']}".encode("utf-8")).hexdigest(), row["candidate_id"]))


def _ordinal_gains(rows):
    ordered = _ordered(rows, lambda row: row["utility"])
    return {row["candidate_id"]: float(len(ordered) - index) for index, row in enumerate(ordered)}


def _mean_metrics(values):
    if not values:
        return {"groups": 0, "top_1_agreement": None, "top_k_agreement": None, "ndcg": None, "top_1_teacher_utility": None}
    return {"groups": len(values), **{key: float(np.mean([row[key] for row in values])) for key in values[0]}}


def _pearson(x, y):
    x, y = np.asarray(x, dtype=np.float64), np.asarray(y, dtype=np.float64)
    if len(x) < 2 or not np.isfinite(x).all() or not np.isfinite(y).all() or np.std(x) == 0 or np.std(y) == 0:
        return None
    return float(np.corrcoef(x, y)[0, 1])


def _finite_or_none(value):
    try:
        value = float(value)
    except (TypeError, ValueError):
        return None
    return value if math.isfinite(value) else None


def _bpm_baseline_score(row):
    candidate = row.get("candidate", {})
    try:
        source = float(candidate["source_bpm"])
        target = float(candidate["target_bpm"])
        return -abs(math.log(target / source))
    except (KeyError, TypeError, ValueError, ZeroDivisionError):
        value = row.get("bpm_compatibility")
        return _finite_or_none(value)


def _harmony_baseline_score(row):
    value = row.get("harmonic_compatibility")
    if value is not None:
        return _finite_or_none(value)
    global_features = row.get("global_features")
    # Feature Protocol's global field is intentionally the only fallback;
    # provenance identifiers, IDs, SHA values and audio paths are never read.
    if global_features is not None and len(global_features) == 16:
        from src.features.contract import global_feature_index
        return _finite_or_none(global_features[global_feature_index("harmonic_compatibility")])
    return None


def _score_group(model, group, device):
    members = tuple(group.get("members", group.get("candidates", ()))) if isinstance(group, dict) else tuple(group)
    if not members:
        raise ValueError("Cue-Ranker group must contain members")
    scores = [None] * len(members)
    by_length = {}
    for index, row in enumerate(members):
        by_length.setdefault(int(row["features_a"].shape[0]), []).append((index, row))
    for _time, indexed_rows in by_length.items():
        a = torch.stack([row["features_a"] for _, row in indexed_rows]).to(device=device, dtype=torch.float32)
        b = torch.stack([row["features_b"] for _, row in indexed_rows]).to(device=device, dtype=torch.float32)
        global_features = torch.stack([row["global_features"] for _, row in indexed_rows]).to(device=device, dtype=torch.float32)
        length = torch.stack([row["length_condition"] for _, row in indexed_rows]).to(device=device, dtype=torch.float32)
        context = torch.stack([row.get("candidate_context", torch.zeros(CUE_RANKER_CONTEXT_DIMENSION)) for _, row in indexed_rows]).to(device=device, dtype=torch.float32)
        grid_ids = torch.stack([row.get("grid_source_ids", torch.zeros(2, dtype=torch.long)) for _, row in indexed_rows]).to(device=device, dtype=torch.long)
        current = model(a, b, global_features, length, context, grid_ids)
        for (index, _row), value in zip(indexed_rows, current, strict=True):
            scores[index] = value
    return torch.stack(scores)


def _labels(group, device, dtype):
    members = tuple(group.get("members", group.get("candidates", ())))
    utility = []
    inclusion = []
    status = []
    for row in members:
        value = row.get("teacher_utility", row.get("utility", float("nan")))
        utility.append(float(value) if value is not None else float("nan"))
        inclusion.append(float(row.get("p_inclusion", row.get("inclusion_probability", 1.0))))
        status.append(str(row.get("teacher_status", row.get("status", "scored"))))
    return torch.tensor(utility, device=device, dtype=dtype), torch.tensor(inclusion, device=device, dtype=dtype), status


def _normalise_batch(raw_batch):
    if isinstance(raw_batch, dict) and "members" in raw_batch:
        return (raw_batch,)
    if isinstance(raw_batch, (list, tuple)):
        if raw_batch and isinstance(raw_batch[0], dict) and "features_a" in raw_batch[0]:
            return ({"members": tuple(raw_batch)},)
        return tuple(raw_batch)
    raise TypeError("Cue-Ranker loader batches must be groups or sequences of groups")


def _training_contract(dataset_sha, config, model_config):
    training_config = config.to_dict()
    # max_epochs is the caller's extension horizon and is intentionally not
    # part of the immutable resume contract.
    training_config.pop("max_epochs", None)
    return {
        "format_version": CUE_RANKER_RUN_FORMAT_VERSION,
        "runner_name": CUE_RANKER_RUNNER_NAME,
        "model_name": CUE_RANKER_MODEL_NAME,
        "model_format_version": CUE_RANKER_MODEL_FORMAT_VERSION,
        "dataset_manifest_sha256": dataset_sha,
        "split_scope": ["train", "validation"],
        "test_split": {"state": "sealed_not_materialized", "loader_api": "absent"},
        "model": {"name": CUE_RANKER_MODEL_NAME, "config": model_config.to_dict()},
        "loss": {"name": "grouped_ipw_soft_target_listwise_cross_entropy_v1", "tau_teacher": config.tau_teacher, "tau_model": config.tau_model, "guard_margin": config.guard_margin},
        "training": training_config,
        "determinism": {"seed": config.seed, "torch_deterministic_algorithms": True},
        "input_contract": {"features_a": ["T", 54], "features_b": ["T", 54], "global_features": [16], "length_condition": [1], "candidate_context": [CUE_RANKER_CONTEXT_DIMENSION], "raw_sample_positions": False},
    }


def _load_resume(manifest_path, manifest_sha_path, latest_path, *, expected_contract, expected_run_id):
    manifest_path, manifest_sha_path, latest_path = map(Path, (manifest_path, manifest_sha_path, latest_path))
    if not manifest_path.is_file() or not manifest_sha_path.is_file() or not latest_path.is_file():
        raise FileNotFoundError("Resume requires manifest.json, manifest.sha256 and latest.pt")
    declared_manifest_sha = manifest_sha_path.read_text(encoding="utf-8").strip().split()[0]
    if declared_manifest_sha != _sha256(manifest_path):
        raise ValueError("Cue-Ranker manifest SHA-256 differs from manifest.sha256")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("contract") != expected_contract or manifest.get("run_id") != expected_run_id:
        raise ValueError("Cue-Ranker resume contract differs from the requested run")
    for name in ("history", "best"):
        record = manifest.get("files", {}).get(name)
        if record is None:
            raise ValueError(f"Cue-Ranker run manifest is missing {name}")
        artifact = manifest_path.parent / record["path"]
        if _sha256(artifact) != record.get("sha256"):
            raise ValueError(f"Cue-Ranker {name} SHA-256 differs from the run manifest")
    record = manifest.get("files", {}).get("latest")
    if not record or _sha256(latest_path) != record.get("sha256"):
        raise ValueError("Cue-Ranker latest checkpoint SHA-256 differs from the run manifest")
    checkpoint = torch.load(latest_path, map_location="cpu", weights_only=True)
    if checkpoint.get("format_version") != CUE_RANKER_RUN_FORMAT_VERSION or checkpoint.get("run_id") != expected_run_id or checkpoint.get("contract") != expected_contract:
        raise ValueError("Cue-Ranker checkpoint contract is invalid")
    return checkpoint, manifest


def load_cue_ranker_checkpoint_for_resume(manifest_path, latest_path, *, expected_contract, expected_run_id=None):
    """Verify all run hashes before the sole safe ``weights_only`` load."""

    manifest_path = Path(manifest_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    run_id = manifest.get("run_id") if expected_run_id is None else expected_run_id
    checkpoint, _ = _load_resume(
        manifest_path,
        manifest_path.parent / "manifest.sha256",
        Path(latest_path),
        expected_contract=expected_contract,
        expected_run_id=run_id,
    )
    return checkpoint


def _write_run_files(manifest_path, manifest_sha_path, history_path, latest_path, best_path, run_id, contract, history, *, status):
    _atomic_json_write(history_path, {"format_version": CUE_RANKER_RUN_FORMAT_VERSION, "run_id": run_id, "epochs": history})
    payload = {
        "format_version": CUE_RANKER_RUN_FORMAT_VERSION,
        "runner_name": CUE_RANKER_RUNNER_NAME,
        "run_id": run_id,
        "status": status,
        "contract": contract,
        "files": {
            "history": _file_record(history_path),
            "latest": _file_record(latest_path),
            "best": _file_record(best_path) if best_path.is_file() else None,
        },
    }
    _atomic_json_write(manifest_path, payload)
    _atomic_text_write(manifest_sha_path, _sha256(manifest_path) + "  manifest.json\n")


def _atomic_torch_save(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        torch.save(payload, temporary)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _atomic_json_write(path, payload):
    _atomic_text_write(path, json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


def _atomic_text_write(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        temporary.write_text(text, encoding="utf-8")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _file_record(path):
    path = Path(path)
    return {"path": path.name, "sha256": _sha256(path), "bytes": path.stat().st_size}


def _group_indices(group_ids, count):
    if group_ids.shape != (count,):
        raise ValueError("group_ids must have one value per candidate")
    output, seen = [], set()
    for index, value in enumerate(group_ids.tolist()):
        if value not in seen:
            seen.add(value)
            output.append(torch.nonzero(group_ids == value, as_tuple=False).reshape(-1))
    return output


def _normalise_status(status, shape, device):
    if status is None:
        return np.full(int(np.prod(shape)), "scored", dtype=object)
    values = list(status) if not isinstance(status, torch.Tensor) else status.tolist()
    if len(values) != int(np.prod(shape)):
        raise ValueError("teacher_status must have one value per candidate")
    # Python strings are intentionally kept outside torch; loss indexing uses
    # this tiny object array, which also avoids string padding semantics.
    return np.asarray([str(value) for value in values], dtype=object)


def _seed_everything(seed):
    seed = int(seed)
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
        torch.backends.cudnn.benchmark = False
        torch.backends.cudnn.deterministic = True


def _canonical_json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _require_sha(value, name):
    value = str(value).lower()
    if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
        raise ValueError(f"{name} must be a SHA-256 hex digest")
    return value


def _sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()
