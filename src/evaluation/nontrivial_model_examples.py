"""Export separate examples for models with incompatible evaluation contracts."""

from __future__ import annotations

import argparse
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

from src.control import DifferentiableVocalAwareRenderer
from src.evaluation.all_models_control_study import (
    ALL_MODELS_STUDY_FORMAT_VERSION,
    RATING_CRITERIA,
    _empty_ratings,
    build_listening_page,
)
from src.evaluation.control_probe import _audio_metadata, _write_audio_atomic
from src.features.variable_contract import SUPPORTED_VARIABLE_LENGTHS
from src.ml.variable_data import VariableFeatureDataset
from src.ml.variable_model import (
    VARIABLE_TCN_BILSTM_MODEL_NAME,
    VariableTCNBiLSTMControlConfig,
    VariableTCNBiLSTMTransitionControl,
)
from src.ml.variable_runner import (
    VARIABLE_TEMPORAL_TRAINING_RUNNER_NAME,
    validate_variable_checkpoint,
)
from src.ml.variable_waveform_cache import (
    VARIABLE_WAVEFORM_CACHE_ROOT,
    VARIABLE_WAVEFORM_SAMPLE_RATE,
    build_variable_cache_loader,
)


NONTRIVIAL_EXAMPLES_FORMAT_VERSION = 1
VARIABLE_STUDY_NAME = "blind_variable_tcn_by_length_v1"
DEFAULT_BLIND_SEED = 20260904


