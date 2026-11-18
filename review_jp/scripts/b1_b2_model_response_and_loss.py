"""B1 (reagiert das Netz auf seine Eingabe?) und B2 (Loss-Zerlegung).

Für jeden Lauf in common.RUNS:
  * Best-Checkpoint laden (weights_only=True), Kurven für train+validation
    vorhersagen, pro Control-Kanal Streuung über Beispiele und Abweichung von
    der Referenz (frisch initialisiertes Modell = Epoche 0) messen.
  * Jeden Objective-Term einzeln auswerten für
      equal_power   frisch initialisiertes Modell (Epoche 0 des Runners)
      model         Best-Checkpoint, Kurven aus den eigenen Features
      mean_curve    EINE Kurve für alle: Mittel der Modellkurven über train
      swapped       Kurven aus den Features von Beispiel i, bewertet auf
                    Audio+Features von Beispiel j (alle i != j in validation)
      shared_opt    EINE direkt optimierte Kurve (auf train optimiert, kein
                    Netz, keine Eingabe) -> eingabeunabhängiges Optimum
      direct_opt    pro Beispiel direkt optimierte Kurven (Repo-Funktion
                    optimize_control_curves / optimize_vocal_control_curves)
  * Plausibilitätskontrolle: equal_power und model müssen die Werte aus
    history.json (Epoche 0 bzw. best_epoch, validation) reproduzieren.

Es wird nichts trainiert und nichts außerhalb von review_jp/ geschrieben.

Start:  review_jp/.venv/bin/python review_jp/scripts/b1_b2_model_response_and_loss.py [run ...]
Andere Läufe (z. B. TCN, kind="tcn_v1"): Eintrag in common.RUNS ergänzen.
"""

from __future__ import annotations

import json
import math
import sys
import time

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import torch

from common import (
    PLOTS,
    RUNS,
    build_model,
    build_renderer_and_objective,
    dump_json,
    load_metadata,
    load_run,
    load_split,
    load_waveforms,
)
from src.control import bounded_monotone_unit_curve
from src.control.differentiable import (
    OptimizableControlCurves,
    OptimizableVocalControlCurves,
    _frame_rms_db,
    _u_shaped_energy_target,
    optimize_control_curves,
    optimize_vocal_control_curves,
)

SEED = 20261113
MAX_TRAIN_AUDIO = 60          # Trainingsbeispiele, für die Audio gerendert wird
SHARED_STEPS = 300            # Adam-Schritte für die eine gemeinsame Kurve
SHARED_BATCH = 8
DIRECT_STEPS = 100            # Repo-Default von optimize_control_curves
INK, MUTED, GRID = "#0b0b0b", "#52514e", "#e4e3df"
BLUE, ORANGE, AQUA, YELLOW, MAGENTA, GREEN, VIOLET = (
    "#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6")
SURFACE = "#fcfcfb"

TERM_WEIGHTS = {
    "energy_shape": "energy_shape_weight",
    "boundary": "boundary_weight",
    "control_smoothness": "control_smoothness_weight",
    "control_curvature": "control_curvature_weight",
    "monotonicity": "monotonicity_weight",
    "clipping": "clipping_weight",
    "vocal_overlap": "vocal_overlap_weight",
    "vocal_boundary": "vocal_boundary_weight",
    "transient_artifact": "transient_artifact_weight",
    "vocal_stem_overlap": "vocal_stem_overlap_weight",
    "vocal_audibility": "vocal_audibility_weight",
    "vocal_mid_phrase_gain_change": "vocal_mid_phrase_gain_change_weight",
}
CONTROL_NAMES = {
    "mlp_v1": ("mix_position", "low_end_position"),
    "vocal_mlp_v2": ("mix_position", "low_end_position", "vocal_position",
                     "vocal_duck_a", "vocal_duck_b"),
    "tcn_v1": ("gain_A", "gain_B", "eq_low_A", "eq_low_B", "eq_mid_A", "eq_mid_B",
               "eq_high_A", "eq_high_B", "low_end_ownership", "vocal_ducking"),
}


