"""Reproducible Objective-v5 training runner for vocal-aware controls."""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import random
import uuid

import numpy as np
import torch
from torch.utils.data import DataLoader

from src.bridge import DEFAULT_FEATURE_CACHE_ROOT
from src.control import (
    VOCAL_CONTROL_PROTOCOL_VERSION,
    VOCAL_OBJECTIVE_VERSION,
    DifferentiableVocalAwareRenderer,
    VocalAwareTransitionObjective,
    VocalAwareTransitionObjectiveConfig,
)
from src.features.vocal import DEFAULT_ROFORMER_MODEL
from src.torch_device import (
    DEFAULT_TORCH_DEVICE,
    resolve_torch_device,
    validate_torch_device_spec,
)

from .data import (
    DEFAULT_TRAINING_SAMPLE_RATE,
    DEFAULT_VOCAL_BRIDGE_WAVEFORM_CACHE_ROOT,
    VOCAL_BRIDGE_WAVEFORM_CACHE_FORMAT_VERSION,
    VOCAL_BRIDGE_WAVEFORM_EXTRACTOR_VERSION,
    VocalFeatureControlDataset,
    collate_feature_control_examples,
)
from .model import (
    VOCAL_FEATURE_CONTROL_MODEL_FORMAT_VERSION,
    VOCAL_FEATURE_CONTROL_MODEL_NAME,
    VocalFeatureControlMLP,
    VocalFeatureControlMLPConfig,
)
from .runner import TrainingRunResult
from .training import vocal_self_supervised_batch_loss
from .wandb_logging import WandbConfig, WandbLogger


VOCAL_TRAINING_RUN_FORMAT_VERSION = 3
SUPPORTED_VOCAL_TRAINING_RUN_FORMAT_VERSIONS = (2, VOCAL_TRAINING_RUN_FORMAT_VERSION)
VOCAL_TRAINING_RUNNER_NAME = "self_supervised_vocal_train_validation_v2"


@dataclass(frozen=True)
class VocalTrainingConfig:
    """Optimization and renderer settings stored with every vocal-aware run."""

    seed: int = 20260805
    max_epochs: int = 30
    batch_size: int = 5
    optimizer: str = "adamw"
    learning_rate: float = 1e-3
    weight_decay: float = 1e-4
    adam_beta1: float = 0.9
    adam_beta2: float = 0.999
    adam_epsilon: float = 1e-8
    lr_scheduler: str = "reduce_on_plateau"
    scheduler_factor: float = 0.5
    scheduler_patience: int = 3
    scheduler_threshold: float = 1e-4
    scheduler_cooldown: int = 0
    scheduler_min_lr: float = 1e-6
    patience: int = 6
    min_delta: float = 1e-4
    gradient_clip_norm: float = 1.0
    training_sample_rate: int = DEFAULT_TRAINING_SAMPLE_RATE
    lowpass_cutoff_hz: float = 180.0
    lowpass_kernel_size: int = 127
    device: str = DEFAULT_TORCH_DEVICE

    def __post_init__(self):
        if int(self.max_epochs) < 1:
            raise ValueError("max_epochs must be at least 1")
        if int(self.batch_size) < 1:
            raise ValueError("batch_size must be at least 1")
        if self.optimizer not in {"adam", "adamw"}:
            raise ValueError("optimizer must be 'adam' or 'adamw'")
        if float(self.learning_rate) <= 0 or float(self.weight_decay) < 0:
            raise ValueError("learning_rate must be positive and weight_decay non-negative")
        if not 0 < float(self.adam_beta1) < 1 or not 0 < float(self.adam_beta2) < 1:
            raise ValueError("Adam beta values must be between 0 and 1")
        if float(self.adam_epsilon) <= 0:
            raise ValueError("adam_epsilon must be positive")
        if self.lr_scheduler not in {"none", "reduce_on_plateau", "cosine"}:
            raise ValueError(
                "lr_scheduler must be 'none', 'reduce_on_plateau', or 'cosine'"
            )
        if not 0 < float(self.scheduler_factor) < 1:
            raise ValueError("scheduler_factor must be between 0 and 1")
        if int(self.scheduler_patience) < 1:
            raise ValueError("scheduler_patience must be at least 1")
        if float(self.scheduler_threshold) < 0:
            raise ValueError("scheduler_threshold must be non-negative")
        if int(self.scheduler_cooldown) < 0:
            raise ValueError("scheduler_cooldown must be non-negative")
        if not 0 <= float(self.scheduler_min_lr) <= float(self.learning_rate):
            raise ValueError("scheduler_min_lr must be between 0 and learning_rate")
        if int(self.patience) < 1 or float(self.min_delta) < 0:
            raise ValueError("patience must be positive and min_delta non-negative")
        if float(self.gradient_clip_norm) <= 0:
            raise ValueError("gradient_clip_norm must be positive")
        if int(self.training_sample_rate) <= 0:
            raise ValueError("training_sample_rate must be positive")
        if float(self.lowpass_cutoff_hz) <= 0:
            raise ValueError("lowpass_cutoff_hz must be positive")
        if int(self.lowpass_kernel_size) < 3 or int(self.lowpass_kernel_size) % 2 == 0:
            raise ValueError("lowpass_kernel_size must be an odd integer of at least 3")
        validate_torch_device_spec(self.device)

    def to_dict(self):
        return asdict(self)


