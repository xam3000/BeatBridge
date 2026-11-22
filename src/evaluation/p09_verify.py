"""Reconcile the full P09 run against the sealed rows, histories and real weights."""

import argparse
import csv
import hashlib
import math
from collections import defaultdict
from pathlib import Path

import numpy as np
import torch

from src.features.p07_mert import file_sha256
from src.features.p08_pairs import MODEL_SEEDS, OUTPUT
from src.features.p08_windows import P07, checked, read_json
from src.ml.p08_contrastive import PairWindows, VERIFIED_RELEASE, batch_order
from src.ml.p09_metric import ContinuationMetric
from src.ml.p09_train import save_json


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read_csv(path):
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def verify(run, dataset, p07):
    torch.set_num_threads(1)
    config = read_json(run / "config.json")
    audit = read_json(VERIFIED_RELEASE)
    require(not config["smoke"] and config["dataset_sha256"] == audit["manifest_sha256"], "Wrong run")
    release = read_json(checked(dataset / "manifest.json", config["dataset_sha256"]))
    for key in ("epochs", "model_seeds", "batch_size", "scaler_id", "p07_manifest_sha256",
                "temperature", "tau_plus", "freeze_commit"):
        require(config[key] == release[key], f"Wrong {key}")
    require((config["epochs"], config["batch_size"], config["lr"], config["weight_decay"]) ==
            (30, 32, .001, .0001), "Wrong budget")
    n_train = audit["splits"]["train"]["queries"]
    order_hashes = {}
    for seed in MODEL_SEEDS:
        for epoch in range(config["epochs"]):
            batches = batch_order(range(n_train), seed, epoch, config["batch_size"])
            order = np.asarray([index for batch in batches for index in batch], dtype="<i8")
            order_hashes[seed, epoch] = hashlib.sha256(order.tobytes()).hexdigest()
    rows = []
    config_sha = file_sha256(run / "config.json")
    for family in ("classical", "mert"):
        validation = PairWindows(dataset, p07, "validation", family)
        n_val = len(validation.rows)
        # Spaced, fixed indices chosen without using scores; replay raw four-bar panels on CPU.
        probes = np.linspace(0, n_val - 1, 11, dtype=int)
        panels = [validation.retrieval_item(i) for i in probes]
        q = torch.from_numpy(np.stack([a for a, _, _ in panels])).mean(1)
        c = torch.from_numpy(np.stack([b for _, b, _ in panels])).mean(2)
        truth = torch.tensor([target for _, _, target in panels])
        query_ids = [r["query_id"] for r in validation.rows]
        for level in range(3):
            for seed in (MODEL_SEEDS if level else (None,)):
                base = run / f"{family}_s{level}_{seed or 'deterministic'}"
                result = read_json(base / "result.json")
                model = ContinuationMetric(family, level)
                require((result["family"], result["level"], result["seed"], result["parameters"]) ==
                        (family, level, seed, sum(p.numel() for p in model.parameters())), "Wrong head")
                extra = {}
                if level:
                    history = read_json(base / "history.json")
                    require(len(history) == result["epochs"] == config["epochs"], "Missing epoch")
                    for epoch, h in enumerate(history):
                        require(h["order_sha256"] == order_hashes[seed, epoch] and h["queries"] == n_train
                                and h["steps"] == (epoch+1)*math.ceil(n_train/config["batch_size"])
                                and h["epoch"] == epoch+1 and math.isfinite(h["train_dcl"]), "Wrong history")
                    best = max(history, key=lambda h: h["recall1"])
                    require(result["best_epoch"] == best["epoch"] and result["steps"] == history[-1]["steps"]
                            and all(best[k] == result[k] for k in ("recall1", "mrr")), "Wrong selection")
                    path = checked(run / result["checkpoint"], result["checkpoint_sha256"])
                    ckpt = torch.load(path, map_location="cpu", weights_only=True)
                    require(ckpt["config_sha256"] == config_sha and ckpt["epoch"] == best["epoch"] and
                            (ckpt["seed"], ckpt["level"], ckpt["family"]) == (seed, level, family),
                            "Wrong checkpoint")
                    model.load_state_dict(ckpt["state_dict"], strict=True)
                    extra["history_sha256"] = file_sha256(base / "history.json")
                    if model.layer_logits is not None:
                        extra["mert_layer_weights"] = model.layer_logits.detach().softmax(0).tolist()
                else:
                    require(result["steps"] == result["epochs"] == 0 and result["checkpoint"] is None,
                            "Invalid deterministic baseline")
                ranked = read_csv(base / "validation_ranks.csv")
                require([r["query_id"] for r in ranked] == query_ids, "Validation panel mismatch")
                ranks = np.array([int(r["rank"]) for r in ranked])
                require(np.all((ranks >= 1) & (ranks <= 9)), "Invalid rank")
                by_recording = defaultdict(list)
                for qid, rank in zip(query_ids, ranks, strict=True):
                    by_recording[qid.split(":")[0]].append(rank)
                for key in ("recall1", "mrr"):
                    values = [np.asarray(v) for v in by_recording.values()]
                    metric = np.mean([np.mean(v == 1 if key == "recall1" else 1/v) for v in values])
                    require(abs(metric-result[key]) < 1e-12, f"Macro {key} differs")
                with torch.no_grad():
                    scores = model(q, c)
                ordering = scores.argsort(descending=True, stable=True)
                replay = (ordering == truth[:, None]).long().argmax(1).numpy()+1
                require(np.array_equal(replay, ranks[probes]), f"Raw-window CPU replay differs in {base}")
                rows.append({**result, **extra, "ranks_sha256": file_sha256(base / "validation_ranks.csv")})
    matrix = read_csv(run / "matrix.csv")
    require(len(matrix) == len(rows) == 14, "Incomplete matrix")
    for line, record in zip(matrix, rows, strict=True):
        require(all(s == ("" if record[k] is None else str(record[k])) for k, s in line.items()),
                "Matrix differs from run records")
    return dict(format_version=1, result="passed", run=run.as_posix(), config_sha256=config_sha,
                matrix_sha256=file_sha256(run / "matrix.csv"), train_queries=n_train,
                validation_queries=n_val, validation_recordings=len(by_recording),
                validation_groups=len({r["group"] for r in validation.rows}),
                raw_cpu_probe_indices=probes.tolist(), rows=rows)