# --------------------------------------------------------------------------
# Modell -> Controls, Controls -> Objective-Terme
# --------------------------------------------------------------------------
def predict(kind, model, data):
    with torch.no_grad():
        output = model(
            torch.from_numpy(data["features_a"]),
            torch.from_numpy(data["features_b"]),
            torch.from_numpy(data["global_features"]),
        )
    if kind == "tcn_v1":
        return {name: output[name].clone() for name in CONTROL_NAMES[kind]}
    return {name: getattr(output, name).clone() for name in CONTROL_NAMES[kind]}


def evaluate(kind, renderer, objective, controls, wave, features_a, features_b):
    """controls: dict name -> (T,) Tensor. Gibt Roh-Terme als dict zurück."""
    src, tgt = wave["source_audio"], wave["target_audio"]
    if kind == "mlp_v1":
        rendered = renderer(src, tgt, controls["mix_position"], controls["low_end_position"])
        return objective(rendered, src, tgt, features_a, features_b), rendered
    if kind == "vocal_mlp_v2":
        srcv, tgtv = wave["source_vocal_audio"], wave["target_vocal_audio"]
        rendered = renderer(
            src, tgt, srcv, tgtv,
            controls["mix_position"], controls["low_end_position"],
            controls["vocal_position"], controls["vocal_duck_a"], controls["vocal_duck_b"],
        )
        return objective(rendered, src, tgt, srcv, tgtv, features_a, features_b), rendered
    if kind == "tcn_v1":
        rendered = renderer(
            src, tgt,
            controls["gain_A"], controls["gain_B"],
            controls["eq_low_A"], controls["eq_low_B"],
            controls["eq_mid_A"], controls["eq_mid_B"],
            controls["eq_high_A"], controls["eq_high_B"],
            controls["low_end_ownership"], controls["vocal_ducking"],
        )
        return objective(rendered, src, tgt, features_a, features_b), rendered
    raise ValueError(kind)


def weighted(terms, config):
    out = {}
    for name, attribute in TERM_WEIGHTS.items():
        if name in terms and hasattr(config, attribute):
            out[name] = float(getattr(config, attribute)) * float(terms[name])
    return out


def row(controls, index):
    return {name: value[index] for name, value in controls.items()}


class SharedTCNCurves(torch.nn.Module):
    """Freie Logits (T, 10) mit derselben Ausgabetransformation wie
    TCNBiLSTMTransitionControl.forward (src/ml/model.py:373-386)."""

    def __init__(self, points=32, bound=0.6):
        super().__init__()
        self.logits = torch.nn.Parameter(torch.zeros(points, 10))
        self.bound = bound

    def forward(self):
        controls = torch.sigmoid(self.logits).clone()
        mix = bounded_monotone_unit_curve(self.logits[:-1, 1], self.bound)
        low = bounded_monotone_unit_curve(self.logits[:-1, 8], self.bound)
        columns = [controls[:, i] for i in range(10)]
        columns[0], columns[1], columns[8] = 1.0 - mix, mix, low
        return dict(zip(CONTROL_NAMES["tcn_v1"], columns))


def make_shared_curves(kind, model_config):
    bound = float(model_config.get("increment_logit_bound", 0.6))
    if kind == "mlp_v1":
        module = OptimizableControlCurves(32, increment_logit_bound=bound)
        return module, lambda: dict(zip(CONTROL_NAMES[kind], module()))
    if kind == "vocal_mlp_v2":
        module = OptimizableVocalControlCurves(
            32,
            increment_logit_bound=bound,
            maximum_vocal_ducking=float(model_config["maximum_vocal_ducking"]),
            initial_vocal_duck_logit=float(model_config["initial_vocal_duck_logit"]),
        )
        return module, lambda: dict(zip(CONTROL_NAMES[kind], module()))
    module = SharedTCNCurves(32, bound)
    return module, module


