"""FÜR DEN STUDENTEN: B1/B2 für das variable TCN/BiLSTM-Modell (Dataset-Format 2).

Auf dem Rechner des Betreuers fehlen Checkpoint, Dataset und Waveform-Cache
des variablen Modells. Dieses Skript beantwortet auf dem Entwicklungsrechner
dieselben Fragen wie b1_b2_model_response_and_loss.py:

  1. Reagiert das Netz auf seine Eingabe? (Streuung der Kurven über Beispiele,
     Abweichung von der Initialisierung, je Übergangslänge)
  2. Was passiert, wenn man die Kurven von Beispiel i auf Audio+Features von
     Beispiel j anwendet (gleiche Länge)? Bleibt der Loss-Gewinn erhalten,
     ist die Eingabeabhängigkeit wertlos.
  3. Welcher Objective-Term trägt den Gewinn gegenüber der Initialisierung
     und gegenüber EINER gemittelten Kurve für alle Beispiele?

Es wird nichts trainiert und nichts außerhalb von review_jp/ geschrieben. Es
werden nur train/validation gelesen (genau wie der Trainings-Runner).

ANPASSEN (vier Pfade, Beispielwerte aus docs/RESULTS_EVIDENCE_LEDGER.md R4/D4):

  --run      output/training_runs/prive_scantraxx_all_models_dataset_v2_variable_tcn_bilstm_20260926_run01
  --dataset  output/datasets/prive_scantraxx_extension_variable_v2_fp2_roformer_2-4-6-8bar_top1x3_split20260923_run02_local_four_four
  --cache    der beim Training benutzte --cache-root (Default des Repos:
             src.ml.variable_waveform_cache.VARIABLE_WAVEFORM_CACHE_ROOT)
  --lengths  2 4 6 8   (wie beim Training)

Aufruf (Windows, aus dem Repo-Root):
  .venv\\Scripts\\python.exe review_jp\\scripts\\student_variable_model_check.py ^
      --run <RUN> --dataset <DATASET> --cache <CACHE> --lengths 2 4 6 8

Selbsttest ohne Daten (prüft nur, dass der Auswertungscode läuft):
  python review_jp/scripts/student_variable_model_check.py --selftest

Ergebnis: review_jp/results/student_variable_<run>.json und
          review_jp/plots/student_variable_<run>_L<bars>.png
Bitte beide zurückschicken.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import torch

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
RESULTS = REPO / "review_jp" / "results"
PLOTS = REPO / "review_jp" / "plots"

from src.control import DifferentiableVocalAwareRenderer  # noqa: E402
from src.control.variable_differentiable import (  # noqa: E402
    VariableVocalAwareTransitionObjective,
)
from src.features.variable_contract import geometry_for_length  # noqa: E402
from src.ml.variable_model import (  # noqa: E402
    VariableTCNBiLSTMControlConfig,
    VariableTCNBiLSTMTransitionControl,
)

CONTROLS = ("mix_position", "low_end_position", "vocal_position",
            "vocal_duck_a", "vocal_duck_b")
WEIGHTS = {
    "energy_shape": "energy_shape_weight", "boundary": "boundary_weight",
    "control_smoothness": "control_smoothness_weight",
    "control_curvature": "control_curvature_weight",
    "clipping": "clipping_weight", "transient_artifact": "transient_artifact_weight",
    "vocal_overlap": "vocal_overlap_weight", "vocal_boundary": "vocal_boundary_weight",
    "vocal_stem_overlap": "vocal_stem_overlap_weight",
    "vocal_audibility": "vocal_audibility_weight",
    "vocal_mid_phrase_gain_change": "vocal_mid_phrase_gain_change_weight",
}


def load_real_batches(args):
    """Baut train/validation-Batches exakt wie src/ml/variable_runner.py:346-410."""
    import hashlib

    from src.ml.variable_data import (
        VariableFeatureDatasetCollection,
        VariableLengthBatchSampler,
        collate_variable_feature_examples,
    )
    from src.ml.variable_waveform_cache import (
        VARIABLE_WAVEFORM_RENDER_SAMPLE_RATE,
        build_variable_cache_loader,
        load_variable_waveform_cache_index,
    )

    dataset = Path(args.dataset)
    digest = hashlib.sha256((dataset / "manifest.json").read_bytes()).hexdigest()
    lengths = tuple(sorted(set(args.lengths)))
    binding = load_variable_waveform_cache_index(
        args.cache, dataset_manifest_sha256=digest,
        required_splits=("train", "validation"), required_lengths=lengths,
    )
    loader = build_variable_cache_loader(
        dataset, cache_root=args.cache, training_sample_rate=args.sample_rate,
        render_sample_rate=VARIABLE_WAVEFORM_RENDER_SAMPLE_RATE, require_index=True,
        required_splits=("train", "validation"), required_lengths=lengths,
    )
    batches = {}
    for split in ("train", "validation"):  # der Test-Split wird nie instanziiert
        collection = VariableFeatureDatasetCollection(
            dataset, split, transition_length_bars=lengths, waveform_loader=loader,
            include_example_ids=binding["entries"].keys(),
        )
        sampler = VariableLengthBatchSampler(collection, 8, shuffle=False, seed=0)
        batches[split] = [
            collate_variable_feature_examples([collection[i] for i in indices])
            for indices in sampler
        ]
    return batches


def synthetic_batches():
    """Zufallsdaten für --selftest (keine Aussage über das Modell!)."""
    generator = torch.Generator().manual_seed(0)
    batches = {"train": [], "validation": []}
    for split, count in (("train", 6), ("validation", 5)):
        for bars in (2, 4):
            geometry = geometry_for_length(bars)
            steps = geometry.sequence_length
            features = lambda: torch.rand(count, steps, 54, generator=generator)  # noqa: E731
            audio = lambda: tuple(  # noqa: E731
                0.2 * torch.randn(2, 4000 * bars, generator=generator) for _ in range(count))
            batches[split].append({
                "example_ids": tuple(f"{split}-{bars}-{i}" for i in range(count)),
                "transition_length_bars": bars, "sequence_length": steps,
                "features_a": features(), "features_b": features(),
                "global_features": torch.rand(count, 16, generator=generator) * 0.5,
                "length_condition": torch.full((count, 1), float(geometry.length_condition)),
                "source_audio": audio(), "target_audio": audio(),
                "source_vocal_audio": audio(), "target_vocal_audio": audio(),
            })
    return batches


def predict(model, batch):
    with torch.no_grad():
        output = model(
            batch["features_a"].float(), batch["features_b"].float(),
            batch["global_features"].float(),
            transition_length_bars=int(batch["transition_length_bars"]),
            length_condition=batch["length_condition"].float(),
        )
    return {name: getattr(output, name).clone() for name in CONTROLS}


def evaluate(renderer, objective, controls, batch, index, bars):
    audio = [batch[name][index].float() for name in
             ("source_audio", "target_audio", "source_vocal_audio", "target_vocal_audio")]
    with torch.no_grad():
        rendered = renderer(*audio, *(controls[name] for name in CONTROLS))
        terms = objective(rendered, *audio, batch["features_a"][index].float(),
                          batch["features_b"][index].float(), transition_length_bars=bars)
    return {name: float(value) for name, value in terms.items()}


def mean_terms(rows, config):
    out = {}
    for name in rows[0]:
        mean = float(np.mean([row[name] for row in rows]))
        weight = getattr(config, WEIGHTS[name], None) if name in WEIGHTS else None
        out[name] = {"mean": mean,
                     "weighted": None if weight is None else float(weight) * mean}
    return out


def flatten(batches, model, fresh):
    """Liste aller Beispiele: (batch, index, Modellkurven, Init-Kurven)."""
    items = []
    for batch in batches:
        predicted, initial = predict(model, batch), predict(fresh, batch)
        for index in range(batch["features_a"].shape[0]):
            items.append((batch, index,
                          {k: v[index] for k, v in predicted.items()},
                          {k: v[index] for k, v in initial.items()}))
    return items


def analyse_length(bars, train_items, validation_items, renderer, objective, config, tag):
    stack = lambda items, which, name: torch.stack(  # noqa: E731
        [item[which][name] for item in items]).numpy()
    all_items = train_items + validation_items
    b1 = {}
    for name in CONTROLS:
        values, reference = stack(all_items, 2, name), stack(all_items, 3, name)
        span = 0.75 if name.startswith("vocal_duck") else 1.0
        b1[name] = {
            "std_over_range_mean_pct": float(100 * values.std(axis=0).mean() / span),
            "std_over_range_max_pct": float(100 * values.std(axis=0).max() / span),
            "mean_abs_deviation_from_init": float(np.abs(values - reference).mean()),
            "max_abs_deviation_from_init": float(np.abs(values - reference).max()),
        }
    mean_curve = {name: torch.from_numpy(stack(train_items, 2, name).mean(axis=0))
                  for name in CONTROLS}
    rows = {"init": [], "model": [], "mean_curve": []}
    for batch, index, predicted, initial in validation_items:
        rows["init"].append(evaluate(renderer, objective, initial, batch, index, bars))
        rows["model"].append(evaluate(renderer, objective, predicted, batch, index, bars))
        rows["mean_curve"].append(evaluate(renderer, objective, mean_curve, batch, index, bars))
    count = len(validation_items)
    swap = np.zeros((count, count))
    for j, (batch, index, _, _) in enumerate(validation_items):
        for i in range(count):
            swap[i, j] = evaluate(renderer, objective, validation_items[i][2],
                                  batch, index, bars)["loss"]
    off = ~np.eye(count, dtype=bool)
    init_loss = float(np.mean([row["loss"] for row in rows["init"]]))
    matched = float(np.diag(swap).mean())
    swapped = float(swap[off].mean()) if count > 1 else None
    result = {
        "transition_length_bars": bars,
        "n_train": len(train_items), "n_validation": count,
        "b1_controls": b1,
        "b2_terms_validation": {key: mean_terms(value, config) for key, value in rows.items()},
        "swap": {
            "init_loss": init_loss, "matched_loss": matched, "swapped_loss": swapped,
            "share_of_gain_kept_with_wrong_inputs_pct":
                None if swapped is None or abs(init_loss - matched) < 1e-9
                else 100 * (init_loss - swapped) / (init_loss - matched),
            "own_curve_is_best_fraction":
                float(np.mean(np.argmin(swap, axis=0) == np.arange(count))),
        },
    }
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        figure, axes = plt.subplots(1, len(CONTROLS), figsize=(3.4 * len(CONTROLS), 3.2))
        for ax, name in zip(axes, CONTROLS):
            for row in stack(all_items, 2, name):
                ax.plot(row, color="#2a78d6", linewidth=0.6, alpha=0.3)
            ax.plot(stack(all_items, 3, name).mean(axis=0), color="#0b0b0b",
                    linestyle="--", linewidth=1.5, label="Initialisierung")
            ax.set_title(name, fontsize=9)
            ax.set_xlabel("Halbbeat", fontsize=8)
        axes[0].legend(fontsize=7, frameon=False)
        figure.suptitle(f"{tag}: {bars} Takte, alle Modellkurven (train+validation)", fontsize=10)
        figure.tight_layout()
        PLOTS.mkdir(parents=True, exist_ok=True)
        figure.savefig(PLOTS / f"student_variable_{tag}_L{bars}.png", dpi=130)
        plt.close(figure)
    except ImportError:
        result["plot"] = "matplotlib fehlt"
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--run")
    parser.add_argument("--dataset")
    parser.add_argument("--cache")
    parser.add_argument("--lengths", nargs="+", type=int, default=[2, 4, 6, 8])
    parser.add_argument("--sample-rate", type=int, default=None,
                        help="Default: training_sample_rate aus dem Run-Manifest")
    parser.add_argument("--max-validation", type=int, default=60,
                        help="Obergrenze je Länge (Vertauschungstest ist quadratisch)")
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args()

    if args.selftest:
        torch.manual_seed(1)
        model_config = VariableTCNBiLSTMControlConfig()
        model = VariableTCNBiLSTMTransitionControl(model_config).eval()
        with torch.no_grad():  # Zufallskopf, damit die Kurven nicht konstant sind
            model.output_head.weight.normal_(0.0, 0.05)
        renderer_kwargs = {"sample_rate": 11025, "lowpass_cutoff_hz": 180.0,
                           "lowpass_kernel_size": 127}
        batches, tag = synthetic_batches(), "selftest"
    else:
        if not (args.run and args.dataset and args.cache):
            parser.error("--run, --dataset und --cache sind erforderlich")
        run = Path(args.run)
        manifest = json.loads((run / "manifest.json").read_text(encoding="utf-8"))
        contract = manifest["contract"]
        raw = dict(contract["model"]["config"])
        raw["encoder_channels"] = tuple(raw["encoder_channels"])
        model_config = VariableTCNBiLSTMControlConfig(**raw)
        model = VariableTCNBiLSTMTransitionControl(model_config).eval()
        checkpoint = torch.load(run / "checkpoints" / "best.pt", map_location="cpu",
                                weights_only=True)
        model.load_state_dict(checkpoint["model_state_dict"])
        training = contract["training"]
        args.sample_rate = args.sample_rate or int(training["training_sample_rate"])
        renderer_kwargs = {
            "sample_rate": args.sample_rate,
            "lowpass_cutoff_hz": float(training.get("lowpass_cutoff_hz", 180.0)),
            "lowpass_kernel_size": int(training.get("lowpass_kernel_size", 127)),
        }
        batches, tag = load_real_batches(args), run.name

    torch.manual_seed(0)
    fresh = VariableTCNBiLSTMTransitionControl(model_config).eval()  # = Initialisierung
    renderer = DifferentiableVocalAwareRenderer(**renderer_kwargs)
    objective = VariableVocalAwareTransitionObjective()
    report = {"run": tag, "by_length": {}}
    for bars in sorted({int(batch["transition_length_bars"]) for batch in batches["train"]}):
        select = lambda split: [  # noqa: E731
            batch for batch in batches[split] if int(batch["transition_length_bars"]) == bars]
        train_items = flatten(select("train"), model, fresh)
        validation_items = flatten(select("validation"), model, fresh)[: args.max_validation]
        if not train_items or not validation_items:
            continue
        report["by_length"][str(bars)] = analyse_length(
            bars, train_items, validation_items, renderer, objective, objective.config, tag)
        swap = report["by_length"][str(bars)]["swap"]
        print(f"L={bars}: init {swap['init_loss']:.5f} model {swap['matched_loss']:.5f} "
              f"vertauscht {swap['swapped_loss']}, Gewinn mit falschen Eingaben erhalten: "
              f"{swap['share_of_gain_kept_with_wrong_inputs_pct']} %")
        for name, stats in report["by_length"][str(bars)]["b1_controls"].items():
            print(f"   {name:18} std/Range {stats['std_over_range_mean_pct']:.2f} % "
                  f"(max {stats['std_over_range_max_pct']:.2f} %), max |Δ Init| "
                  f"{stats['max_abs_deviation_from_init']:.4f}")
    RESULTS.mkdir(parents=True, exist_ok=True)
    path = RESULTS / f"student_variable_{tag}.json"
    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("geschrieben:", path)


if __name__ == "__main__":
    main()
