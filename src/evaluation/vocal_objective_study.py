"""Render a blind Objective-v4 versus Objective-v5 vocal-control study."""

from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import random
import uuid

import librosa
import numpy as np
import torch

from src.analysis.pre_analysis import PreAnalysis
from src.bridge import extract_aligned_vocal_bridge
from src.control import (
    CONTROL_PROTOCOL_VERSION,
    DEFAULT_INCREMENT_LOGIT_BOUND,
    OBJECTIVE_VERSION,
    VOCAL_CONTROL_PROTOCOL_VERSION,
    VOCAL_OBJECTIVE_VERSION,
    DifferentiableTransitionObjective,
    DifferentiableTwoBandRenderer,
    DifferentiableVocalAwareRenderer,
    VocalAwareTransitionObjective,
    VocalAwareTransitionObjectiveConfig,
    optimize_control_curves,
    optimize_vocal_control_curves,
)
from src.evaluation.blind_control_study import (
    BLIND_CONTROL_STUDY_FORMAT_VERSION,
    DEFAULT_BLIND_SEED,
)
from src.evaluation.control_probe import _audio_metadata, _write_audio_atomic
from src.evaluation.control_study_ratings import create_control_study_ratings
from src.evaluation.heldout_control_study import _load_candidate, _load_split_features
from src.features import SEQUENCE_LENGTH, feature_index
from src.pipeline import DEFAULT_SAMPLE_RATE, RENDER_RESULT_FORMAT_VERSION


VOCAL_OBJECTIVE_STUDY_FORMAT_VERSION = 1
VOCAL_OBJECTIVE_STUDY_NAME = "blind_objective_v4_vs_v5_vocal_controls"
BASELINE_METHOD_NAME = "objective_v4_controls_vocal_renderer"
VOCAL_METHOD_NAME = "objective_v5_vocal_controls"
DEFAULT_SPLITS = ("train", "validation")
DEFAULT_PAIR_COUNT = 6
DEFAULT_OPTIMIZATION_SAMPLE_RATE = 11_025
DEFAULT_PREFIX_SECONDS = 5.0
DEFAULT_SUFFIX_SECONDS = 8.0