def optimize_shared(kind, model_config, renderer, objective, examples, rng):
    """Eine einzige Kurvenschar für alle Beispiele (eingabeunabhängig)."""
    module, curves = make_shared_curves(kind, model_config)
    optimizer = torch.optim.Adam(module.parameters(), lr=0.05)
    order = list(range(len(examples)))
    for _ in range(SHARED_STEPS):
        batch = rng.choice(order, size=min(SHARED_BATCH, len(order)), replace=False)
        optimizer.zero_grad()
        loss = 0.0
        for index in batch:
            wave, fa, fb = examples[index]
            terms, _ = evaluate(kind, renderer, objective, curves(), wave, fa, fb)
            loss = loss + terms["loss"] / len(batch)
        loss.backward()
        optimizer.step()
    with torch.no_grad():
        return {name: value.detach().clone() for name, value in curves().items()}


def optimize_direct(kind, model_config, renderer, objective, wave, fa, fb):
    bound = float(model_config.get("increment_logit_bound", 0.6))
    if kind == "mlp_v1":
        result = optimize_control_curves(
            wave["source_audio"], wave["target_audio"],
            renderer=renderer, objective=objective, control_points=32,
            steps=DIRECT_STEPS, learning_rate=0.05, increment_logit_bound=bound,
            features_a=fa, features_b=fb,
        )
        return {"mix_position": result.mix_position,
                "low_end_position": result.low_end_position}
    if kind == "vocal_mlp_v2":
        result = optimize_vocal_control_curves(
            wave["source_audio"], wave["target_audio"],
            wave["source_vocal_audio"], wave["target_vocal_audio"],
            renderer=renderer, objective=objective, control_points=32,
            steps=DIRECT_STEPS, learning_rate=0.05, increment_logit_bound=bound,
            maximum_vocal_ducking=float(model_config["maximum_vocal_ducking"]),
            features_a=fa, features_b=fb,
        )
        return {name: getattr(result, name) for name in CONTROL_NAMES[kind]}
    module = SharedTCNCurves(32, bound)
    optimizer = torch.optim.Adam(module.parameters(), lr=0.05)
    for _ in range(DIRECT_STEPS):
        optimizer.zero_grad()
        terms, _ = evaluate(kind, renderer, objective, module(), wave, fa, fb)
        terms["loss"].backward()
        optimizer.step()
    with torch.no_grad():
        return {name: value.detach().clone() for name, value in module().items()}


# --------------------------------------------------------------------------
# Statistik
# --------------------------------------------------------------------------
def control_range(kind, name, model_config):
    if name.startswith("vocal_duck_"):
        return float(model_config.get("maximum_vocal_ducking", 0.75))
    return 1.0


def max_deviation_from_linear(points=32, bound=0.6):
    """Größte mögliche Abweichung einer bounded-monotone-Kurve von der Rampe."""
    increments = points - 1
    best = 0.0
    for k in range(1, increments):
        high, low = math.exp(bound), math.exp(-bound)
        position = k * high / (k * high + (increments - k) * low)
        best = max(best, position - k / increments)
    return best


def summarize_terms(rows, config):
    names = sorted({name for item in rows for name in item})
    summary = {}
    for name in names:
        values = np.asarray([float(item[name]) for item in rows if name in item])
        attribute = TERM_WEIGHTS.get(name)
        weight = float(getattr(config, attribute)) if attribute and hasattr(config, attribute) else None
        summary[name] = {
            "mean": float(values.mean()),
            "weight": weight,
            "weighted_mean": None if weight is None else float(weight * values.mean()),
        }
    return summary


# --------------------------------------------------------------------------
# Plots
# --------------------------------------------------------------------------
def style(ax):
    ax.set_facecolor(SURFACE)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(GRID)
    ax.grid(True, color=GRID, linewidth=0.6)
    ax.tick_params(colors=MUTED, labelsize=8)
    ax.set_axisbelow(True)


