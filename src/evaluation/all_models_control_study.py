"""Build a blinded, multi-way listening comparison for trained control models.

The comparison deliberately uses one Dataset-v1 split and the same candidate,
context, audio alignment, and joint peak gain for every variant in a row.  A
cue-point ranker is not a control model and therefore cannot be rendered as an
additional variant here.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import html
import json
import os
from pathlib import Path
import random
import uuid

import numpy as np
import torch

from src.ml.control_initialization import read_model_config

from src.analysis.pre_analysis import PreAnalysis
from src.bridge import extract_aligned_vocal_bridge
from src.control import (
    DifferentiableFullBandTransitionRenderer,
    DifferentiableTwoBandRenderer,
    DifferentiableVocalAwareRenderer,
)
from src.evaluation.control_probe import _audio_metadata, _write_audio_atomic
from src.evaluation.ml_control_study import (
    _file_sha256,
    _load_best_model,
    _load_candidate_verified,
)
from src.evaluation.vocal_ml_control_study import (
    _load_best_vocal_model,
    _validate_run_dataset,
)
from src.evaluation.vocal_objective_study import _validate_bridge, _vocal_statistics
from src.ml import (
    TCNBiLSTMTransitionControl,
    TCNBiLSTMTransitionControlConfig,
    VocalFeatureControlDataset,
)
from src.pipeline import DEFAULT_SAMPLE_RATE


ALL_MODELS_STUDY_FORMAT_VERSION = 1
ALL_MODELS_STUDY_NAME = "blind_all_compatible_control_models_v1"
SUPPORTED_SPLITS = ("validation", "test")
DEFAULT_PAIR_COUNT = 5
DEFAULT_PREFIX_SECONDS = 5.0
DEFAULT_SUFFIX_SECONDS = 8.0
DEFAULT_BLIND_SEED = 20260904
RATING_CRITERIA = (
    "cleanliness",
    "energy_shape",
    "low_end_handover",
    "vocal_clarity",
    "artifact_freedom",
)


@dataclass(frozen=True)
class LoadedControlModel:
    method_id: str
    display_name: str
    family: str
    model: torch.nn.Module
    provenance: dict


def discover_representative_runs(training_runs_root, dataset_directory):
    """Return one best compatible real run per supported model family.

    Runs must declare the exact Dataset-v1 ID and manifest SHA.  Within one
    family, the lowest finite validation loss wins; path order is the stable
    tie breaker.  TCN runs without the full-band renderer are excluded because
    their rendering contract is not comparable to the completed architecture.
    """

    training_runs_root = Path(training_runs_root)
    dataset_directory = Path(dataset_directory).resolve()
    dataset_manifest_path = dataset_directory / "manifest.json"
    dataset_manifest = _read_json(dataset_manifest_path)
    dataset_id = dataset_manifest.get("dataset_id")
    dataset_sha = _file_sha256(dataset_manifest_path)
    supported = {
        "time_shared_mlp_v1",
        "vocal_time_shared_mlp_v2",
        "tcn_bilstm_transition_control_v1",
    }
    candidates: dict[str, list[tuple[float, str, Path]]] = {}
    for manifest_path in sorted(training_runs_root.glob("*/manifest.json")):
        manifest = _read_json(manifest_path)
        if manifest.get("status") not in {"completed", "early_stopped"}:
            continue
        contract = manifest.get("contract", {})
        model_contract = contract.get("model", {})
        model_name = model_contract.get("name")
        if model_name not in supported:
            continue
        dataset_contract = contract.get("dataset", {})
        if (
            dataset_contract.get("dataset_id") != dataset_id
            or dataset_contract.get("manifest_sha256") != dataset_sha
        ):
            continue
        if model_name == "tcn_bilstm_transition_control_v1" and (
            contract.get("renderer", {}).get("name")
            != "differentiable_full_band_transition_v1"
        ):
            continue
        loss = manifest.get("best_validation_loss")
        if not isinstance(loss, (int, float)) or not np.isfinite(loss):
            continue
        checkpoint = manifest.get("files", {}).get("best_checkpoint")
        if not isinstance(checkpoint, dict):
            continue
        checkpoint_path = manifest_path.parent / checkpoint.get("path", "")
        if not checkpoint_path.is_file():
            continue
        candidates.setdefault(model_name, []).append(
            (float(loss), str(manifest_path.parent), manifest_path.parent)
        )
    return tuple(
        min(items, key=lambda item: (item[0], item[1]))[2]
        for family in sorted(candidates)
        for items in (candidates[family],)
    )


def export_all_models_control_study(
    dataset_directory,
    training_run_directories,
    output_directory,
    *,
    split="validation",
    pair_count=DEFAULT_PAIR_COUNT,
    minimum_mean_vocal_strength=0.15,
    max_track_uses=3,
    maximum_tempo_adjustment_fraction=0.005,
    analysis_location=Path("output") / "pre_analysis",
    blind_seed=DEFAULT_BLIND_SEED,
    prefix_seconds=DEFAULT_PREFIX_SECONDS,
    suffix_seconds=DEFAULT_SUFFIX_SECONDS,
    analysis=None,
    bridge_extractor=extract_aligned_vocal_bridge,
):
    """Render Equal Power and all supplied supported runs as a blind study."""

    dataset_directory = Path(dataset_directory).resolve()
    output_directory = Path(output_directory).resolve()
    if split not in SUPPORTED_SPLITS:
        raise ValueError(f"split must be one of {SUPPORTED_SPLITS}")
    if output_directory.exists():
        raise FileExistsError(f"Study output already exists: {output_directory}")
    if int(pair_count) < 1 or int(max_track_uses) < 1:
        raise ValueError("pair_count and max_track_uses must be at least 1")
    if float(prefix_seconds) < 0 or float(suffix_seconds) < 0:
        raise ValueError("prefix_seconds and suffix_seconds must be non-negative")

    dataset = VocalFeatureControlDataset(dataset_directory, split)
    dataset_manifest_path = dataset_directory / "manifest.json"
    loaded_models = tuple(
        _load_control_model(Path(run_directory).resolve(), dataset.manifest, dataset_manifest_path)
        for run_directory in training_run_directories
    )
    families = [item.family for item in loaded_models]
    if not loaded_models:
        raise ValueError("At least one compatible training run is required")
    if len(set(families)) != len(families):
        raise ValueError("Supply at most one training run per model family")

    selectable = []
    for dataset_index, example in enumerate(dataset.examples):
        vocal = _vocal_statistics(
            dataset.features_a[dataset_index], dataset.features_b[dataset_index]
        )
        if (
            vocal["source_mean_strength"] < float(minimum_mean_vocal_strength)
            or vocal["target_mean_strength"] < float(minimum_mean_vocal_strength)
        ):
            continue
        candidate, historical_score = _load_candidate_verified(example)
        tempo_fraction = abs(
            float(candidate["source_bpm"]) / float(candidate["target_bpm"]) - 1.0
        )
        if tempo_fraction > float(maximum_tempo_adjustment_fraction):
            continue
        selectable.append({
            "dataset_index": dataset_index,
            "example": example,
            "candidate": candidate,
            "historical_score": historical_score,
            "vocal_statistics": vocal,
            "tempo_adjustment_fraction": tempo_fraction,
        })
    selected = _select_examples(selectable, int(pair_count), int(max_track_uses))

    analysis = analysis or PreAnalysis(str(Path(analysis_location)) + os.sep)
    output_directory.mkdir(parents=True)
    rng = random.Random(int(blind_seed))
    methods = (
        {
            "method_id": "baseline_equal_power",
            "display_name": "Equal Power",
            "family": "baseline",
            "provenance": {"renderer": "DifferentiableTwoBandRenderer"},
        },
        *(
            {
                "method_id": item.method_id,
                "display_name": item.display_name,
                "family": item.family,
                "provenance": item.provenance,
            }
            for item in loaded_models
        ),
    )
    labels = tuple(chr(ord("A") + index) for index in range(len(methods)))
    if len(labels) > 26:
        raise ValueError("At most 26 comparison methods are supported")
    public_pairs = []
    answer_pairs = []

    try:
        for study_index, item in enumerate(selected, start=1):
            dataset_index = item["dataset_index"]
            example = item["example"]
            candidate = item["candidate"]
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
            feature_inputs = (
                torch.from_numpy(dataset.features_a[dataset_index]),
                torch.from_numpy(dataset.features_b[dataset_index]),
                torch.from_numpy(dataset.global_features[dataset_index]),
            )
            audio_inputs = tuple(
                torch.from_numpy(value)
                for value in (source, target, source_vocal, target_vocal)
            )
            with torch.no_grad():
                transitions = {
                    "baseline_equal_power": _render_equal_power(source, target),
                }
                for loaded in loaded_models:
                    transitions[loaded.method_id] = _render_loaded_model(
                        loaded, feature_inputs, audio_inputs
                    )

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
            previews = {
                method_id: np.concatenate((prefix, transition, suffix), axis=-1).astype(
                    np.float32, copy=False
                )
                for method_id, transition in transitions.items()
            }
            raw_joint_peak = max(float(np.max(np.abs(value))) for value in previews.values())
            shared_gain = min(1.0, 0.98 / max(raw_joint_peak, 1e-8))
            for value in previews.values():
                value *= shared_gain

            shuffled_methods = [method["method_id"] for method in methods]
            rng.shuffle(shuffled_methods)
            mapping = dict(zip(labels, shuffled_methods, strict=True))
            metadata_by_label = {}
            for label in labels:
                preview = previews[mapping[label]]
                audio_path = pair_directory / f"{label}.wav"
                _write_audio_atomic(audio_path, preview, DEFAULT_SAMPLE_RATE)
                metadata = _audio_metadata(audio_path, preview, DEFAULT_SAMPLE_RATE)
                metadata["sha256"] = _file_sha256(audio_path)
                metadata_by_label[label] = metadata

            relative_directory = str(pair_directory.relative_to(output_directory))
            public_pairs.append({
                "index": study_index,
                "directory": relative_directory,
                "source_track": candidate["source_track"]["path"],
                "target_track": candidate["target_track"]["path"],
                "transition_length_bars": int(candidate["transition_length_bars"]),
                "tempo_adjustment_fraction": item["tempo_adjustment_fraction"],
                "labels": list(labels),
                "files": metadata_by_label,
            })
            answer_pairs.append({
                "index": study_index,
                "directory": relative_directory,
                "mapping": mapping,
                "candidate_id": candidate["candidate_id"],
                "example_id": example["example_id"],
                "shared_peak_gain": shared_gain,
                "raw_joint_peak": raw_joint_peak,
                "vocal_selection": item["vocal_statistics"],
            })
            print(
                f"[{study_index}/{len(selected)}] {example['example_id']} "
                f"variants={len(methods)}",
                flush=True,
            )

        created_at = _utc_now()
        public_manifest = {
            "format_version": ALL_MODELS_STUDY_FORMAT_VERSION,
            "study_name": ALL_MODELS_STUDY_NAME,
            "blind": True,
            "status": "completed",
            "created_at_utc": created_at,
            "dataset_id": dataset.manifest["dataset_id"],
            "dataset_split": split,
            "method_count": len(methods),
            "method_labels": list(labels),
            "pair_count": len(public_pairs),
            "criteria": list(RATING_CRITERIA),
            "pairs": public_pairs,
            "answer_key": "answer_key.json",
            "ratings": "ratings.json",
            "player": "index.html",
            "interpretation_limit": (
                "Development comparison on one model-selection split; it is not an "
                "independent generalization test. Different model families retain "
                "their declared renderer semantics."
            ),
        }
        answer_key = {
            "format_version": ALL_MODELS_STUDY_FORMAT_VERSION,
            "warning": "Do not inspect before completing the listening comparison.",
            "methods": list(methods),
            "pairs": answer_pairs,
        }
        ratings = _empty_ratings(public_manifest)
        _write_json_atomic(output_directory / "manifest.json", public_manifest)
        _write_json_atomic(output_directory / "answer_key.json", answer_key)
        _write_json_atomic(output_directory / "ratings.json", ratings)
        _write_text_atomic(output_directory / "index.html", build_listening_page(public_manifest))
        _write_text_atomic(output_directory / "README.md", _readme(public_manifest))
    except Exception:
        # Preserve an interrupted export for diagnosis; never silently present it
        # as a completed study.
        if output_directory.exists():
            _write_json_atomic(
                output_directory / "INCOMPLETE.json",
                {"status": "incomplete", "created_at_utc": _utc_now()},
            )
        raise
    return output_directory / "index.html"


def _load_control_model(run_directory, dataset_manifest, dataset_manifest_path):
    manifest_path = run_directory / "manifest.json"
    manifest = _read_json(manifest_path)
    contract = manifest.get("contract", {})
    model_name = contract.get("model", {}).get("name")
    if model_name == "time_shared_mlp_v1":
        model, provenance, _, _ = _load_best_model(run_directory)
        _validate_dataset_contract(contract, dataset_manifest, dataset_manifest_path)
        return LoadedControlModel(
            "time_shared_mlp_v1_best", "Time-shared MLP v1", model_name, model, provenance
        )
    if model_name == "vocal_time_shared_mlp_v2":
        model, _, provenance, _, _ = _load_best_vocal_model(run_directory)
        _validate_run_dataset(provenance, dataset_manifest, dataset_manifest_path)
        return LoadedControlModel(
            "vocal_time_shared_mlp_v2_best", "Vocal MLP v2", model_name, model, provenance
        )
    if model_name == "tcn_bilstm_transition_control_v1":
        model, provenance = _load_best_tcn(run_directory)
        _validate_dataset_contract(contract, dataset_manifest, dataset_manifest_path)
        return LoadedControlModel(
            "tcn_bilstm_transition_control_v1_best",
            "TCN/BiLSTM v1",
            model_name,
            model,
            provenance,
        )
    raise ValueError(f"Unsupported control model in {manifest_path}: {model_name}")


def _load_best_tcn(run_directory):
    manifest_path = run_directory / "manifest.json"
    manifest = _read_json(manifest_path)
    if manifest.get("status") not in {"completed", "early_stopped"}:
        raise ValueError("TCN training run must be completed or early_stopped")
    contract = manifest["contract"]
    if contract["model"]["name"] != "tcn_bilstm_transition_control_v1":
        raise ValueError("Unsupported TCN model")
    if contract.get("renderer", {}).get("name") != "differentiable_full_band_transition_v1":
        raise ValueError("TCN run does not declare the full-band renderer")
    record = manifest["files"]["best_checkpoint"]
    checkpoint_path = run_directory / record["path"]
    checkpoint_sha = _file_sha256(checkpoint_path)
    if checkpoint_sha != record["sha256"]:
        raise ValueError("Best-checkpoint SHA-256 differs from the TCN manifest")
    checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=True)
    if checkpoint.get("run_id") != manifest["run_id"]:
        raise ValueError("TCN checkpoint run ID differs from the manifest")
    if int(checkpoint["epoch"]) != int(manifest["best_epoch"]):
        raise ValueError("TCN checkpoint epoch differs from the manifest")
    raw = contract["model"]["config"]
    config = read_model_config(TCNBiLSTMTransitionControlConfig, raw)
    model = TCNBiLSTMTransitionControl(config)
    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()
    provenance = {
        "run_id": manifest["run_id"],
        "run_manifest_path": str(manifest_path),
        "run_manifest_sha256": _file_sha256(manifest_path),
        "checkpoint_path": str(checkpoint_path),
        "checkpoint_sha256": checkpoint_sha,
        "checkpoint_epoch": int(checkpoint["epoch"]),
        "model_name": contract["model"]["name"],
        "model_config": raw,
        "model_parameter_count": int(manifest["model_parameter_count"]),
        "renderer": contract["renderer"],
    }
    return model, provenance


def _validate_dataset_contract(contract, dataset_manifest, dataset_manifest_path):
    declared = contract.get("dataset", {})
    if declared.get("dataset_id") != dataset_manifest.get("dataset_id"):
        raise ValueError("Training run and requested dataset IDs differ")
    if declared.get("manifest_sha256") != _file_sha256(dataset_manifest_path):
        raise ValueError("Dataset manifest SHA-256 differs from the training contract")


def _render_equal_power(source, target):
    controls = torch.linspace(0.0, 1.0, 32)
    renderer = DifferentiableTwoBandRenderer(
        sample_rate=DEFAULT_SAMPLE_RATE, lowpass_kernel_size=511
    )
    return renderer(
        torch.from_numpy(source), torch.from_numpy(target), controls, controls
    ).audio.numpy()


def _render_loaded_model(loaded, feature_inputs, audio_inputs):
    source, target, source_vocal, target_vocal = audio_inputs
    output = loaded.model(*feature_inputs)
    if loaded.family == "time_shared_mlp_v1":
        renderer = DifferentiableTwoBandRenderer(
            sample_rate=DEFAULT_SAMPLE_RATE,
            lowpass_cutoff_hz=float(loaded.provenance["renderer"]["lowpass_cutoff_hz"]),
            lowpass_kernel_size=511,
        )
        return renderer(
            source, target, output.mix_position, output.low_end_position
        ).audio.numpy()
    if loaded.family == "vocal_time_shared_mlp_v2":
        renderer = DifferentiableVocalAwareRenderer(
            sample_rate=DEFAULT_SAMPLE_RATE,
            lowpass_cutoff_hz=float(loaded.provenance["renderer"]["lowpass_cutoff_hz"]),
            lowpass_kernel_size=511,
        )
        return renderer(
            source,
            target,
            source_vocal,
            target_vocal,
            output.mix_position,
            output.low_end_position,
            output.vocal_position,
            output.vocal_duck_a,
            output.vocal_duck_b,
        ).audio.numpy()
    if loaded.family == "tcn_bilstm_transition_control_v1":
        renderer_contract = loaded.provenance["renderer"]
        renderer = DifferentiableFullBandTransitionRenderer(
            sample_rate=DEFAULT_SAMPLE_RATE,
            lowpass_cutoff_hz=float(renderer_contract["lowpass_cutoff_hz"]),
            midpass_cutoff_hz=float(renderer_contract.get("midpass_cutoff_hz", 3500.0)),
            lowpass_kernel_size=511,
        )
        controls = output.renderer_arguments(source.shape[-1])
        # This model was trained with the documented mid-band vocal proxy, so
        # its inference renderer intentionally receives no separated stems.
        return renderer(source, target, *controls).audio.numpy()
    raise ValueError(f"Unsupported loaded model family: {loaded.family}")


def _select_examples(items, pair_count, max_track_uses):
    ordered = sorted(
        items,
        key=lambda item: (
            item["tempo_adjustment_fraction"],
            -item["vocal_statistics"]["selection_score"],
            int(item["example"]["candidate_rank"]),
            item["example"]["example_id"],
        ),
    )
    selected = []
    directed_pairs = set()
    track_uses = {}
    for item in ordered:
        example = item["example"]
        source_hash = example["source_track"]["sha256"]
        target_hash = example["target_track"]["sha256"]
        directed_pair = (source_hash, target_hash)
        if directed_pair in directed_pairs:
            continue
        if track_uses.get(source_hash, 0) >= max_track_uses:
            continue
        if track_uses.get(target_hash, 0) >= max_track_uses:
            continue
        selected.append(item)
        directed_pairs.add(directed_pair)
        track_uses[source_hash] = track_uses.get(source_hash, 0) + 1
        track_uses[target_hash] = track_uses.get(target_hash, 0) + 1
        if len(selected) == pair_count:
            return tuple(selected)
    raise ValueError(
        f"Only {len(selected)} diverse examples satisfy the selection; requested {pair_count}"
    )


def _empty_ratings(manifest):
    """Use per-label ranks (null or 1..N); equal ranks represent ties.

    The legacy ranking list is populated by the player only for complete,
    strict orders. Existing format-1 fields remain available unchanged.
    """
    return {
        "format_version": ALL_MODELS_STUDY_FORMAT_VERSION,
        "study_manifest": "manifest.json",
        "status": "unrated",
        "criteria": list(RATING_CRITERIA),
        "ratings": [
            {
                "pair_index": pair["index"],
                "ranking": [],
                "ranks": {label: None for label in pair["labels"]},
                "scores": {
                    label: {criterion: None for criterion in RATING_CRITERIA}
                    for label in pair["labels"]
                },
                "notes": "",
            }
            for pair in manifest["pairs"]
        ],
    }


def build_listening_page(manifest):
    """Return a dependency-free local player with downloadable ratings."""

    payload = json.dumps(manifest, ensure_ascii=False).replace("</", "<\\/")
    title = html.escape("BeatBridge – geblendeter Modell-Hörvergleich")
    introduction = html.escape(
        manifest.get(
            "instructions",
            "Alle Varianten einer Zeile verwenden denselben Cuepoint, Kontext und "
            "gemeinsamen Peak-Gain. Die Buchstaben sind pro Zeile neu gemischt. "
            "Höre mit gleicher Systemlautstärke und wähle für jeden Kandidaten einen "
            "Platz (1 = bester Übergang). Gleich gute Kandidaten können denselben "
            "Platz erhalten; Plätze dürfen frei bleiben.",
        )
    )
    return f"""<!doctype html>
