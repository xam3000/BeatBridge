"""Checkpoint and resume contracts for the additive variable MLP baseline."""

from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import uuid

import torch

from src.control import DifferentiableVocalAwareRenderer, VariableVocalAwareTransitionObjective
from src.features.variable_contract import SUPPORTED_VARIABLE_LENGTHS, geometry_for_length
from src.torch_device import DEFAULT_TORCH_DEVICE, resolve_torch_device, validate_torch_device_spec
from .variable_model import (
    VARIABLE_LENGTH_CONDITIONING_VERSION,
    VARIABLE_MLP_MODEL_FORMAT_VERSION,
    VARIABLE_TIME_SHARED_MLP_MODEL_NAME,
    VARIABLE_TCN_BILSTM_MODEL_FORMAT_VERSION,
    VARIABLE_TCN_BILSTM_MODEL_NAME,
)
from .control_initialization import LEGACY, run_initialization
from .variable_control_initialization import (
    VariableTimeSharedMLPConfig,
    VariableTCNBiLSTMControlConfig,
    VariableTCNBiLSTMTransitionControl,
)
from .variable_data import (
    VariableFeatureControlDataset,
    VariableFeatureDataset,
    VariableLengthBatchSampler,
    collate_variable_feature_examples,
)
from .variable_training import variable_vocal_self_supervised_batch_loss
from .lr_schedule import (
    apply_linear_warmup,
    current_learning_rate,
    make_plateau_scheduler,
    step_plateau_after_warmup,
    validate_lr_schedule_config,
)
from .variable_waveform_cache import (
    VARIABLE_WAVEFORM_CACHE_ROOT,
    VARIABLE_WAVEFORM_RENDER_SAMPLE_RATE,
    VARIABLE_WAVEFORM_SAMPLE_RATE,
    build_variable_cache_loader,
    load_variable_waveform_cache_index,
)
from .wandb_logging import WandbConfig, WandbLogger


VARIABLE_TRAINING_RUN_FORMAT_VERSION = 2
VARIABLE_TRAINING_RUNNER_NAME = "self_supervised_train_validation_variable_mlp_v1"
VARIABLE_TEMPORAL_TRAINING_RUNNER_NAME = "self_supervised_train_validation_variable_tcn_bilstm_v1"


class VariableTemporalTrainingConfig:
    """Small explicit configuration for the Dataset-2 temporal runner."""

    def __init__(
        self,
        *,
        seed=20260820,
        max_epochs=1,
        learning_rate=1e-3,
        weight_decay=1e-4,
        gradient_clip_norm=1.0,
        training_sample_rate=11_025,
        lowpass_cutoff_hz=180.0,
        lowpass_kernel_size=127,
        device=DEFAULT_TORCH_DEVICE,
        length_weighting="equal_length",
        patience=30,
        min_delta=0.0,
        lr_warmup_epochs=5,
        lr_warmup_start_factor=0.1,
        lr_scheduler_patience=10,
        lr_scheduler_factor=0.5,
        lr_scheduler_threshold=1e-4,
        lr_scheduler_min_lr_factor=0.05,
    ):
        self.seed = int(seed)
        self.max_epochs = int(max_epochs)
        self.learning_rate = float(learning_rate)
        self.weight_decay = float(weight_decay)
        self.gradient_clip_norm = float(gradient_clip_norm)
        self.training_sample_rate = int(training_sample_rate)
        self.lowpass_cutoff_hz = float(lowpass_cutoff_hz)
        self.lowpass_kernel_size = int(lowpass_kernel_size)
        self.device = str(device)
        self.length_weighting = str(length_weighting)
        self.patience = int(patience)
        self.min_delta = float(min_delta)
        self.lr_warmup_epochs = int(lr_warmup_epochs)
        self.lr_warmup_start_factor = float(lr_warmup_start_factor)
        self.lr_scheduler_patience = int(lr_scheduler_patience)
        self.lr_scheduler_factor = float(lr_scheduler_factor)
        self.lr_scheduler_threshold = float(lr_scheduler_threshold)
        self.lr_scheduler_min_lr_factor = float(lr_scheduler_min_lr_factor)
        if self.max_epochs < 1 or self.learning_rate <= 0 or self.weight_decay < 0:
            raise ValueError("Invalid variable temporal optimization configuration")
        if self.gradient_clip_norm <= 0 or self.training_sample_rate <= 0:
            raise ValueError("gradient_clip_norm and training_sample_rate must be positive")
        if self.lowpass_kernel_size < 3 or self.lowpass_kernel_size % 2 == 0:
            raise ValueError("lowpass_kernel_size must be an odd integer of at least 3")
        if self.length_weighting != "equal_length":
            raise ValueError("Only equal_length weighting is supported by the v1 temporal runner")
        if self.patience < 1 or self.min_delta < 0:
            raise ValueError("patience must be at least 1 and min_delta must be non-negative")
        validate_lr_schedule_config(
            warmup_epochs=self.lr_warmup_epochs,
            warmup_start_factor=self.lr_warmup_start_factor,
            scheduler_patience=self.lr_scheduler_patience,
            scheduler_factor=self.lr_scheduler_factor,
            scheduler_threshold=self.lr_scheduler_threshold,
            scheduler_min_lr_factor=self.lr_scheduler_min_lr_factor,
        )
        validate_torch_device_spec(self.device)

    def to_dict(self):
        return dict(self.__dict__)