def run_vocal_feature_control_training(
    dataset_directory,
    output_directory,
    *,
    config: VocalTrainingConfig | None = None,
    model_config: VocalFeatureControlMLPConfig | None = None,
    objective_config: VocalAwareTransitionObjectiveConfig | None = None,
    waveform_cache_root=DEFAULT_VOCAL_BRIDGE_WAVEFORM_CACHE_ROOT,
    feature_cache_root=DEFAULT_FEATURE_CACHE_ROOT,
    vocal_model=DEFAULT_ROFORMER_MODEL,
    resume=False,
    progress=print,
    wandb_config: WandbConfig | None = None,
):
    """Materialize train/validation mix-plus-vocal caches and train model v2."""
    config = _resolve_training_device(config or VocalTrainingConfig())
    dataset_directory = Path(dataset_directory).resolve()
    dataset_manifest_path = dataset_directory / "manifest.json"
    dataset_manifest = _read_json(dataset_manifest_path)
    dataset_kwargs = {
        "waveform_cache_root": waveform_cache_root,
        "feature_cache_root": feature_cache_root,
        "training_sample_rate": config.training_sample_rate,
        "vocal_model": vocal_model,
        "build_missing_waveforms": True,
    }
    train_dataset = VocalFeatureControlDataset(dataset_directory, "train", **dataset_kwargs)
    validation_dataset = VocalFeatureControlDataset(
        dataset_directory,
        "validation",
        **dataset_kwargs,
    )
    train_examples = _materialize_dataset(train_dataset, "train", progress)
    validation_examples = _materialize_dataset(
        validation_dataset,
        "validation",
        progress,
    )
    dataset_identity = {
        "path": str(dataset_directory),
        "dataset_id": dataset_manifest.get("dataset_id"),
        "manifest_sha256": _file_sha256(dataset_manifest_path),
        "split_counts": {
            "train": len(train_examples),
            "validation": len(validation_examples),
        },
        "vocal_waveform_cache_manifests": {
            "train": _cache_manifest_records(train_examples),
            "validation": _cache_manifest_records(validation_examples),
        },
    }
    return train_vocal_feature_control_model(
        train_examples,
        validation_examples,
        output_directory,
        config=config,
        model_config=model_config,
        objective_config=objective_config,
        dataset_identity=dataset_identity,
        vocal_model=vocal_model,
        resume=resume,
        progress=progress,
        wandb_config=wandb_config,
    )


