"""Plot the P06 paired controls, normalized within each renderer and length."""

import numpy as np


def plot_gains(rows, output):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    keys = list(dict.fromkeys((r["profile"], r["bars"], r["model_initialization"]) for r in rows))
    fig, ax = plt.subplots(figsize=(8.2, 5.1), layout="constrained")
    labels = []
    for y, (profile, bars, init) in enumerate(keys):
        subset = [r for r in rows if (r["profile"], r["bars"], r["model_initialization"]) == (profile, bars, init)]
        n = len({r["seed"] for r in subset})
        labels.append(f"{profile} · {bars} T · {'Legacy' if init == 'legacy' else 'EP-Start'} · n={n}")
        for cond, offset, mark, color, label in [
            ("F", -.19, "s", "#74411b", "Feste Train-Kurve"),
            ("M", 0, "o", "#00567d", "Eigene Controls"),
            ("swapped", .19, "x", "#5c6470", "Vertauschte Controls"),
        ]:
            x = [r["share_pct_ED"] for r in subset if r["condition"] == cond and r["share_pct_ED"] is not None]
            if not x:
                continue
            ax.plot(np.mean(x), y + offset, marker=mark, color=color, linestyle="none",
                    markersize=5.5, label=label if y == 0 else None)
            if n > 1:
                ax.hlines(y + offset, min(x), max(x), color=color, linewidth=1.5)
    for x, style in ((0, "-"), (100, "--")):
        ax.axvline(x, color="#555555", linestyle=style, linewidth=.9, zorder=0)
    for y in range(len(keys)-1):
        ax.axhline(y+.5, color="#eeeeee", linewidth=.7, zorder=0)
    ax.set_yticks(range(len(keys)), labels, fontsize=9)
    ax.invert_yaxis()
    ax.set_xlabel("Anteil am direkt erreichten Proxygewinn (%)\n100 × (E − X) / (E − D)  ·  0 = Equal Power, 100 = direkte Optimierung")
    ax.legend(loc="lower center", bbox_to_anchor=(.5, 1.01), ncol=3, frameon=False, fontsize=9)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.tick_params(axis="y", length=0)
    fig.savefig(output, dpi=240, facecolor="white")
    plt.close(fig)
