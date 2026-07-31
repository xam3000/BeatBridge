"""Render a feature-conditioned control study from a track-held-out dataset split."""

from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import uuid

import numpy as np

from src.analysis.pre_analysis import PreAnalysis
from src.control import (
    CONTROL_PROTOCOL_VERSION,
    DEFAULT_INCREMENT_LOGIT_BOUND,
    OBJECTIVE_VERSION,
    DifferentiableTransitionObjectiveConfig,
)
from src.evaluation.blind_control_study import (
    DEFAULT_BLIND_SEED,
    blind_existing_control_comparison,
)
from src.evaluation.control_probe import (
    CONTROL_COMPARISON_MANIFEST_FORMAT_VERSION,
    DEFAULT_CONTROL_POINTS,
    DEFAULT_OPTIMIZATION_SAMPLE_RATE,
    DEFAULT_PREFIX_SECONDS,
    DEFAULT_SUFFIX_SECONDS,
    _render_comparison_pair,
)
from src.pipeline import DEFAULT_SAMPLE_RATE, RENDER_RESULT_FORMAT_VERSION


HELDOUT_SELECTION_POLICY = "track_disjoint_dataset_split_all_examples_v1"
SUPPORTED_SPLITS = ("validation", "test")


def export_heldout_control_comparisons(
    dataset_directory,
    output_directory,
    *,
    split="test",
    analysis_location=Path("output") / "pre_analysis",
    max_examples_per_pair=3,
    example_limit=None,
    control_points=DEFAULT_CONTROL_POINTS,
    optimization_steps=80,
    optimization_learning_rate=0.06,
    optimization_sample_rate=DEFAULT_OPTIMIZATION_SAMPLE_RATE,
    increment_logit_bound=DEFAULT_INCREMENT_LOGIT_BOUND,
    prefix_seconds=DEFAULT_PREFIX_SECONDS,
    suffix_seconds=DEFAULT_SUFFIX_SECONDS,
):
    """Render Equal Power and objective-v4 curves for one held-out split."""
    dataset_directory = Path(dataset_directory)
    output_directory = Path(output_directory)
    split = str(split)
    if split not in SUPPORTED_SPLITS:
        raise ValueError(f"split must be one of {SUPPORTED_SPLITS}")
    if output_directory.exists():
        raise FileExistsError(
            f"Comparison output already exists; choose a new directory: {output_directory}"
        )
    if max_examples_per_pair <= 0:
        raise ValueError("max_examples_per_pair must be greater than 0")
    if example_limit is not None and int(example_limit) <= 0:
        raise ValueError("example_limit must be greater than 0 when set")

    dataset_manifest_path = dataset_directory / "manifest.json"
    examples_path = dataset_directory / "examples.jsonl"
    split_path = dataset_directory / f"{split}.npz"
    dataset_manifest = _read_json(dataset_manifest_path)
    examples = [
        json.loads(line)
        for line in examples_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    selected_examples = _select_examples(
        examples,
        split=split,
        max_examples_per_pair=int(max_examples_per_pair),
        example_limit=None if example_limit is None else int(example_limit),
    )
    feature_rows = _load_split_features(split_path)
    missing = [
        item["example_id"]
        for item in selected_examples
        if item["example_id"] not in feature_rows
    ]
    if missing:
        raise ValueError(f"Selected examples are missing from {split_path}: {missing}")

    output_directory.mkdir(parents=True)
    manifest_path = output_directory / "manifest.json"
    payload = {
        "format_version": CONTROL_COMPARISON_MANIFEST_FORMAT_VERSION,
        "control_protocol_version": CONTROL_PROTOCOL_VERSION,
        "objective_version": OBJECTIVE_VERSION,
        "rendering_protocol_version": RENDER_RESULT_FORMAT_VERSION,
        "status": "running",
        "created_at_utc": _utc_now(),
        "completed_at_utc": None,
        "source_batch": str(dataset_directory),
        "source_dataset": str(dataset_directory),
        "source_dataset_manifest_sha256": _file_sha256(dataset_manifest_path),
        "dataset_id": dataset_manifest["dataset_id"],
        "dataset_split": split,
        "selection_policy": HELDOUT_SELECTION_POLICY,
        "track_exclusions_path": "inherited_from_dataset_export",
        "config": {
            "example_count": len(selected_examples),
            "max_examples_per_pair": int(max_examples_per_pair),
            "example_limit": None if example_limit is None else int(example_limit),
            "transition_bars": int(dataset_manifest["transition_bars"]),
            "control_points": int(control_points),
            "optimization_steps": int(optimization_steps),
            "optimization_learning_rate": float(optimization_learning_rate),
            "optimization_sample_rate": int(optimization_sample_rate),
            "increment_logit_bound": float(increment_logit_bound),
            "render_sample_rate": DEFAULT_SAMPLE_RATE,
            "prefix_seconds": float(prefix_seconds),
            "suffix_seconds": float(suffix_seconds),
            "objective": asdict(DifferentiableTransitionObjectiveConfig()),
        },
        "pairs": [],
        "failures": [],
    }
    _write_json_atomic(manifest_path, payload)

    analysis = PreAnalysis(str(Path(analysis_location)) + os.sep)
    for index, example in enumerate(selected_examples, start=1):
        example_id = example["example_id"]
        candidate, historical_score = _load_candidate(example)
        pair_directory = output_directory / (
            f"{index:02d}__{_safe_name(Path(candidate['source_track']['path']).stem)}"
            f"__to__{_safe_name(Path(candidate['target_track']['path']).stem)}"
            f"__{example_id[-6:]}"
        )
        pair_directory.mkdir()
        features_a, features_b = feature_rows[example_id]
        selection = {
            "pair_relative_directory": str(Path(example["pair_manifest_path"]).parent),
            "historical_score": historical_score,
            "historical_variant": None,
        }
        try:
            result = _render_comparison_pair(
                candidate,
                selection,
                pair_directory,
                analysis=analysis,
                control_points=control_points,
                optimization_steps=optimization_steps,
                optimization_learning_rate=optimization_learning_rate,
                optimization_sample_rate=optimization_sample_rate,
                increment_logit_bound=increment_logit_bound,
                prefix_seconds=prefix_seconds,
                suffix_seconds=suffix_seconds,
                features_a=features_a,
                features_b=features_b,
            )
            result["index"] = index
            result["directory"] = str(pair_directory.relative_to(output_directory))
            result["dataset_example"] = example
            payload["pairs"].append(result)
            print(
                f"[{index}/{len(selected_examples)}] {example_id}: "
                f"{result['optimization']['initial_loss']:.4f} -> "
                f"{result['optimization']['final_loss']:.4f}",
                flush=True,
            )
        except Exception as error:
            payload["failures"].append(
                {
                    "index": index,
                    "example_id": example_id,
                    "candidate_id": candidate["candidate_id"],
                    "error_type": type(error).__name__,
                    "message": str(error),
                }
            )
            print(f"[{index}/{len(selected_examples)}] failed {example_id}: {error}")
        _write_json_atomic(manifest_path, payload)

    payload["completed_at_utc"] = _utc_now()
    payload["status"] = "completed" if not payload["failures"] else "completed_with_failures"
    _write_json_atomic(manifest_path, payload)
    return manifest_path


def export_blind_heldout_control_study(
    dataset_directory,
    output_directory,
    *,
    blind_seed=DEFAULT_BLIND_SEED,
    **kwargs,
):
    """Render and immediately blind a held-out objective-v4 comparison."""
    manifest_path = export_heldout_control_comparisons(
        dataset_directory,
        output_directory,
        **kwargs,
    )
    return blind_existing_control_comparison(
        manifest_path,
        blind_seed=blind_seed,
    )


def _select_examples(examples, *, split, max_examples_per_pair, example_limit):
    eligible = [item for item in examples if item.get("split") == split]
    eligible.sort(
        key=lambda item: (
            item["source_track"]["sha256"],
            item["target_track"]["sha256"],
            int(item["candidate_rank"]),
            item["example_id"],
        )
    )
    selected = []
    pair_counts = {}
    for item in eligible:
        pair = (
            item["source_track"]["sha256"],
            item["target_track"]["sha256"],
        )
        if pair_counts.get(pair, 0) >= max_examples_per_pair:
            continue
        selected.append(item)
        pair_counts[pair] = pair_counts.get(pair, 0) + 1
        if example_limit is not None and len(selected) >= example_limit:
            break
    if not selected:
        raise ValueError(f"Dataset contains no selectable examples in split {split!r}")
    return tuple(selected)


def _load_split_features(path):
    with np.load(path, allow_pickle=False) as payload:
        ids = [str(value) for value in payload["example_ids"]]
        features_a = payload["features_a"]
        features_b = payload["features_b"]
    if len(ids) != len(set(ids)):
        raise ValueError(f"Duplicate example IDs in {path}")
    if features_a.shape[0] != len(ids) or features_b.shape[0] != len(ids):
        raise ValueError(f"Feature row count does not match example IDs in {path}")
    return {
        example_id: (features_a[index], features_b[index])
        for index, example_id in enumerate(ids)
    }


def _load_candidate(example):
    pair_manifest = _read_json(example["pair_manifest_path"])
    candidate_by_id = {
        item["candidate_id"]: item
        for item in pair_manifest["candidate_generation"]["candidates"]
    }
    candidate = candidate_by_id.get(example["candidate_id"])
    if candidate is None:
        raise ValueError(
            f"Candidate {example['candidate_id']} is absent from {example['pair_manifest_path']}"
        )
    historical_score = next(
        (
            item
            for item in pair_manifest["candidate_ranking"]["scores"]
            if item["candidate_id"] == example["candidate_id"]
        ),
        {
            "candidate_id": example["candidate_id"],
            "rank": example["candidate_rank"],
            "total_score": example["candidate_score"],
        },
    )
    return candidate, historical_score


def _safe_name(value):
    cleaned = "".join(character if character.isalnum() else "_" for character in value)
    return "_".join(part for part in cleaned.split("_") if part)


def _read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _file_sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json_atomic(path, payload):
    path = Path(path)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def build_argument_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset_directory")
    parser.add_argument("output_directory")
    parser.add_argument("--split", choices=SUPPORTED_SPLITS, default="test")
    parser.add_argument("--analysis-location", default=str(Path("output") / "pre_analysis"))
    parser.add_argument("--max-examples-per-pair", type=int, default=3)
    parser.add_argument("--example-limit", type=int)
    parser.add_argument("--control-points", type=int, default=DEFAULT_CONTROL_POINTS)
    parser.add_argument("--optimization-steps", type=int, default=80)
    parser.add_argument("--learning-rate", type=float, default=0.06)
    parser.add_argument(
        "--optimization-sample-rate",
        type=int,
        default=DEFAULT_OPTIMIZATION_SAMPLE_RATE,
    )
    parser.add_argument(
        "--increment-logit-bound",
        type=float,
        default=DEFAULT_INCREMENT_LOGIT_BOUND,
    )
    parser.add_argument("--prefix-seconds", type=float, default=DEFAULT_PREFIX_SECONDS)
    parser.add_argument("--suffix-seconds", type=float, default=DEFAULT_SUFFIX_SECONDS)
    parser.add_argument("--blind-seed", type=int, default=DEFAULT_BLIND_SEED)
    parser.add_argument("--not-blind", action="store_true")
    return parser


def main():
    args = build_argument_parser().parse_args()
    kwargs = {
        "split": args.split,
        "analysis_location": args.analysis_location,
        "max_examples_per_pair": args.max_examples_per_pair,
        "example_limit": args.example_limit,
        "control_points": args.control_points,
        "optimization_steps": args.optimization_steps,
        "optimization_learning_rate": args.learning_rate,
        "optimization_sample_rate": args.optimization_sample_rate,
        "increment_logit_bound": args.increment_logit_bound,
        "prefix_seconds": args.prefix_seconds,
        "suffix_seconds": args.suffix_seconds,
    }
    if args.not_blind:
        manifest_path = export_heldout_control_comparisons(
            args.dataset_directory,
            args.output_directory,
            **kwargs,
        )
    else:
        manifest_path = export_blind_heldout_control_study(
            args.dataset_directory,
            args.output_directory,
            blind_seed=args.blind_seed,
            **kwargs,
        )
    print(manifest_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
