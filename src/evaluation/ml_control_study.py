"""Render a blinded Equal-Power versus learned-MLP control study."""

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
from src.bridge import extract_aligned_bridge
from src.control import (
    CONTROL_PROTOCOL_VERSION,
    OBJECTIVE_VERSION,
    DifferentiableTransitionObjective,
    DifferentiableTransitionObjectiveConfig,
    DifferentiableTwoBandRenderer,
)
from src.evaluation.blind_control_study import (
    BLIND_CONTROL_STUDY_FORMAT_VERSION,
    DEFAULT_BLIND_SEED,
)
from src.evaluation.control_probe import _audio_metadata, _write_audio_atomic
from src.evaluation.control_study_ratings import create_control_study_ratings
from src.features import SEQUENCE_LENGTH
from src.ml import FeatureControlDataset, FeatureControlMLP, FeatureControlMLPConfig
from src.pipeline import DEFAULT_SAMPLE_RATE, RENDER_RESULT_FORMAT_VERSION
from src.ranking.rendered_transition import (
    RenderedTransitionInput,
    rank_rendered_transitions,
)


ML_CONTROL_STUDY_FORMAT_VERSION = 1
ML_CONTROL_STUDY_NAME = "blind_equal_power_vs_time_shared_mlp_v1"
LEARNED_METHOD_NAME = "learned_time_shared_mlp_v1_best"
BASELINE_METHOD_NAME = "baseline_equal_power"
SUPPORTED_SPLITS = ("validation", "test")
DEFAULT_PREFIX_SECONDS = 5.0
DEFAULT_SUFFIX_SECONDS = 8.0


