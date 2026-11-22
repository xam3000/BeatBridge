"""Render a blind initial-versus-learned Vocal-MLP control study."""

from __future__ import annotations

import argparse
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

from src.ml.control_initialization import read_model_config

from src.analysis.pre_analysis import PreAnalysis
from src.bridge import extract_aligned_vocal_bridge
from src.control import (
    CONTROL_PROTOCOL_VERSION,
    VOCAL_CONTROL_PROTOCOL_VERSION,
    VOCAL_OBJECTIVE_VERSION,
    DifferentiableVocalAwareRenderer,
    VocalAwareTransitionObjective,
    VocalAwareTransitionObjectiveConfig,
)
from src.evaluation.blind_control_study import (
    BLIND_CONTROL_STUDY_FORMAT_VERSION,
    DEFAULT_BLIND_SEED,
)
from src.evaluation.control_probe import _audio_metadata, _write_audio_atomic
from src.evaluation.control_study_ratings import create_control_study_ratings
from src.evaluation.ml_control_study import _load_candidate_verified
from src.evaluation.vocal_objective_study import _validate_bridge, _vocal_statistics
from src.features import SEQUENCE_LENGTH
from src.ml import (
    SUPPORTED_VOCAL_TRAINING_RUN_FORMAT_VERSIONS,
    VOCAL_FEATURE_CONTROL_MODEL_FORMAT_VERSION,
    VOCAL_FEATURE_CONTROL_MODEL_NAME,
    VOCAL_TRAINING_RUNNER_NAME,
    VocalFeatureControlDataset,
    VocalFeatureControlMLP,
    VocalFeatureControlMLPConfig,
)
from src.pipeline import DEFAULT_SAMPLE_RATE, RENDER_RESULT_FORMAT_VERSION
from src.ranking.rendered_transition import (
    RenderedTransitionInput,
    rank_rendered_transitions,
)


VOCAL_ML_CONTROL_STUDY_FORMAT_VERSION = 1
VOCAL_ML_CONTROL_STUDY_NAME = "blind_vocal_mlp_v2_initial_vs_best"
BASELINE_METHOD_NAME = "vocal_time_shared_mlp_v2_initialization"
LEARNED_METHOD_NAME = "vocal_time_shared_mlp_v2_best"
SUPPORTED_SPLITS = ("validation", "test")
DEFAULT_PAIR_COUNT = 5
DEFAULT_MAX_TRACK_USES = 3
DEFAULT_MAXIMUM_TEMPO_ADJUSTMENT_FRACTION = 0.005
DEFAULT_PREFIX_SECONDS = 5.0
DEFAULT_SUFFIX_SECONDS = 8.0