def train_variable_temporal_control_model(
    train_batches,
    validation_batches,
    output_directory,
    *,
    config: VariableTemporalTrainingConfig | None = None,
    model_config: VariableTCNBiLSTMControlConfig | None = None,
    dataset_manifest_sha256,
    supported_lengths=SUPPORTED_VARIABLE_LENGTHS,
    resume=False,
    save_checkpoints=True,
    waveform_cache_index_sha256=None,
    waveform_cache_root_manifest_sha256=None,
    initialize_from_manifest=None,
    initialize_from_checkpoint=None,
    progress=print,
    wandb_config: WandbConfig | None = None,
):
    """Train only supplied train/validation batches; the test split is never opened.

    Batches must already be length-homogeneous Dataset-2 batches.  This keeps
    test-split isolation at the API boundary: no path or loader for a test
    split exists in this runner.
    """

    config = config or VariableTemporalTrainingConfig()
    config.device = str(resolve_torch_device(config.device))
    model_config = model_config or VariableTCNBiLSTMControlConfig(
        control_initialization=run_initialization(output_directory, resume, source_manifest=initialize_from_manifest),
    )
    train_batches = tuple(train_batches)
    validation_batches = tuple(validation_batches)
    if not train_batches or not validation_batches:
        raise ValueError("train and validation batches must both be non-empty")
    lengths = tuple(
        sorted(
            {
                geometry_for_length(value).transition_length_bars
                for value in supported_lengths
            }
        )
    )
    _validate_temporal_batches(train_batches, lengths, "train")
    _validate_temporal_batches(validation_batches, lengths, "validation")
    contract = build_variable_training_contract(
        dataset_manifest_sha256=dataset_manifest_sha256,
        supported_lengths=lengths,
        model_name=VARIABLE_TCN_BILSTM_MODEL_NAME,
        model_format_version=VARIABLE_TCN_BILSTM_MODEL_FORMAT_VERSION,
        objective_name="objective_v5_time_normalized_variable_tcn_bilstm_v1",
        waveform_cache_index_sha256=waveform_cache_index_sha256,
        waveform_cache_root_manifest_sha256=waveform_cache_root_manifest_sha256,
    )
    immutable_training = config.to_dict()
    immutable_training.pop("max_epochs")
    initialization = None
    initialization_checkpoint = None
    if (initialize_from_manifest is None) != (initialize_from_checkpoint is None):
        raise ValueError("Initialization requires both a source manifest and checkpoint")
    if resume and initialize_from_manifest is not None:
        raise ValueError("Fine-tune initialization and resume are mutually exclusive")
    if resume:
        previous = json.loads((Path(output_directory) / "manifest.json").read_text(encoding="utf-8"))
        initialization = previous["contract"].get("initialization")
    if initialize_from_manifest is not None:
        initialization_checkpoint, initialization = load_variable_checkpoint_for_initialization(
            initialize_from_manifest,
            initialize_from_checkpoint,
        )
        source_config = initialization_checkpoint["contract"]["model"]["config"]
        if source_config.get("control_initialization", LEGACY) != getattr(model_config, "control_initialization", LEGACY):
            raise ValueError("Fine-tune control_initialization differs from the checkpoint contract")
        # For the new map the logit origin is part of the meaning of the weights.
        if (source_config.get("control_initialization", LEGACY) != LEGACY
                and source_config["initial_vocal_duck_logit"] != model_config.initial_vocal_duck_logit):
            raise ValueError("Fine-tune vocal duck logit origin differs from the checkpoint contract")
    contract.update({
        "runner_name": VARIABLE_TEMPORAL_TRAINING_RUNNER_NAME,
        "model": {"config": model_config.to_dict()},
        "training": immutable_training,
        "renderer": {
            "name": "DifferentiableVocalAwareRenderer",
            "sample_rate": config.training_sample_rate,
            "lowpass_cutoff_hz": config.lowpass_cutoff_hz,
            "lowpass_kernel_size": config.lowpass_kernel_size,
        },
        "length_scheduler": {
            "kind": "provided_length_homogeneous_batches",
            "length_order": list(lengths),
            "weighting": config.length_weighting,
        },
    })
    if initialization is not None:
        contract["initialization"] = initialization
    run_id = hashlib.sha256(_canonical_json(contract)).hexdigest()[:20]
    output_directory = Path(output_directory).resolve()
    checkpoint_directory = output_directory / "checkpoints"
    latest_path = checkpoint_directory / "latest.pt"
    best_path = checkpoint_directory / "best.pt"
    if not save_checkpoints and resume:
        raise ValueError("Cannot resume a run when save_checkpoints=False")
    manifest_path = output_directory / "manifest.json"
    history_path = output_directory / "history.json"
    device = torch.device(config.device)
    torch.manual_seed(config.seed)
    model = VariableTCNBiLSTMTransitionControl(model_config).to(device=device, dtype=torch.float32)
    if initialization_checkpoint is not None:
        model.load_state_dict(initialization_checkpoint["model_state_dict"], strict=True)
    renderer = DifferentiableVocalAwareRenderer(
        sample_rate=config.training_sample_rate,
        lowpass_cutoff_hz=config.lowpass_cutoff_hz,
        lowpass_kernel_size=config.lowpass_kernel_size,
    ).to(device=device, dtype=torch.float32)
    objective = VariableVocalAwareTransitionObjective().to(device=device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=config.learning_rate, weight_decay=config.weight_decay)
    lr_scheduler = make_plateau_scheduler(optimizer, config)
    if resume:
        checkpoint = load_variable_checkpoint_for_resume(
            manifest_path,
            latest_path,
            expected_contract=contract,
            expected_runner_name=VARIABLE_TEMPORAL_TRAINING_RUNNER_NAME,
        )
        model.load_state_dict(checkpoint["model_state_dict"])
        optimizer.load_state_dict(checkpoint["optimizer_state_dict"])
        scheduler_state = checkpoint.get("lr_scheduler_state_dict")
        if not isinstance(scheduler_state, dict):
            raise ValueError("Variable TCN/BiLSTM checkpoint has no compatible learning-rate scheduler state")
        lr_scheduler.load_state_dict(scheduler_state)
        history = list(checkpoint.get("history", ()))
        start_epoch = int(checkpoint["epoch"]) + 1
        best_loss = float(checkpoint.get("best_validation_loss", math.inf))
        best_epoch = int(checkpoint.get("best_epoch", 0))
        if config.max_epochs < start_epoch:
            raise ValueError("max_epochs must extend beyond the latest checkpoint epoch")
    else:
        if output_directory.exists():
            raise FileExistsError(f"Training output already exists; use resume=True: {output_directory}")
        if save_checkpoints:
            checkpoint_directory.mkdir(parents=True)
        history = []
        start_epoch = 1
        best_loss = math.inf
        best_epoch = 0
    stale_epochs = checkpoint.get("stale_epochs", 0) if resume else 0
    wandb_logger = WandbLogger.start(
        wandb_config,
        run_id=run_id,
        runner_name=VARIABLE_TEMPORAL_TRAINING_RUNNER_NAME,
        contract=contract,
        output_directory=output_directory,
        resume=resume,
    )

    def publish_epoch(*, improved):
        epoch = history[-1]["epoch"]
        if save_checkpoints:
            checkpoint = variable_checkpoint_payload(
                run_id=run_id, epoch=epoch, model=model, optimizer=optimizer,
                contract=contract, history=history, runner_name=VARIABLE_TEMPORAL_TRAINING_RUNNER_NAME,
                lr_scheduler=lr_scheduler,
            )
            checkpoint.update(best_epoch=best_epoch, best_validation_loss=best_loss, stale_epochs=stale_epochs)
            _atomic_torch_save(latest_path, checkpoint)
            if improved:
                _atomic_torch_save(best_path, checkpoint)
        _write_temporal_run_files(manifest_path, history_path, run_id, contract, history,
                                  latest_path, best_path, status="running")

    try:
        if not resume:
            with torch.no_grad():
                train_zero = _run_temporal_epoch(model, train_batches, renderer, objective, None, config, device)
                val_zero = _run_temporal_epoch(model, validation_batches, renderer, objective, None, config, device)
            phase = ("checkpoint_initialization" if initialization is not None else
                     "legacy_initialization" if getattr(model_config, "control_initialization", LEGACY) == LEGACY
                     else "equal_power_initialization")
            history.append({"epoch": 0, "phase": phase, "train": train_zero, "validation": val_zero})
            # E0 is observational. Keep the historical selection among trained epochs.
            publish_epoch(improved=False)
            wandb_logger.log_epoch(0, _flat_metrics(train_zero), _flat_metrics(val_zero),
                                   best_validation_loss=None, stale_epochs=0, improved=False)
            progress(f"epoch=0 {phase} train={train_zero['loss']:.6f} validation={val_zero['loss']:.6f}")
        for epoch in range(start_epoch, config.max_epochs + 1):
            apply_linear_warmup(
                optimizer,
                epoch=epoch,
                warmup_epochs=config.lr_warmup_epochs,
                start_factor=config.lr_warmup_start_factor,
            )
            epoch_learning_rate = current_learning_rate(optimizer)
            train_metrics = _run_temporal_epoch(model, train_batches, renderer, objective, optimizer, config, device)
            train_metrics["learning_rate"] = epoch_learning_rate
            validation_metrics = _run_temporal_epoch(model, validation_batches, renderer, objective, None, config, device)
            validation_loss = float(validation_metrics["loss"])
            improved = validation_loss < (best_loss - config.min_delta)
            if improved:
                best_loss, best_epoch = validation_loss, epoch
                stale_epochs = 0
            else:
                stale_epochs += 1
            step_plateau_after_warmup(
                lr_scheduler,
                validation_loss,
                epoch=epoch,
                warmup_epochs=config.lr_warmup_epochs,
            )
            epoch_record = {"epoch": epoch, "train": train_metrics, "validation": validation_metrics}
            history.append(epoch_record)
            publish_epoch(improved=improved)
            wandb_logger.log_epoch(
                epoch,
                _flat_metrics(train_metrics),
                _flat_metrics(validation_metrics),
                best_validation_loss=best_loss,
                stale_epochs=stale_epochs,
                improved=improved,
            )
            progress(f"epoch={epoch} train={train_metrics['loss']:.6f} validation={validation_loss:.6f}")
            if stale_epochs >= config.patience:
                break
        _write_temporal_run_files(manifest_path, history_path, run_id, contract, history, latest_path, best_path, status="completed")
        wandb_logger.finish(status="completed", last_epoch=history[-1]["epoch"], best_epoch=best_epoch, best_validation_loss=best_loss, output_directory=output_directory)
    except Exception as error:
        wandb_logger.finish(status="failed", last_epoch=history[-1]["epoch"] if history else 0, best_epoch=best_epoch, best_validation_loss=best_loss, output_directory=output_directory, error=error)
        raise
    return {"output_directory": output_directory, "run_id": run_id, "history": tuple(history), "best_epoch": best_epoch, "best_validation_loss": best_loss}