def train_vocal_feature_control_model(
    train_examples,
    validation_examples,
    output_directory,
    *,
    config: VocalTrainingConfig | None = None,
    model_config: VocalFeatureControlMLPConfig | None = None,
    objective_config: VocalAwareTransitionObjectiveConfig | None = None,
    dataset_identity: dict | None = None,
    vocal_model=DEFAULT_ROFORMER_MODEL,
    resume=False,
    progress=print,
    wandb_config: WandbConfig | None = None,
):
    """Train model v2 from materialized examples and persist restartable artifacts."""
    config = _resolve_training_device(config or VocalTrainingConfig())
    model_config = model_config or VocalFeatureControlMLPConfig()
    objective_config = objective_config or VocalAwareTransitionObjectiveConfig()
    train_examples = tuple(train_examples)
    validation_examples = tuple(validation_examples)
    if not train_examples or not validation_examples:
        raise ValueError("train and validation must both contain at least one example")
    _validate_vocal_examples(train_examples, "train")
    _validate_vocal_examples(validation_examples, "validation")

    output_directory = Path(output_directory).resolve()
    checkpoint_directory = output_directory / "checkpoints"
    manifest_path = output_directory / "manifest.json"
    history_path = output_directory / "history.json"
    latest_path = checkpoint_directory / "latest.pt"
    best_path = checkpoint_directory / "best.pt"
    dataset_identity = dict(dataset_identity or {
        "path": None,
        "dataset_id": None,
        "manifest_sha256": None,
        "split_counts": {
            "train": len(train_examples),
            "validation": len(validation_examples),
        },
        "vocal_waveform_cache_manifests": None,
    })
    immutable_contract = _immutable_contract(
        config,
        model_config,
        objective_config,
        dataset_identity,
        vocal_model,
    )
    run_id = hashlib.sha256(
        json.dumps(immutable_contract, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()[:20]

    device = torch.device(config.device)
    _seed_everything(config.seed)
    model = VocalFeatureControlMLP(model_config).to(device=device, dtype=torch.float32)
    renderer = DifferentiableVocalAwareRenderer(
        sample_rate=config.training_sample_rate,
        lowpass_cutoff_hz=config.lowpass_cutoff_hz,
        lowpass_kernel_size=config.lowpass_kernel_size,
    ).to(device=device, dtype=torch.float32)
    objective = VocalAwareTransitionObjective(
        objective_config,
        energy_frames=32,
    ).to(device=device)
    progress(f"torch_device={device}")
    optimizer_type = torch.optim.AdamW if config.optimizer == "adamw" else torch.optim.Adam
    optimizer = optimizer_type(
        model.parameters(),
        lr=config.learning_rate,
        weight_decay=config.weight_decay,
        betas=(config.adam_beta1, config.adam_beta2),
        eps=config.adam_epsilon,
    )
    if config.lr_scheduler == "reduce_on_plateau":
        lr_scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
            optimizer,
            mode="min",
            factor=config.scheduler_factor,
            patience=config.scheduler_patience,
            threshold=config.scheduler_threshold,
            cooldown=config.scheduler_cooldown,
            min_lr=config.scheduler_min_lr,
        )
    elif config.lr_scheduler == "cosine":
        lr_scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
            optimizer,
            T_max=config.max_epochs,
            eta_min=config.scheduler_min_lr,
        )
    else:
        lr_scheduler = None

    if resume:
        if not manifest_path.is_file() or not latest_path.is_file():
            raise FileNotFoundError("Resume requires manifest.json and checkpoints/latest.pt")
        manifest = _read_json(manifest_path)
        if manifest.get("run_id") != run_id or manifest.get("contract") != immutable_contract:
            raise ValueError("Existing vocal run contract differs from the requested configuration")
        declared_latest = manifest.get("files", {}).get("latest_checkpoint")
        if not declared_latest or _file_sha256(latest_path) != declared_latest.get("sha256"):
            raise ValueError("Latest vocal checkpoint hash differs from the run manifest")
        checkpoint = torch.load(latest_path, map_location=device, weights_only=True)
        _validate_checkpoint(checkpoint, run_id)
        model.load_state_dict(checkpoint["model_state_dict"])
        optimizer.load_state_dict(checkpoint["optimizer_state_dict"])
        if lr_scheduler is not None:
            scheduler_state = checkpoint["lr_scheduler_state_dict"]
            if not isinstance(scheduler_state, dict):
                raise ValueError(
                    "Vocal checkpoint has no compatible learning-rate scheduler state"
                )
            lr_scheduler.load_state_dict(scheduler_state)
        elif checkpoint["lr_scheduler_state_dict"] is not None:
            raise ValueError("Vocal checkpoint includes a scheduler but the requested run does not")
        history = list(checkpoint["history"])
        start_epoch = int(checkpoint["epoch"]) + 1
        best_epoch = int(checkpoint["best_epoch"])
        best_validation_loss = float(checkpoint["best_validation_loss"])
        stale_epochs = int(checkpoint["stale_epochs"])
        created_at = manifest["created_at_utc"]
        if config.max_epochs < start_epoch:
            raise ValueError("max_epochs must extend beyond the latest checkpoint epoch")
    else:
        if output_directory.exists():
            raise FileExistsError(
                f"Vocal training output already exists; use resume=True: {output_directory}"
            )
        checkpoint_directory.mkdir(parents=True)
        history = []
        start_epoch = 1
        best_epoch = 0
        best_validation_loss = math.inf
        stale_epochs = 0
        created_at = _now_utc()

    wandb_logger = WandbLogger.start(
        wandb_config,
        run_id=run_id,
        runner_name=VOCAL_TRAINING_RUNNER_NAME,
        contract=immutable_contract,
        output_directory=output_directory,
        resume=resume,
    )

    previous_deterministic = torch.are_deterministic_algorithms_enabled()
    previous_warn_only = torch.is_deterministic_algorithms_warn_only_enabled()
    torch.use_deterministic_algorithms(True, warn_only=device.type == "cuda")
    status = "running"
    last_epoch = start_epoch - 1
    try:
        if not history:
            initial_train = _run_epoch(
                model,
                train_examples,
                config,
                renderer,
                objective,
                optimizer=None,
                epoch=0,
            )
            initial_validation = _run_epoch(
                model,
                validation_examples,
                config,
                renderer,
                objective,
                optimizer=None,
                epoch=0,
            )
            history.append({
                "epoch": 0,
                "phase": "vocal_near_equal_power_initialization",
                "train": initial_train,
                "validation": initial_validation,
            })
            best_validation_loss = float(initial_validation["loss"])
            checkpoint = _checkpoint_payload(
                run_id,
                0,
                model,
                optimizer,
                lr_scheduler,
                best_epoch,
                best_validation_loss,
                stale_epochs,
                history,
            )
            _atomic_torch_save(best_path, checkpoint)
            _atomic_torch_save(latest_path, checkpoint)
            _write_run_files(
                manifest_path,
                history_path,
                run_id,
                "running",
                created_at,
                immutable_contract,
                config,
                model,
                history,
                best_epoch,
                best_validation_loss,
                latest_path,
                best_path,
            )
            progress(
                f"epoch=0 vocal_initialization train={initial_train['loss']:.6f} "
                f"validation={initial_validation['loss']:.6f}"
            )
            wandb_logger.log_epoch(
                0,
                initial_train,
                initial_validation,
                best_validation_loss=best_validation_loss,
                stale_epochs=stale_epochs,
                improved=False,
            )

        status = "completed"
        for epoch in range(start_epoch, config.max_epochs + 1):
            train_metrics = _run_epoch(
                model,
                train_examples,
                config,
                renderer,
                objective,
                optimizer=optimizer,
                epoch=epoch,
            )
            validation_metrics = _run_epoch(
                model,
                validation_examples,
                config,
                renderer,
                objective,
                optimizer=None,
                epoch=epoch,
            )
            validation_loss = float(validation_metrics["loss"])
            train_metrics["learning_rate"] = float(optimizer.param_groups[0]["lr"])
            history.append({
                "epoch": epoch,
                "phase": "training",
                "train": train_metrics,
                "validation": validation_metrics,
            })
            improved = validation_loss < best_validation_loss - config.min_delta
            if improved:
                best_validation_loss = validation_loss
                best_epoch = epoch
                stale_epochs = 0
            else:
                stale_epochs += 1
            if isinstance(lr_scheduler, torch.optim.lr_scheduler.ReduceLROnPlateau):
                lr_scheduler.step(validation_loss)
            elif lr_scheduler is not None:
                lr_scheduler.step()
            last_epoch = epoch
            checkpoint = _checkpoint_payload(
                run_id,
                epoch,
                model,
                optimizer,
                lr_scheduler,
                best_epoch,
                best_validation_loss,
                stale_epochs,
                history,
            )
            _atomic_torch_save(latest_path, checkpoint)
            if improved:
                _atomic_torch_save(best_path, checkpoint)
            _write_run_files(
                manifest_path,
                history_path,
                run_id,
                "running",
                created_at,
                immutable_contract,
                config,
                model,
                history,
                best_epoch,
                best_validation_loss,
                latest_path,
                best_path,
            )
            progress(
                f"epoch={epoch} train={train_metrics['loss']:.6f} "
                f"validation={validation_loss:.6f} best={best_validation_loss:.6f} "
                f"stale={stale_epochs}/{config.patience}"
            )
            wandb_logger.log_epoch(
                epoch,
                train_metrics,
                validation_metrics,
                best_validation_loss=best_validation_loss,
                stale_epochs=stale_epochs,
                improved=improved,
            )
            if stale_epochs >= config.patience:
                status = "early_stopped"
                break

        _write_run_files(
            manifest_path,
            history_path,
            run_id,
            status,
            created_at,
            immutable_contract,
            config,
            model,
            history,
            best_epoch,
            best_validation_loss,
            latest_path,
            best_path,
            completed_at=_now_utc(),
        )
        wandb_logger.finish(
            status=status,
            last_epoch=last_epoch,
            best_epoch=best_epoch,
            best_validation_loss=best_validation_loss,
            output_directory=output_directory,
        )
    except Exception as error:
        if output_directory.exists():
            _write_run_files(
                manifest_path,
                history_path,
                run_id,
                "failed",
                created_at,
                immutable_contract,
                config,
                model,
                history,
                best_epoch,
                best_validation_loss,
                latest_path,
                best_path,
                completed_at=_now_utc(),
            )
        wandb_logger.finish(
            status="failed",
            last_epoch=last_epoch,
            best_epoch=best_epoch,
            best_validation_loss=best_validation_loss,
            output_directory=output_directory,
            error=error,
        )
        raise
    finally:
        torch.use_deterministic_algorithms(
            previous_deterministic,
            warn_only=previous_warn_only,
        )

    return TrainingRunResult(
        output_directory=output_directory,
        status=status,
        last_epoch=last_epoch,
        best_epoch=best_epoch,
        best_validation_loss=best_validation_loss,
        history=tuple(history),
    )


