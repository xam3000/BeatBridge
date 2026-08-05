"""Reproducible train/validation runner for the feature-to-control baseline."""

from __future__ import annotations

from dataclasses import asdict, dataclass
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

from src.control import (
    CONTROL_PROTOCOL_VERSION,
    OBJECTIVE_VERSION,
    DifferentiableTransitionObjective,
    DifferentiableTransitionObjectiveConfig,
    DifferentiableTwoBandRenderer,
)

from .data import (
    DEFAULT_BRIDGE_WAVEFORM_CACHE_ROOT,
    DEFAULT_TRAINING_SAMPLE_RATE,
    FeatureControlDataset,
    collate_feature_control_examples,
)
from .model import FEATURE_CONTROL_MODEL_NAME, FeatureControlMLP, FeatureControlMLPConfig
from .training import self_supervised_batch_loss


TRAINING_RUN_FORMAT_VERSION = 1
TRAINING_RUNNER_NAME = "self_supervised_train_validation_v1"


@dataclass(frozen=True)
class TrainingConfig:
    """Optimization and renderer settings stored with every run."""

    seed: int = 20260804
    max_epochs: int = 30
    batch_size: int = 5
    learning_rate: float = 1e-3
    weight_decay: float = 1e-4
    patience: int = 6
    min_delta: float = 1e-4
    gradient_clip_norm: float = 1.0
    training_sample_rate: int = DEFAULT_TRAINING_SAMPLE_RATE
    lowpass_cutoff_hz: float = 180.0
    lowpass_kernel_size: int = 127
    device: str = "cpu"

    def __post_init__(self):
        if int(self.max_epochs) < 1:
            raise ValueError("max_epochs must be at least 1")
        if int(self.batch_size) < 1:
            raise ValueError("batch_size must be at least 1")
        if float(self.learning_rate) <= 0 or float(self.weight_decay) < 0:
            raise ValueError("learning_rate must be positive and weight_decay non-negative")
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
        if str(self.device) != "cpu" and not str(self.device).startswith("cuda"):
            raise ValueError("device must be cpu or a CUDA device")

    def to_dict(self):
        return asdict(self)


@dataclass(frozen=True)
class TrainingRunResult:
    """Summary of a completed or early-stopped run."""

    output_directory: Path
    status: str
    last_epoch: int
    best_epoch: int
    best_validation_loss: float
    history: tuple[dict, ...]


def run_feature_control_training(
    dataset_directory,
    output_directory,
    *,
    config: TrainingConfig | None = None,
    model_config: FeatureControlMLPConfig | None = None,
    objective_config: DifferentiableTransitionObjectiveConfig | None = None,
    waveform_cache_root=DEFAULT_BRIDGE_WAVEFORM_CACHE_ROOT,
    resume=False,
    progress=print,
):
    """Materialize train/validation audio caches and run self-supervised training."""
    config = config or TrainingConfig()
    dataset_directory = Path(dataset_directory).resolve()
    dataset_manifest_path = dataset_directory / "manifest.json"
    dataset_manifest = _read_json(dataset_manifest_path)
    train_dataset = FeatureControlDataset(
        dataset_directory,
        "train",
        waveform_cache_root=waveform_cache_root,
        training_sample_rate=config.training_sample_rate,
        build_missing_waveforms=True,
    )
    validation_dataset = FeatureControlDataset(
        dataset_directory,
        "validation",
        waveform_cache_root=waveform_cache_root,
        training_sample_rate=config.training_sample_rate,
        build_missing_waveforms=True,
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
    }
    return train_feature_control_model(
        train_examples,
        validation_examples,
        output_directory,
        config=config,
        model_config=model_config,
        objective_config=objective_config,
        dataset_identity=dataset_identity,
        resume=resume,
        progress=progress,
    )