def plot_curves(name, kind, curves, reference, n_train, n_validation, bound):
    names = CONTROL_NAMES[kind]
    figure, axes = plt.subplots(2, len(names), figsize=(3.6 * len(names), 6.2),
                                squeeze=False, facecolor=SURFACE)
    steps = np.arange(32)
    for column, control in enumerate(names):
        values = curves[control].numpy()
        ref = reference[control].numpy()
        for row_index, (ax, data, ref_line) in enumerate((
            (axes[0, column], values, ref.mean(axis=0)),
            (axes[1, column], values - ref, np.zeros(ref.shape[-1])),
        )):
            style(ax)
            for i in range(n_train):
                ax.plot(steps, data[i], color=BLUE, linewidth=0.7, alpha=0.25,
                        label="Modell, train" if i == 0 else None)
            for i in range(n_train, n_train + n_validation):
                ax.plot(steps, data[i], color=ORANGE, linewidth=0.9, alpha=0.7,
                        label="Modell, validation" if i == n_train else None)
            ax.plot(steps, ref_line, color=INK, linewidth=1.6, linestyle="--",
                    label="Referenz (Epoche 0)")
            if row_index == 0:
                ax.set_title(control, fontsize=10, color=INK)
                ax.set_ylim(-0.03, 1.03)
            else:
                limit = max(0.02, 1.15 * float(np.abs(values - ref).max()))
                ax.set_ylim(-limit, limit)
                ax.set_xlabel("Halbbeat (0–31)", fontsize=8, color=MUTED)
        axes[0, column].set_ylabel("Control-Wert" if column == 0 else "", fontsize=8, color=MUTED)
        axes[1, column].set_ylabel("Abweichung von Referenz" if column == 0 else "",
                                   fontsize=8, color=MUTED)
    axes[0, 0].legend(fontsize=7, frameon=False, loc="upper left")
    figure.suptitle(
        f"{name}: {n_train} train + {n_validation} validation, oben absolut, unten "
        f"Differenz zur Referenz\n(Positionskurven können höchstens ±{bound:.2f} "
        f"von der Rampe abweichen)",
        fontsize=10, color=INK,
    )
    figure.tight_layout(rect=(0, 0, 1, 0.95))
    path = PLOTS / f"b1_curves_{name}.png"
    figure.savefig(path, dpi=140)
    plt.close(figure)
    return path


def plot_loss(name, conditions, config):
    groups = [
        ("energy_shape", "Energie-V-Form", BLUE),
        ("vocal_boundary", "vocal_boundary (v4)", ORANGE),
        ("transient_artifact", "transient_artifact", AQUA),
        ("vocal_audibility", "vocal_audibility (v5)", MAGENTA),
        ("vocal_overlap", "vocal_overlap (v4)", YELLOW),
        ("vocal_stem_overlap", "vocal_stem_overlap (v5)", GREEN),
        ("_regularizer", "Glattheit+Krümmung", VIOLET),
        ("_rest", "Rest (boundary, clipping, …)", "#9a9992"),
    ]
    labels = list(conditions)
    figure, ax = plt.subplots(figsize=(1.5 * len(labels) + 3.2, 4.6), facecolor=SURFACE)
    style(ax)
    ax.grid(axis="x", visible=False)
    bottoms = np.zeros(len(labels))
    used = set()
    for key, label, color in groups:
        heights = []
        for condition in labels:
            terms = conditions[condition]
            if key == "_regularizer":
                value = sum((terms.get(n, {}).get("weighted_mean") or 0.0)
                            for n in ("control_smoothness", "control_curvature"))
            elif key == "_rest":
                value = sum((terms.get(n, {}).get("weighted_mean") or 0.0)
                            for n in ("boundary", "clipping", "monotonicity",
                                      "vocal_mid_phrase_gain_change"))
            else:
                value = terms.get(key, {}).get("weighted_mean") or 0.0
            heights.append(value)
        heights = np.asarray(heights)
        if heights.max() < 1e-4:
            continue
        used.add(key)
        ax.bar(labels, heights, bottom=bottoms, width=0.55, color=color, label=label,
               edgecolor=SURFACE, linewidth=1.5)
        bottoms += heights
    for x, condition in enumerate(labels):
        total = conditions[condition]["loss"]["mean"]
        ax.text(x, bottoms[x] + 0.004, f"{total:.4f}", ha="center", va="bottom",
                fontsize=8, color=INK)
    ax.set_ylabel("gewichteter Beitrag zum Loss (Mittel, validation)", fontsize=8, color=MUTED)
    ax.set_title(f"{name}: Loss-Zerlegung auf validation", fontsize=10, color=INK)
    ax.legend(fontsize=7, frameon=False, loc="upper left", bbox_to_anchor=(1.0, 1.0))
    plt.setp(ax.get_xticklabels(), fontsize=8, color=INK)
    figure.tight_layout()
    path = PLOTS / f"b2_loss_{name}.png"
    figure.savefig(path, dpi=140)
    plt.close(figure)
    return path