def export_variable_tcn_examples(
    dataset_directory,
    training_run_directory,
    output_directory,
    *,
    waveform_cache_root=VARIABLE_WAVEFORM_CACHE_ROOT,
    split="validation",
    transition_lengths=SUPPORTED_VARIABLE_LENGTHS,
    blind_seed=DEFAULT_BLIND_SEED,
):
    """Render one blind Equal-Power versus Variable-TCN example per length."""

    if split != "validation":
        raise ValueError("This development exporter intentionally permits validation only")
    dataset_directory = Path(dataset_directory).resolve()
    training_run_directory = Path(training_run_directory).resolve()
    output_directory = Path(output_directory).resolve()
    if output_directory.exists():
        raise FileExistsError(f"Study output already exists: {output_directory}")
    model, provenance, renderer_contract = _load_variable_tcn(
        training_run_directory, dataset_directory
    )
    waveform_loader = build_variable_cache_loader(
        dataset_directory, cache_root=waveform_cache_root
    )
    lengths = tuple(sorted({int(value) for value in transition_lengths}))
    datasets = {
        length: VariableFeatureDataset(
            dataset_directory, length, split, waveform_loader=waveform_loader
        )
        for length in lengths
    }
    selected = {
        length: min(
            range(len(dataset)),
            key=lambda index: (
                int(dataset.examples[index]["candidate_rank"]),
                dataset.examples[index]["example_id"],
            ),
        )
        for length, dataset in datasets.items()
    }
    renderer = DifferentiableVocalAwareRenderer(
        sample_rate=int(renderer_contract["sample_rate"]),
        lowpass_cutoff_hz=float(renderer_contract["lowpass_cutoff_hz"]),
        lowpass_kernel_size=int(renderer_contract["lowpass_kernel_size"]),
    )
    output_directory.mkdir(parents=True)
    rng = random.Random(int(blind_seed))
    public_pairs = []
    answer_pairs = []
    labels = ("A", "B")
    methods = (
        {
            "method_id": "variable_equal_power",
            "display_name": "Equal Power (variable renderer)",
            "family": "baseline",
        },
        {
            "method_id": "variable_tcn_bilstm_transition_control_v1_best",
            "display_name": "Variable TCN/BiLSTM v1",
            "family": VARIABLE_TCN_BILSTM_MODEL_NAME,
            "provenance": provenance,
        },
    )
    try:
        for study_index, length in enumerate(lengths, start=1):
            dataset = datasets[length]
            local_index = selected[length]
            example = dataset.examples[local_index]
            item = dataset[local_index]
            source = item["source_audio"]
            target = item["target_audio"]
            source_vocal = item["source_vocal_audio"]
            target_vocal = item["target_vocal_audio"]
            time_steps = int(item["sequence_length"])
            linear = torch.linspace(0.0, 1.0, time_steps)
            zero_duck = torch.zeros(time_steps)
            with torch.no_grad():
                baseline = renderer(
                    source,
                    target,
                    source_vocal,
                    target_vocal,
                    linear,
                    linear,
                    linear,
                    zero_duck,
                    zero_duck,
                ).audio.numpy()
                controls = model(
                    item["features_a"],
                    item["features_b"],
                    item["global_features"],
                    transition_length_bars=length,
                    length_condition=item["length_condition"],
                )
                learned = renderer(
                    source,
                    target,
                    source_vocal,
                    target_vocal,
                    controls.mix_position,
                    controls.low_end_position,
                    controls.vocal_position,
                    controls.vocal_duck_a,
                    controls.vocal_duck_b,
                ).audio.numpy()
            variants = {
                "variable_equal_power": np.asarray(baseline, dtype=np.float32),
                "variable_tcn_bilstm_transition_control_v1_best": np.asarray(
                    learned, dtype=np.float32
                ),
            }
            peak = max(float(np.max(np.abs(value))) for value in variants.values())
            shared_gain = min(1.0, 0.98 / max(peak, 1e-8))
            for value in variants.values():
                value *= shared_gain
            method_order = [method["method_id"] for method in methods]
            rng.shuffle(method_order)
            mapping = dict(zip(labels, method_order, strict=True))
            pair_directory = output_directory / (
                f"{study_index:02d}__{length}bar__"
                f"{_safe_name(Path(example['source_track']['path']).stem)}__to__"
                f"{_safe_name(Path(example['target_track']['path']).stem)}"
            )
            pair_directory.mkdir()
            files = {}
            for label in labels:
                audio = variants[mapping[label]]
                path = pair_directory / f"{label}.wav"
                _write_audio_atomic(path, audio, VARIABLE_WAVEFORM_SAMPLE_RATE)
                metadata = _audio_metadata(path, audio, VARIABLE_WAVEFORM_SAMPLE_RATE)
                metadata["sha256"] = _file_sha256(path)
                files[label] = metadata
            relative = str(pair_directory.relative_to(output_directory))
            public_pairs.append({
                "index": study_index,
                "directory": relative,
                "source_track": example["source_track"]["path"],
                "target_track": example["target_track"]["path"],
                "transition_length_bars": length,
                "tempo_adjustment_fraction": abs(
                    float(example["source_bpm"]) / float(example["target_bpm"]) - 1.0
                ),
                "labels": list(labels),
                "files": files,
            })
            answer_pairs.append({
                "index": study_index,
                "directory": relative,
                "mapping": mapping,
                "example_id": example["example_id"],
                "candidate_id": example["candidate_id"],
                "shared_peak_gain": shared_gain,
                "waveform_cache": item["waveform_cache_directory"],
            })
        created_at = _utc_now()
        manifest = {
            "format_version": ALL_MODELS_STUDY_FORMAT_VERSION,
            "study_name": VARIABLE_STUDY_NAME,
            "blind": True,
            "status": "completed",
            "created_at_utc": created_at,
            "dataset_id": next(iter(datasets.values())).manifest["dataset_id"],
            "dataset_split": split,
            "method_count": 2,
            "method_labels": list(labels),
            "pair_count": len(public_pairs),
            "criteria": list(RATING_CRITERIA),
            "pairs": public_pairs,
            "answer_key": "answer_key.json",
            "ratings": "ratings.json",
            "player": "index.html",
            "instructions": (
                "Dieser separate Hörsatz vergleicht das Variable-Length-TCN mit "
                "seiner Equal-Power-Referenz auf 2, 4, 6 und 8 Takten. Die Audiofiles "
                "enthalten nur das exakt ausgerichtete Übergangsfenster ohne Vor- und "
                "Nachlauf; beide Varianten einer Zeile teilen Cache, Renderer und Peak-Gain."
            ),
            "interpretation_limit": (
                "Development examples on Dataset/Feature Protocol 2 validation. They "
                "must not be pooled statistically with the Dataset-v1 study."
            ),
        }
        answer_key = {
            "format_version": NONTRIVIAL_EXAMPLES_FORMAT_VERSION,
            "warning": "Do not inspect before completing ratings.json.",
            "methods": list(methods),
            "pairs": answer_pairs,
        }
        _write_json(output_directory / "manifest.json", manifest)
        _write_json(output_directory / "answer_key.json", answer_key)
        _write_json(output_directory / "ratings.json", _empty_ratings(manifest))
        _write_text(output_directory / "index.html", build_listening_page(manifest))
        _write_text(
            output_directory / "README.md",
            "# Variable-Length-TCN-Hörbeispiele\n\n"
            "`index.html` öffnen, A/B je Übergangslänge vergleichen und erst nach "
            "dem Ratings-Export `answer_key.json` ansehen. Diese Beispiele dürfen "
            "nicht statistisch mit dem Dataset-v1-Hörsatz zusammengelegt werden.\n",
        )
    except Exception:
        if output_directory.exists():
            _write_json(output_directory / "INCOMPLETE.json", {"status": "incomplete"})
        raise
    return output_directory / "index.html"