def run_variable_tcn_bilstm_training(
    dataset_directory,
    output_directory,
    *,
    config: VariableTemporalTrainingConfig | None = None,
    model_config: VariableTCNBiLSTMControlConfig | None = None,
    waveform_cache_root=VARIABLE_WAVEFORM_CACHE_ROOT,
    transition_lengths=SUPPORTED_VARIABLE_LENGTHS,
    batch_size=4,
    resume=False,
    save_checkpoints=True,
    wandb_config: WandbConfig | None = None,
    progress=print,
    initialize_from_manifest=None,
    initialize_from_checkpoint=None,
):
    """Run the real Dataset-2 TCN/BiLSTM path using cache hits only.

    This wrapper intentionally constructs only the train and validation
    collections.  No test ``VariableFeatureDataset`` is instantiated here.
    """

    from .variable_data import VariableFeatureDatasetCollection

    config = config or VariableTemporalTrainingConfig()
    dataset_directory = Path(dataset_directory)
    dataset_manifest_path = dataset_directory / "manifest.json"
    dataset_manifest = json.loads(dataset_manifest_path.read_text(encoding="utf-8"))
    dataset_manifest_sha256 = _sha256(dataset_manifest_path)
    lengths = tuple(sorted({geometry_for_length(value).transition_length_bars for value in transition_lengths}))
    if not lengths:
        raise ValueError("At least one transition length is required")
    batch_size = int(batch_size)
    if batch_size < 1:
        raise ValueError("batch_size must be at least 1")
    cache_binding = load_variable_waveform_cache_index(
        waveform_cache_root,
        dataset_manifest_sha256=dataset_manifest_sha256,
        required_splits=("train", "validation"),
        required_lengths=lengths,
    )
    cache_exclusions = _validated_cache_exclusions(
        dataset_directory,
        waveform_cache_root,
        dataset_manifest_sha256,
        cache_binding,
        lengths,
    )
    waveform_loader = build_variable_cache_loader(
        dataset_directory,
        cache_root=waveform_cache_root,
        training_sample_rate=config.training_sample_rate,
        render_sample_rate=VARIABLE_WAVEFORM_RENDER_SAMPLE_RATE,
        require_index=True,
        required_splits=("train", "validation"),
        required_lengths=lengths,
    )
    train_dataset = VariableFeatureDatasetCollection(
        dataset_directory,
        "train",
        transition_length_bars=lengths,
        waveform_loader=waveform_loader,
        include_example_ids=cache_binding["entries"].keys(),
    )
    validation_dataset = VariableFeatureDatasetCollection(
        dataset_directory,
        "validation",
        transition_length_bars=lengths,
        waveform_loader=waveform_loader,
        include_example_ids=cache_binding["entries"].keys(),
    )

    def make_batches(dataset, *, shuffle, seed):
        sampler = VariableLengthBatchSampler(
            dataset,
            batch_size,
            shuffle=shuffle,
            seed=seed,
        )
        return tuple(
            collate_variable_feature_examples([dataset[index] for index in indices])
            for indices in sampler
        )

    train_batches = make_batches(train_dataset, shuffle=True, seed=config.seed)
    validation_batches = make_batches(validation_dataset, shuffle=False, seed=config.seed)
    result = train_variable_temporal_control_model(
        train_batches,
        validation_batches,
        output_directory,
        config=config,
        model_config=model_config,
        save_checkpoints=save_checkpoints,
        dataset_manifest_sha256=dataset_manifest_sha256,
        supported_lengths=lengths,
        resume=resume,
        waveform_cache_index_sha256=cache_binding["file_sha256"],
        waveform_cache_root_manifest_sha256=cache_binding["payload"]["cache_root_manifest_sha256"],
        initialize_from_manifest=initialize_from_manifest,
        initialize_from_checkpoint=initialize_from_checkpoint,
        wandb_config=wandb_config,
        progress=progress,
    )
    audit_path = Path(output_directory) / "io_audit.json"
    audit_payload = {
        "format_version": 1,
        "policy": "train_validation_only_test_closed_v1",
        "dataset_manifest_sha256": dataset_manifest_sha256,
        "waveform_cache_index_sha256": cache_binding["file_sha256"],
        "opened_splits": ["train", "validation"],
        "test_reads": 0,
        "train_examples_read": int(sum(len(batch["example_ids"]) for batch in train_batches)),
        "validation_examples_read": int(sum(len(batch["example_ids"]) for batch in validation_batches)),
        "materialization_report_sha256": cache_exclusions["report_sha256"],
        "excluded_validation_cache_rejections": cache_exclusions["rejections"],
    }
    _atomic_json_write(audit_path, audit_payload)
    run_manifest_path = Path(output_directory) / "manifest.json"
    run_manifest = json.loads(run_manifest_path.read_text(encoding="utf-8"))
    run_manifest.setdefault("files", {})["io_audit"] = _file_record(
        audit_path, run_manifest_path.parent
    )
    _atomic_json_write(run_manifest_path, run_manifest)
    result.update({
        "status": "completed",
        "last_epoch": int(result["history"][-1]["epoch"]),
        "dataset_id": dataset_manifest["dataset_id"],
        "cache_root": str(Path(waveform_cache_root)),
        "cache_index_sha256": cache_binding["file_sha256"],
        "train_batch_count": len(train_batches),
        "validation_batch_count": len(validation_batches),
        "cache_hits": int(sum(1 for batch in train_batches + validation_batches for _ in batch["example_ids"])),
        "test_reads": 0,
        "excluded_validation_examples": len(cache_exclusions["rejections"]),
    })
    return result