def _run_epoch(model, examples, config, renderer, objective, optimizer, epoch):
    training = optimizer is not None
    model.train(training)
    if training:
        torch.manual_seed(int(config.seed) + int(epoch))
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(int(config.seed) + int(epoch))
    generator = torch.Generator()
    generator.manual_seed(int(config.seed) + int(epoch))
    loader = DataLoader(
        examples,
        batch_size=config.batch_size,
        shuffle=training,
        generator=generator if training else None,
        num_workers=0,
        collate_fn=collate_feature_control_examples,
    )
    totals: dict[str, float] = {}
    example_count = 0
    context = torch.enable_grad() if training else torch.no_grad()
    with context:
        for batch in loader:
            batch = _move_feature_batch(batch, torch.device(config.device))
            if training:
                optimizer.zero_grad(set_to_none=True)
            result = vocal_self_supervised_batch_loss(
                model,
                batch,
                renderer=renderer,
                objective=objective,
            )
            loss = result.terms["loss"]
            if not torch.isfinite(loss):
                raise FloatingPointError(f"Non-finite vocal loss in epoch {epoch}")
            if training:
                loss.backward()
                torch.nn.utils.clip_grad_norm_(
                    model.parameters(),
                    config.gradient_clip_norm,
                    error_if_nonfinite=True,
                )
                optimizer.step()
            batch_size = int(batch["features_a"].shape[0])
            example_count += batch_size
            for name, value in result.terms.items():
                scalar = float(value.detach().cpu())
                if not math.isfinite(scalar):
                    raise FloatingPointError(f"Non-finite vocal objective term {name}")
                totals[name] = totals.get(name, 0.0) + scalar * batch_size
    return {name: value / example_count for name, value in sorted(totals.items())}