def export_blind_vocal_ml_control_study(
    dataset_directory,
    training_run_directory,
    output_directory,
    *,
    split="validation",
    pair_count=DEFAULT_PAIR_COUNT,
    minimum_mean_vocal_strength=0.15,
    max_track_uses=DEFAULT_MAX_TRACK_USES,
    maximum_tempo_adjustment_fraction=DEFAULT_MAXIMUM_TEMPO_ADJUSTMENT_FRACTION,
    analysis_location=Path("output") / "pre_analysis",
    blind_seed=DEFAULT_BLIND_SEED,
    prefix_seconds=DEFAULT_PREFIX_SECONDS,
    suffix_seconds=DEFAULT_SUFFIX_SECONDS,
    analysis=None,
    bridge_extractor=extract_aligned_vocal_bridge,
):
    """Export a vocal-active blind comparison of epoch 0 and the best checkpoint."""
    dataset_directory = Path(dataset_directory).resolve()
    training_run_directory = Path(training_run_directory).resolve()
    output_directory = Path(output_directory).resolve()
    split = str(split)
    if split not in SUPPORTED_SPLITS:
        raise ValueError(f"split must be one of {SUPPORTED_SPLITS}")
    if output_directory.exists():
        raise FileExistsError(f"Study output already exists: {output_directory}")
    if int(pair_count) < 1 or int(max_track_uses) < 1:
        raise ValueError("pair_count and max_track_uses must be at least 1")
    if not 0.0 <= float(minimum_mean_vocal_strength) <= 1.0:
        raise ValueError("minimum_mean_vocal_strength must be in [0, 1]")
    if not 0.0 <= float(maximum_tempo_adjustment_fraction) < 1.0:
        raise ValueError("maximum_tempo_adjustment_fraction must be in [0, 1)")
    if float(prefix_seconds) < 0 or float(suffix_seconds) < 0:
        raise ValueError("prefix_seconds and suffix_seconds must be non-negative")

    dataset_manifest_path = dataset_directory / "manifest.json"
    dataset = VocalFeatureControlDataset(dataset_directory, split)
    learned_model, model_config, model_provenance, objective_config, training_sample_rate = (
        _load_best_vocal_model(training_run_directory)
    )
    _validate_run_dataset(model_provenance, dataset.manifest, dataset_manifest_path)
    baseline_model = VocalFeatureControlMLP(model_config).eval()

    selectable = []
    for dataset_index, example in enumerate(dataset.examples):
        statistics = _vocal_statistics(
            dataset.features_a[dataset_index], dataset.features_b[dataset_index]
        )
        if (
            statistics["source_mean_strength"] < float(minimum_mean_vocal_strength)
            or statistics["target_mean_strength"] < float(minimum_mean_vocal_strength)
        ):
            continue
        candidate, historical_score = _load_candidate_verified(example)
        tempo_adjustment_fraction = abs(
            float(candidate["source_bpm"]) / float(candidate["target_bpm"]) - 1.0
        )
        selectable.append(
            {
                "dataset_index": dataset_index,
                "example": example,
                "candidate": candidate,
                "historical_score": historical_score,
                "vocal_statistics": statistics,
                "tempo_adjustment_fraction": tempo_adjustment_fraction,
            }
        )
    selected = _select_vocal_examples(
        selectable,
        pair_count=int(pair_count),
        max_track_uses=int(max_track_uses),
        maximum_tempo_adjustment_fraction=float(maximum_tempo_adjustment_fraction),
    )

    renderer_kwargs = {
        "lowpass_cutoff_hz": float(model_provenance["renderer"]["lowpass_cutoff_hz"]),
    }
    proxy_renderer = DifferentiableVocalAwareRenderer(
        sample_rate=training_sample_rate,
        lowpass_kernel_size=int(model_provenance["renderer"]["lowpass_kernel_size"]),
        **renderer_kwargs,
    )
    full_renderer = DifferentiableVocalAwareRenderer(
        sample_rate=DEFAULT_SAMPLE_RATE,
        lowpass_kernel_size=511,
        **renderer_kwargs,
    )
    objective = VocalAwareTransitionObjective(
        objective_config,
        energy_frames=SEQUENCE_LENGTH,
    )
    analysis = analysis or PreAnalysis(str(Path(analysis_location)) + os.sep)
    rng = random.Random(int(blind_seed))
    output_directory.mkdir(parents=True)
    public_pairs = []
    answer_pairs = []

    for study_index, selected_item in enumerate(selected, start=1):
        dataset_index = selected_item["dataset_index"]
        example = selected_item["example"]
        candidate = selected_item["candidate"]
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
            source, target, source_vocal, target_vocal
        )
        features_a = torch.from_numpy(dataset.features_a[dataset_index])
        features_b = torch.from_numpy(dataset.features_b[dataset_index])
        global_features = torch.from_numpy(dataset.global_features[dataset_index])
        with torch.no_grad():
            baseline = baseline_model(features_a, features_b, global_features)
            learned = learned_model(features_a, features_b, global_features)

        proxy_audio = tuple(
            torch.from_numpy(
                librosa.resample(
                    item,
                    orig_sr=DEFAULT_SAMPLE_RATE,
                    target_sr=training_sample_rate,
                    axis=-1,
                    res_type="soxr_hq",
                ).astype(np.float32, copy=False)
            )
            for item in (source, target, source_vocal, target_vocal)
        )
        with torch.no_grad():
            baseline_proxy = proxy_renderer(
                *proxy_audio,
                baseline.mix_position,
                baseline.low_end_position,
                baseline.vocal_position,
                baseline.vocal_duck_a,
                baseline.vocal_duck_b,
            )
            learned_proxy = proxy_renderer(
                *proxy_audio,
                learned.mix_position,
                learned.low_end_position,
                learned.vocal_position,
                learned.vocal_duck_a,
                learned.vocal_duck_b,
            )
            baseline_terms = objective(
                baseline_proxy, *proxy_audio, features_a, features_b
            )
            learned_terms = objective(
                learned_proxy, *proxy_audio, features_a, features_b
            )
            full_audio = tuple(
                torch.from_numpy(item)
                for item in (source, target, source_vocal, target_vocal)
            )
            baseline_transition = full_renderer(
                *full_audio,
                baseline.mix_position,
                baseline.low_end_position,
                baseline.vocal_position,
                baseline.vocal_duck_a,
                baseline.vocal_duck_b,
            ).audio.numpy()
            learned_transition = full_renderer(
                *full_audio,
                learned.mix_position,
                learned.low_end_position,
                learned.vocal_position,
                learned.vocal_duck_a,
                learned.vocal_duck_b,
            ).audio.numpy()

        prefix = geometry["source_audio"][
            ...,
            max(
                0,
                int(geometry["source_cut_sample"])
                - int(round(float(prefix_seconds) * DEFAULT_SAMPLE_RATE)),
            ) : int(geometry["source_cut_sample"]),
        ]
        suffix = geometry["target_audio"][
            ...,
            int(geometry["target_cut_sample"]) : min(
                geometry["target_audio"].shape[-1],
                int(geometry["target_cut_sample"])
                + int(round(float(suffix_seconds) * DEFAULT_SAMPLE_RATE)),
            ),
        ]
        baseline_preview = np.concatenate(
            (prefix, baseline_transition, suffix), axis=-1
        ).astype(np.float32, copy=False)
        learned_preview = np.concatenate(
            (prefix, learned_transition, suffix), axis=-1
        ).astype(np.float32, copy=False)
        raw_peak = max(
            float(np.max(np.abs(baseline_preview))),
            float(np.max(np.abs(learned_preview))),
        )
        shared_gain = min(1.0, 0.98 / max(raw_peak, 1e-8))
        baseline_preview *= shared_gain
        learned_preview *= shared_gain

        baseline_label = rng.choice(("A", "B"))
        learned_label = "B" if baseline_label == "A" else "A"
        audio_by_label = {
            baseline_label: baseline_preview,
            learned_label: learned_preview,
        }
        metadata_by_label = {}
        for label in ("A", "B"):
            path = pair_directory / f"{label}.wav"
            _write_audio_atomic(path, audio_by_label[label], DEFAULT_SAMPLE_RATE)
            metadata = _audio_metadata(path, audio_by_label[label], DEFAULT_SAMPLE_RATE)
            metadata["sha256"] = _file_sha256(path)
            metadata_by_label[label] = metadata

        transition_start = int(prefix.shape[-1])
        transition_end = transition_start + int(source.shape[-1])
        historical_metric = rank_rendered_transitions(
            (
                RenderedTransitionInput(
                    candidate_id=candidate["candidate_id"],
                    renderer=BASELINE_METHOD_NAME,
                    audio=baseline_preview,
                    sample_rate=DEFAULT_SAMPLE_RATE,
                    transition_start_sample=transition_start,
                    transition_end_sample=transition_end,
                    transition_length_beats=candidate["transition_length_beats"],
                    bpm=candidate["source_bpm"],
                ),
                RenderedTransitionInput(
                    candidate_id=candidate["candidate_id"],
                    renderer=LEARNED_METHOD_NAME,
                    audio=learned_preview,
                    sample_rate=DEFAULT_SAMPLE_RATE,
                    transition_start_sample=transition_start,
                    transition_end_sample=transition_end,
                    transition_length_beats=candidate["transition_length_beats"],
                    bpm=candidate["source_bpm"],
                ),
            )
        ).to_dict()

        relative_directory = str(pair_directory.relative_to(output_directory))
        public_pairs.append(
            {
                "index": study_index,
                "directory": relative_directory,
                "source_track": candidate["source_track"]["path"],
                "target_track": candidate["target_track"]["path"],
                "transition_length_bars": int(candidate["transition_length_bars"]),
                "tempo_backend": geometry.get("tempo_backend"),
                "tempo_adjustment_fraction": selected_item[
                    "tempo_adjustment_fraction"
                ],
                "vocal_selection": selected_item["vocal_statistics"],
                "files": metadata_by_label,
            }
        )
        answer_pairs.append(
            {
                "index": study_index,
                "directory": relative_directory,
                "mapping": {
                    baseline_label: BASELINE_METHOD_NAME,
                    learned_label: LEARNED_METHOD_NAME,
                },
                "details": {
                    "dataset_example": example,
                    "candidate": candidate,
                    "historical_render_score": selected_item["historical_score"],
                    "geometry": {
                        key: value
                        for key, value in geometry.items()
                        if key
                        not in {
                            "source_audio",
                            "target_audio",
                            "source_vocal_audio",
                            "target_vocal_audio",
                        }
                    },
                    "vocal_selection": selected_item["vocal_statistics"],
                    "tempo_adjustment_fraction": selected_item[
                        "tempo_adjustment_fraction"
                    ],
                    "model": model_provenance,
                    "objective": {
                        "version": VOCAL_OBJECTIVE_VERSION,
                        "baseline_components": _tensor_terms_to_float(baseline_terms),
                        "learned_components": _tensor_terms_to_float(learned_terms),
                        "relative_loss_improvement": float(
                            1.0
                            - float(learned_terms["loss"])
                            / max(float(baseline_terms["loss"]), 1e-12)
                        ),
                    },
                    "controls": {
                        **_control_payload("baseline", baseline),
                        **_control_payload("learned", learned),
                    },
                    "exports": {
                        "files": metadata_by_label,
                        "shared_peak_gain": shared_gain,
                        "raw_joint_peak": raw_peak,
                        "transition_start_sample": transition_start,
                        "transition_end_sample": transition_end,
                    },
                    "historical_metric_comparison": historical_metric,
                },
            }
        )
        print(
            f"[{study_index}/{len(selected)}] {example['example_id']} "
            f"tempo={selected_item['tempo_adjustment_fraction'] * 100:.3f}% "
            f"loss={float(baseline_terms['loss']):.6f}"
            f"->{float(learned_terms['loss']):.6f}",
            flush=True,
        )

    created_at = _utc_now()
    answer_key = {
        "format_version": VOCAL_ML_CONTROL_STUDY_FORMAT_VERSION,
        "blind_seed": int(blind_seed),
        "warning": "Do not inspect before completing ratings.json.",
        "methods": [BASELINE_METHOD_NAME, LEARNED_METHOD_NAME],
        "pairs": answer_pairs,
    }
    public_manifest = {
        "format_version": BLIND_CONTROL_STUDY_FORMAT_VERSION,
        "vocal_ml_control_study_format_version": VOCAL_ML_CONTROL_STUDY_FORMAT_VERSION,
        "study_name": VOCAL_ML_CONTROL_STUDY_NAME,
        "blind": True,
        "status": "completed",
        "created_at_utc": created_at,
        "completed_at_utc": created_at,
        "control_protocol_version": CONTROL_PROTOCOL_VERSION,
        "vocal_control_protocol_version": VOCAL_CONTROL_PROTOCOL_VERSION,
        "objective_version": VOCAL_OBJECTIVE_VERSION,
        "rendering_protocol_version": RENDER_RESULT_FORMAT_VERSION,
        "source_dataset": str(dataset_directory),
        "source_dataset_manifest_sha256": _file_sha256(dataset_manifest_path),
        "dataset_id": dataset.manifest["dataset_id"],
        "dataset_split": split,
        "selection_policy": "vocal_active_distinct_pairs_low_tempo_adjustment_v1",
        "track_exclusions_path": "inherited_from_dataset_export_plus_struggling_name_guard",
        "config": {
            "pair_count": len(selected),
            "minimum_mean_vocal_strength": float(minimum_mean_vocal_strength),
            "max_track_uses": int(max_track_uses),
            "maximum_tempo_adjustment_fraction": float(
                maximum_tempo_adjustment_fraction
            ),
            "blind_seed": int(blind_seed),
            "prefix_seconds": float(prefix_seconds),
            "suffix_seconds": float(suffix_seconds),
            "model_run_id": model_provenance["run_id"],
            "model_checkpoint_sha256": model_provenance["checkpoint_sha256"],
        },
        "answer_key": "answer_key.json",
        "ratings": "ratings.json",
        "pairs": public_pairs,
        "failures": [],
        "interpretation_limit": (
            "Development comparison on the model-selection split with vocal- and "
            "tempo-conditioned selection; not an independent generalization test."
        ),
    }
    _write_json_atomic(output_directory / "answer_key.json", answer_key)
    _write_json_atomic(output_directory / "manifest.json", public_manifest)
    create_control_study_ratings(output_directory)
    _write_readme(output_directory, public_manifest)
    return output_directory / "manifest.json"