def _validated_cache_exclusions(
    dataset_directory,
    cache_root,
    dataset_manifest_sha256,
    cache_binding,
    lengths,
):
    """Allow only report-bound Validation cache rejections to be omitted.

    Train examples may never be omitted.  The immutable index, dataset shards,
    and materialization report must agree exactly before filtering Validation.
    """

    from .variable_data import VariableFeatureDataset

    expected = {}
    requested_counts = {split: {int(length): 0 for length in lengths} for split in ("train", "validation")}
    for split in ("train", "validation"):
        for length in lengths:
            dataset = VariableFeatureDataset(dataset_directory, length, split)
            requested_counts[split][length] = len(dataset.examples)
            for example in dataset.examples:
                example_id = str(example["example_id"])
                if example_id in expected:
                    raise ValueError(f"Duplicate Dataset-v2 example ID across shards: {example_id}")
                expected[example_id] = {
                    "split": split,
                    "transition_length_bars": int(length),
                }

    indexed = cache_binding["entries"]
    for example_id, row in indexed.items():
        if example_id not in expected:
            raise ValueError(f"Waveform cache index contains an unknown dataset example: {example_id}")
        if row.get("split") != expected[example_id]["split"] or int(row.get("transition_length_bars", -1)) != expected[example_id]["transition_length_bars"]:
            raise ValueError(f"Waveform cache index metadata differs from dataset: {example_id}")
    missing = set(expected) - set(indexed)
    missing_train = sorted(value for value in missing if expected[value]["split"] == "train")
    if missing_train:
        raise ValueError(f"Waveform cache index lacks Train examples: {missing_train[:5]}")

    report_path = Path(cache_root) / "materialization_report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report_index = report.get("cache_index", {})
    if report.get("dataset_manifest_sha256") != dataset_manifest_sha256:
        raise ValueError("Materialization report dataset SHA differs")
    if report_index.get("file_sha256") != cache_binding["file_sha256"]:
        raise ValueError("Materialization report does not bind the sealed cache index")
    if report_index.get("entry_count") != len(indexed):
        raise ValueError("Materialization report entry count differs from cache index")
    if tuple(sorted(int(value) for value in report.get("lengths", ()))) != tuple(sorted(lengths)):
        raise ValueError("Materialization report transition lengths differ")
    if set(report.get("splits", ())) != {"train", "validation"}:
        raise ValueError("Materialization report must cover exactly Train and Validation")

    rejected_rows = report.get("rejections", ())
    rejection_ids = [str(row.get("example_id", "")) for row in rejected_rows]
    if len(set(rejection_ids)) != len(rejection_ids) or set(rejection_ids) != missing:
        raise ValueError("Materialization report rejections do not match uncached dataset examples")
    if any(
        row.get("split") != "validation"
        or str(row.get("reason", "")) == ""
        or expected.get(str(row.get("example_id"))) != {
            "split": "validation",
            "transition_length_bars": int(row.get("length", -1)),
        }
        for row in rejected_rows
    ):
        raise ValueError("Only explicitly reported Validation cache rejections may be excluded")

    for split in ("train", "validation"):
        for length in lengths:
            bucket = report.get("counts", {}).get(split, {}).get(str(length), {})
            total = sum(int(bucket.get(key, -1)) for key in ("cache_hits", "cache_misses", "rejected"))
            if int(bucket.get("requested", -1)) != requested_counts[split][length] or total != requested_counts[split][length]:
                raise ValueError(f"Materialization report counts differ from Dataset-v2 {split}/{length}")

    return {
        "report_sha256": _sha256(report_path),
        "rejections": sorted(
            (dict(row) for row in rejected_rows),
            key=lambda row: str(row["example_id"]),
        ),
    }