<html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title>
<style>
:root{{--bg:#0b0d12;--card:#151923;--line:#2a3140;--text:#eef2f7;--muted:#9ba8ba;--accent:#79d7c4}}
*{{box-sizing:border-box}} body{{margin:0;background:var(--bg);color:var(--text);font:16px system-ui,sans-serif}}
main{{max-width:1180px;margin:auto;padding:32px 20px 80px}} h1{{font-size:clamp(1.8rem,4vw,3.2rem);margin:.2em 0}}
.lede,.meta{{color:var(--muted);max-width:780px;line-height:1.55}} .toolbar{{display:flex;gap:12px;flex-wrap:wrap;margin:24px 0}}
button{{border:1px solid var(--line);border-radius:10px;background:#202635;color:var(--text);padding:10px 14px;cursor:pointer}}
button:hover{{border-color:var(--accent)}} .pair{{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:20px;margin:18px 0}}
.pair h2{{margin:0 0 5px;font-size:1.15rem}} .variants{{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:12px;margin:16px 0}}
.variant{{background:#0f131b;border:1px solid var(--line);border-radius:12px;padding:12px}} .label{{font-size:1.35rem;font-weight:750;color:var(--accent)}}
audio{{width:100%;margin-top:8px}} label{{display:block;color:var(--muted);font-size:.9rem;margin-top:8px}} select,textarea{{width:100%;background:#0f131b;color:var(--text);border:1px solid var(--line);border-radius:8px;padding:8px}}
textarea{{min-height:64px}} .saved{{color:var(--accent)}}
</style></head><body><main>
<p class="meta">BeatBridge / lokale Studie</p><h1>{title}</h1>
<p class="lede">{introduction}</p>
<div class="toolbar"><button id="save">Bewertungen herunterladen</button><button id="clear">Lokale Eingaben löschen</button><span id="state" class="saved"></span></div>
<div id="pairs"></div>
<script id="manifest" type="application/json">{payload}</script><script>
const manifest=JSON.parse(document.getElementById('manifest').textContent); const key='beatbridge:'+manifest.dataset_id+':'+manifest.created_at_utc;
let ratings=JSON.parse(localStorage.getItem(key)||'{{}}'); const root=document.getElementById('pairs');
const esc=s=>String(s).replace(/[&<>"']/g,c=>({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[c]));
function persist(){{localStorage.setItem(key,JSON.stringify(ratings)); document.getElementById('state').textContent='lokal gespeichert';}}
function normalizeRating(pair,stored={{}}){{
 const ranks=Object.fromEntries(pair.labels.map(label=>{{
  const oldIndex=(stored.ranking||[]).indexOf(label);
  const rank=stored.ranks ? stored.ranks[label] : (oldIndex<0?null:oldIndex+1);
  return [label,Number.isInteger(rank)&&rank>=1&&rank<=pair.labels.length?rank:null];
 }}));
 const values=Object.values(ranks);
 // Keep the legacy strict order only when it can represent the chosen places.
 const ranking=values.every(rank=>rank!==null)&&new Set(values).size===pair.labels.length
  ? [...pair.labels].sort((a,b)=>ranks[a]-ranks[b]) : [];
 return {{...stored,ranks,ranking,notes:stored.notes||''}};
}}
for(const pair of manifest.pairs){{const section=document.createElement('section');section.className='pair';const current=normalizeRating(pair,ratings[pair.index]);ratings[pair.index]=current;
 section.innerHTML=`<h2>${{pair.index}}. ${{esc(pair.source_track.split(/[\\\\/]/).pop())}} → ${{esc(pair.target_track.split(/[\\\\/]/).pop())}}</h2><div class="meta">${{pair.transition_length_bars}} Takte · ${{(100*pair.tempo_adjustment_fraction).toFixed(2)}} % Tempoanpassung</div><div class="variants">${{pair.labels.map(label=>`<div class="variant"><div class="label">${{esc(label)}}</div><audio controls preload="metadata" src="${{encodeURI(pair.directory+'/'+label+'.wav')}}"></audio><label>Platz für Kandidat ${{esc(label)}}<select class="rank" data-label="${{esc(label)}}"><option value="">– auswählen –</option>${{pair.labels.map((_,i)=>`<option value="${{i+1}}" ${{current.ranks[label]===i+1?'selected':''}}>${{i+1}}${{i===0?' (bester)':''}}</option>`).join('')}}</select></label></div>`).join('')}}</div><p class="meta">Gleicher Platz = gleich gut. Plätze dürfen frei bleiben.</p><label>Notizen<textarea class="notes">${{esc(current.notes||'')}}</textarea></label>`;
 section.querySelectorAll('.rank').forEach(select=>select.addEventListener('change',e=>{{const updated=ratings[pair.index];updated.ranks[e.target.dataset.label]=e.target.value?Number(e.target.value):null;ratings[pair.index]=normalizeRating(pair,updated);persist();}}));
 section.querySelector('.notes').addEventListener('input',e=>{{ratings[pair.index]=ratings[pair.index]||{{}};ratings[pair.index].notes=e.target.value;persist();}});root.appendChild(section);}}
document.getElementById('save').onclick=()=>{{const out={{format_version:1,study_manifest:'manifest.json',exported_at_utc:new Date().toISOString(),ratings:manifest.pairs.map(p=>({{...normalizeRating(p,ratings[p.index]),pair_index:p.index}}))}};const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([JSON.stringify(out,null,2)],{{type:'application/json'}}));a.download='ratings.json';a.click();URL.revokeObjectURL(a.href);}};
document.getElementById('clear').onclick=()=>{{if(confirm('Alle lokalen Eingaben dieser Studie löschen?')){{localStorage.removeItem(key);location.reload();}}}};
</script></main></body></html>"""


def _readme(manifest):
    return f"""# Geblendeter Modell-Hörvergleich

Öffne `index.html` in einem Browser. Pro Songpaar stehen
{manifest['method_count']} zufällig beschriftete Varianten desselben Übergangs
bereit. Wähle pro Kandidat einen Platz (1 = bester; Gleichstände sind erlaubt)
und lade anschließend `ratings.json`
herunter. Erst danach `answer_key.json` öffnen.

Der Vergleich enthält Equal Power und je einen repräsentativen, zum Datensatz
kompatiblen Checkpoint der trainierten Control-Modellfamilien. Cue-Ranker sind
nicht enthalten: Sie wählen Übergangspunkte, erzeugen aber keine hörbare
Control-Kurve. Variable-Length-Modelle verwenden Dataset-/Feature-Protokoll 2
und benötigen deshalb einen separaten, protokollgleichen Hörsatz.

Dieser Satz verwendet den Split `{manifest['dataset_split']}` und ist ein
Entwicklungsvergleich, kein unabhängiger Generalisierungsnachweis.
"""


def _safe_name(value):
    cleaned = "".join(character if character.isalnum() else "_" for character in value)
    return "_".join(part for part in cleaned.split("_") if part)


def _read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _write_json_atomic(path, payload):
    _write_text_atomic(
        path, json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    )


def _write_text_atomic(path, text):
    path = Path(path)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        temporary.write_text(text, encoding="utf-8")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def build_argument_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset_directory")
    parser.add_argument("output_directory")
    parser.add_argument(
        "--training-runs-root", default=str(Path("output") / "training_runs")
    )
    parser.add_argument("--run", action="append", default=[], help="Explicit run directory; repeatable")
    parser.add_argument("--split", choices=SUPPORTED_SPLITS, default="validation")
    parser.add_argument("--pair-count", type=int, default=DEFAULT_PAIR_COUNT)
    parser.add_argument("--minimum-mean-vocal-strength", type=float, default=0.15)
    parser.add_argument("--max-track-uses", type=int, default=3)
    parser.add_argument("--maximum-tempo-adjustment-fraction", type=float, default=0.005)
    parser.add_argument("--analysis-location", default=str(Path("output") / "pre_analysis"))
    parser.add_argument("--blind-seed", type=int, default=DEFAULT_BLIND_SEED)
    parser.add_argument("--prefix-seconds", type=float, default=DEFAULT_PREFIX_SECONDS)
    parser.add_argument("--suffix-seconds", type=float, default=DEFAULT_SUFFIX_SECONDS)
    return parser


def main():
    args = build_argument_parser().parse_args()
    runs = tuple(Path(value) for value in args.run)
    if not runs:
        runs = discover_representative_runs(args.training_runs_root, args.dataset_directory)
    if not runs:
        raise SystemExit("No compatible completed control-model runs found")
    player = export_all_models_control_study(
        args.dataset_directory,
        runs,
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
    print(player)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
