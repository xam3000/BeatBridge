"""Export a blinded four-model listening test on shared Dataset-v1 stimuli.

The three fixed-length models use their Dataset-v1 features. The variable model
uses its own Feature Protocol 2 inputs derived from the same validation
candidates. The result is a shared-stimulus listening comparison, not a pooled
statistical benchmark across incompatible training contracts.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import random

import numpy as np
from src.tempo.cue_alignment import LEGACY_ALIGNMENT
import torch

from src.analysis.pre_analysis import PreAnalysis
from src.bridge import extract_aligned_vocal_bridge
from src.control import DifferentiableVocalAwareRenderer
from src.evaluation.all_models_control_study import (
    ALL_MODELS_STUDY_FORMAT_VERSION,
    RATING_CRITERIA,
    _empty_ratings,
    _load_control_model,
    _render_equal_power,
    _render_loaded_model,
    _safe_name,
    _select_examples,
    build_listening_page,
)
from src.evaluation.control_probe import _audio_metadata, _write_audio_atomic
from src.evaluation.ml_control_study import _file_sha256, _load_candidate_verified
from src.evaluation.nontrivial_model_examples import _load_variable_tcn
from src.evaluation.vocal_objective_study import _validate_bridge, _vocal_statistics
from src.features.extract_track import FeatureNormalizationStats, extract_or_load_track_features
from src.features.variable_extract import extract_variable_track_window
from src.features.variable_global_pair import build_variable_global_pair_features
from src.features.vocal import extract_or_load_vocal_stem_with_backend
from src.ml import VocalFeatureControlDataset
from src.pipeline import DEFAULT_SAMPLE_RATE, PROJECT_ROOT


DEFAULT_V1_DATASET = Path(
    "output/datasets/feature_protocol_v1_extended_bpm145_165_top10_4bar_split_20260805"
)
DEFAULT_V2_DATASET = Path(
    "output/datasets/prive_scantraxx_extension_variable_v2_fp2_roformer_2-4-6-8bar_top1x3_split20260923_run02_local_four_four"
)
DEFAULT_RUN_ROOT = Path("output/training_runs")
DEFAULT_OUTPUT = Path("output/four_models_shared_2pairs_validation_20260927")
DEFAULT_ANALYSIS_ROOT = Path("output/pre_analysis")
DEFAULT_CACHE_ROOT = Path("output/feature_cache")
DEFAULT_VOCAL_CACHE_ROOT = Path("output/feature_cache")
DEFAULT_SEED = 20260927
MODEL_RUNS = {
    "time_shared_mlp_v1": "prive_scantraxx_all_models_dataset_v1_time_shared_mlp_v1_20260926_run01",
    "vocal_time_shared_mlp_v2": "prive_scantraxx_all_models_dataset_v1_vocal_time_shared_mlp_v2_20260926_run01",
    "tcn_bilstm_transition_control_v1": "prive_scantraxx_all_models_dataset_v1_tcn_bilstm_transition_control_v1_20260926_run01",
    "variable_tcn_bilstm_transition_control_v1": "prive_scantraxx_all_models_dataset_v2_variable_tcn_bilstm_20260926_run01",
}


def export_four_model_listening_study(
    *,
    v1_dataset=DEFAULT_V1_DATASET,
    v2_dataset=DEFAULT_V2_DATASET,
    training_runs_root=DEFAULT_RUN_ROOT,
    output_directory=DEFAULT_OUTPUT,
    analysis_location=DEFAULT_ANALYSIS_ROOT,
    feature_cache_root=DEFAULT_CACHE_ROOT,
    vocal_cache_root=DEFAULT_VOCAL_CACHE_ROOT,
    pair_count=2,
    seed=DEFAULT_SEED,
    smoke_only=False,
    allow_track_reuse=False,
):
    """Render four trained models plus Equal Power on identical 4-bar pairs."""
    v1_dataset = Path(v1_dataset).resolve()
    v2_dataset = Path(v2_dataset).resolve()
    training_runs_root = Path(training_runs_root).resolve()
    output_directory = Path(output_directory).resolve()
    if output_directory.exists():
        raise FileExistsError(f"Study output already exists: {output_directory}")

    v1_manifest_path = v1_dataset / "manifest.json"
    v2_manifest_path = v2_dataset / "manifest.json"
    v1_manifest = _read_json(v1_manifest_path)
    v2_manifest = _read_json(v2_manifest_path)
    dataset = VocalFeatureControlDataset(v1_dataset, "validation")
    fixed_runs = [training_runs_root / MODEL_RUNS[name] for name in tuple(MODEL_RUNS)[:3]]
    fixed_models = tuple(
        _load_control_model(run.resolve(), dataset.manifest, v1_manifest_path)
        for run in fixed_runs
    )
    variable_run = training_runs_root / MODEL_RUNS["variable_tcn_bilstm_transition_control_v1"]
    variable_model, variable_provenance, variable_renderer_contract = _load_variable_tcn(
        variable_run.resolve(), v2_dataset
    )

    selectable = []
    for index, example in enumerate(dataset.examples):
        vocal = _vocal_statistics(dataset.features_a[index], dataset.features_b[index])
        candidate, historical_score = _load_candidate_verified(example)
        tempo_fraction = abs(float(candidate["source_bpm"]) / float(candidate["target_bpm"]) - 1.0)
        if vocal["source_mean_strength"] < 0.15 or vocal["target_mean_strength"] < 0.15:
            continue
        if tempo_fraction > 0.005:
            continue
        selectable.append({
            "dataset_index": index,
            "example": example,
            "candidate": candidate,
            "historical_score": historical_score,
            "vocal_statistics": vocal,
            "tempo_adjustment_fraction": tempo_fraction,
        })
    requested_count = 1 if smoke_only else int(pair_count)
    if allow_track_reuse:
        selected = _select_balanced_examples(selectable, requested_count)
    else:
        selected = _select_examples(
            selectable, requested_count, max_track_uses=1
        )

    norm = v2_manifest["normalization"]
    normalization = FeatureNormalizationStats(
        spectral_flux_log1p_p99=float(norm["spectral_flux_log1p_p99"]),
        onset_strength_log1p_p99=float(norm["onset_strength_log1p_p99"]),
        stats_id=str(norm["stats_id"]),
    )
    analysis = PreAnalysis(str(Path(analysis_location)) + "\\")
    artifact_cache = {}
    prepared = []
    for item in selected:
        candidate = item["candidate"]
        source_artifact = _feature_artifact(
            candidate["source_track"], target_bpm=None, cache=artifact_cache,
            feature_cache_root=feature_cache_root, vocal_cache_root=vocal_cache_root,
            analysis=analysis,
        )
        target_artifact = _feature_artifact(
            candidate["target_track"], target_bpm=float(candidate["source_bpm"]), cache=artifact_cache,
            feature_cache_root=feature_cache_root, vocal_cache_root=vocal_cache_root,
            analysis=analysis,
        )
        source_cue = int(candidate["source_cutpoint"]["sample"])
        target_cue = int(round(
            int(candidate["target_cutpoint"]["sample"])
            * float(candidate["target_bpm"]) / float(candidate["source_bpm"])
        ))
        features_a = extract_variable_track_window(
            source_artifact, source_cue, role="source", normalization=normalization,
            transition_length_bars=4, sequence_length=32,
        )
        features_b = extract_variable_track_window(
            target_artifact, target_cue, role="target", normalization=normalization,
            transition_length_bars=4, sequence_length=32,
        )
        global_features = build_variable_global_pair_features(
            features_a, features_b, transition_length_bars=4, sequence_length=32,
            bpm_a=float(candidate["source_bpm"]), bpm_b=float(candidate["target_bpm"]),
            artifact_a=source_artifact, artifact_b=target_artifact,
            cue_sample_a=source_cue, cue_sample_b=target_cue,
        )
        prepared.append((item, source_artifact, target_artifact, features_a, features_b, global_features))

    methods = (
        {"method_id": "baseline_equal_power", "display_name": "Equal Power", "family": "baseline"},
        *({"method_id": model.method_id, "display_name": model.display_name,
           "family": model.family, "provenance": model.provenance} for model in fixed_models),
        {"method_id": "variable_tcn_bilstm_transition_control_v1_best",
         "display_name": "Variable TCN/BiLSTM v1", "family": "variable_tcn_bilstm_transition_control_v1",
         "provenance": variable_provenance},
    )
    labels = tuple(chr(ord("A") + index) for index in range(len(methods)))
    rng = random.Random(int(seed))
    if not smoke_only:
        output_directory.mkdir(parents=True)
    public_pairs, answer_pairs = [], []
    try:
        for study_index, row in enumerate(prepared, start=1):
            item, source_artifact, target_artifact, features_a, features_b, global_features = row
            example, candidate = item["example"], item["candidate"]
            pair_dir = output_directory / (
                f"{study_index:02d}__{_safe_name(Path(candidate['source_track']['path']).stem)}"
                f"__to__{_safe_name(Path(candidate['target_track']['path']).stem)}__{example['example_id'][-6:]}"
            )
            if not smoke_only:
                pair_dir.mkdir()
            source, target, source_vocal, target_vocal, geometry = extract_aligned_vocal_bridge(
                candidate, analysis, sample_rate=DEFAULT_SAMPLE_RATE, include_context_audio=True,
                feature_cache_root=feature_cache_root,
                source_vocal_artifact=_vocal_artifact(candidate["source_track"], vocal_cache_root),
                target_vocal_artifact=_vocal_artifact(candidate["target_track"], vocal_cache_root),
                tempo_alignment=LEGACY_ALIGNMENT,
            )
            source, target = _validate_bridge(source, target)
            feature_inputs = (
                torch.from_numpy(dataset.features_a[item["dataset_index"]]),
                torch.from_numpy(dataset.features_b[item["dataset_index"]]),
                torch.from_numpy(dataset.global_features[item["dataset_index"]]),
            )
            audio_inputs = tuple(torch.from_numpy(value) for value in (source, target, source_vocal, target_vocal))
            with torch.no_grad():
                transitions = {"baseline_equal_power": _render_equal_power(source, target)}
                for model in fixed_models:
                    transitions[model.method_id] = _render_loaded_model(model, feature_inputs, audio_inputs)
                variable_transition = _render_variable(
                    variable_model, variable_renderer_contract,
                    (source, target, source_vocal, target_vocal),
                    (features_a, features_b, global_features),
                )
            transitions["variable_tcn_bilstm_transition_control_v1_best"] = variable_transition
            if smoke_only:
                expected_methods = {method["method_id"] for method in methods}
                if set(transitions) != expected_methods:
                    raise ValueError("Smoke test did not render every expected method")
                for method_id, audio in transitions.items():
                    if audio.ndim != 2 or audio.shape[0] != 2 or not np.isfinite(audio).all():
                        raise ValueError(f"Smoke render is invalid for {method_id}")
                print(
                    f"SMOKE OK {example['example_id']} methods={len(transitions)} "
                    f"samples={source.shape[-1]}", flush=True,
                )
                return None
            prefix = geometry["source_audio"][..., max(0, int(geometry["source_cut_sample"]) - 5 * DEFAULT_SAMPLE_RATE):int(geometry["source_cut_sample"])]
            suffix = geometry["target_audio"][..., int(geometry["target_cut_sample"]):int(geometry["target_cut_sample"]) + 8 * DEFAULT_SAMPLE_RATE]
            previews = {
                method_id: np.concatenate((prefix, _fit_transition_length(transition, source.shape[-1]), suffix), axis=-1).astype(np.float32, copy=False)
                for method_id, transition in transitions.items()
            }
            raw_peak = max(float(np.max(np.abs(audio))) for audio in previews.values())
            shared_gain = min(1.0, 0.98 / max(raw_peak, 1e-8))
            for audio in previews.values():
                audio *= shared_gain
            order = [method["method_id"] for method in methods]
            rng.shuffle(order)
            mapping = dict(zip(labels, order, strict=True))
            files = {}
            for label in labels:
                audio = previews[mapping[label]]
                path = pair_dir / f"{label}.wav"
                _write_audio_atomic(path, audio, DEFAULT_SAMPLE_RATE)
                metadata = _audio_metadata(path, audio, DEFAULT_SAMPLE_RATE)
                metadata["sha256"] = _file_sha256(path)
                files[label] = metadata
            relative = str(pair_dir.relative_to(output_directory))
            public_pairs.append({
                "index": study_index, "directory": relative,
                "source_track": candidate["source_track"]["path"],
                "target_track": candidate["target_track"]["path"],
                "transition_length_bars": 4,
                "tempo_adjustment_fraction": item["tempo_adjustment_fraction"],
                "labels": list(labels), "files": files,
            })
            answer_pairs.append({
                "index": study_index, "directory": relative, "mapping": mapping,
                "example_id": example["example_id"], "candidate_id": example["candidate_id"],
                "pair_manifest_sha256": example["pair_manifest_sha256"],
                "source_track_sha256": candidate["source_track"]["sha256"],
                "target_track_sha256": candidate["target_track"]["sha256"],
                "shared_peak_gain": shared_gain, "raw_joint_peak": raw_peak,
                "vocal_selection": item["vocal_statistics"],
                "feature_protocol_2": {
                    "stats_id": normalization.stats_id,
                    "source_feature_manifest_sha256": _json_sha256(source_artifact.manifest),
                    "target_feature_manifest_sha256": _json_sha256(target_artifact.manifest),
                    "source_vocal_artifact_sha256": source_artifact.manifest["vocal_artifact"]["artifact_sha256"],
                    "target_vocal_artifact_sha256": target_artifact.manifest["vocal_artifact"]["artifact_sha256"],
                },
            })
            print(f"[{study_index}/{len(prepared)}] {example['example_id']} variants={len(methods)}", flush=True)

        manifest = {
            "format_version": ALL_MODELS_STUDY_FORMAT_VERSION,
            "study_name": "blind_four_model_shared_stimuli_v1",
            "blind": True, "status": "completed",
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "dataset_id": v1_manifest["dataset_id"], "dataset_manifest_sha256": _file_sha256(v1_manifest_path),
            "dataset_split": "validation", "variable_dataset_id": v2_manifest["dataset_id"],
            "variable_dataset_manifest_sha256": _file_sha256(v2_manifest_path),
            "method_count": len(methods), "method_labels": list(labels),
            "pair_count": len(public_pairs), "criteria": list(RATING_CRITERIA),
            "pairs": public_pairs, "answer_key": "answer_key.json", "ratings": "ratings.json", "player": "index.html",
            "selection": {
                "policy": "balanced_round_robin_distinct_candidate_cues" if allow_track_reuse else "unique_tracks",
                "eligible_validation_examples": len(selectable),
                "distinct_track_pairs_selected": len({
                    (row[0]["candidate"]["source_track"]["sha256"],
                     row[0]["candidate"]["target_track"]["sha256"])
                    for row in prepared
                }),
                "examples_per_track_pair": _selected_pair_counts(prepared),
                "unique_candidate_cues": len({
                    (row[0]["candidate"]["candidate_id"],
                     row[0]["example"]["aligned_source_cue_sample"],
                     row[0]["example"]["aligned_target_cue_sample"])
                    for row in prepared
                }),
                "track_reuse_note": (
                    "Song pairs repeat because the eligible validation pool contains only five directed track pairs; "
                    "candidate cues are distinct, so ratings within one song pair are correlated."
                    if allow_track_reuse else None
                ),
            },
            "contracts": {
                "fixed_models": "Dataset-v1 / Feature Protocol 1 / four bars",
                "variable_model": "Dataset-v2 / Feature Protocol 2 / four bars; features recomputed on same v1 validation cues with v2 training-only normalization",
                "rendering": "same aligned 44.1-kHz mix/stem bridge; all model renderers and the Equal Power baseline are evaluated directly at 44.1 kHz with FIR kernels scaled to preserve the training filter time constants (variable contract kernel 127 at 11.025 kHz rendered as kernel 511 at 44.1 kHz), so every candidate is full-band",
                "shared_stimuli": "same source-target pair, cues, context, and joint peak gain for all labels",
            },
            "interpretation_limit": "Exploratory shared-stimulus listening test only; variable model is out-of-domain on Dataset-v1 tracks and model inputs/renderers follow incompatible training contracts. Do not pool as a protocol-matched benchmark.",
            "source_policy": "Audio WAVs and model weights are local outputs; neither is a source-code commit artifact.",
        }
        answer_key = {
            "format_version": ALL_MODELS_STUDY_FORMAT_VERSION,
            "warning": "Do not inspect before completing ratings.json.",
            "methods": list(methods), "pairs": answer_pairs,
            "dataset_manifests": {
                "fixed_models": {"path": str(v1_manifest_path), "sha256": _file_sha256(v1_manifest_path)},
                "variable_model": {"path": str(v2_manifest_path), "sha256": _file_sha256(v2_manifest_path)},
            },
        }
        _write_json(output_directory / "manifest.json", manifest)
        _write_json(output_directory / "answer_key.json", answer_key)
        _write_json(output_directory / "ratings.json", _empty_ratings(manifest))
        (output_directory / "index.html").write_text(build_listening_page(manifest), encoding="utf-8")
        (output_directory / "README.md").write_text(_readme(manifest), encoding="utf-8")
    except Exception:
        if output_directory.exists():
            _write_json(output_directory / "INCOMPLETE.json", {"status": "incomplete"})
        raise
    return output_directory / "index.html"


def _feature_artifact(track, *, target_bpm, cache, feature_cache_root, vocal_cache_root, analysis):
    path = Path(track["path"])
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    key = (str(path.resolve()), target_bpm)
    if key not in cache:
        def load_stem(song_path, **kwargs):
            kwargs.pop("cache_root", None)
            return extract_or_load_vocal_stem_with_backend(
                song_path, backend="roformer", cache_root=vocal_cache_root, **kwargs,
            )

        artifact = extract_or_load_track_features(
            path, cache_root=feature_cache_root, analysis=analysis,
            target_bpm=target_bpm, vocal_backend="roformer",
            vocal_stem_loader=load_stem,
        )
        if artifact.manifest["source_sha256"] != track["sha256"]:
            raise ValueError(f"Feature Protocol 2 source SHA differs: {path}")
        cache[key] = artifact
    return cache[key]


def _select_balanced_examples(items, count):
    """Balance distinct candidate/cue identities across ordered track pairs."""
    count = int(count)
    if count < 1:
        raise ValueError("pair_count must be at least one")
    groups = {}
    seen = set()
    for item in items:
        example = item["example"]
        candidate = item["candidate"]
        identity = (
            str(candidate["candidate_id"]),
            int(example["aligned_source_cue_sample"]),
            int(example["aligned_target_cue_sample"]),
        )
        if identity in seen:
            continue
        seen.add(identity)
        track_pair = (
            str(candidate["source_track"]["sha256"]),
            str(candidate["target_track"]["sha256"]),
        )
        groups.setdefault(track_pair, []).append(item)
    group_order = sorted(groups)
    for key in group_order:
        groups[key].sort(key=lambda item: (
            item["tempo_adjustment_fraction"],
            -item["vocal_statistics"]["selection_score"],
            int(item["example"]["candidate_rank"]),
            item["example"]["example_id"],
        ))
    selected = []
    depth = 0
    while len(selected) < count:
        progressed = False
        for key in group_order:
            if depth < len(groups[key]):
                selected.append(groups[key][depth])
                progressed = True
                if len(selected) == count:
                    break
        if not progressed:
            raise ValueError(
                f"Only {len(selected)} distinct eligible candidate cues; requested {count}"
            )
        depth += 1
    return tuple(selected)


def _selected_pair_counts(prepared):
    from collections import Counter
    counts = Counter(
        (row[0]["candidate"]["source_track"]["sha256"][:12],
         row[0]["candidate"]["target_track"]["sha256"][:12])
        for row in prepared
    )
    return [
        {"source_sha256_prefix": pair[0], "target_sha256_prefix": pair[1], "count": count}
        for pair, count in sorted(counts.items())
    ]


def _vocal_artifact(track, feature_cache_root):
    path = Path(track["path"])
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return extract_or_load_vocal_stem_with_backend(
        path, backend="roformer", cache_root=feature_cache_root,
        source_sha256=track["sha256"],
    )


def _render_variable(model, contract, audio, features):
    # Render directly at the study's 44.1 kHz like every other candidate.
    # Kernel 511 mirrors the fixed-model renderers here (contract kernel 127 at
    # 11,025 Hz keeps its time constant when scaled 4x). The previous path
    # round-tripped all stems through 11,025 Hz, band-limiting the bridge to
    # below 5.5 kHz (measured muffle in 20/20 examples on 2026-11-05).
    renderer = DifferentiableVocalAwareRenderer(
        sample_rate=DEFAULT_SAMPLE_RATE,
        lowpass_cutoff_hz=float(contract["lowpass_cutoff_hz"]),
        lowpass_kernel_size=511,
    )
    feature_a, feature_b, global_features = features
    output = model(
        torch.from_numpy(feature_a), torch.from_numpy(feature_b),
        torch.from_numpy(global_features), transition_length_bars=4,
        length_condition=torch.tensor([0.5], dtype=torch.float32),
    )
    mixed = renderer(
        *(torch.from_numpy(value) for value in audio),
        output.mix_position, output.low_end_position, output.vocal_position,
        output.vocal_duck_a, output.vocal_duck_b,
    ).audio.numpy()
    return np.asarray(mixed, dtype=np.float32)


def _fit_transition_length(audio, samples):
    audio = np.asarray(audio, dtype=np.float32)
    samples = int(samples)
    if audio.shape[-1] > samples:
        return audio[..., :samples]
    if audio.shape[-1] < samples:
        return np.pad(audio, ((0, 0), (0, samples - audio.shape[-1])))
    return audio


def _json_sha256(value):
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _write_json(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _readme(manifest):
    return (
        "# Blinder Vier-Modell-Hörtest\n\n"
        f"Vergleiche pro Übergang {manifest['method_count']} zufällig beschriftete Varianten. "
        "Alle Labels einer Zeile verwenden dieselben vier 4-Takt-Stimuli, Cuepoints, "
        "Kontextstücke und gemeinsamen Peak-Gain. Bewertungen lokal eingeben und als "
        "ratings.json herunterladen; answer_key.json erst danach öffnen.\n\n"
        "Wichtig: Der variable Checkpoint ist auf Dataset-v2/Feature Protocol 2 trainiert, "
        "während die übrigen drei Modelle Dataset-v1/Feature Protocol 1 verwenden. Seine "
        "Features wurden für dieselben Dataset-v1-Validierungs-Cues mit der "
        "v2-Trainingsnormalisierung berechnet. Das ist ein explorativer gemeinsamer Stimulusvergleich, "
        "kein protokollgleicher oder unabhängiger Generalisierungstest.\n"
    )


def build_argument_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--v1-dataset", default=str(DEFAULT_V1_DATASET))
    parser.add_argument("--v2-dataset", default=str(DEFAULT_V2_DATASET))
    parser.add_argument("--training-runs-root", default=str(DEFAULT_RUN_ROOT))
    parser.add_argument("--output-directory", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--analysis-location", default=str(DEFAULT_ANALYSIS_ROOT))
    parser.add_argument("--feature-cache-root", default=str(DEFAULT_CACHE_ROOT))
    parser.add_argument("--vocal-cache-root", default=str(DEFAULT_VOCAL_CACHE_ROOT))
    parser.add_argument("--pair-count", type=int, default=2)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--smoke-only", action="store_true")
    parser.add_argument("--allow-track-reuse", action="store_true")
    return parser


def main(argv=None):
    args = build_argument_parser().parse_args(argv)
    path = export_four_model_listening_study(
        v1_dataset=args.v1_dataset, v2_dataset=args.v2_dataset,
        training_runs_root=args.training_runs_root, output_directory=args.output_directory,
        analysis_location=args.analysis_location, feature_cache_root=args.feature_cache_root,
        vocal_cache_root=args.vocal_cache_root,
        pair_count=args.pair_count, seed=args.seed, smoke_only=args.smoke_only,
        allow_track_reuse=args.allow_track_reuse,
    )
    print(path)


if __name__ == "__main__":
    main()