def plot_histories(run, rows, output):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D

    fig, axes = plt.subplots(2, 2, figsize=(10, 6.4), sharex=True, sharey="col", layout="constrained")
    colors = {1: "#176080", 2: "#a04419"}
    styles = dict(zip(MODEL_SEEDS, ("-", "--", ":"), strict=True))
    for i, (family, title) in enumerate((("classical", "Klassisch"), ("mert", "MERT"))):
        loss_ax, recall_ax = axes[i]
        for row in (r for r in rows if r["family"] == family):
            if row["level"] == 0:
                recall_ax.axhline(100*row["recall1"], color="#6a7073", lw=1)
                continue
            history = read_json((run / row["checkpoint"]).with_name("history.json"))
            epochs = [h["epoch"] for h in history]
            style = dict(color=colors[row["level"]], linestyle=styles[row["seed"]], lw=1.4)
            loss_ax.plot(epochs, [h["train_dcl"] for h in history], **style)
            recall_ax.plot(epochs, [100*h["recall1"] for h in history], **style)
            recall_ax.scatter(row["best_epoch"], 100*row["recall1"], color=style["color"], s=22)
        loss_ax.set_ylabel(f"{title}\nTrainingsverlust (DCL)")
        recall_ax.set_ylabel("Validation-Recall@1 (%)")
        for ax in axes[i]:
            ax.set_xlim(1, 30)
            ax.set_xticks([1, 5, 10, 15, 20, 25, 30])
            ax.spines[["top", "right"]].set_visible(False)
            ax.grid(axis="y", alpha=.2)
            if i == 1:
                ax.set_xlabel("Epoche")
    handles = [Line2D([], [], color=color, label=f"Stufe {level}") for level, color in colors.items()]
    handles += [Line2D([], [], color="#333333", ls=ls, label=str(s)) for s, ls in styles.items()]
    handles += [Line2D([], [], color="#6a7073", label="Kosinus"),
                Line2D([], [], color="#333333", marker="o", ls="", label="Bestepoche")]
    fig.legend(handles=handles, loc="outside upper center", ncol=7, frameon=False, fontsize=9)
    fig.savefig(output, dpi=190, facecolor="white")
    plt.close(fig)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, default=OUTPUT)
    parser.add_argument("--p07", type=Path, default=P07)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--figure", type=Path)
    args = parser.parse_args()
    if args.receipt.exists():
        raise FileExistsError(args.receipt)
    if args.figure and args.figure.exists():
        raise FileExistsError(args.figure)
    receipt = verify(args.run, args.dataset, args.p07)
    if args.figure:
        plot_histories(args.run, receipt["rows"], args.figure)
    save_json(args.receipt, receipt)
    print(f"Verified {len(receipt['rows'])} conditions, {receipt['validation_queries']} ranks each.")