def build_variable_training_contract(
    *,
    dataset_manifest_sha256,
    supported_lengths=SUPPORTED_VARIABLE_LENGTHS,
    model_name=VARIABLE_TIME_SHARED_MLP_MODEL_NAME,
    model_config=None,
    model_format_version=VARIABLE_MLP_MODEL_FORMAT_VERSION,
    objective_name="objective_v5_time_normalized_variable_v1",
    waveform_cache_index_sha256=None,
    waveform_cache_root_manifest_sha256=None,
):
    """Build the immutable contract embedded in run manifests and checkpoints."""

    lengths = tuple(
        sorted(
            {
                geometry_for_length(value).transition_length_bars
                for value in supported_lengths
            }
        )
    )
    if not lengths:
        raise ValueError("supported_lengths must not be empty")
    geometries = {str(length): geometry_for_length(length) for length in lengths}
    digest = str(dataset_manifest_sha256).lower()
    if len(digest) != 64 or any(character not in "0123456789abcdef" for character in digest):
        raise ValueError("dataset_manifest_sha256 must be a SHA-256 hex digest")
    contract = {
        "dataset_format_version": 2,
        "feature_protocol_version": 2,
        "dataset_manifest_sha256": digest,
        "supported_lengths": list(lengths),
        "sequence_lengths": {
            key: geometry.sequence_length for key, geometry in geometries.items()
        },
        "transition_length_beats": {
            key: geometry.transition_length_beats for key, geometry in geometries.items()
        },
        "length_conditioning": {
            "version": VARIABLE_LENGTH_CONDITIONING_VERSION,
            "field": "length_condition",
            "dimension": 1,
            "normalization": "transition_length_bars / 8",
        },
        "model_name": str(model_name),
        "model_format_version": int(model_format_version),
        "objective_name": str(objective_name),
    }
    if (waveform_cache_index_sha256 is None) != (waveform_cache_root_manifest_sha256 is None):
        raise ValueError("Both waveform cache SHA bindings must be supplied together")
    if model_config is None and model_name == VARIABLE_TIME_SHARED_MLP_MODEL_NAME:
        model_config = VariableTimeSharedMLPConfig()
    if model_config is not None:
        contract["model"] = {"config": model_config.to_dict()}
    if waveform_cache_index_sha256 is not None:
        for name, value in (
            ("waveform_cache_index_sha256", waveform_cache_index_sha256),
            ("waveform_cache_root_manifest_sha256", waveform_cache_root_manifest_sha256),
        ):
            value = str(value).lower()
            if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
                raise ValueError(f"{name} must be a SHA-256 hex digest")
            contract[name] = value
        contract["waveform_cache_index_format_version"] = 1
    return contract