def plot_energy(name, energy_rows):
    figure, axes = plt.subplots(1, 2, figsize=(10.5, 4.0), facecolor=SURFACE, sharey=True)
    frames = np.arange(32)
    for ax, key, title in (
        (axes[0], "equal_power", "Equal Power (Epoche 0)"),
        (axes[1], "model", "Modell (Best-Checkpoint)"),
    ):
        style(ax)
        for index, item in enumerate(energy_rows):
            ax.plot(frames, np.asarray(item[key]) - np.asarray(item["line"]),
                    color=BLUE, linewidth=0.9, alpha=0.5,
                    label="gerendert" if index == 0 else None)
        target = np.mean([np.asarray(item["target"]) - np.asarray(item["line"])
                          for item in energy_rows], axis=0)
        ax.plot(frames, target, color=INK, linewidth=1.8, linestyle="--",
                label="Ziel des Objectives (V, −6 dB)")
        ax.set_title(title, fontsize=10, color=INK)
        ax.set_xlabel("Energie-Frame (0–31)", fontsize=8, color=MUTED)
    axes[0].set_ylabel("RMS in dB relativ zur Geraden\nStartpegel A → Endpegel B",
                       fontsize=8, color=MUTED)
    axes[0].legend(fontsize=7, frameon=False, loc="lower left")
    figure.suptitle(f"{name}: gerenderter Energieverlauf gegen die feste Zielform "
                    f"(validation)", fontsize=10, color=INK)
    figure.tight_layout(rect=(0, 0, 1, 0.94))
    path = PLOTS / f"b2_energy_{name}.png"
    figure.savefig(path, dpi=140)
    plt.close(figure)
    return path