def export_comparison_hub(
    main_study_directory,
    variable_study_directory,
    cue_ranker_run_directory,
    output_directory,
):
    """Create one landing page while preserving the studies' separate contracts."""

    main_study_directory = Path(main_study_directory).resolve()
    variable_study_directory = Path(variable_study_directory).resolve()
    cue_ranker_run_directory = Path(cue_ranker_run_directory).resolve()
    output_directory = Path(output_directory).resolve()
    if output_directory.exists():
        raise FileExistsError(f"Hub output already exists: {output_directory}")
    main = _read_json(main_study_directory / "manifest.json")
    variable = _read_json(variable_study_directory / "manifest.json")
    cue_manifest = _read_json(cue_ranker_run_directory / "manifest.json")
    history = _read_json(cue_ranker_run_directory / "history.json")
    cue_rows = _cue_ranker_demo_rows(cue_manifest, history)
    output_directory.mkdir(parents=True)
    main_href = (main_study_directory / "index.html").as_uri()
    variable_href = (variable_study_directory / "index.html").as_uri()
    rows = "".join(
        "<tr>"
        f"<td>{row['length']} Takte</td>"
        f"<td>{_percent(row['ranker_top1'])}</td>"
        f"<td>{_percent(row['baseline_top1'])}</td>"
        f"<td>{_number(row['ranker_ndcg'])}</td>"
        "</tr>"
        for row in cue_rows
    )
    page = f"""<!doctype html><html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>BeatBridge Modellvergleich</title>
<style>body{{margin:0;background:#0b0d12;color:#eef2f7;font:16px system-ui,sans-serif}}main{{max-width:1000px;margin:auto;padding:40px 20px}}h1{{font-size:clamp(2rem,5vw,4rem)}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:18px}}.card{{padding:22px;border:1px solid #2a3140;border-radius:16px;background:#151923}}a{{color:#79d7c4}}p{{color:#b3bdca;line-height:1.55}}table{{width:100%;border-collapse:collapse}}td,th{{padding:9px;border-bottom:1px solid #2a3140;text-align:left}}.warn{{border-left:4px solid #e7b35b;padding-left:14px}}</style></head><body><main>
<p>BeatBridge / Vergleichszentrale</p><h1>Modelle fair anhören – getrennt nach Vertrag</h1><p>Die Modellfamilien werden nicht künstlich in eine gemeinsame Statistik gezwungen. Jede Karte hält Dataset, Renderer und Aufgabe konstant.</p>
<div class="grid"><section class="card"><h2>Control-Modelle · 4 Takte</h2><p>{main['pair_count']} Paare: Equal Power, MLP v1, Vocal-MLP v2 und Full-Band-TCN/BiLSTM v1.</p><a href="{html.escape(main_href)}">Geblendeten Vergleich öffnen →</a></section>
<section class="card"><h2>Variable TCN · 2/4/6/8 Takte</h2><p>{variable['pair_count']} Beispiele gegen eine protokollgleiche Equal-Power-Referenz.</p><a href="{html.escape(variable_href)}">Variable Hörbeispiele öffnen →</a></section></div>
<section class="card" style="margin-top:18px"><h2>Cue-Ranker · synthetische Funktionsdemo</h2><p class="warn">Kein Hörtest und kein Qualitätsnachweis: Der vorhandene Ranker wurde nur auf synthetischen Gruppen trainiert. Er wählt Cuepoints; hörbar würde er erst zusammen mit einem nachgelagerten Controller und Renderer.</p>
<table><thead><tr><th>Länge</th><th>Ranker Top-1/Teacher</th><th>Feature-Baseline Top-1/Teacher</th><th>Ranker NDCG</th></tr></thead><tbody>{rows}</tbody></table>
<p>Quelle: letzter Validation-Eintrag aus <code>{html.escape(cue_ranker_run_directory.name)}</code>. Pro Länge liegt nur eine synthetische Gruppe vor; die Zahlen dürfen nicht als reale Modellgüte interpretiert werden.</p></section>
</main></body></html>"""
    _write_text(output_directory / "index.html", page)
    _write_json(
        output_directory / "manifest.json",
        {
            "format_version": NONTRIVIAL_EXAMPLES_FORMAT_VERSION,
            "created_at_utc": _utc_now(),
            "main_study": str(main_study_directory),
            "variable_study": str(variable_study_directory),
            "cue_ranker_run": str(cue_ranker_run_directory),
            "cue_ranker_demo": cue_rows,
        },
    )
    return output_directory / "index.html"