def variable_checkpoint_payload(
    *,
    run_id,
    epoch,
    model,
    optimizer,
    contract,
    history=(),
    runner_name=VARIABLE_TRAINING_RUNNER_NAME,
    lr_scheduler=None,
):
    """Return a new-format checkpoint payload; old checkpoints are incompatible."""

    _validate_contract(contract)
    bound = contract.get("model", {}).get("config", {}).get("control_initialization", LEGACY)
    if bound != getattr(model.config, "control_initialization", LEGACY):
        raise ValueError("Model and checkpoint control_initialization differ")
    return {
        "format_version": VARIABLE_TRAINING_RUN_FORMAT_VERSION,
        "runner_name": str(runner_name),
        "model_name": contract["model_name"],
        "run_id": str(run_id),
        "epoch": int(epoch),
        "model_state_dict": model.state_dict(),
        "optimizer_state_dict": optimizer.state_dict(),
        "lr_scheduler_state_dict": (
            lr_scheduler.state_dict() if lr_scheduler is not None else None
        ),
        "history": list(history),
        "contract": contract,
    }


def validate_variable_checkpoint(checkpoint, *, expected_contract=None, run_id=None, expected_runner_name=VARIABLE_TRAINING_RUNNER_NAME):
    if not isinstance(checkpoint, dict):
        raise ValueError("Variable checkpoint must be a mapping")
    if checkpoint.get("format_version") != VARIABLE_TRAINING_RUN_FORMAT_VERSION:
        raise ValueError("Unsupported variable training checkpoint format")
    if checkpoint.get("runner_name") != expected_runner_name:
        raise ValueError("Checkpoint runner differs from the variable runner")
    if run_id is not None and checkpoint.get("run_id") != str(run_id):
        raise ValueError("Checkpoint run ID differs from the requested contract")
    contract = checkpoint.get("contract")
    _validate_contract(contract)
    if checkpoint.get("model_name") != contract["model_name"]:
        raise ValueError("Checkpoint model name differs from its contract")
    if expected_contract is not None and contract != expected_contract:
        raise ValueError("Variable checkpoint contract differs from the requested resume contract")
    return checkpoint