def _load_best_vocal_model(training_run_directory):
    training_run_directory = Path(training_run_directory)
    manifest_path = training_run_directory / "manifest.json"
    manifest = _read_json(manifest_path)
    if manifest.get("status") not in {"completed", "early_stopped"}:
        raise ValueError("Training run must be completed or early_stopped")
    if (
        manifest.get("format_version")
        not in SUPPORTED_VOCAL_TRAINING_RUN_FORMAT_VERSIONS
    ):
        raise ValueError("Unsupported vocal training-run format")
    if manifest.get("runner_name") != VOCAL_TRAINING_RUNNER_NAME:
        raise ValueError("Unsupported vocal training runner")
    contract = manifest["contract"]
    model_contract = contract["model"]
    if (
        model_contract.get("name") != VOCAL_FEATURE_CONTROL_MODEL_NAME
        or model_contract.get("format_version")
        != VOCAL_FEATURE_CONTROL_MODEL_FORMAT_VERSION
    ):
        raise ValueError("Unsupported vocal feature-control model")
    checkpoint_record = manifest["files"]["best_checkpoint"]
    checkpoint_path = training_run_directory / checkpoint_record["path"]
    checkpoint_sha256 = _file_sha256(checkpoint_path)
    if checkpoint_sha256 != checkpoint_record["sha256"]:
        raise ValueError("Best-checkpoint SHA-256 differs from the training manifest")
    checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=True)
    if checkpoint.get("run_id") != manifest["run_id"]:
        raise ValueError("Checkpoint run ID differs from the training manifest")
    if int(checkpoint["epoch"]) != int(manifest["best_epoch"]):
        raise ValueError("Best checkpoint epoch differs from the training manifest")
    raw_model_config = model_contract["config"]
    model_config = read_model_config(VocalFeatureControlMLPConfig, raw_model_config)
    model = VocalFeatureControlMLP(model_config)
    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()
    objective_config = VocalAwareTransitionObjectiveConfig(
        **contract["objective"]["config"]
    )
    provenance = {
        "run_id": manifest["run_id"],
        "run_manifest_path": str(manifest_path.resolve()),
        "run_manifest_sha256": _file_sha256(manifest_path),
        "checkpoint_path": str(checkpoint_path.resolve()),
        "checkpoint_sha256": checkpoint_sha256,
        "checkpoint_epoch": int(checkpoint["epoch"]),
        "model_name": model_contract["name"],
        "model_format_version": int(model_contract["format_version"]),
        "model_config": raw_model_config,
        "model_parameter_count": int(manifest["model_parameter_count"]),
        "renderer": contract["renderer"],
        "dataset": contract["dataset"],
    }
    return (
        model,
        model_config,
        provenance,
        objective_config,
        int(contract["renderer"]["sample_rate"]),
    )