def _resolve_training_device(config):
    return replace(config, device=str(resolve_torch_device(config.device)))


def _move_feature_batch(batch, device):
    result = dict(batch)
    for name in ("features_a", "features_b", "global_features"):
        result[name] = batch[name].to(device=device, dtype=torch.float32)
    return result


def _materialize_dataset(dataset, split, progress):
    examples = []
    cache_hits = 0
    for index in range(len(dataset)):
        item = dataset[index]
        examples.append(item)
        cache_hits += int(item["waveform_cache_hit"])
        progress(
            f"vocal-cache split={split} {index + 1}/{len(dataset)} "
            f"id={item['example_id']} hit={item['waveform_cache_hit']}"
        )
    progress(
        f"vocal-cache split={split} ready examples={len(examples)} "
        f"hits={cache_hits} misses={len(examples) - cache_hits}"
    )
    return tuple(examples)


def _validate_vocal_examples(examples, split):
    required = {
        "features_a",
        "features_b",
        "global_features",
        "source_audio",
        "target_audio",
        "source_vocal_audio",
        "target_vocal_audio",
    }
    for index, example in enumerate(examples):
        missing = required.difference(example)
        if missing:
            raise ValueError(
                f"{split} example {index} is missing vocal training fields: {sorted(missing)}"
            )


