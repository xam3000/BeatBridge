"""Read-only sweep audit; preserves the CSV, training histories, and checkpoints."""
import csv
import hashlib
import json
import statistics
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "wandb_export_2026-10-02T09_20_57.391+02_00.csv"
DEST = ROOT / "output/analysis/wandb_sweep_20261002"
rows = list(csv.DictReader(SOURCE.open(encoding="utf-8-sig", newline="")))
valid = [r for r in rows if r["best_validation_loss"]]
finished = [r for r in valid if r["State"] == "finished"]
ranked = sorted(valid, key=lambda r: float(r["best_validation_loss"]))
params = ["learning_rate", "batch_size", "dropout", "tcn_dilation",
          "tcn_kernel_size", "weight_decay", "gradient_clip_norm"]

def stats(rs):
    vals = [float(r["best_validation_loss"]) for r in rs]
    return {"n": len(rs), "min": min(vals), "median": statistics.median(vals),
            "max": max(vals), "below_0.30": sum(v < .30 for v in vals)}

groups = {}
for p in params[1:]:
    groups[p] = {}
    for value in sorted({r[p] for r in valid}):
        selected = [r for r in valid if r[p] == value]
        complete = [r for r in selected if r["State"] == "finished"]
        groups[p][value] = {"all": stats(selected),
                            "finished": stats(complete) if complete else None}

audits = []
histories = {}
for r in valid:
    run = r["Name"].rsplit("-", 1)[1]
    directory = ROOT / "output/training_runs/wandb_sweeps/tcn_bilstm_transition_control_v1" / r["Sweep"] / run
    history_path = directory / "history.json"
    manifest_path = directory / "manifest.json"
    item = {"run": run, "history_present": history_path.exists(),
            "manifest_present": manifest_path.exists()}
    if history_path.exists() and manifest_path.exists():
        h = json.loads(history_path.read_text(encoding="utf-8"))["epochs"]
        m = json.loads(manifest_path.read_text(encoding="utf-8"))
        best = min(h, key=lambda e: e["validation"]["loss"])
        histories[run] = h
        item.update(best_epoch_history=best["epoch"], best_loss_history=best["validation"]["loss"],
                    csv_loss_matches=abs(best["validation"]["loss"] - float(r["best_validation_loss"])) < 1e-10,
                    history_last_epoch=h[-1]["epoch"], manifest_status=m["status"],
                    checkpoint_present=m["files"].get("best_checkpoint") is not None,
                    history_hash_matches=hashlib.sha256(history_path.read_bytes()).hexdigest() == m["files"]["history"]["sha256"],
                    best_validation=best["validation"], best_train=best["train"],
                    initial_validation=h[0]["validation"], objective_weights=m["contract"]["objective"]["config"])
    audits.append(item)

components = {}
for r in ranked[:4] + [next(x for x in valid if x["Name"].endswith("1w51w9t6"))]:
    run = r["Name"].rsplit("-", 1)[1]
    a = next(x for x in audits if x["run"] == run)
    if "best_validation" in a:
        components[run] = {k: a["best_validation"][k] * a["objective_weights"][k + "_weight"]
                           for k in a["best_validation"] if k + "_weight" in a["objective_weights"]}

summary = {"source": SOURCE.name, "source_sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
           "rows": len(rows), "columns": len(rows[0]), "states": dict(Counter(r["State"] for r in rows)),
           "sweeps": dict(Counter(r["Sweep"] for r in rows)), "all": stats(valid), "finished": stats(finished),
           "killed": stats([r for r in valid if r["State"] == "killed"]),
           "summed_runtime_hours": sum(float(r["Runtime"]) for r in rows)/3600,
           "killed_epochs": dict(Counter(r["epoch"] for r in valid if r["State"] == "killed")),
           "best_epoch_median_finished": statistics.median(int(r["best_epoch"]) for r in finished),
           "groups": groups, "top10": [{k: r[k] for k in ["Name", "State", "best_validation_loss", "best_epoch", "epoch", "validation/loss"] + params} for r in ranked[:10]],
           "audits": audits, "weighted_best_epoch_components": components,
           "metric_alias_mismatches": sum(r["best_validation_loss"] != r["best/validation_loss"] for r in valid)}
DEST.mkdir(parents=True, exist_ok=True)
(DEST / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
# Static research figure, with a fixed scale shared by the selected histories.
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
fig, axes = plt.subplots(1, 2, figsize=(12, 4.5), constrained_layout=True)
for state, color in [("finished", "#2166ac"), ("killed", "#969696")]:
    selected = [r for r in valid if r["State"] == state]
    axes[0].scatter([float(r["learning_rate"]) for r in selected],
                    [float(r["best_validation_loss"]) for r in selected],
                    color=color, label=f"{state} (n={len(selected)})", alpha=.8, s=32)
axes[0].set_xscale("log")
axes[0].set(xlabel="Basis-Lernrate (logarithmisch)", ylabel="Bester Validation-Loss",
            title="91 Runs mit Metriken")
axes[0].legend(frameon=False)
for run in list(components):
    h = histories[run]
    axes[1].plot([e["epoch"] for e in h], [e["validation"]["loss"] for e in h],
                 label=run, linewidth=1.4)
axes[1].set(xlabel="Epoche", ylabel="Validation-Loss", ylim=(.25, .36), xlim=(1,150),
            title="Top 4 und ein Run aus dem typischen Loss-Bereich")
axes[1].legend(frameon=False, fontsize=8)
for ax in axes:
    ax.grid(alpha=.2)
fig.savefig(DEST / "sweep_analysis.png", dpi=180)
plt.close(fig)
print(json.dumps({"states": summary["states"], "source_sha256": summary["source_sha256"],
                  "local_histories": sum(a["history_present"] for a in audits),
                  "csv_loss_mismatches": [a["run"] for a in audits if a.get("csv_loss_matches") is False],
                  "hash_mismatches": [a["run"] for a in audits if a.get("history_hash_matches") is False],
                  "best_epoch_components": components,
                  "top4_epoch50": {r["Name"].rsplit("-", 1)[1]: min(e["validation"]["loss"] for e in histories[r["Name"].rsplit("-", 1)[1]] if e["epoch"] <= 50) for r in ranked[:4]},
                  "summary": str(DEST / "summary.json")}, indent=2))