# --------------------------------------------------------------------------
# Hauptablauf pro Lauf
# --------------------------------------------------------------------------
def analyse(name, spec, manifest, model, fresh_model, label=None):
    kind = spec["kind"]
    label = label or name
    started = time.time()
    rng = np.random.default_rng(SEED)
    torch.manual_seed(SEED)
    model_config = manifest["contract"]["model"]["config"]
    sample_rate = int(manifest["contract"]["training"]["training_sample_rate"])
    renderer, objective = build_renderer_and_objective(kind, manifest)
    config = objective.config

    train = load_split(spec["dataset"], "train")
    validation = load_split(spec["dataset"], "validation")
    metadata = load_metadata(spec["dataset"])
    n_train, n_validation = len(train["example_ids"]), len(validation["example_ids"])

    merged = {key: np.concatenate((train[key], validation[key])) for key in
              ("features_a", "features_b", "global_features")}
    curves = predict(kind, model, merged) if model is not None else None
    reference = predict(kind, fresh_model, merged)
    if curves is None:
        curves = reference

    # ---- B1: Streuung und Abweichung -------------------------------------
    bound = max_deviation_from_linear(32, float(model_config.get("increment_logit_bound", 0.6)))
    b1 = {}
    for control in CONTROL_NAMES[kind]:
        values = curves[control].numpy()
        ref = reference[control].numpy()
        span = control_range(kind, control, model_config)
        per_step_std = values.std(axis=0)
        b1[control] = {
            "range": span,
            "std_over_examples_mean_over_time": float(per_step_std.mean()),
            "std_over_examples_max_over_time": float(per_step_std.max()),
            "std_over_range_mean_pct": float(100 * per_step_std.mean() / span),
            "std_over_range_max_pct": float(100 * per_step_std.max() / span),
            "mean_abs_deviation_from_reference": float(np.abs(values - ref).mean()),
            "max_abs_deviation_from_reference": float(np.abs(values - ref).max()),
            "mean_curve_max_abs_deviation_from_reference":
                float(np.abs(values.mean(axis=0) - ref.mean(axis=0)).max()),
            "reference_spread_max": float(ref.std(axis=0).max()),
        }
    curve_plot = plot_curves(label, kind, curves, reference, n_train, n_validation, bound)

    # ---- Audio laden ------------------------------------------------------
    def bundle(split_data, offset, indices):
        items = []
        for index in indices:
            wave = load_waveforms(spec["cache"], split_data["example_ids"][index], sample_rate)
            items.append((
                wave,
                torch.from_numpy(split_data["features_a"][index]),
                torch.from_numpy(split_data["features_b"][index]),
                offset + index,
            ))
        return items

    train_indices = sorted(rng.choice(n_train, size=min(MAX_TRAIN_AUDIO, n_train),
                                      replace=False).tolist())
    train_items = bundle(train, 0, train_indices)
    validation_items = bundle(validation, n_train, range(n_validation))

    mean_curve = {control: curves[control][:n_train].mean(dim=0)
                  for control in CONTROL_NAMES[kind]}
    shared = optimize_shared(
        kind, model_config, renderer, objective,
        [(wave, fa, fb) for wave, fa, fb, _ in train_items], rng,
    )

    def run_condition(items, controls_for):
        rows = []
        for wave, fa, fb, global_index in items:
            with torch.no_grad():
                terms, _ = evaluate(kind, renderer, objective, controls_for(global_index),
                                    wave, fa, fb)
            rows.append({k: float(v) for k, v in terms.items()})
        return rows

    results = {}
    per_example = {}
    for split_name, items in (("validation", validation_items), ("train_subset", train_items)):
        conditions = {
            "equal_power": run_condition(items, lambda g: row(reference, g)),
            "model": run_condition(items, lambda g: row(curves, g)),
            "mean_curve": run_condition(items, lambda g: mean_curve),
            "shared_opt": run_condition(items, lambda g: shared),
        }
        if split_name == "validation":
            direct_rows = []
            for wave, fa, fb, _ in items:
                direct = optimize_direct(kind, model_config, renderer, objective, wave, fa, fb)
                with torch.no_grad():
                    terms, _ = evaluate(kind, renderer, objective, direct, wave, fa, fb)
                direct_rows.append({k: float(v) for k, v in terms.items()})
            conditions["direct_opt"] = direct_rows
        per_example[split_name] = {key: [item["loss"] for item in value]
                                   for key, value in conditions.items()}
        results[split_name] = {key: summarize_terms(value, config)
                               for key, value in conditions.items()}

    # ---- Vertauschungstest (validation, alle i != j) -----------------------
    swap = np.zeros((n_validation, n_validation))
    for j, (wave, fa, fb, _) in enumerate(validation_items):
        for i in range(n_validation):
            with torch.no_grad():
                terms, _ = evaluate(kind, renderer, objective, row(curves, n_train + i),
                                    wave, fa, fb)
            swap[i, j] = float(terms["loss"])
    pair_of = []
    for example_id in validation["example_ids"]:
        item = metadata[example_id]
        pair_of.append((item["source_track"]["sha256"], item["target_track"]["sha256"]))
    off = ~np.eye(n_validation, dtype=bool)
    same_pair = np.asarray([[pair_of[i] == pair_of[j] for j in range(n_validation)]
                            for i in range(n_validation)])
    matched = float(np.diag(swap).mean())
    equal_power_loss = results["validation"]["equal_power"]["loss"]["mean"]
    swapped_all = float(swap[off].mean())
    swap_summary = {
        "matched_loss": matched,
        "swapped_loss_all_i_ne_j": swapped_all,
        "swapped_loss_other_track_pair": float(swap[off & ~same_pair].mean())
            if (off & ~same_pair).any() else None,
        "swapped_loss_same_track_pair": float(swap[off & same_pair].mean())
            if (off & same_pair).any() else None,
        "fraction_of_examples_where_own_curve_is_best":
            float(np.mean(np.argmin(swap, axis=0) == np.arange(n_validation))),
        "mean_rank_of_own_curve_1_is_best":
            float(np.mean([1 + int(np.sum(swap[:, j] < swap[j, j]))
                           for j in range(n_validation)])),
        "gain_vs_equal_power_matched": equal_power_loss - matched,
        "gain_vs_equal_power_swapped": equal_power_loss - swapped_all,
    }
    gain = swap_summary["gain_vs_equal_power_matched"]
    swap_summary["share_of_gain_kept_with_wrong_inputs_pct"] = (
        float(100 * swap_summary["gain_vs_equal_power_swapped"] / gain) if abs(gain) > 1e-9 else None
    )
    results["validation"]["swapped"] = {
        "loss": {"mean": swapped_all, "weight": None, "weighted_mean": None}}

    # ---- Energieverlauf gegen Zielform -------------------------------------
    energy_rows = []
    valley_only = []
    for wave, fa, fb, global_index in validation_items:
        item = {}
        with torch.no_grad():
            src = wave["source_audio"].unsqueeze(0)
            tgt = wave["target_audio"].unsqueeze(0)
            source_db = _frame_rms_db(src, 32, config.epsilon)
            target_db = _frame_rms_db(tgt, 32, config.epsilon)
            shape = _u_shaped_energy_target(source_db[:, 0], target_db[:, -1], 32,
                                            config.valley_depth_db)[0]
            line = torch.linspace(float(source_db[0, 0]), float(target_db[0, -1]), 32)
            for key, source in (("equal_power", reference), ("model", curves)):
                _, rendered = evaluate(kind, renderer, objective, row(source, global_index),
                                       wave, fa, fb)
                item[key] = _frame_rms_db(rendered.audio.unsqueeze(0), 32,
                                          config.epsilon)[0].tolist()
            item["target"], item["line"] = shape.tolist(), line.tolist()
            valley_only.append(float(torch.mean(((line - shape) / config.energy_tolerance_db) ** 2)))
        energy_rows.append(item)
    energy_plot = plot_energy(label, energy_rows)

    # ---- Abgleich mit history.json -----------------------------------------
    check = None
    history_path = spec["run"] / "history.json" if model is not None else None
    if history_path is not None and history_path.is_file():
        history = json.loads(history_path.read_text("utf-8"))["epochs"]
        best = manifest["best_epoch"]
        by_epoch = {item["epoch"]: item for item in history}
        check = {
            "history_epoch0_validation_loss": by_epoch[0]["validation"]["loss"],
            "recomputed_equal_power_validation_loss": equal_power_loss,
            "history_best_epoch": best,
            "history_best_validation_loss": by_epoch[best]["validation"]["loss"],
            "recomputed_model_validation_loss": results["validation"]["model"]["loss"]["mean"],
            "history_epoch0_train_loss": by_epoch[0]["train"]["loss"],
            "history_best_train_loss": by_epoch[best]["train"]["loss"],
            "epochs_run": len(history) - 1,
        }

    loss_plot = plot_loss(label, {k: results["validation"][k] for k in
                                  ("equal_power", "model", "mean_curve", "shared_opt",
                                   "direct_opt")}, config)

    validation_losses = {k: results["validation"][k]["loss"]["mean"]
                         for k in results["validation"]}
    ep, direct = validation_losses["equal_power"], validation_losses["direct_opt"]
    headroom = ep - direct
    gap = {
        "equal_power": ep,
        "model": validation_losses["model"],
        "mean_curve": validation_losses["mean_curve"],
        "shared_opt": validation_losses["shared_opt"],
        "direct_opt": direct,
        "swapped": validation_losses["swapped"],
        "model_gain_abs": ep - validation_losses["model"],
        "model_gain_rel_pct": 100 * (ep - validation_losses["model"]) / ep,
        "direct_gain_rel_pct": 100 * headroom / ep,
        "model_share_of_direct_headroom_pct":
            100 * (ep - validation_losses["model"]) / headroom if headroom > 1e-9 else None,
        "shared_opt_share_of_direct_headroom_pct":
            100 * (ep - validation_losses["shared_opt"]) / headroom if headroom > 1e-9 else None,
        "mean_curve_share_of_model_gain_pct":
            100 * (ep - validation_losses["mean_curve"]) / (ep - validation_losses["model"])
            if abs(ep - validation_losses["model"]) > 1e-9 else None,
        "energy_shape_valley_only_floor_mean": float(np.mean(valley_only)),
    }
    report = {
        "run": str(spec["run"].name) if model is not None else "fresh_init_only",
        "kind": kind,
        "dataset": spec["dataset"].name,
        "n_train": n_train, "n_validation": n_validation,
        "n_train_with_audio": len(train_items),
        "parameter_count": int(sum(p.numel() for p in fresh_model.parameters())),
        "max_possible_position_deviation_from_linear": bound,
        "b1_controls": b1,
        "b2_terms": results,
        "b2_gap_validation": gap,
        "swap_test_validation": swap_summary,
        "history_check": check,
        "per_example_loss": per_example,
        "shared_opt_curves": {k: v.tolist() for k, v in shared.items()},
        "mean_model_curves": {k: v.tolist() for k, v in mean_curve.items()},
        "plots": [str(p.relative_to(PLOTS.parent)) for p in (curve_plot, loss_plot, energy_plot)],
        "seconds": round(time.time() - started, 1),
    }
    dump_json(f"b1_b2_{label}.json", report)

    print(f"\n================ {label} ({kind}, {spec['dataset'].name}) ================")
    if check:
        print("Abgleich history.json:", json.dumps(check, indent=1))
    print("B1 pro Control-Kanal:")
    for control, stats in b1.items():
        print(f"  {control:18} std/Range mean {stats['std_over_range_mean_pct']:.2f}% "
              f"max {stats['std_over_range_max_pct']:.2f}% | |Δ Referenz| mean "
              f"{stats['mean_abs_deviation_from_reference']:.4f} max "
              f"{stats['max_abs_deviation_from_reference']:.4f}")
    print("B2 validation, gewichtete Beiträge:")
    for condition, terms in results["validation"].items():
        parts = ", ".join(f"{k}={v['weighted_mean']:.4f}" for k, v in terms.items()
                          if v["weighted_mean"] is not None and v["weighted_mean"] > 5e-5)
        print(f"  {condition:12} loss={terms['loss']['mean']:.5f} | {parts}")
    print("Lücke:", json.dumps(gap, indent=1))
    print("Vertauschung:", json.dumps(swap_summary, indent=1))
    return report