def _cache_manifest_records(examples):
    records = []
    for example in examples:
        cache_directory = Path(example["waveform_cache_directory"])
        manifest_path = cache_directory / "manifest.json"
        if not manifest_path.is_file():
            raise FileNotFoundError(f"Vocal cache manifest is missing: {manifest_path}")
        records.append({
            "example_id": str(example["example_id"]),
            "path": str(manifest_path.resolve()),
            "sha256": _file_sha256(manifest_path),
        })
    return sorted(records, key=lambda item: item["example_id"])


def _immutable_contract(config, model_config, objective_config, dataset_identity, vocal_model):
    training = config.to_dict()
    training.pop("max_epochs")
    return {
        "format_version": VOCAL_TRAINING_RUN_FORMAT_VERSION,
        "runner_name": VOCAL_TRAINING_RUNNER_NAME,
        "dataset": dataset_identity,
        "waveform_cache": {
            "format_version": VOCAL_BRIDGE_WAVEFORM_CACHE_FORMAT_VERSION,
            "extractor_version": VOCAL_BRIDGE_WAVEFORM_EXTRACTOR_VERSION,
            "vocal_model": str(vocal_model),
        },
        "model": {
            "format_version": VOCAL_FEATURE_CONTROL_MODEL_FORMAT_VERSION,
            "name": VOCAL_FEATURE_CONTROL_MODEL_NAME,
            "config": model_config.to_dict(),
        },
        "training": training,
        "renderer": {
            "control_protocol_version": VOCAL_CONTROL_PROTOCOL_VERSION,
            "sample_rate": config.training_sample_rate,
            "lowpass_cutoff_hz": config.lowpass_cutoff_hz,
            "lowpass_kernel_size": config.lowpass_kernel_size,
        },
        "objective": {
            "version": VOCAL_OBJECTIVE_VERSION,
            "energy_frames": 32,
            "config": asdict(objective_config),
        },
    }