def export_blind_ml_control_study(
    dataset_directory,
    training_run_directory,
    output_directory,
    *,
    split="validation",
    analysis_location=Path("output") / "pre_analysis",
    max_examples_per_pair=3,
    example_limit=None,
    blind_seed=DEFAULT_BLIND_SEED,
    prefix_seconds=DEFAULT_PREFIX_SECONDS,
    suffix_seconds=DEFAULT_SUFFIX_SECONDS,
    analysis=None,
    bridge_extractor=extract_aligned_bridge,
):
    """Export blind A/B previews from Equal Power and the best MLP checkpoint."""
    dataset_directory = Path(dataset_directory).resolve()
    training_run_directory = Path(training_run_directory).resolve()
    output_directory = Path(output_directory).resolve()
    split = str(split)
    if split not in SUPPORTED_SPLITS:
        raise ValueError(f"split must be one of {SUPPORTED_SPLITS}")
    if output_directory.exists():
        raise FileExistsError(f"Study output already exists: {output_directory}")
    if int(max_examples_per_pair) < 1:
        raise ValueError("max_examples_per_pair must be at least 1")
    if example_limit is not None and int(example_limit) < 1:
        raise ValueError("example_limit must be at least 1 when set")
    if float(prefix_seconds) < 0 or float(suffix_seconds) < 0:
        raise ValueError("prefix_seconds and suffix_seconds must be non-negative")

    dataset = FeatureControlDataset(dataset_directory, split)
    selected_indices = _select_indices(
        dataset.examples,
        max_examples_per_pair=int(max_examples_per_pair),
        example_limit=None if example_limit is None else int(example_limit),
    )
    model, model_provenance, objective_config, training_sample_rate = _load_best_model(
        training_run_directory
    )
    proxy_renderer = DifferentiableTwoBandRenderer(
        sample_rate=training_sample_rate,
        lowpass_cutoff_hz=float(model_provenance["renderer"]["lowpass_cutoff_hz"]),
        lowpass_kernel_size=int(model_provenance["renderer"]["lowpass_kernel_size"]),
    )
    full_renderer = DifferentiableTwoBandRenderer(
        sample_rate=DEFAULT_SAMPLE_RATE,
        lowpass_cutoff_hz=float(model_provenance["renderer"]["lowpass_cutoff_hz"]),
        lowpass_kernel_size=511,
    )
    objective = DifferentiableTransitionObjective(
        objective_config,
        energy_frames=SEQUENCE_LENGTH,
    )
    analysis = analysis or PreAnalysis(str(Path(analysis_location)) + os.sep)
    rng = random.Random(int(blind_seed))
    output_directory.mkdir(parents=True)

    public_pairs = []
    answer_pairs = []
    for study_index, dataset_index in enumerate(selected_indices, start=1):
        example = dataset.examples[dataset_index]
        candidate, historical_score = _load_candidate_verified(example)
        pair_directory = output_directory / (
            f"{study_index:02d}__{_safe_name(Path(candidate['source_track']['path']).stem)}"
            f"__to__{_safe_name(Path(candidate['target_track']['path']).stem)}"
            f"__{example['example_id'][-6:]}"
        )
        pair_directory.mkdir()
        source, target, geometry = bridge_extractor(
            candidate,
            analysis,
            sample_rate=DEFAULT_SAMPLE_RATE,
            include_context_audio=True,
        )
        source, target = _validate_bridge(source, target)
        features_a = torch.from_numpy(dataset.features_a[dataset_index])
        features_b = torch.from_numpy(dataset.features_b[dataset_index])
        global_features = torch.from_numpy(dataset.global_features[dataset_index])
        with torch.no_grad():
            learned = model(features_a, features_b, global_features)
        baseline_control = torch.linspace(0.0, 1.0, SEQUENCE_LENGTH)

        proxy_source = torch.from_numpy(
            librosa.resample(
                source,
                orig_sr=DEFAULT_SAMPLE_RATE,
                target_sr=training_sample_rate,
                axis=-1,
                res_type="soxr_hq",
            ).astype(np.float32, copy=False)
        )
        proxy_target = torch.from_numpy(
            librosa.resample(
                target,
                orig_sr=DEFAULT_SAMPLE_RATE,
                target_sr=training_sample_rate,
                axis=-1,
                res_type="soxr_hq",
            ).astype(np.float32, copy=False)
        )
        with torch.no_grad():
            baseline_proxy = proxy_renderer(
                proxy_source,
                proxy_target,
                baseline_control,
                baseline_control,
            )
            learned_proxy = proxy_renderer(
                proxy_source,
                proxy_target,
                learned.mix_position,
                learned.low_end_position,
            )
            baseline_terms = objective(
                baseline_proxy,
                proxy_source,
                proxy_target,
                features_a,
                features_b,
            )
            learned_terms = objective(
                learned_proxy,
                proxy_source,
                proxy_target,
                features_a,
                features_b,
            )
            source_tensor = torch.from_numpy(source)
            target_tensor = torch.from_numpy(target)
            baseline_transition = full_renderer(
                source_tensor,
                target_tensor,
                baseline_control,
                baseline_control,
            ).audio.numpy()
            learned_transition = full_renderer(
                source_tensor,
                target_tensor,
                learned.mix_position,
                learned.low_end_position,
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
        historical_metric = rank_rendered_transitions((
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
        )).to_dict()

        relative_directory = str(pair_directory.relative_to(output_directory))
        public_pairs.append({
            "index": study_index,
            "directory": relative_directory,
            "source_track": candidate["source_track"]["path"],
            "target_track": candidate["target_track"]["path"],
            "transition_length_bars": int(candidate["transition_length_bars"]),
            "tempo_backend": geometry.get("tempo_backend"),
            "files": metadata_by_label,
        })
        answer_pairs.append({
            "index": study_index,
            "directory": relative_directory,
            "mapping": {
                baseline_label: BASELINE_METHOD_NAME,
                learned_label: LEARNED_METHOD_NAME,
            },
            "details": {
                "dataset_example": example,
                "candidate": candidate,
                "historical_render_score": historical_score,
                "geometry": {
                    key: value
                    for key, value in geometry.items()
                    if key not in {"source_audio", "target_audio"}
                },
                "model": model_provenance,
                "objective": {
                    "version": OBJECTIVE_VERSION,
                    "baseline_components": _tensor_terms_to_float(baseline_terms),
                    "learned_components": _tensor_terms_to_float(learned_terms),
                    "relative_loss_improvement": float(
                        1.0
                        - float(learned_terms["loss"])
                        / max(float(baseline_terms["loss"]), 1e-12)
                    ),
                },
                "controls": {
                    "baseline_mix_position": baseline_control.tolist(),
                    "baseline_low_end_position": baseline_control.tolist(),
                    "learned_mix_position": learned.mix_position.tolist(),
                    "learned_low_end_position": learned.low_end_position.tolist(),
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
        })
        print(
            f"[{study_index}/{len(selected_indices)}] {example['example_id']} "
            f"loss={float(baseline_terms['loss']):.6f}"
            f"->{float(learned_terms['loss']):.6f}",
            flush=True,
        )

    created_at = _utc_now()
    answer_key = {
        "format_version": ML_CONTROL_STUDY_FORMAT_VERSION,
        "blind_seed": int(blind_seed),
        "warning": "Do not inspect before completing ratings.json.",
        "methods": [BASELINE_METHOD_NAME, LEARNED_METHOD_NAME],
        "pairs": answer_pairs,
    }
    public_manifest = {
        "format_version": BLIND_CONTROL_STUDY_FORMAT_VERSION,
        "ml_control_study_format_version": ML_CONTROL_STUDY_FORMAT_VERSION,
        "study_name": ML_CONTROL_STUDY_NAME,
        "blind": True,
        "status": "completed",
        "created_at_utc": created_at,
        "completed_at_utc": created_at,
        "control_protocol_version": CONTROL_PROTOCOL_VERSION,
        "objective_version": OBJECTIVE_VERSION,
        "rendering_protocol_version": RENDER_RESULT_FORMAT_VERSION,
        "source_batch": str(dataset_directory),
        "source_dataset": str(dataset_directory),
        "dataset_id": dataset.manifest["dataset_id"],
        "dataset_split": split,
        "selection_policy": "dataset_split_all_examples_max_per_directed_pair_v1",
        "track_exclusions_path": "inherited_from_dataset_export",
        "config": {
            "example_count": len(selected_indices),
            "max_examples_per_pair": int(max_examples_per_pair),
            "example_limit": example_limit,
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
            "Development comparison on the model-selection split; not an independent "
            "generalization test."
        ),
    }
    _write_json_atomic(output_directory / "answer_key.json", answer_key)
    _write_json_atomic(output_directory / "manifest.json", public_manifest)
    create_control_study_ratings(output_directory)
    _write_readme(output_directory, public_manifest)
    return output_directory / "manifest.json"


def _load_best_model(training_run_directory):
    manifest_path = training_run_directory / "manifest.json"
    manifest = _read_json(manifest_path)
    if manifest.get("status") not in {"completed", "early_stopped"}:
        raise ValueError("Training run must be completed or early_stopped")
    contract = manifest["contract"]
    if contract["model"]["name"] != "time_shared_mlp_v1":
        raise ValueError("Unsupported feature-control model")
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
    raw_model_config = contract["model"]["config"]
    model_config = read_model_config(FeatureControlMLPConfig, raw_model_config)
    model = FeatureControlMLP(model_config)
    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()
    objective_config = DifferentiableTransitionObjectiveConfig(
        **contract["objective"]["config"]
    )
    provenance = {
        "run_id": manifest["run_id"],
        "run_manifest_path": str(manifest_path),
        "run_manifest_sha256": _file_sha256(manifest_path),
        "checkpoint_path": str(checkpoint_path),
        "checkpoint_sha256": checkpoint_sha256,
        "checkpoint_epoch": int(checkpoint["epoch"]),
        "model_name": contract["model"]["name"],
        "model_config": raw_model_config,
        "model_parameter_count": int(manifest["model_parameter_count"]),
        "renderer": contract["renderer"],
    }
    return model, provenance, objective_config, int(contract["renderer"]["sample_rate"])


def _select_indices(examples, *, max_examples_per_pair, example_limit):
    ordered = sorted(
        enumerate(examples),
        key=lambda item: (
            item[1]["source_track"]["sha256"],
            item[1]["target_track"]["sha256"],
            int(item[1]["candidate_rank"]),
            item[1]["example_id"],
        ),
    )
    selected = []
    pair_counts = {}
    for index, example in ordered:
        pair = (example["source_track"]["sha256"], example["target_track"]["sha256"])
        if pair_counts.get(pair, 0) >= max_examples_per_pair:
            continue
        selected.append(index)
        pair_counts[pair] = pair_counts.get(pair, 0) + 1
        if example_limit is not None and len(selected) >= example_limit:
            break
    if not selected:
        raise ValueError("Dataset split contains no selectable examples")
    return tuple(selected)


def _load_candidate_verified(example):
    pair_manifest_path = Path(example["pair_manifest_path"])
    if _file_sha256(pair_manifest_path) != example["pair_manifest_sha256"]:
        raise ValueError(f"Pair manifest SHA-256 differs from dataset: {pair_manifest_path}")
    pair_manifest = _read_json(pair_manifest_path)
    candidate = next(
        (
            item
            for item in pair_manifest["candidate_generation"]["candidates"]
            if item["candidate_id"] == example["candidate_id"]
        ),
        None,
    )
    if candidate is None:
        raise ValueError(f"Candidate is absent from pair manifest: {example['candidate_id']}")
    historical_score = next(
        (
            item
            for item in pair_manifest["candidate_ranking"]["scores"]
            if item["candidate_id"] == example["candidate_id"]
        ),
        None,
    )
    return candidate, historical_score


def _validate_bridge(source, target):
    source = np.ascontiguousarray(source, dtype=np.float32)
    target = np.ascontiguousarray(target, dtype=np.float32)
    if source.shape != target.shape or source.ndim != 2 or source.shape[0] != 2:
        raise ValueError("Aligned bridge audio must be sample-identical stereo")
    if source.shape[-1] == 0 or not np.isfinite(source).all() or not np.isfinite(target).all():
        raise ValueError("Aligned bridge audio must be non-empty and finite")
    return source, target


def _tensor_terms_to_float(terms):
    return {name: float(value.detach().cpu()) for name, value in terms.items()}


def _safe_name(value):
    cleaned = "".join(character if character.isalnum() else "_" for character in value)
    return "_".join(part for part in cleaned.split("_") if part)


def _write_readme(output_directory, manifest):
    text = f"""# Blinder MLP-Control-A/B-Vergleich

Höre in jedem Paar zuerst `A.wav` und `B.wav`, ohne `answer_key.json`
zu öffnen. Beide Dateien besitzen denselben Kontext und dieselbe gemeinsame
Peak-Absenkung. Eine Variante ist Equal Power, die andere stammt aus dem
besten Checkpoint des Feature→Control-MLP.

Bewerte Sauberkeit, Energieverlauf, Low-End-Übergabe, rhythmische Stabilität,
Vocal-Klarheit und Artefaktfreiheit jeweils von 1 bis 5. Notiere außerdem
`A`, `B` oder `tie` als Präferenz.

Dieser Satz verwendet `{manifest['dataset_split']}` und ist deshalb ein
Entwicklungsvergleich, kein unabhängiger finaler Generalisierungsnachweis.
Der Antwortschlüssel soll erst nach allen {len(manifest['pairs'])} Bewertungen
geöffnet werden.
"""
    _write_text_atomic(output_directory / "README.md", text)


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
    parser.add_argument("--analysis-location", default=str(Path("output") / "pre_analysis"))
    parser.add_argument("--max-examples-per-pair", type=int, default=3)
    parser.add_argument("--example-limit", type=int)
    parser.add_argument("--blind-seed", type=int, default=DEFAULT_BLIND_SEED)
    parser.add_argument("--prefix-seconds", type=float, default=DEFAULT_PREFIX_SECONDS)
    parser.add_argument("--suffix-seconds", type=float, default=DEFAULT_SUFFIX_SECONDS)
    return parser


def main():
    args = build_argument_parser().parse_args()
    manifest_path = export_blind_ml_control_study(
        args.dataset_directory,
        args.training_run_directory,
        args.output_directory,
        split=args.split,
        analysis_location=args.analysis_location,
        max_examples_per_pair=args.max_examples_per_pair,
        example_limit=args.example_limit,
        blind_seed=args.blind_seed,
        prefix_seconds=args.prefix_seconds,
        suffix_seconds=args.suffix_seconds,
    )
    print(manifest_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