def main():
    names = sys.argv[1:] or list(RUNS)
    for name in names:
        if name == "tcn_fresh_init":
            # Kein lokaler TCN-Checkpoint: nur Initialisierung + direkte Optimierung.
            base = RUNS["mlp_v1_top3"]
            manifest = json.loads((base["run"] / "manifest.json").read_text("utf-8"))
            manifest = json.loads(json.dumps(manifest))
            manifest["contract"]["model"]["config"] = {
                "encoder_channels": [64, 128], "tcn_kernel_size": 3, "tcn_dilation": 2,
                "fusion_dimension": 256, "controller_hidden_size": 128,
                "controller_layers": 2, "output_dimension": 10, "dropout": 0.0,
                "increment_logit_bound": 0.6,
            }
            spec = {"kind": "tcn_v1", "run": base["run"], "dataset": base["dataset"],
                    "cache": base["cache"]}
            torch.manual_seed(SEED)
            fresh = build_model("tcn_v1", manifest).eval()
            analyse(name, spec, manifest, None, fresh, label=name)
            continue
        spec, manifest, model, _ = load_run(name)
        torch.manual_seed(int(manifest["contract"]["training"]["seed"]))
        fresh = build_model(spec["kind"], manifest).eval()
        analyse(name, spec, manifest, model, fresh)


if __name__ == "__main__":
    main()