def export_blind_vocal_objective_study(
    dataset_directory,
    output_directory,
    *,
    splits=DEFAULT_SPLITS,
    pair_count=DEFAULT_PAIR_COUNT,
    minimum_mean_vocal_strength=0.15,
    max_track_uses=2,
    analysis_location=Path("output") / "pre_analysis",
    control_points=SEQUENCE_LENGTH,
    optimization_steps=80,
    optimization_learning_rate=0.06,
    optimization_sample_rate=DEFAULT_OPTIMIZATION_SAMPLE_RATE,
    increment_logit_bound=DEFAULT_INCREMENT_LOGIT_BOUND,
    maximum_vocal_ducking=0.75,
    prefix_seconds=DEFAULT_PREFIX_SECONDS,
    suffix_seconds=DEFAULT_SUFFIX_SECONDS,
    blind_seed=DEFAULT_BLIND_SEED,
    analysis=None,
    bridge_extractor=extract_aligned_vocal_bridge,
):
    """Select vocal-active transition windows and export blinded A/B WAVs."""
    dataset_directory = Path(dataset_directory).resolve()
    output_directory = Path(output_directory).resolve()
    splits = tuple(str(split) for split in splits)
    if output_directory.exists():
        raise FileExistsError(f"Study output already exists: {output_directory}")
    if not splits or any(split not in {"train", "validation", "test"} for split in splits):
        raise ValueError("splits must contain train, validation, and/or test")
    if int(pair_count) < 1 or int(max_track_uses) < 1:
        raise ValueError("pair_count and max_track_uses must be at least 1")
    if not 0.0 <= float(minimum_mean_vocal_strength) <= 1.0:
        raise ValueError("minimum_mean_vocal_strength must be in [0, 1]")
    if float(prefix_seconds) < 0 or float(suffix_seconds) < 0:
        raise ValueError("prefix_seconds and suffix_seconds must be non-negative")

    dataset_manifest_path = dataset_directory / "manifest.json"
    dataset_manifest = _read_json(dataset_manifest_path)
    examples = [
        json.loads(line)
        for line in (dataset_directory / "examples.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    ]
    feature_rows = {}
    for split in splits:
        rows = _load_split_features(dataset_directory / f"{split}.npz")
        duplicate_ids = set(feature_rows).intersection(rows)
        if duplicate_ids:
            raise ValueError(f"Feature rows occur in more than one split: {duplicate_ids}")
        feature_rows.update(rows)
    selected = _select_vocal_examples(
        examples,
        feature_rows,
        splits=splits,
        pair_count=int(pair_count),
        minimum_mean_vocal_strength=float(minimum_mean_vocal_strength),
        max_track_uses=int(max_track_uses),
    )

    analysis = analysis or PreAnalysis(str(Path(analysis_location)) + os.sep)
    rng = random.Random(int(blind_seed))
    output_directory.mkdir(parents=True)
    public_pairs = []
    answer_pairs = []

    for study_index, selected_item in enumerate(selected, start=1):
        example = selected_item["example"]
        features_a_array, features_b_array = feature_rows[example["example_id"]]
        candidate, historical_score = _load_candidate(example)
        pair_directory = output_directory / (
            f"{study_index:02d}__{_safe_name(Path(candidate['source_track']['path']).stem)}"
            f"__to__{_safe_name(Path(candidate['target_track']['path']).stem)}"
            f"__{example['example_id'][-6:]}"
        )
        pair_directory.mkdir()
        source, target, source_vocal, target_vocal, geometry = bridge_extractor(
            candidate,
            analysis,
            sample_rate=DEFAULT_SAMPLE_RATE,
            include_context_audio=True,
        )
        source, target, source_vocal, target_vocal = _validate_bridge(
            source,
            target,
            source_vocal,
            target_vocal,
        )
        features_a = torch.from_numpy(np.asarray(features_a_array, dtype=np.float32))
        features_b = torch.from_numpy(np.asarray(features_b_array, dtype=np.float32))
        proxy_audio = tuple(
            torch.from_numpy(
                librosa.resample(
                    item,
                    orig_sr=DEFAULT_SAMPLE_RATE,
                    target_sr=int(optimization_sample_rate),
                    axis=-1,
                    res_type="soxr_hq",
                ).astype(np.float32, copy=False)
            )
            for item in (source, target, source_vocal, target_vocal)
        )

        v4_renderer = DifferentiableTwoBandRenderer(
            sample_rate=int(optimization_sample_rate),
            lowpass_kernel_size=127,
        )
        v4_objective = DifferentiableTransitionObjective(energy_frames=control_points)
        v4_optimization = optimize_control_curves(
            proxy_audio[0],
            proxy_audio[1],
            renderer=v4_renderer,
            objective=v4_objective,
            control_points=control_points,
            steps=optimization_steps,
            learning_rate=optimization_learning_rate,
            increment_logit_bound=increment_logit_bound,
            features_a=features_a,
            features_b=features_b,
        )

        v5_renderer = DifferentiableVocalAwareRenderer(
            sample_rate=int(optimization_sample_rate),
            lowpass_kernel_size=127,
        )
        v5_objective = VocalAwareTransitionObjective(energy_frames=control_points)
        v5_optimization = optimize_vocal_control_curves(
            *proxy_audio,
            renderer=v5_renderer,
            objective=v5_objective,
            control_points=control_points,
            steps=optimization_steps,
            learning_rate=optimization_learning_rate,
            increment_logit_bound=increment_logit_bound,
            maximum_vocal_ducking=maximum_vocal_ducking,
            features_a=features_a,
            features_b=features_b,
        )

        no_duck = torch.zeros_like(v4_optimization.mix_position)
        with torch.no_grad():
            baseline_proxy = v5_renderer(
                *proxy_audio,
                v4_optimization.mix_position,
                v4_optimization.low_end_position,
                v4_optimization.mix_position,
                no_duck,
                no_duck,
            )
            v5_proxy = v5_renderer(
                *proxy_audio,
                v5_optimization.mix_position,
                v5_optimization.low_end_position,
                v5_optimization.vocal_position,
                v5_optimization.vocal_duck_a,
                v5_optimization.vocal_duck_b,
            )
            baseline_terms = v5_objective(
                baseline_proxy,
                *proxy_audio,
                features_a,
                features_b,
            )
            v5_terms = v5_objective(
                v5_proxy,
                *proxy_audio,
                features_a,
                features_b,
            )

            full_renderer = DifferentiableVocalAwareRenderer(
                sample_rate=DEFAULT_SAMPLE_RATE,
                lowpass_kernel_size=511,
            )
            full_audio = tuple(torch.from_numpy(item) for item in (
                source,
                target,
                source_vocal,
                target_vocal,
            ))
            baseline_transition = full_renderer(
                *full_audio,
                v4_optimization.mix_position,
                v4_optimization.low_end_position,
                v4_optimization.mix_position,
                no_duck,
                no_duck,
            ).audio.numpy()
            v5_transition = full_renderer(
                *full_audio,
                v5_optimization.mix_position,
                v5_optimization.low_end_position,
                v5_optimization.vocal_position,
                v5_optimization.vocal_duck_a,
                v5_optimization.vocal_duck_b,
            ).audio.numpy()

        prefix = geometry["source_audio"][
            ...,
            max(0, int(geometry["source_cut_sample"]) - int(round(prefix_seconds * DEFAULT_SAMPLE_RATE)))
            : int(geometry["source_cut_sample"]),
        ]
        suffix = geometry["target_audio"][
            ...,
            int(geometry["target_cut_sample"])
            : min(
                geometry["target_audio"].shape[-1],
                int(geometry["target_cut_sample"]) + int(round(suffix_seconds * DEFAULT_SAMPLE_RATE)),
            ),
        ]
        baseline_preview = np.concatenate((prefix, baseline_transition, suffix), axis=-1)
        v5_preview = np.concatenate((prefix, v5_transition, suffix), axis=-1)
        baseline_preview = baseline_preview.astype(np.float32, copy=False)
        v5_preview = v5_preview.astype(np.float32, copy=False)
        raw_peak = max(float(np.max(np.abs(baseline_preview))), float(np.max(np.abs(v5_preview))))
        shared_gain = min(1.0, 0.98 / max(raw_peak, 1e-8))
        baseline_preview *= shared_gain
        v5_preview *= shared_gain

        baseline_label = rng.choice(("A", "B"))
        v5_label = "B" if baseline_label == "A" else "A"
        audio_by_label = {baseline_label: baseline_preview, v5_label: v5_preview}
        metadata_by_label = {}
        for label in ("A", "B"):
            path = pair_directory / f"{label}.wav"
            _write_audio_atomic(path, audio_by_label[label], DEFAULT_SAMPLE_RATE)
            metadata = _audio_metadata(path, audio_by_label[label], DEFAULT_SAMPLE_RATE)
            metadata["sha256"] = _file_sha256(path)
            metadata_by_label[label] = metadata

        relative_directory = str(pair_directory.relative_to(output_directory))
        public_pairs.append({
            "index": study_index,
            "directory": relative_directory,
            "source_track": candidate["source_track"]["path"],
            "target_track": candidate["target_track"]["path"],
            "transition_length_bars": int(candidate["transition_length_bars"]),
            "tempo_backend": geometry.get("tempo_backend"),
            "vocal_selection": selected_item["vocal_statistics"],
            "files": metadata_by_label,
        })
        answer_pairs.append({
            "index": study_index,
            "directory": relative_directory,
            "mapping": {baseline_label: BASELINE_METHOD_NAME, v5_label: VOCAL_METHOD_NAME},
            "details": {
                "dataset_example": example,
                "candidate": candidate,
                "historical_render_score": historical_score,
                "geometry": {
                    key: value
                    for key, value in geometry.items()
                    if key not in {
                        "source_audio",
                        "target_audio",
                        "source_vocal_audio",
                        "target_vocal_audio",
                    }
                },
                "vocal_selection": selected_item["vocal_statistics"],
                "objective_v5": {
                    "config": asdict(VocalAwareTransitionObjectiveConfig()),
                    "baseline_components": _tensor_terms_to_float(baseline_terms),
                    "v5_components": _tensor_terms_to_float(v5_terms),
                    "relative_loss_improvement": float(
                        1.0 - float(v5_terms["loss"]) / max(float(baseline_terms["loss"]), 1e-12)
                    ),
                },
                "controls": {
                    "v4_mix_position": v4_optimization.mix_position.tolist(),
                    "v4_low_end_position": v4_optimization.low_end_position.tolist(),
                    "v5_mix_position": v5_optimization.mix_position.tolist(),
                    "v5_low_end_position": v5_optimization.low_end_position.tolist(),
                    "v5_vocal_position": v5_optimization.vocal_position.tolist(),
                    "v5_vocal_duck_a": v5_optimization.vocal_duck_a.tolist(),
                    "v5_vocal_duck_b": v5_optimization.vocal_duck_b.tolist(),
                },
                "exports": {
                    "files": metadata_by_label,
                    "shared_peak_gain": shared_gain,
                    "raw_joint_peak": raw_peak,
                    "transition_start_sample": int(prefix.shape[-1]),
                    "transition_end_sample": int(prefix.shape[-1] + source.shape[-1]),
                },
            },
        })
        print(
            f"[{study_index}/{len(selected)}] {example['example_id']} "
            f"vocal={selected_item['vocal_statistics']['selection_score']:.3f} "
            f"loss={float(baseline_terms['loss']):.4f}->{float(v5_terms['loss']):.4f}",
            flush=True,
        )

    timestamp = _utc_now()
    answer_key = {
        "format_version": VOCAL_OBJECTIVE_STUDY_FORMAT_VERSION,
        "blind_seed": int(blind_seed),
        "warning": "Do not inspect before completing ratings.json.",
        "methods": [BASELINE_METHOD_NAME, VOCAL_METHOD_NAME],
        "pairs": answer_pairs,
    }
    public_manifest = {
        "format_version": BLIND_CONTROL_STUDY_FORMAT_VERSION,
        "vocal_objective_study_format_version": VOCAL_OBJECTIVE_STUDY_FORMAT_VERSION,
        "study_name": VOCAL_OBJECTIVE_STUDY_NAME,
        "blind": True,
        "status": "completed",
        "created_at_utc": timestamp,
        "completed_at_utc": timestamp,
        "control_protocol_version": CONTROL_PROTOCOL_VERSION,
        "baseline_objective_version": OBJECTIVE_VERSION,
        "vocal_control_protocol_version": VOCAL_CONTROL_PROTOCOL_VERSION,
        "objective_version": VOCAL_OBJECTIVE_VERSION,
        "rendering_protocol_version": RENDER_RESULT_FORMAT_VERSION,
        "source_batch": str(dataset_directory),
        "source_dataset": str(dataset_directory),
        "source_dataset_manifest_sha256": _file_sha256(dataset_manifest_path),
        "dataset_id": dataset_manifest["dataset_id"],
        "dataset_split": list(splits),
        "selection_policy": "vocal_strength_both_sides_diverse_pairs_v1",
        "track_exclusions_path": "inherited_from_dataset_export_plus_struggling_name_guard",
        "config": {
            "pair_count": len(selected),
            "minimum_mean_vocal_strength": float(minimum_mean_vocal_strength),
            "max_track_uses": int(max_track_uses),
            "control_points": int(control_points),
            "optimization_steps": int(optimization_steps),
            "optimization_learning_rate": float(optimization_learning_rate),
            "optimization_sample_rate": int(optimization_sample_rate),
            "increment_logit_bound": float(increment_logit_bound),
            "maximum_vocal_ducking": float(maximum_vocal_ducking),
            "prefix_seconds": float(prefix_seconds),
            "suffix_seconds": float(suffix_seconds),
            "blind_seed": int(blind_seed),
        },
        "answer_key": "answer_key.json",
        "ratings": "ratings.json",
        "pairs": public_pairs,
        "failures": [],
        "interpretation_limit": (
            "Development gate selected for audible vocals on both transition sides; "
            "not an independent generalization test."
        ),
    }
    _write_json_atomic(output_directory / "answer_key.json", answer_key)
    _write_json_atomic(output_directory / "manifest.json", public_manifest)
    create_control_study_ratings(output_directory)
    _write_readme(output_directory, public_manifest)
    return output_directory / "manifest.json"


def _select_vocal_examples(
    examples,
    feature_rows,
    *,
    splits,
    pair_count,
    minimum_mean_vocal_strength,
    max_track_uses,
):
    candidates = []
    for example in examples:
        if example.get("split") not in splits or example["example_id"] not in feature_rows:
            continue
        paths = f"{example['source_track']['path']} {example['target_track']['path']}".lower()
        if "struggling" in paths:
            continue
        statistics = _vocal_statistics(*feature_rows[example["example_id"]])
        if (
            statistics["source_mean_strength"] < minimum_mean_vocal_strength
            or statistics["target_mean_strength"] < minimum_mean_vocal_strength
        ):
            continue
        candidates.append({"example": example, "vocal_statistics": statistics})
    candidates.sort(
        key=lambda item: (
            -item["vocal_statistics"]["selection_score"],
            int(item["example"]["candidate_rank"]),
            item["example"]["example_id"],
        )
    )
    selected = []
    pair_ids = set()
    track_uses = {}
    for item in candidates:
        example = item["example"]
        source_hash = example["source_track"]["sha256"]
        target_hash = example["target_track"]["sha256"]
        pair_id = (source_hash, target_hash)
        if pair_id in pair_ids:
            continue
        if track_uses.get(source_hash, 0) >= max_track_uses:
            continue
        if track_uses.get(target_hash, 0) >= max_track_uses:
            continue
        selected.append(item)
        pair_ids.add(pair_id)
        track_uses[source_hash] = track_uses.get(source_hash, 0) + 1
        track_uses[target_hash] = track_uses.get(target_hash, 0) + 1
        if len(selected) == pair_count:
            break
    if len(selected) < pair_count:
        raise ValueError(
            f"Only {len(selected)} vocal-active diverse examples satisfy the selection; "
            f"requested {pair_count}"
        )
    return tuple(selected)


def _vocal_statistics(features_a, features_b):
    activity = feature_index("vocal_activity")
    prominence = feature_index("vocal_prominence")
    valid = feature_index("vocal_valid")
    source = features_a[:, activity] * features_a[:, prominence] * features_a[:, valid]
    target = features_b[:, activity] * features_b[:, prominence] * features_b[:, valid]
    overlap = np.minimum(source, target)
    source_mean = float(np.mean(source))
    target_mean = float(np.mean(target))
    overlap_mean = float(np.mean(overlap))
    return {
        "source_mean_strength": source_mean,
        "target_mean_strength": target_mean,
        "overlap_mean_strength": overlap_mean,
        "simultaneously_active_bins_above_0_2": int(np.sum((source > 0.2) & (target > 0.2))),
        "selection_score": overlap_mean + 0.25 * (source_mean + target_mean),
    }


def _validate_bridge(*arrays):
    values = tuple(np.asarray(item, dtype=np.float32) for item in arrays)
    if not values or any(item.shape != values[0].shape for item in values):
        raise ValueError("Mix and vocal bridge arrays must have identical shapes")
    if values[0].ndim != 2 or values[0].shape[0] != 2 or values[0].shape[-1] == 0:
        raise ValueError("Bridge arrays must be non-empty stereo audio")
    if any(not np.isfinite(item).all() for item in values):
        raise ValueError("Bridge arrays must contain only finite values")
    return values


def _tensor_terms_to_float(terms):
    return {key: float(value.detach().cpu()) for key, value in terms.items()}


def _safe_name(value):
    cleaned = "".join(character if character.isalnum() else "_" for character in value)
    return "_".join(part for part in cleaned.split("_") if part)


def _file_sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


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


def _write_readme(output_directory, manifest):
    lines = [
        "# Blinder Vocal-Control-Hörvergleich",
        "",
        "Höre pro Ordner zuerst `A.wav` und `B.wav`, ohne `answer_key.json` zu öffnen.",
        "Beide Varianten verwenden denselben stem-fähigen Renderer, Kontext und Peak-Gain.",
        "Verglichen werden Objective-v4-Controls ohne Vocal-Ducking und direkt optimierte",
        "Objective-v5-Controls mit eigener Vocal-Übergabe und Ducking.",
        "",
        "Achte besonders auf Vocal-Clash, zu leise eingeblendete Vocals, abgeschnittene",
        "Silben, Pegelsprünge mitten im Satz und die allgemeine Sauberkeit.",
        "",
        f"Paare: {len(manifest['pairs'])}. Alle ausgewählten Übergangsfenster besitzen",
        "gemessene Vocal-Aktivität auf Source- und Target-Seite.",
        "",
    ]
    path = Path(output_directory) / "README.md"
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        temporary.write_text("\n".join(lines), encoding="utf-8")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def build_argument_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset_directory")
    parser.add_argument("output_directory")
    parser.add_argument("--splits", nargs="+", default=list(DEFAULT_SPLITS))
    parser.add_argument("--pair-count", type=int, default=DEFAULT_PAIR_COUNT)
    parser.add_argument("--minimum-mean-vocal-strength", type=float, default=0.15)
    parser.add_argument("--max-track-uses", type=int, default=2)
    parser.add_argument("--analysis-location", default=str(Path("output") / "pre_analysis"))
    parser.add_argument("--control-points", type=int, default=SEQUENCE_LENGTH)
    parser.add_argument("--optimization-steps", type=int, default=80)
    parser.add_argument("--learning-rate", type=float, default=0.06)
    parser.add_argument("--optimization-sample-rate", type=int, default=DEFAULT_OPTIMIZATION_SAMPLE_RATE)
    parser.add_argument("--increment-logit-bound", type=float, default=DEFAULT_INCREMENT_LOGIT_BOUND)
    parser.add_argument("--maximum-vocal-ducking", type=float, default=0.75)
    parser.add_argument("--prefix-seconds", type=float, default=DEFAULT_PREFIX_SECONDS)
    parser.add_argument("--suffix-seconds", type=float, default=DEFAULT_SUFFIX_SECONDS)
    parser.add_argument("--blind-seed", type=int, default=DEFAULT_BLIND_SEED)
    return parser


def main():
    args = build_argument_parser().parse_args()
    manifest_path = export_blind_vocal_objective_study(
        args.dataset_directory,
        args.output_directory,
        splits=args.splits,
        pair_count=args.pair_count,
        minimum_mean_vocal_strength=args.minimum_mean_vocal_strength,
        max_track_uses=args.max_track_uses,
        analysis_location=args.analysis_location,
        control_points=args.control_points,
        optimization_steps=args.optimization_steps,
        optimization_learning_rate=args.learning_rate,
        optimization_sample_rate=args.optimization_sample_rate,
        increment_logit_bound=args.increment_logit_bound,
        maximum_vocal_ducking=args.maximum_vocal_ducking,
        prefix_seconds=args.prefix_seconds,
        suffix_seconds=args.suffix_seconds,
        blind_seed=args.blind_seed,
    )
    print(manifest_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
