"""Command-line utilities for the feature-to-control ML baseline."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from pathlib import Path

from torch.utils.data import DataLoader

from src.bridge import DEFAULT_FEATURE_CACHE_ROOT
from src.features.vocal import DEFAULT_ROFORMER_MODEL, DEFAULT_VOCAL_BACKEND

from .data import (
    DEFAULT_BRIDGE_WAVEFORM_CACHE_ROOT,
    DEFAULT_TRAINING_SAMPLE_RATE,
    DEFAULT_VOCAL_BRIDGE_WAVEFORM_CACHE_ROOT,
    FeatureControlDataset,
    VocalFeatureControlDataset,
)
from .model import (
    TRANSITION_CONTROL_MODEL_NAME,
    TRANSITION_CONTROL_OUTPUT_NAMES,
    VOCAL_FEATURE_CONTROL_MODEL_NAME,
    FeatureControlMLP,
    FeatureControlMLPConfig,
    TCNBiLSTMTransitionControl,
    TCNBiLSTMTransitionControlConfig,
    VocalFeatureControlMLPConfig,
    VocalFeatureControlMLP,
)
from .runner import (
    ConstantRateTCNTrainingConfig,
    TCNBiLSTMTrainingConfig,
    TrainingConfig,
    run_feature_control_training,
)
from .runner import run_tcn_bilstm_transition_control_training
from .vocal_runner import VocalTrainingConfig, run_vocal_feature_control_training
from .variable_runner import (
    VariableTemporalTrainingConfig,
    run_variable_tcn_bilstm_training,
)
from .variable_control_initialization import VariableTCNBiLSTMControlConfig
from .control_initialization import EQUAL_POWER, LEGACY, run_initialization
from .variable_waveform_cache import (
    VARIABLE_WAVEFORM_CACHE_ROOT,
    VARIABLE_WAVEFORM_RENDER_SAMPLE_RATE,
    VARIABLE_WAVEFORM_SAMPLE_RATE,
    materialize_variable_waveform_cache,
)
from .wandb_logging import WandbConfig, load_sweep_parameters
from .cue_ranker_teacher import (
    TeacherLabelingConfig,
    label_cue_ranker_teacher,
    seal_teacher_release,
    verify_teacher_release,
)
from .cue_ranker_teacher_resolver import CueRankerCandidateResolver
from .cue_ranker_data import CueRankerGroupedDataset, collate_cue_ranker_groups
from .cue_ranker_runner import CueRankerTrainingConfig, train_cue_ranker


def _add_wandb_options(parser):
    parser.add_argument(
        "--wandb-mode",
        choices=("disabled", "offline", "online"),
        default=None,
        help="W&B mode; defaults to WANDB_MODE or disabled",
    )
    parser.add_argument(
        "--wandb-project",
        default=None,
        help="W&B project; defaults to WANDB_PROJECT or beatbridge",
    )
    parser.add_argument(
        "--wandb-entity",
        default=None,
        help="W&B entity/team; defaults to WANDB_ENTITY",
    )
    parser.add_argument(
        "--wandb-group",
        default=None,
        help="Optional W&B run group; defaults to WANDB_GROUP",
    )
    parser.add_argument("--wandb-name", default=None, help="Optional W&B run name")
    parser.add_argument("--wandb-tags", nargs="*", default=None, help="Optional W&B run tags")
    parser.add_argument(
        "--wandb-log-checkpoints",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Log checkpoints and local run files as a W&B artifact",
    )


def _wandb_config_from_args(args):
    environment = WandbConfig.from_environment(mode=args.wandb_mode)
    return WandbConfig(
        mode=environment.mode,
        project=args.wandb_project or environment.project,
        entity=args.wandb_entity or environment.entity,
        group=args.wandb_group or environment.group,
        name=args.wandb_name or environment.name,
        tags=tuple(args.wandb_tags) if args.wandb_tags is not None else environment.tags,
        log_checkpoints=(
            environment.log_checkpoints
            if args.wandb_log_checkpoints is None
            else args.wandb_log_checkpoints
        ),
    )


def _sweep_trial_directory(output_root, command):
    sweep_id = os.environ.get("WANDB_SWEEP_ID", "")
    sweep_run_id = os.environ.get("WANDB_RUN_ID", "")
    safe_id = re.compile(r"[A-Za-z0-9_-]+\Z")
    if not safe_id.fullmatch(sweep_id) or not safe_id.fullmatch(sweep_run_id):
        raise RuntimeError(
            f"{command} must run under a W&B agent with valid "
            "WANDB_SWEEP_ID and WANDB_RUN_ID values."
        )
    return Path(output_root).resolve() / sweep_id / sweep_run_id


def _validate_sweep_parameter_names(parameters, expected_parameters, command):
    missing_parameters = expected_parameters - set(parameters)
    unknown_parameters = set(parameters) - expected_parameters
    if missing_parameters or unknown_parameters:
        raise ValueError(
            f"W&B sweep config does not match {command}; "
            f"missing={sorted(missing_parameters)}, unknown={sorted(unknown_parameters)}"
        )


def build_argument_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    cache_parser = subparsers.add_parser("cache-waveforms")
    cache_parser.add_argument("dataset_directory")
    cache_parser.add_argument("--split", choices=("train", "validation", "test"), default="train")
    cache_parser.add_argument("--cache-root", default=str(DEFAULT_BRIDGE_WAVEFORM_CACHE_ROOT))
    cache_parser.add_argument("--training-sample-rate", type=int, default=DEFAULT_TRAINING_SAMPLE_RATE)
    cache_parser.add_argument("--limit", type=int)

    vocal_cache_parser = subparsers.add_parser("cache-vocal-waveforms")
    vocal_cache_parser.add_argument("dataset_directory")
    vocal_cache_parser.add_argument(
        "--split",
        choices=("train", "validation", "test"),
        default="train",
    )
    vocal_cache_parser.add_argument(
        "--cache-root",
        default=str(DEFAULT_VOCAL_BRIDGE_WAVEFORM_CACHE_ROOT),
    )
    vocal_cache_parser.add_argument(
        "--training-sample-rate",
        type=int,
        default=DEFAULT_TRAINING_SAMPLE_RATE,
    )
    vocal_cache_parser.add_argument("--limit", type=int)

    subparsers.add_parser("model-info")
    subparsers.add_parser("model-info-vocal")
    subparsers.add_parser("model-info-tcn-bilstm")
    train_parser = subparsers.add_parser("train")
    train_parser.add_argument("dataset_directory")
    train_parser.add_argument("output_directory")
    train_parser.add_argument("--cache-root", default=str(DEFAULT_BRIDGE_WAVEFORM_CACHE_ROOT))
    train_parser.add_argument("--seed", type=int, default=TrainingConfig.seed)
    train_parser.add_argument("--max-epochs", type=int, default=TrainingConfig.max_epochs)
    train_parser.add_argument("--batch-size", type=int, default=TrainingConfig.batch_size)
    train_parser.add_argument("--learning-rate", type=float, default=TrainingConfig.learning_rate)
    train_parser.add_argument("--weight-decay", type=float, default=TrainingConfig.weight_decay)
    train_parser.add_argument("--patience", type=int, default=TrainingConfig.patience)
    train_parser.add_argument("--min-delta", type=float, default=TrainingConfig.min_delta)
    train_parser.add_argument("--gradient-clip-norm", type=float, default=TrainingConfig.gradient_clip_norm)
    train_parser.add_argument("--training-sample-rate", type=int, default=DEFAULT_TRAINING_SAMPLE_RATE)
    train_parser.add_argument(
        "--device",
        default=TrainingConfig.device,
        help="PyTorch device: auto (CUDA if available), cpu, cuda, or cuda:<index>",
    )
    train_parser.add_argument("--resume", action="store_true")
    _add_wandb_options(train_parser)

    tcn_train_parser = subparsers.add_parser("train-tcn-bilstm")
    tcn_train_parser.add_argument("dataset_directory")
    tcn_train_parser.add_argument("output_directory")
    tcn_train_parser.add_argument(
        "--cache-root", default=str(DEFAULT_BRIDGE_WAVEFORM_CACHE_ROOT)
    )
    tcn_train_parser.add_argument("--seed", type=int, default=TCNBiLSTMTrainingConfig.seed)
    tcn_train_parser.add_argument(
        "--max-epochs", type=int, default=TCNBiLSTMTrainingConfig.max_epochs
    )
    tcn_train_parser.add_argument(
        "--batch-size", type=int, default=TCNBiLSTMTrainingConfig.batch_size
    )
    tcn_train_parser.add_argument(
        "--learning-rate", type=float, default=TCNBiLSTMTrainingConfig.learning_rate
    )
    tcn_train_parser.add_argument(
        "--weight-decay", type=float, default=TCNBiLSTMTrainingConfig.weight_decay
    )
    tcn_train_parser.add_argument("--patience", type=int, default=TCNBiLSTMTrainingConfig.patience)
    tcn_train_parser.add_argument("--min-delta", type=float, default=TCNBiLSTMTrainingConfig.min_delta)
    tcn_train_parser.add_argument(
        "--gradient-clip-norm",
        type=float,
        default=TCNBiLSTMTrainingConfig.gradient_clip_norm,
    )
    tcn_train_parser.add_argument(
        "--training-sample-rate",
        type=int,
        default=DEFAULT_TRAINING_SAMPLE_RATE,
    )
    tcn_train_parser.add_argument(
        "--device",
        default=TCNBiLSTMTrainingConfig.device,
        help="PyTorch device: auto (CUDA if available), cpu, cuda, or cuda:<index>",
    )
    tcn_train_parser.add_argument("--resume", action="store_true")
    tcn_train_parser.add_argument(
        "--constant-learning-rate", action="store_true",
        help="Use the fixed AdamW rate of the September reference, without warmup or scheduler.",
    )
    _add_wandb_options(tcn_train_parser)

    variable_cache_parser = subparsers.add_parser("cache-variable-waveforms")
    variable_cache_parser.add_argument("dataset_directory")
    variable_cache_parser.add_argument("--cache-root", default=str(VARIABLE_WAVEFORM_CACHE_ROOT))
    variable_cache_parser.add_argument("--feature-cache-root", default=None)
    variable_cache_parser.add_argument("--transition-bars", nargs="+", type=int, default=[2, 4, 6, 8])
    variable_cache_parser.add_argument("--limit", type=int, help="Maximum examples per split and length")
    variable_cache_parser.add_argument("--training-sample-rate", type=int, default=VARIABLE_WAVEFORM_SAMPLE_RATE)
    variable_cache_parser.add_argument("--render-sample-rate", type=int, default=VARIABLE_WAVEFORM_RENDER_SAMPLE_RATE)
    variable_cache_parser.add_argument("--rounding-tolerance-samples", type=int, default=2)

    variable_train_parser = subparsers.add_parser("train-variable-tcn-bilstm")
    variable_train_parser.add_argument("dataset_directory")
    variable_train_parser.add_argument("output_directory")
    variable_train_parser.add_argument("--cache-root", default=str(VARIABLE_WAVEFORM_CACHE_ROOT))
    variable_train_parser.add_argument("--transition-bars", nargs="+", type=int, default=[2, 4, 6, 8])
    variable_train_parser.add_argument("--seed", type=int, default=VariableTemporalTrainingConfig().seed)
    variable_train_parser.add_argument("--max-epochs", type=int, default=VariableTemporalTrainingConfig().max_epochs)
    variable_train_parser.add_argument("--batch-size", type=int, default=4)
    variable_train_parser.add_argument("--learning-rate", type=float, default=VariableTemporalTrainingConfig().learning_rate)
    variable_train_parser.add_argument("--weight-decay", type=float, default=VariableTemporalTrainingConfig().weight_decay)
    variable_train_parser.add_argument("--patience", type=int, default=VariableTemporalTrainingConfig().patience)
    variable_train_parser.add_argument("--min-delta", type=float, default=VariableTemporalTrainingConfig().min_delta)
    variable_train_parser.add_argument("--gradient-clip-norm", type=float, default=VariableTemporalTrainingConfig().gradient_clip_norm)
    variable_train_parser.add_argument("--training-sample-rate", type=int, default=VARIABLE_WAVEFORM_SAMPLE_RATE)
    variable_train_parser.add_argument("--device", default=VariableTemporalTrainingConfig().device)
    variable_train_parser.add_argument("--resume", action="store_true")
    variable_train_parser.add_argument("--initialize-from-manifest")
    variable_train_parser.add_argument("--initialize-from-checkpoint")
    _add_wandb_options(variable_train_parser)

    teacher_seal_parser = subparsers.add_parser(
        "seal-cue-ranker-teacher",
        help="Seal the explicitly supplied completed Variable-TCN run for offline Cue-Ranker labels",
    )
    teacher_seal_parser.add_argument("teacher_run_directory")
    teacher_seal_parser.add_argument("release_path")
    teacher_seal_parser.add_argument("--normalizer", required=True, help="Training-only normalizer JSON")
    teacher_seal_parser.add_argument("--backend-provenance", required=True, help="JSON file with the Rubber-Band backend/executable SHA")
    teacher_seal_parser.add_argument("--device", default="cpu")
    teacher_seal_parser.add_argument("--gpu-tolerance", type=float, default=None)

    teacher_label_parser = subparsers.add_parser(
        "label-cue-ranker-teacher",
        help="Resolve and label only sealed train/validation Candidate-v2 rows",
    )
    teacher_label_parser.add_argument("universe_directory")
    teacher_label_parser.add_argument("teacher_release")
    teacher_label_parser.add_argument("output_directory")
    teacher_label_parser.add_argument("--split-map", required=True)
    teacher_label_parser.add_argument("--resume", action="store_true")
    teacher_label_parser.add_argument("--analysis-root", default=None)
    teacher_label_parser.add_argument("--feature-cache-root", default=None)
    teacher_label_parser.add_argument("--waveform-cache-root", default=None)
    teacher_label_parser.add_argument("--vocal-backend", choices=("demucs", "roformer"), default=DEFAULT_VOCAL_BACKEND)
    teacher_label_parser.add_argument("--vocal-model", default=DEFAULT_ROFORMER_MODEL)
    teacher_label_parser.add_argument("--guard-threshold", type=float, default=0.50)
    teacher_label_parser.add_argument("--max-candidates", type=int, default=None)
    teacher_label_parser.add_argument("--max-technical-failures", type=int, default=None)
    teacher_label_parser.add_argument("--max-technical-failure-rate", type=float, default=None)

    cue_ranker_train_parser = subparsers.add_parser(
        "train-cue-ranker",
        help="Train learned_cue_ranker_v1 from sealed Format-3 train/validation shards only.",
    )
    cue_ranker_train_parser.add_argument("dataset_directory")
    cue_ranker_train_parser.add_argument("output_directory")
    cue_ranker_train_parser.add_argument("--feature-cache-root", default=str(DEFAULT_FEATURE_CACHE_ROOT))
    cue_ranker_train_parser.add_argument("--seed", type=int, default=CueRankerTrainingConfig.seed)
    cue_ranker_train_parser.add_argument("--max-epochs", type=int, default=CueRankerTrainingConfig.max_epochs)
    cue_ranker_train_parser.add_argument("--batch-size", type=int, default=1)
    cue_ranker_train_parser.add_argument("--learning-rate", type=float, default=CueRankerTrainingConfig.learning_rate)
    cue_ranker_train_parser.add_argument("--weight-decay", type=float, default=CueRankerTrainingConfig.weight_decay)
    cue_ranker_train_parser.add_argument("--patience", type=int, default=CueRankerTrainingConfig.patience)
    cue_ranker_train_parser.add_argument("--min-delta", type=float, default=CueRankerTrainingConfig.min_delta)
    cue_ranker_train_parser.add_argument("--gradient-clip-norm", type=float, default=CueRankerTrainingConfig.gradient_clip_norm)
    cue_ranker_train_parser.add_argument("--device", default=CueRankerTrainingConfig.device)
    cue_ranker_train_parser.add_argument("--resume", action="store_true")
    _add_wandb_options(cue_ranker_train_parser)

    vocal_train_parser = subparsers.add_parser("train-vocal")
    vocal_train_parser.add_argument("dataset_directory")
    vocal_train_parser.add_argument("output_directory")
    vocal_train_parser.add_argument(
        "--cache-root",
        default=str(DEFAULT_VOCAL_BRIDGE_WAVEFORM_CACHE_ROOT),
    )
    vocal_train_parser.add_argument(
        "--feature-cache-root",
        default=str(DEFAULT_FEATURE_CACHE_ROOT),
    )
    vocal_train_parser.add_argument("--vocal-model", default=DEFAULT_ROFORMER_MODEL)
    vocal_train_parser.add_argument("--seed", type=int, default=VocalTrainingConfig.seed)
    vocal_train_parser.add_argument(
        "--hidden-dimensions",
        nargs="+",
        type=int,
        default=list(VocalFeatureControlMLPConfig().hidden_dimensions),
    )
    vocal_train_parser.add_argument(
        "--dropout", type=float, default=VocalFeatureControlMLPConfig().dropout
    )
    vocal_train_parser.add_argument(
        "--maximum-vocal-ducking",
        type=float,
        default=VocalFeatureControlMLPConfig().maximum_vocal_ducking,
    )
    vocal_train_parser.add_argument(
        "--initial-vocal-duck-logit",
        type=float,
        default=VocalFeatureControlMLPConfig().initial_vocal_duck_logit,
    )
    vocal_train_parser.add_argument(
        "--optimizer", choices=("adam", "adamw"), default=VocalTrainingConfig.optimizer
    )
    vocal_train_parser.add_argument(
        "--max-epochs",
        type=int,
        default=VocalTrainingConfig.max_epochs,
    )
    vocal_train_parser.add_argument(
        "--batch-size",
        type=int,
        default=VocalTrainingConfig.batch_size,
    )
    vocal_train_parser.add_argument(
        "--learning-rate",
        type=float,
        default=VocalTrainingConfig.learning_rate,
    )
    vocal_train_parser.add_argument(
        "--weight-decay",
        type=float,
        default=VocalTrainingConfig.weight_decay,
    )
    vocal_train_parser.add_argument(
        "--adam-beta1", type=float, default=VocalTrainingConfig.adam_beta1
    )
    vocal_train_parser.add_argument(
        "--adam-beta2", type=float, default=VocalTrainingConfig.adam_beta2
    )
    vocal_train_parser.add_argument(
        "--adam-epsilon", type=float, default=VocalTrainingConfig.adam_epsilon
    )
    vocal_train_parser.add_argument(
        "--lr-scheduler",
        choices=("none", "reduce_on_plateau", "cosine"),
        default=VocalTrainingConfig.lr_scheduler,
    )
    vocal_train_parser.add_argument(
        "--scheduler-factor", type=float, default=VocalTrainingConfig.scheduler_factor
    )
    vocal_train_parser.add_argument(
        "--scheduler-patience", type=int, default=VocalTrainingConfig.scheduler_patience
    )
    vocal_train_parser.add_argument(
        "--scheduler-threshold", type=float, default=VocalTrainingConfig.scheduler_threshold
    )
    vocal_train_parser.add_argument(
        "--scheduler-cooldown", type=int, default=VocalTrainingConfig.scheduler_cooldown
    )
    vocal_train_parser.add_argument(
        "--scheduler-min-lr", type=float, default=VocalTrainingConfig.scheduler_min_lr
    )
    vocal_train_parser.add_argument(
        "--patience",
        type=int,
        default=VocalTrainingConfig.patience,
    )
    vocal_train_parser.add_argument(
        "--min-delta",
        type=float,
        default=VocalTrainingConfig.min_delta,
    )
    vocal_train_parser.add_argument(
        "--gradient-clip-norm",
        type=float,
        default=VocalTrainingConfig.gradient_clip_norm,
    )
    vocal_train_parser.add_argument(
        "--training-sample-rate",
        type=int,
        default=DEFAULT_TRAINING_SAMPLE_RATE,
    )
    vocal_train_parser.add_argument(
        "--device",
        default=VocalTrainingConfig.device,
        help="PyTorch device: auto (CUDA if available), cpu, cuda, or cuda:<index>",
    )
    vocal_train_parser.add_argument("--resume", action="store_true")
    _add_wandb_options(vocal_train_parser)
    for command in (train_parser, vocal_train_parser, tcn_train_parser, variable_train_parser):
        command.add_argument("--control-initialization", choices=(EQUAL_POWER, LEGACY),
                             help="Fresh runs default to equal_power_v1; resume inherits its bound contract.")

    vocal_sweep_parser = subparsers.add_parser(
        "sweep-vocal",
        help="Run one vocal-aware training trial assigned by a W&B sweep agent.",
    )
    vocal_sweep_parser.add_argument("dataset_directory")
    vocal_sweep_parser.add_argument("output_root")
    vocal_sweep_parser.add_argument(
        "--cache-root", default=str(DEFAULT_VOCAL_BRIDGE_WAVEFORM_CACHE_ROOT)
    )
    vocal_sweep_parser.add_argument(
        "--feature-cache-root", default=str(DEFAULT_FEATURE_CACHE_ROOT)
    )
    vocal_sweep_parser.add_argument("--vocal-model", default=DEFAULT_ROFORMER_MODEL)
    vocal_sweep_parser.add_argument("--device", default=VocalTrainingConfig.device)
    vocal_sweep_parser.add_argument("--wandb-project", default="beatbridge")
    vocal_sweep_parser.add_argument(
        "--wandb-log-checkpoints",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Upload model checkpoints as W&B artifacts for every sweep trial.",
    )

    tcn_sweep_parser = subparsers.add_parser(
        "sweep-tcn-bilstm",
        help="Run one fixed-length TCN/BiLSTM training trial assigned by a W&B sweep agent.",
    )
    tcn_sweep_parser.add_argument("dataset_directory")
    tcn_sweep_parser.add_argument("output_root")
    tcn_sweep_parser.add_argument(
        "--cache-root", default=str(DEFAULT_BRIDGE_WAVEFORM_CACHE_ROOT)
    )
    tcn_sweep_parser.add_argument("--device", default=TrainingConfig.device)
    tcn_sweep_parser.add_argument("--wandb-project", default="beatbridge")
    tcn_sweep_parser.add_argument(
        "--save-checkpoints",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Save best/latest checkpoints locally for each fixed-length TCN sweep trial.",
    )
    tcn_sweep_parser.add_argument(
        "--wandb-log-checkpoints",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Upload model checkpoints as W&B artifacts for every sweep trial.",
    )

    variable_tcn_sweep_parser = subparsers.add_parser(
        "sweep-variable-tcn-bilstm",
        help="Run one variable-length TCN/BiLSTM trial assigned by a W&B sweep agent.",
    )
    variable_tcn_sweep_parser.add_argument("dataset_directory")
    variable_tcn_sweep_parser.add_argument("output_root")
    variable_tcn_sweep_parser.add_argument(
        "--cache-root", default=str(VARIABLE_WAVEFORM_CACHE_ROOT)
    )
    variable_tcn_sweep_parser.add_argument(
        "--transition-bars", nargs="+", type=int, default=[2, 4, 6, 8]
    )
    variable_tcn_sweep_parser.add_argument(
        "--device", default=VariableTemporalTrainingConfig().device
    )
    variable_tcn_sweep_parser.add_argument("--wandb-project", default="beatbridge")
    variable_tcn_sweep_parser.add_argument(
        "--wandb-log-checkpoints",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Upload model checkpoints as W&B artifacts for every sweep trial.",
    )
    return parser


def main():
    args = build_argument_parser().parse_args()
    if hasattr(args, "control_initialization"):
        control_initialization = run_initialization(
            args.output_directory, args.resume, args.control_initialization,
            getattr(args, "initialize_from_manifest", None),
        )
    if args.command == "model-info":
        model = FeatureControlMLP()
        print(
            json.dumps(
                {
                    "model_name": "time_shared_mlp_v1",
                    "parameter_count": model.parameter_count,
                    "config": model.config.to_dict(),
                },
                indent=2,
            )
        )
        return 0

    if args.command == "seal-cue-ranker-teacher":
        run_directory = Path(args.teacher_run_directory)
        manifest_path = run_directory / "manifest.json"
        if not manifest_path.is_file():
            raise FileNotFoundError(f"Teacher run manifest does not exist: {manifest_path}")
        run_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        best = run_manifest.get("files", {}).get("best_checkpoint", {})
        checkpoint_path = Path(best.get("path", ""))
        if not checkpoint_path.is_absolute():
            checkpoint_path = run_directory / checkpoint_path
        backend = json.loads(Path(args.backend_provenance).read_text(encoding="utf-8"))
        release = seal_teacher_release(
            manifest_path,
            checkpoint_path,
            args.release_path,
            normalizer_path=args.normalizer,
            backend_provenance=backend,
            device=args.device,
            gpu_tolerance=args.gpu_tolerance,
        )
        print(json.dumps({"release_path": str(release)}, indent=2))
        return 0

    if args.command == "label-cue-ranker-teacher":
        release, release_sha = verify_teacher_release(args.teacher_release)
        resolver_kwargs = {"vocal_backend": args.vocal_backend, "vocal_model": args.vocal_model}
        if args.analysis_root is not None: resolver_kwargs["analysis_root"] = args.analysis_root
        if args.feature_cache_root is not None: resolver_kwargs["feature_cache_root"] = args.feature_cache_root
        if args.waveform_cache_root is not None: resolver_kwargs["waveform_cache_root"] = args.waveform_cache_root
        config = TeacherLabelingConfig(
            guard_threshold=args.guard_threshold,
            max_candidates=args.max_candidates,
            max_technical_failures=args.max_technical_failures,
            max_technical_failure_rate=args.max_technical_failure_rate,
        )
        result = label_cue_ranker_teacher(
            args.universe_directory,
            args.teacher_release,
            args.output_directory,
            split_map=args.split_map,
            resume=args.resume,
            config=config,
            resolver=CueRankerCandidateResolver(release, release_sha, **resolver_kwargs),
        )
        print(json.dumps({"output_directory": str(result.output_directory), "counts": result.counts, "cache_hits": result.cache_hits, "cache_misses": result.cache_misses}, indent=2))
        return 0

    if args.command == "train-cue-ranker":
        if args.batch_size < 1:
            raise ValueError("--batch-size must be at least one")
        dataset_directory = Path(args.dataset_directory)
        manifest_path = dataset_directory / "manifest.json"
        if not manifest_path.is_file():
            raise FileNotFoundError(f"Cue-Ranker dataset manifest does not exist: {manifest_path}")
        dataset_sha = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
        # Construction is intentionally explicit and has no test argument or
        # default: Format 3 exposes exactly these two sealed splits.
        train_dataset = CueRankerGroupedDataset(dataset_directory, "train", feature_cache_root=args.feature_cache_root)
        validation_dataset = CueRankerGroupedDataset(dataset_directory, "validation", feature_cache_root=args.feature_cache_root)
        train_loader = DataLoader(train_dataset, batch_size=args.batch_size, shuffle=False, collate_fn=collate_cue_ranker_groups)
        validation_loader = DataLoader(validation_dataset, batch_size=args.batch_size, shuffle=False, collate_fn=collate_cue_ranker_groups)
        config = CueRankerTrainingConfig(
            seed=args.seed, max_epochs=args.max_epochs, learning_rate=args.learning_rate,
            weight_decay=args.weight_decay, patience=args.patience, min_delta=args.min_delta,
            gradient_clip_norm=args.gradient_clip_norm, device=args.device,
        )
        result = train_cue_ranker(train_loader, validation_loader, args.output_directory, dataset_manifest_sha256=dataset_sha, config=config, resume=args.resume, wandb_config=_wandb_config_from_args(args))
        print(json.dumps({"output_directory": str(result.output_directory), "status": result.status, "last_epoch": result.last_epoch, "best_epoch": result.best_epoch, "best_validation_loss": result.best_validation_loss}, indent=2))
        return 0

    if args.command == "model-info-vocal":
        model = VocalFeatureControlMLP()
        print(
            json.dumps(
                {
                    "model_name": VOCAL_FEATURE_CONTROL_MODEL_NAME,
                    "parameter_count": model.parameter_count,
                    "config": model.config.to_dict(),
                    "outputs": [
                        "mix_position",
                        "low_end_position",
                        "vocal_position",
                        "vocal_duck_a",
                        "vocal_duck_b",
                        "vocal_gain_a",
                        "vocal_gain_b",
                    ],
                },
                indent=2,
            )
        )
        return 0

    if args.command == "model-info-tcn-bilstm":
        model = TCNBiLSTMTransitionControl()
        print(
            json.dumps(
                {
                    "model_name": TRANSITION_CONTROL_MODEL_NAME,
                    "parameter_count": model.parameter_count,
                    "config": model.config.to_dict(),
                    "outputs": list(TRANSITION_CONTROL_OUTPUT_NAMES),
                },
                indent=2,
            )
        )
        return 0

    if args.command == "train":
        config = TrainingConfig(
            seed=args.seed,
            max_epochs=args.max_epochs,
            batch_size=args.batch_size,
            learning_rate=args.learning_rate,
            weight_decay=args.weight_decay,
            patience=args.patience,
            min_delta=args.min_delta,
            gradient_clip_norm=args.gradient_clip_norm,
            training_sample_rate=args.training_sample_rate,
            device=args.device,
        )
        result = run_feature_control_training(
            args.dataset_directory,
            args.output_directory,
            model_config=FeatureControlMLPConfig(control_initialization=control_initialization),
            config=config,
            waveform_cache_root=args.cache_root,
            resume=args.resume,
            wandb_config=_wandb_config_from_args(args),
        )
        print(json.dumps({
            "output_directory": str(result.output_directory),
            "status": result.status,
            "last_epoch": result.last_epoch,
            "best_epoch": result.best_epoch,
            "best_validation_loss": result.best_validation_loss,
        }, indent=2))
        return 0

    if args.command == "train-tcn-bilstm":
        config_class = ConstantRateTCNTrainingConfig if args.constant_learning_rate else TCNBiLSTMTrainingConfig
        config = config_class(
            seed=args.seed,
            max_epochs=args.max_epochs,
            batch_size=args.batch_size,
            learning_rate=args.learning_rate,
            weight_decay=args.weight_decay,
            patience=args.patience,
            min_delta=args.min_delta,
            gradient_clip_norm=args.gradient_clip_norm,
            training_sample_rate=args.training_sample_rate,
            device=args.device,
        )
        result = run_tcn_bilstm_transition_control_training(
            args.dataset_directory,
            args.output_directory,
            model_config=TCNBiLSTMTransitionControlConfig(control_initialization=control_initialization),
            config=config,
            waveform_cache_root=args.cache_root,
            resume=args.resume,
            wandb_config=_wandb_config_from_args(args),
        )
        print(json.dumps({
            "output_directory": str(result.output_directory),
            "status": result.status,
            "last_epoch": result.last_epoch,
            "best_epoch": result.best_epoch,
            "best_validation_loss": result.best_validation_loss,
        }, indent=2))
        return 0

    if args.command == "cache-variable-waveforms":
        report = materialize_variable_waveform_cache(
            args.dataset_directory,
            cache_root=args.cache_root,
            feature_cache_root=args.feature_cache_root,
            transition_lengths=args.transition_bars,
            limit=args.limit,
            training_sample_rate=args.training_sample_rate,
            render_sample_rate=args.render_sample_rate,
            rounding_tolerance_samples=args.rounding_tolerance_samples,
        )
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    if args.command == "train-variable-tcn-bilstm":
        config = VariableTemporalTrainingConfig(
            seed=args.seed,
            max_epochs=args.max_epochs,
            learning_rate=args.learning_rate,
            weight_decay=args.weight_decay,
            patience=args.patience,
            min_delta=args.min_delta,
            gradient_clip_norm=args.gradient_clip_norm,
            training_sample_rate=args.training_sample_rate,
            device=args.device,
        )
        result = run_variable_tcn_bilstm_training(
            args.dataset_directory,
            args.output_directory,
            model_config=VariableTCNBiLSTMControlConfig(control_initialization=control_initialization),
            config=config,
            waveform_cache_root=args.cache_root,
            transition_lengths=args.transition_bars,
            batch_size=args.batch_size,
            resume=args.resume,
            initialize_from_manifest=args.initialize_from_manifest,
            initialize_from_checkpoint=args.initialize_from_checkpoint,
            wandb_config=_wandb_config_from_args(args),
        )
        print(json.dumps({
            "output_directory": str(result["output_directory"]),
            "status": result["status"],
            "last_epoch": result["last_epoch"],
            "best_epoch": result["best_epoch"],
            "best_validation_loss": result["best_validation_loss"],
            "cache_hits": result["cache_hits"],
        }, indent=2))
        return 0

    if args.command == "train-vocal":
        config = VocalTrainingConfig(
            seed=args.seed,
            max_epochs=args.max_epochs,
            batch_size=args.batch_size,
            optimizer=args.optimizer,
            learning_rate=args.learning_rate,
            weight_decay=args.weight_decay,
            adam_beta1=args.adam_beta1,
            adam_beta2=args.adam_beta2,
            adam_epsilon=args.adam_epsilon,
            lr_scheduler=args.lr_scheduler,
            scheduler_factor=args.scheduler_factor,
            scheduler_patience=args.scheduler_patience,
            scheduler_threshold=args.scheduler_threshold,
            scheduler_cooldown=args.scheduler_cooldown,
            scheduler_min_lr=args.scheduler_min_lr,
            patience=args.patience,
            min_delta=args.min_delta,
            gradient_clip_norm=args.gradient_clip_norm,
            training_sample_rate=args.training_sample_rate,
            device=args.device,
        )
        model_config = VocalFeatureControlMLPConfig(
            control_initialization=control_initialization,
            hidden_dimensions=tuple(args.hidden_dimensions),
            dropout=args.dropout,
            maximum_vocal_ducking=args.maximum_vocal_ducking,
            initial_vocal_duck_logit=args.initial_vocal_duck_logit,
        )
        result = run_vocal_feature_control_training(
            args.dataset_directory,
            args.output_directory,
            config=config,
            model_config=model_config,
            waveform_cache_root=args.cache_root,
            feature_cache_root=args.feature_cache_root,
            vocal_model=args.vocal_model,
            resume=args.resume,
            wandb_config=_wandb_config_from_args(args),
        )
        print(json.dumps({
            "output_directory": str(result.output_directory),
            "status": result.status,
            "last_epoch": result.last_epoch,
            "best_epoch": result.best_epoch,
            "best_validation_loss": result.best_validation_loss,
        }, indent=2))
        return 0

    if args.command == "sweep-vocal":
        sweep_id = os.environ.get("WANDB_SWEEP_ID", "")
        sweep_run_id = os.environ.get("WANDB_RUN_ID", "")
        safe_id = re.compile(r"[A-Za-z0-9_-]+\Z")
        if not safe_id.fullmatch(sweep_id) or not safe_id.fullmatch(sweep_run_id):
            raise RuntimeError(
                "sweep-vocal must run under a W&B agent with valid "
                "WANDB_SWEEP_ID and WANDB_RUN_ID values."
            )

        parameters = dict(load_sweep_parameters())
        requested = parameters.pop("control_initialization", None)
        training_fields = set(VocalTrainingConfig.__dataclass_fields__) - {
            "device",
            "training_sample_rate",
            "lowpass_cutoff_hz",
            "lowpass_kernel_size",
        }
        model_fields = {
            "hidden_dimensions",
            "dropout",
            "maximum_vocal_ducking",
            "initial_vocal_duck_logit",
        }
        expected_parameters = training_fields | model_fields
        missing_parameters = expected_parameters - set(parameters)
        unknown_parameters = set(parameters) - expected_parameters
        if missing_parameters or unknown_parameters:
            raise ValueError(
                "W&B sweep config does not match the vocal runner; "
                f"missing={sorted(missing_parameters)}, unknown={sorted(unknown_parameters)}"
            )

        training_parameters = {
            name: value for name, value in parameters.items() if name in training_fields
        }
        training_parameters["device"] = args.device
        config = VocalTrainingConfig(**training_parameters)
        model_parameters = {
            name: value for name, value in parameters.items() if name in model_fields
        }
        model_parameters["hidden_dimensions"] = tuple(
            model_parameters["hidden_dimensions"]
        )
        output_directory = (
            Path(args.output_root).resolve() / sweep_id / sweep_run_id
        )
        mode = run_initialization(output_directory, output_directory.exists(), requested)
        model_config = VocalFeatureControlMLPConfig(**model_parameters, control_initialization=mode)
        result = run_vocal_feature_control_training(
            args.dataset_directory,
            output_directory,
            config=config,
            model_config=model_config,
            waveform_cache_root=args.cache_root,
            feature_cache_root=args.feature_cache_root,
            vocal_model=args.vocal_model,
            resume=output_directory.exists(),
            wandb_config=WandbConfig(
                mode="online",
                project=args.wandb_project,
                tags=("sweep", "vocal_time_shared_mlp_v2"),
                log_checkpoints=args.wandb_log_checkpoints,
            ),
        )
        print(json.dumps({
            "output_directory": str(result.output_directory),
            "status": result.status,
            "last_epoch": result.last_epoch,
            "best_epoch": result.best_epoch,
            "best_validation_loss": result.best_validation_loss,
        }, indent=2))
        return 0

    if args.command == "sweep-tcn-bilstm":
        parameters = dict(load_sweep_parameters())
        parameters.setdefault("control_initialization", EQUAL_POWER)
        training_fields = set(TCNBiLSTMTrainingConfig.__dataclass_fields__) - {
            "device",
            "training_sample_rate",
            "lowpass_cutoff_hz",
            "lowpass_kernel_size",
            "patience",
            "min_delta",
        }
        model_fields = set(TCNBiLSTMTransitionControlConfig.__dataclass_fields__)
        _validate_sweep_parameter_names(
            parameters, training_fields | model_fields, args.command
        )
        training_parameters = {
            name: value for name, value in parameters.items() if name in training_fields
        }
        training_parameters["patience"] = int(parameters["max_epochs"]) + 1
        training_parameters["min_delta"] = 0.0
        training_parameters["device"] = args.device
        config = TCNBiLSTMTrainingConfig(**training_parameters)
        model_parameters = {
            name: value for name, value in parameters.items() if name in model_fields
        }
        model_parameters["encoder_channels"] = tuple(
            model_parameters["encoder_channels"]
        )
        model_config = TCNBiLSTMTransitionControlConfig(**model_parameters)
        output_directory = _sweep_trial_directory(args.output_root, args.command)
        result = run_tcn_bilstm_transition_control_training(
            args.dataset_directory,
            output_directory,
            config=config,
            model_config=model_config,
            waveform_cache_root=args.cache_root,
            resume=False,
            save_checkpoints=args.save_checkpoints,
            wandb_config=WandbConfig(
                mode="online",
                project=args.wandb_project,
                tags=("sweep", "tcn_bilstm_transition_control_v1", "dataset_format_v1"),
                log_checkpoints=args.wandb_log_checkpoints,
            ),
        )
        print(json.dumps({
            "output_directory": str(result.output_directory),
            "status": result.status,
            "last_epoch": result.last_epoch,
            "best_epoch": result.best_epoch,
            "best_validation_loss": result.best_validation_loss,
        }, indent=2))
        return 0

    if args.command == "sweep-variable-tcn-bilstm":
        parameters = dict(load_sweep_parameters())
        parameters.setdefault("control_initialization", EQUAL_POWER)
        default_training_config = VariableTemporalTrainingConfig()
        training_fields = set(default_training_config.to_dict()) - {
            "device",
            "training_sample_rate",
            "lowpass_cutoff_hz",
            "lowpass_kernel_size",
            "patience",
            "min_delta",
        }
        model_fields = set(VariableTCNBiLSTMControlConfig.__dataclass_fields__)
        _validate_sweep_parameter_names(
            parameters, training_fields | model_fields | {"batch_size"}, args.command
        )
        training_parameters = {
            name: value for name, value in parameters.items() if name in training_fields
        }
        training_parameters["patience"] = int(parameters["max_epochs"]) + 1
        training_parameters["min_delta"] = 0.0
        training_parameters["device"] = args.device
        config = VariableTemporalTrainingConfig(**training_parameters)
        model_parameters = {
            name: value for name, value in parameters.items() if name in model_fields
        }
        model_parameters["encoder_channels"] = tuple(
            model_parameters["encoder_channels"]
        )
        model_config = VariableTCNBiLSTMControlConfig(**model_parameters)
        output_directory = _sweep_trial_directory(args.output_root, args.command)
        result = run_variable_tcn_bilstm_training(
            args.dataset_directory,
            output_directory,
            config=config,
            waveform_cache_root=args.cache_root,
            transition_lengths=args.transition_bars,
            batch_size=int(parameters["batch_size"]),
            model_config=model_config,
            resume=False,
            save_checkpoints=False,
            wandb_config=WandbConfig(
                mode="online",
                project=args.wandb_project,
                tags=(
                    "sweep",
                    "variable_tcn_bilstm_transition_control_v1",
                    "dataset_format_v2",
                ),
                log_checkpoints=args.wandb_log_checkpoints,
            ),
        )
        print(json.dumps({
            "output_directory": str(result["output_directory"]),
            "status": result["status"],
            "last_epoch": result["last_epoch"],
            "best_epoch": result["best_epoch"],
            "best_validation_loss": result["best_validation_loss"],
        }, indent=2))
        return 0

    dataset_class = (
        VocalFeatureControlDataset
        if args.command == "cache-vocal-waveforms"
        else FeatureControlDataset
    )
    dataset = dataset_class(
        args.dataset_directory,
        args.split,
        waveform_cache_root=args.cache_root,
        training_sample_rate=args.training_sample_rate,
        build_missing_waveforms=True,
    )
    limit = len(dataset) if args.limit is None else min(int(args.limit), len(dataset))
    if limit < 0:
        raise ValueError("limit must be greater than or equal to 0")
    hits = 0
    for index in range(limit):
        item = dataset[index]
        hits += int(item["waveform_cache_hit"])
        print(
            f"[{index + 1}/{limit}] {item['example_id']} "
            f"cache_hit={item['waveform_cache_hit']} "
            f"samples={item['source_audio'].shape[-1]}",
            flush=True,
        )
    print(
        json.dumps(
            {
                "split": args.split,
                "examples": limit,
                "cache_hits": hits,
                "cache_misses": limit - hits,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
