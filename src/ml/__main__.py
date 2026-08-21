"""Command-line utilities for the feature-to-control ML baseline."""

from __future__ import annotations

import argparse
import json

from src.bridge import DEFAULT_FEATURE_CACHE_ROOT
from src.features.vocal import DEFAULT_ROFORMER_MODEL

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
    TCNBiLSTMTransitionControl,
    VocalFeatureControlMLP,
)
from .runner import TrainingConfig, run_feature_control_training
from .runner import run_tcn_bilstm_transition_control_training
from .vocal_runner import VocalTrainingConfig, run_vocal_feature_control_training
from .variable_runner import (
    VariableTemporalTrainingConfig,
    run_variable_tcn_bilstm_training,
)
from .variable_waveform_cache import (
    VARIABLE_WAVEFORM_CACHE_ROOT,
    VARIABLE_WAVEFORM_RENDER_SAMPLE_RATE,
    VARIABLE_WAVEFORM_SAMPLE_RATE,
    materialize_variable_waveform_cache,
)
from .wandb_logging import WandbConfig


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
        log_checkpoints=(
            environment.log_checkpoints
            if args.wandb_log_checkpoints is None
            else args.wandb_log_checkpoints
        ),
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
    tcn_train_parser.add_argument("--seed", type=int, default=TrainingConfig.seed)
    tcn_train_parser.add_argument(
        "--max-epochs", type=int, default=TrainingConfig.max_epochs
    )
    tcn_train_parser.add_argument(
        "--batch-size", type=int, default=TrainingConfig.batch_size
    )
    tcn_train_parser.add_argument(
        "--learning-rate", type=float, default=TrainingConfig.learning_rate
    )
    tcn_train_parser.add_argument(
        "--weight-decay", type=float, default=TrainingConfig.weight_decay
    )
    tcn_train_parser.add_argument("--patience", type=int, default=TrainingConfig.patience)
    tcn_train_parser.add_argument("--min-delta", type=float, default=TrainingConfig.min_delta)
    tcn_train_parser.add_argument(
        "--gradient-clip-norm",
        type=float,
        default=TrainingConfig.gradient_clip_norm,
    )
    tcn_train_parser.add_argument(
        "--training-sample-rate",
        type=int,
        default=DEFAULT_TRAINING_SAMPLE_RATE,
    )
    tcn_train_parser.add_argument(
        "--device",
        default=TrainingConfig.device,
        help="PyTorch device: auto (CUDA if available), cpu, cuda, or cuda:<index>",
    )
    tcn_train_parser.add_argument("--resume", action="store_true")
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
    _add_wandb_options(variable_train_parser)

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
    return parser


def main():
    args = build_argument_parser().parse_args()
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
        result = run_tcn_bilstm_transition_control_training(
            args.dataset_directory,
            args.output_directory,
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
            config=config,
            waveform_cache_root=args.cache_root,
            transition_lengths=args.transition_bars,
            batch_size=args.batch_size,
            resume=args.resume,
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
            learning_rate=args.learning_rate,
            weight_decay=args.weight_decay,
            patience=args.patience,
            min_delta=args.min_delta,
            gradient_clip_norm=args.gradient_clip_norm,
            training_sample_rate=args.training_sample_rate,
            device=args.device,
        )
        result = run_vocal_feature_control_training(
            args.dataset_directory,
            args.output_directory,
            config=config,
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