def write_variable_run_manifest(manifest_path, *, run_id, contract, status, checkpoint_path):
    """Write a reproducible manifest for a new run; refuse to overwrite artifacts."""

    manifest_path = Path(manifest_path)
    checkpoint_path = Path(checkpoint_path)
    if manifest_path.exists():
        raise FileExistsError(f"Refusing to overwrite run manifest: {manifest_path}")
    if not checkpoint_path.is_file():
        raise FileNotFoundError(checkpoint_path)
    _validate_contract(contract)
    payload = {
        "format_version": VARIABLE_TRAINING_RUN_FORMAT_VERSION,
        "runner_name": VARIABLE_TRAINING_RUNNER_NAME,
        "run_id": str(run_id),
        "status": str(status),
        "contract": contract,
        "files": {
            "latest_checkpoint": {
                "path": checkpoint_path.relative_to(manifest_path.parent).as_posix(),
                "sha256": _sha256(checkpoint_path),
                "bytes": checkpoint_path.stat().st_size,
            }
        },
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return payload


def load_variable_checkpoint_for_resume(manifest_path, checkpoint_path, *, expected_contract, expected_runner_name=VARIABLE_TRAINING_RUNNER_NAME):
    """Verify the manifest hash and immutable v2 contract before loading state."""

    manifest_path = Path(manifest_path)
    checkpoint_path = Path(checkpoint_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("format_version") != VARIABLE_TRAINING_RUN_FORMAT_VERSION:
        raise ValueError("Unsupported variable training manifest format")
    record = manifest.get("files", {}).get("latest_checkpoint")
    if not record or _sha256(checkpoint_path) != record.get("sha256"):
        raise ValueError("Variable latest checkpoint hash differs from the run manifest")
    checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=True)
    return validate_variable_checkpoint(
        checkpoint,
        expected_contract=expected_contract,
        run_id=manifest.get("run_id"),
        expected_runner_name=expected_runner_name,
    )


def load_variable_checkpoint_for_initialization(manifest_path, checkpoint_path):
    """Load model weights only and return SHA provenance for a fresh optimizer run."""

    manifest_path = Path(manifest_path)
    checkpoint_path = Path(checkpoint_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("runner_name") != VARIABLE_TEMPORAL_TRAINING_RUNNER_NAME:
        raise ValueError("Initialization source is not a variable temporal run")
    checkpoint_sha256 = _sha256(checkpoint_path)
    records = tuple(
        value for value in manifest.get("files", {}).values()
        if isinstance(value, dict) and value.get("sha256")
    )
    if not any(record.get("sha256") == checkpoint_sha256 for record in records):
        raise ValueError("Initialization checkpoint hash is not bound by the source manifest")
    checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=True)
    validate_variable_checkpoint(
        checkpoint,
        expected_contract=manifest["contract"],
        run_id=manifest["run_id"],
        expected_runner_name=VARIABLE_TEMPORAL_TRAINING_RUNNER_NAME,
    )
    provenance = {
        "mode": "model_weights_only_optimizer_reset_v1",
        "source_run_id": str(manifest["run_id"]),
        "source_manifest_sha256": _sha256(manifest_path),
        "source_checkpoint_sha256": checkpoint_sha256,
        "source_dataset_manifest_sha256": checkpoint["contract"].get("dataset_manifest_sha256"),
        "optimizer_state_loaded": False,
        "scheduler_state_loaded": False,
    }
    return checkpoint, provenance


def _validate_temporal_batches(batches, supported_lengths, split):
    supported = {
        geometry_for_length(value).transition_length_bars
        for value in supported_lengths
    }
    for index, batch in enumerate(batches):
        if not isinstance(batch, dict):
            raise TypeError(f"{split} batch {index} must be a mapping")
        try:
            length = geometry_for_length(
                batch.get("transition_length_bars", -1)
            ).transition_length_bars
        except (TypeError, ValueError) as error:
            raise ValueError(
                f"{split} batch {index} has invalid transition length"
            ) from error
        if length not in supported:
            raise ValueError(f"{split} batch {index} has unsupported transition length")
        geometry = geometry_for_length(length)
        if int(batch.get("sequence_length", -1)) != geometry.sequence_length:
            raise ValueError(f"{split} batch {index} has inconsistent sequence_length")
        features = batch.get("features_a")
        if not isinstance(features, torch.Tensor) or features.ndim != 3:
            raise ValueError(f"{split} batch {index} lacks a feature batch")
        if features.shape[1] != geometry.sequence_length:
            raise ValueError(f"{split} batch {index} is not length-homogeneous")


def _run_temporal_epoch(model, batches, renderer, objective, optimizer, config, device):
    training = optimizer is not None
    model.train(training)
    totals_by_length = {}
    for batch in batches:
        batch = _move_temporal_batch(batch, device)
        if training:
            optimizer.zero_grad(set_to_none=True)
        result = variable_vocal_self_supervised_batch_loss(
            model,
            batch,
            renderer=renderer,
            objective=objective,
        )
        loss = result.terms["loss"]
        if not torch.isfinite(loss):
            raise FloatingPointError("Non-finite variable temporal loss")
        if training:
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), config.gradient_clip_norm, error_if_nonfinite=True)
            optimizer.step()
        length = str(batch["transition_length_bars"])
        bucket = totals_by_length.setdefault(length, {"count": 0, "terms": {}})
        count = int(batch["features_a"].shape[0])
        bucket["count"] += count
        for name, value in result.terms.items():
            scalar = float(value.detach().cpu())
            if not math.isfinite(scalar):
                raise FloatingPointError(f"Non-finite objective term: {name}")
            bucket["terms"][name] = bucket["terms"].get(name, 0.0) + scalar * count
    by_length = {
        length: {
            name: value / bucket["count"]
            for name, value in sorted(bucket["terms"].items())
        }
        for length, bucket in sorted(totals_by_length.items(), key=lambda item: int(item[0]))
    }
    if not by_length:
        raise ValueError("Temporal epoch has no batches")
    names = sorted({name for terms in by_length.values() for name in terms})
    overall = {
        name: sum(terms[name] for terms in by_length.values()) / len(by_length)
        for name in names
    }
    return {**overall, "by_length": by_length, "length_batch_counts": {key: int(value["count"]) for key, value in totals_by_length.items()}}