def _validate_run_dataset(model_provenance, dataset_manifest, dataset_manifest_path):
    run_dataset = model_provenance["dataset"]
    if run_dataset["dataset_id"] != dataset_manifest["dataset_id"]:
        raise ValueError("Training run and requested dataset IDs differ")
    if run_dataset["manifest_sha256"] != _file_sha256(dataset_manifest_path):
        raise ValueError("Dataset manifest SHA-256 differs from the training contract")


def _select_vocal_examples(
    items,
    *,
    pair_count,
    max_track_uses,
    maximum_tempo_adjustment_fraction,
):
    candidates = []
    for item in items:
        example = item["example"]
        paths = f"{example['source_track']['path']} {example['target_track']['path']}".lower()
        if "struggling" in paths:
            continue
        if item["tempo_adjustment_fraction"] > maximum_tempo_adjustment_fraction:
            continue
        candidates.append(item)
    candidates.sort(
        key=lambda item: (
            item["tempo_adjustment_fraction"],
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
            f"Only {len(selected)} vocal-active, tempo-safe diverse examples satisfy "
            f"the selection; requested {pair_count}"
        )
    return tuple(selected)


def _control_payload(prefix, controls):
    return {
        f"{prefix}_mix_position": controls.mix_position.tolist(),
        f"{prefix}_low_end_position": controls.low_end_position.tolist(),
        f"{prefix}_vocal_position": controls.vocal_position.tolist(),
        f"{prefix}_vocal_duck_a": controls.vocal_duck_a.tolist(),
        f"{prefix}_vocal_duck_b": controls.vocal_duck_b.tolist(),
        f"{prefix}_vocal_gain_a": controls.vocal_gain_a.tolist(),
        f"{prefix}_vocal_gain_b": controls.vocal_gain_b.tolist(),
    }


def _tensor_terms_to_float(terms):
    return {name: float(value.detach().cpu()) for name, value in terms.items()}


def _safe_name(value):
    cleaned = "".join(character if character.isalnum() else "_" for character in value)
    return "_".join(part for part in cleaned.split("_") if part)


def _write_readme(output_directory, manifest):
    text = f"""# Blinder Vocal-MLP-A/B-Hörvergleich

Höre pro Ordner zuerst `A.wav` und `B.wav`, ohne `answer_key.json` zu öffnen.
Beide Varianten verwenden denselben stem-fähigen Renderer, Kontext und
gemeinsamen Peak-Gain. Eine Variante ist die ungelernte Initialisierung von
`vocal_time_shared_mlp_v2`, die andere der beste Checkpoint des letzten Laufs.

Achte besonders auf Vocal-Clash, unnatürlich leise Target-Vocals,
Pegeländerungen mitten in einer Phrase, Energieverlauf, Low-End-Übergabe und
Separation-Artefakte. Bewerte alle fünf Kriterien in `ratings.json` und notiere
`A`, `B` oder `tie` als Präferenz.

Der Satz enthält {len(manifest['pairs'])} vocal-aktive Validation-Paare mit
höchstens {manifest['config']['maximum_tempo_adjustment_fraction'] * 100:.2f} %
Tempoanpassung. Er ist ein Entwicklungs-Gate, kein unabhängiger Testnachweis.
"""
    _write_text_atomic(Path(output_directory) / "README.md", text)


def _read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _write_json_atomic(path, payload):
    _write_text_atomic(
        path,
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    )


def _write_text_atomic(path, text):
    path = Path(path)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        temporary.write_text(text, encoding="utf-8")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _file_sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def build_argument_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset_directory")
    parser.add_argument("training_run_directory")
    parser.add_argument("output_directory")
    parser.add_argument("--split", choices=SUPPORTED_SPLITS, default="validation")
    parser.add_argument("--pair-count", type=int, default=DEFAULT_PAIR_COUNT)
    parser.add_argument("--minimum-mean-vocal-strength", type=float, default=0.15)
    parser.add_argument("--max-track-uses", type=int, default=DEFAULT_MAX_TRACK_USES)
    parser.add_argument(
        "--maximum-tempo-adjustment-fraction",
        type=float,
        default=DEFAULT_MAXIMUM_TEMPO_ADJUSTMENT_FRACTION,
    )
    parser.add_argument("--analysis-location", default=str(Path("output") / "pre_analysis"))
    parser.add_argument("--blind-seed", type=int, default=DEFAULT_BLIND_SEED)
    parser.add_argument("--prefix-seconds", type=float, default=DEFAULT_PREFIX_SECONDS)
    parser.add_argument("--suffix-seconds", type=float, default=DEFAULT_SUFFIX_SECONDS)
    return parser


def main():
    args = build_argument_parser().parse_args()
    manifest_path = export_blind_vocal_ml_control_study(
        args.dataset_directory,
        args.training_run_directory,
        args.output_directory,
        split=args.split,
        pair_count=args.pair_count,
        minimum_mean_vocal_strength=args.minimum_mean_vocal_strength,
        max_track_uses=args.max_track_uses,
        maximum_tempo_adjustment_fraction=args.maximum_tempo_adjustment_fraction,
        analysis_location=args.analysis_location,
        blind_seed=args.blind_seed,
        prefix_seconds=args.prefix_seconds,
        suffix_seconds=args.suffix_seconds,
    )
    print(manifest_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