def _load_variable_tcn(run_directory, dataset_directory):
    manifest_path = run_directory / "manifest.json"
    manifest = _read_json(manifest_path)
    if manifest.get("status") != "completed":
        raise ValueError("Variable TCN run must be completed")
    contract = manifest["contract"]
    if contract.get("runner_name") != VARIABLE_TEMPORAL_TRAINING_RUNNER_NAME:
        raise ValueError("Unsupported variable training runner")
    if contract.get("model_name") != VARIABLE_TCN_BILSTM_MODEL_NAME:
        raise ValueError("Unsupported variable model")
    dataset_manifest_path = dataset_directory / "manifest.json"
    if contract["dataset_manifest_sha256"] != _file_sha256(dataset_manifest_path):
        raise ValueError("Variable run and dataset manifest SHA-256 differ")
    record = manifest["files"]["best_checkpoint"]
    checkpoint_path = run_directory / record["path"]
    checkpoint_sha = _file_sha256(checkpoint_path)
    if checkpoint_sha != record["sha256"]:
        raise ValueError("Variable best-checkpoint SHA-256 differs from manifest")
    checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=True)
    validate_variable_checkpoint(
        checkpoint,
        expected_contract=contract,
        run_id=manifest["run_id"],
        expected_runner_name=VARIABLE_TEMPORAL_TRAINING_RUNNER_NAME,
    )
    raw = contract["model"]["config"]
    config = VariableTCNBiLSTMControlConfig(
        encoder_channels=tuple(raw["encoder_channels"]),
        tcn_kernel_size=int(raw["tcn_kernel_size"]),
        tcn_dilation=int(raw["tcn_dilation"]),
        fusion_dimension=int(raw["fusion_dimension"]),
        controller_hidden_size=int(raw["controller_hidden_size"]),
        controller_layers=int(raw["controller_layers"]),
        output_dimension=int(raw["output_dimension"]),
        dropout=float(raw["dropout"]),
        increment_logit_bound=float(raw["increment_logit_bound"]),
        maximum_vocal_ducking=float(raw["maximum_vocal_ducking"]),
        initial_vocal_duck_logit=float(raw["initial_vocal_duck_logit"]),
    )
    model = VariableTCNBiLSTMTransitionControl(config)
    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()
    provenance = {
        "run_id": manifest["run_id"],
        "run_manifest_path": str(manifest_path),
        "run_manifest_sha256": _file_sha256(manifest_path),
        "checkpoint_path": str(checkpoint_path),
        "checkpoint_sha256": checkpoint_sha,
        "checkpoint_epoch": int(checkpoint["epoch"]),
        "model_name": VARIABLE_TCN_BILSTM_MODEL_NAME,
    }
    return model, provenance, contract["renderer"]


def _cue_ranker_demo_rows(manifest, history):
    if manifest.get("status") != "completed" or not history.get("epochs"):
        raise ValueError("Cue-ranker demo requires a completed run with history")
    validation = history["epochs"][-1]["validation"]["ranking"]
    rows = []
    for length in (2, 4, 6, 8):
        bucket = validation[str(length)]
        rows.append({
            "length": length,
            "groups": int(bucket["groups"]),
            "ranker_top1": bucket["ranker"]["top_1_agreement"],
            "baseline_top1": bucket["feature_baseline_v3"]["top_1_agreement"],
            "ranker_ndcg": bucket["ranker"]["ndcg"],
        })
    return rows


def _percent(value):
    return "–" if value is None else f"{100 * float(value):.0f} %"


def _number(value):
    return "–" if value is None else f"{float(value):.3f}"


def _safe_name(value):
    return "_".join(
        part
        for part in "".join(c if c.isalnum() else "_" for c in value).split("_")
        if part
    )


def _file_sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _write_json(path, payload):
    _write_text(path, json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


def _write_text(path, text):
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
    parser.add_argument("training_run_directory")
    parser.add_argument("variable_output_directory")
    parser.add_argument("hub_output_directory")
    parser.add_argument("--main-study-directory", required=True)
    parser.add_argument("--cue-ranker-run-directory", required=True)
    parser.add_argument("--waveform-cache-root", default=str(VARIABLE_WAVEFORM_CACHE_ROOT))
    return parser


def main():
    args = build_argument_parser().parse_args()
    variable_page = export_variable_tcn_examples(
        args.dataset_directory,
        args.training_run_directory,
        args.variable_output_directory,
        waveform_cache_root=args.waveform_cache_root,
    )
    hub = export_comparison_hub(
        args.main_study_directory,
        variable_page.parent,
        args.cue_ranker_run_directory,
        args.hub_output_directory,
    )
    print(variable_page)
    print(hub)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