def _move_temporal_batch(batch, device):
    result = dict(batch)
    for name in ("features_a", "features_b", "global_features", "length_condition"):
        result[name] = batch[name].to(device=device, dtype=torch.float32)
    return result


def _flat_metrics(metrics):
    result = {
        name: value
        for name, value in metrics.items()
        if isinstance(value, (int, float))
    }
    for length, terms in metrics.get("by_length", {}).items():
        for name, value in terms.items():
            result[f"length_{length}/{name}"] = value
    return result


def _write_temporal_run_files(manifest_path, history_path, run_id, contract, history, latest_path, best_path, *, status):
    history_payload = {
        "format_version": VARIABLE_TRAINING_RUN_FORMAT_VERSION,
        "runner_name": VARIABLE_TEMPORAL_TRAINING_RUNNER_NAME,
        "run_id": run_id,
        "epochs": history,
    }
    _atomic_json_write(history_path, history_payload)
    payload = {
        "format_version": VARIABLE_TRAINING_RUN_FORMAT_VERSION,
        "runner_name": VARIABLE_TEMPORAL_TRAINING_RUNNER_NAME,
        "run_id": run_id,
        "status": str(status),
        "contract": contract,
        "last_epoch": int(history[-1]["epoch"]),
        "files": {
            "history": _file_record(history_path, manifest_path.parent),
            "latest_checkpoint": _file_record(latest_path, manifest_path.parent),
            "best_checkpoint": _file_record(best_path, manifest_path.parent),
        },
    }
    _atomic_json_write(manifest_path, payload)


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
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _file_record(path, relative_to):
    path = Path(path)
    if not path.is_file():
        return None
    return {"path": path.relative_to(relative_to).as_posix(), "sha256": _sha256(path), "bytes": path.stat().st_size}


def _canonical_json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _validate_contract(contract):
    if not isinstance(contract, dict):
        raise ValueError("Variable run contract is missing")
    required = (
        "dataset_format_version",
        "supported_lengths",
        "sequence_lengths",
        "length_conditioning",
        "model_name",
        "model_format_version",
    )
    if any(key not in contract for key in required):
        raise ValueError("Variable run contract is incomplete")
    if int(contract["dataset_format_version"]) != 2:
        raise ValueError("Variable runner requires Dataset Format 2")
    lengths = tuple(int(value) for value in contract["supported_lengths"])
    if not lengths or any(length not in SUPPORTED_VARIABLE_LENGTHS for length in lengths):
        raise ValueError("Variable run contract contains unsupported lengths")
    expected = {
        str(length): geometry_for_length(length).sequence_length for length in lengths
    }
    if contract["sequence_lengths"] != expected:
        raise ValueError("Variable run sequence lengths are inconsistent")
    conditioning = contract["length_conditioning"]
    if conditioning.get("version") != VARIABLE_LENGTH_CONDITIONING_VERSION:
        raise ValueError("Unsupported variable length-conditioning version")
    if conditioning.get("field") != "length_condition":
        raise ValueError("Variable run contract must name length_condition")


def _sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
