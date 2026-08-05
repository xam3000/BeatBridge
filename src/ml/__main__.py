"""Command-line utilities for the feature-to-control ML baseline."""

from __future__ import annotations

import argparse
import json

from src.bridge import DEFAULT_FEATURE_CACHE_ROOT
from src.features.vocal import DEFAULT_DEMUCS_MODEL

from .data import (
    DEFAULT_BRIDGE_WAVEFORM_CACHE_ROOT,
    DEFAULT_TRAINING_SAMPLE_RATE,
    DEFAULT_VOCAL_BRIDGE_WAVEFORM_CACHE_ROOT,
    FeatureControlDataset,
    VocalFeatureControlDataset,
)
from .model import (
    VOCAL_FEATURE_CONTROL_MODEL_NAME,
    FeatureControlMLP,
    VocalFeatureControlMLP,
)
from .runner import TrainingConfig, run_feature_control_training
from .vocal_runner import VocalTrainingConfig, run_vocal_feature_control_training


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
    train_parser.add_argument("--device", default=TrainingConfig.device)
    train_parser.add_argument("--resume", action="store_true")

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
    vocal_train_parser.add_argument("--vocal-model", default=DEFAULT_DEMUCS_MODEL)
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
    vocal_train_parser.add_argument("--device", default=VocalTrainingConfig.device)
    vocal_train_parser.add_argument("--resume", action="store_true")
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
        )
        print(json.dumps({
            "output_directory": str(result.output_directory),
            "status": result.status,
            "last_epoch": result.last_epoch,
            "best_epoch": result.best_epoch,
            "best_validation_loss": result.best_validation_loss,
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