def train_feature_control_model(
    train_examples,
    validation_examples,
    output_directory,
    *,
    config: TrainingConfig | None = None,
    model_config: FeatureControlMLPConfig | None = None,
    objective_config: DifferentiableTransitionObjectiveConfig | None = None,
    dataset_identity: dict | None = None,
    resume=False,
    progress=print,
):
    """Train from pre-materialized examples and persist restartable artifacts."""
    config = config or TrainingConfig()
    model_config = model_config or FeatureControlMLPConfig()
    objective_config = objective_config or DifferentiableTransitionObjectiveConfig()
    train_examples = tuple(train_examples)
    validation_examples = tuple(validation_examples)
    if not train_examples or not validation_examples:
        raise ValueError("train and validation must both contain at least one example")
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
    })
    immutable_contract = _immutable_contract(
        config,
        model_config,
        objective_config,
        dataset_identity,
    )
    run_id = hashlib.sha256(
        json.dumps(immutable_contract, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()[:20]

    device = torch.device(config.device)
    if device.type == "cuda" and not torch.cuda.is_available():
        raise RuntimeError(f"Requested device is unavailable: {config.device}")
    _seed_everything(config.seed)
    model = FeatureControlMLP(model_config).to(device=device, dtype=torch.float32)
    renderer = DifferentiableTwoBandRenderer(
        sample_rate=config.training_sample_rate,
        lowpass_cutoff_hz=config.lowpass_cutoff_hz,
        lowpass_kernel_size=config.lowpass_kernel_size,
    ).to(device=device, dtype=torch.float32)
    objective = DifferentiableTransitionObjective(
        objective_config,
        energy_frames=32,
    ).to(device=device)
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=config.learning_rate,
        weight_decay=config.weight_decay,
    )

    if resume:
        if not manifest_path.is_file() or not latest_path.is_file():
            raise FileNotFoundError("Resume requires manifest.json and checkpoints/latest.pt")
        manifest = _read_json(manifest_path)
        if manifest.get("run_id") != run_id or manifest.get("contract") != immutable_contract:
            raise ValueError("Existing run contract differs from the requested configuration")
        checkpoint = torch.load(latest_path, map_location=device, weights_only=False)
        _validate_checkpoint(checkpoint, run_id)
        model.load_state_dict(checkpoint["model_state_dict"])
        optimizer.load_state_dict(checkpoint["optimizer_state_dict"])
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
                f"Training output already exists; use resume=True: {output_directory}"
            )
        checkpoint_directory.mkdir(parents=True)
        history = []
        start_epoch = 1
        best_epoch = 0
        best_validation_loss = math.inf
        stale_epochs = 0
        created_at = _now_utc()

    previous_deterministic = torch.are_deterministic_algorithms_enabled()
    torch.use_deterministic_algorithms(True)
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
                "phase": "equal_power_initialization",
                "train": initial_train,
                "validation": initial_validation,
            })
            best_validation_loss = float(initial_validation["loss"])
            checkpoint = _checkpoint_payload(
                run_id,
                0,
                model,
                optimizer,
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
                f"epoch=0 equal_power train={initial_train['loss']:.6f} "
                f"validation={initial_validation['loss']:.6f}"
            )

        status = "completed"
        last_epoch = start_epoch - 1
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
            history.append({
                "epoch": epoch,
                "phase": "training",
                "train": train_metrics,
                "validation": validation_metrics,
            })
            validation_loss = float(validation_metrics["loss"])
            improved = validation_loss < best_validation_loss - config.min_delta
            if improved:
                best_validation_loss = validation_loss
                best_epoch = epoch
                stale_epochs = 0
            else:
                stale_epochs += 1
            last_epoch = epoch
            checkpoint = _checkpoint_payload(
                run_id,
                epoch,
                model,
                optimizer,
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
    except Exception:
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
        raise
    finally:
        torch.use_deterministic_algorithms(previous_deterministic)

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
        # Makes stochastic layers reproducible even when a run is resumed.
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
            result = self_supervised_batch_loss(
                model,
                batch,
                renderer=renderer,
                objective=objective,
            )
            loss = result.terms["loss"]
            if not torch.isfinite(loss):
                raise FloatingPointError(f"Non-finite loss in epoch {epoch}")
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
                    raise FloatingPointError(f"Non-finite objective term {name}")
                totals[name] = totals.get(name, 0.0) + scalar * batch_size
    return {name: value / example_count for name, value in sorted(totals.items())}


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
            f"cache split={split} {index + 1}/{len(dataset)} "
            f"id={item['example_id']} hit={item['waveform_cache_hit']}"
        )
    progress(
        f"cache split={split} ready examples={len(examples)} "
        f"hits={cache_hits} misses={len(examples) - cache_hits}"
    )
    return tuple(examples)


def _immutable_contract(config, model_config, objective_config, dataset_identity):
    training = config.to_dict()
    training.pop("max_epochs")
    return {
        "format_version": TRAINING_RUN_FORMAT_VERSION,
        "runner_name": TRAINING_RUNNER_NAME,
        "dataset": dataset_identity,
        "model": {
            "name": FEATURE_CONTROL_MODEL_NAME,
            "config": model_config.to_dict(),
        },
        "training": training,
        "renderer": {
            "control_protocol_version": CONTROL_PROTOCOL_VERSION,
            "sample_rate": config.training_sample_rate,
            "lowpass_cutoff_hz": config.lowpass_cutoff_hz,
            "lowpass_kernel_size": config.lowpass_kernel_size,
        },
        "objective": {
            "version": OBJECTIVE_VERSION,
            "energy_frames": 32,
            "config": asdict(objective_config),
        },
    }


def _checkpoint_payload(
    run_id,
    epoch,
    model,
    optimizer,
    best_epoch,
    best_validation_loss,
    stale_epochs,
    history,
):
    return {
        "format_version": TRAINING_RUN_FORMAT_VERSION,
        "run_id": run_id,
        "epoch": int(epoch),
        "model_state_dict": model.state_dict(),
        "optimizer_state_dict": optimizer.state_dict(),
        "best_epoch": int(best_epoch),
        "best_validation_loss": float(best_validation_loss),
        "stale_epochs": int(stale_epochs),
        "history": list(history),
    }


def _validate_checkpoint(checkpoint, run_id):
    if checkpoint.get("format_version") != TRAINING_RUN_FORMAT_VERSION:
        raise ValueError("Unsupported training checkpoint format")
    if checkpoint.get("run_id") != run_id:
        raise ValueError("Checkpoint run ID differs from the requested contract")


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
        "format_version": TRAINING_RUN_FORMAT_VERSION,
        "run_id": run_id,
        "epochs": history,
    }
    _atomic_json_write(history_path, history_payload)
    manifest = {
        "format_version": TRAINING_RUN_FORMAT_VERSION,
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
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def _atomic_torch_save(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        torch.save(payload, temporary)
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


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
