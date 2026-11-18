"""Zusammenfassungsplot für den Full-Band-/TCN-Pfad (ohne lokalen Checkpoint).

Liest review_jp/results/b1_b2_mlp_v1_top3.json und b1_b2_tcn_fresh_init.json
(vorher b1_b2_model_response_and_loss.py mlp_v1_top3 tcn_fresh_init ausführen).
"""

from __future__ import annotations

import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from common import OUT, PLOTS

SURFACE, INK, MUTED, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
GROUPS = (
    ("energy_shape", "Energie-V-Form", "#2a78d6"),
    ("vocal_boundary", "vocal_boundary", "#eb6834"),
    ("transient_artifact", "transient_artifact", "#1baf7a"),
    ("boundary", "boundary (Randpegel)", "#eda100"),
    ("_other", "übrige Terme", "#9a9992"),
)


def main():
    mlp = json.loads((OUT / "b1_b2_mlp_v1_top3.json").read_text())["b2_terms"]["validation"]
    tcn = json.loads((OUT / "b1_b2_tcn_fresh_init.json").read_text())["b2_terms"]["validation"]
    bars = (
        ("Equal Power\n(2-Band, MLP-Epoche 0)", mlp["equal_power"]),
        ("TCN/BiLSTM Epoche 0\n(Full-Band, frisch init.)", tcn["equal_power"]),
        ("EINE feste Kurvenschar\n(kein Netz, keine Eingabe)", tcn["shared_opt"]),
        ("pro Beispiel direkt\noptimiert (Obergrenze)", tcn["direct_opt"]),
    )
    figure, ax = plt.subplots(figsize=(9.6, 4.8), facecolor=SURFACE)
    ax.set_facecolor(SURFACE)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(GRID)
    ax.grid(axis="y", color=GRID, linewidth=0.6)
    ax.set_axisbelow(True)
    labels = [label for label, _ in bars]
    bottoms = np.zeros(len(bars))
    named = {key for key, _, _ in GROUPS}
    for key, label, color in GROUPS:
        heights = []
        for _, terms in bars:
            if key == "_other":
                value = sum((v["weighted_mean"] or 0.0) for k, v in terms.items()
                            if k not in named and k != "loss")
            else:
                value = terms.get(key, {}).get("weighted_mean") or 0.0
            heights.append(value)
        heights = np.asarray(heights)
        ax.bar(labels, heights, bottom=bottoms, width=0.55, color=color, label=label,
               edgecolor=SURFACE, linewidth=1.5)
        bottoms += heights
    for x, (_, terms) in enumerate(bars):
        ax.text(x, bottoms[x] + 0.03, f"{terms['loss']['mean']:.3f}", ha="center",
                fontsize=9, color=INK)
    ax.set_ylabel("gewichteter Beitrag zum Objective v4 (validation, n=9)",
                  fontsize=8, color=MUTED)
    ax.set_title("Full-Band-Pfad: Startpunkt und eingabeunabhängiges Optimum",
                 fontsize=10, color=INK)
    ax.tick_params(colors=MUTED, labelsize=8)
    ax.legend(fontsize=8, frameon=False, loc="upper right")
    figure.tight_layout()
    figure.savefig(PLOTS / "b2_tcn_fullband_summary.png", dpi=140)
    print("geschrieben:", PLOTS / "b2_tcn_fullband_summary.png")


if __name__ == "__main__":
    main()