def _checkpoint_payload(
    run_id,
    epoch,
    model,
    optimizer,
    lr_scheduler,
    best_epoch,
    best_validation_loss,
    stale_epochs,
    history,
):
    return {
        "format_version": VOCAL_TRAINING_RUN_FORMAT_VERSION,
        "runner_name": VOCAL_TRAINING_RUNNER_NAME,
        "model_name": VOCAL_FEATURE_CONTROL_MODEL_NAME,
        "run_id": run_id,
        "epoch": int(epoch),
        "model_state_dict": model.state_dict(),
        "optimizer_state_dict": optimizer.state_dict(),
        "lr_scheduler_state_dict": (
            lr_scheduler.state_dict() if lr_scheduler is not None else None
        ),
        "best_epoch": int(best_epoch),
        "best_validation_loss": float(best_validation_loss),
        "stale_epochs": int(stale_epochs),
        "history": list(history),
    }


def _validate_checkpoint(checkpoint, run_id):
    if checkpoint.get("format_version") != VOCAL_TRAINING_RUN_FORMAT_VERSION:
        raise ValueError("Unsupported vocal training checkpoint format")
    if checkpoint.get("runner_name") != VOCAL_TRAINING_RUNNER_NAME:
        raise ValueError("Vocal checkpoint runner differs from the requested runner")
    if checkpoint.get("model_name") != VOCAL_FEATURE_CONTROL_MODEL_NAME:
        raise ValueError("Vocal checkpoint model differs from the requested model")
    if checkpoint.get("run_id") != run_id:
        raise ValueError("Vocal checkpoint run ID differs from the requested contract")
    if "lr_scheduler_state_dict" not in checkpoint:
        raise ValueError("Vocal checkpoint is missing its learning-rate scheduler state")


def _write_run_files(
    manifest_path,
    history_path,
    run_id,
    status,
    created_at,
    contract,
    config,
    model,
    history,
    best_epoch,
    best_validation_loss,
    latest_path,
    best_path,
    completed_at=None,
):
    history_payload = {
        "format_version": VOCAL_TRAINING_RUN_FORMAT_VERSION,
        "runner_name": VOCAL_TRAINING_RUNNER_NAME,
        "run_id": run_id,
        "epochs": history,
    }
    _atomic_json_write(history_path, history_payload)
    manifest = {
        "format_version": VOCAL_TRAINING_RUN_FORMAT_VERSION,
        "runner_name": VOCAL_TRAINING_RUNNER_NAME,
        "run_id": run_id,
        "status": status,
        "created_at_utc": created_at,
        "updated_at_utc": _now_utc(),
        "completed_at_utc": completed_at,
        "contract": contract,
        "requested_max_epochs": int(config.max_epochs),
        "model_parameter_count": int(model.parameter_count),
        "last_epoch": int(history[-1]["epoch"]) if history else -1,
        "best_epoch": int(best_epoch),
        "best_validation_loss": float(best_validation_loss),
        "files": {
            "history": _file_record(history_path, manifest_path.parent),
            "latest_checkpoint": _file_record(latest_path, manifest_path.parent),
            "best_checkpoint": _file_record(best_path, manifest_path.parent),
        },
    }
    _atomic_json_write(manifest_path, manifest)


def _file_record(path, relative_to):
    path = Path(path)
    if not path.is_file():
        return None
    return {
        "path": str(path.relative_to(relative_to)),
        "sha256": _file_sha256(path),
        "bytes": path.stat().st_size,
    }


def _atomic_json_write(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _atomic_torch_save(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        torch.save(payload, temporary)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _seed_everything(seed):
    seed = int(seed)
    random.seed(seed)
    np.random.seed(seed % (2**32))
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def _read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _file_sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _now_utc():
    return datetime.now(timezone.utc).isoformat()
