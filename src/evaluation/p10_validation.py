"""Replay fixed validation panels, then select the study head using the frozen P01 rules."""

import argparse
import csv
import os
from pathlib import Path

import numpy as np
import torch

from src.evaluation.comparison import write_json
from src.features.p07_mert import file_sha256, model_identity
from src.features.p08_pairs import MODEL_SEEDS, OUTPUT, publish_dataset
from src.features.p08_windows import P07, checked, read_json
from src.ml.p08_contrastive import PairWindows
from src.ml.p09_windows import WindowBank
from src.ranking.continuation import METHOD, P09_AUDIT, load_head


ROOT = Path("output/review_jp_20261118/p10_ranking/run01")


def write_csv(path, rows):
    with path.open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0])
        writer.writeheader()
        writer.writerows(rows)


def macro(values, labels):
    _, index = np.unique(labels, return_inverse=True)
    return float(np.mean(np.bincount(index, weights=values) / np.bincount(index)))


def control(positive, other, groups):
    if not len(positive):
        return None
    return macro((positive > other).astype(float) + .5 * (positive == other), groups)


def decision(rows):
    stages = []
    for level in (1, 2):
        seeds = sorted((r for r in rows if (r["family"], r["level"]) == ("mert", level)),
                       key=lambda r: r["seed"])
        if [r["seed"] for r in seeds] != list(MODEL_SEEDS):
            raise ValueError("Incomplete MERT seed series")
        stage = dict(level=level, mean_recall1=float(np.mean([r["recall1"] for r in seeds])))
        eligible = True
        for name in ("same", "intro_drop"):
            rates = [r[name] for r in seeds]
            mean = None if None in rates else float(np.mean(rates))
            stage["mean_" + name] = mean
            stage["study_seed_" + name] = rates[0]
            eligible &= (min(r[name + "_groups"] for r in seeds) >= 5 and mean is not None
                         and mean > .5 and rates[0] > .5)
        stages.append(dict(**stage, eligible=eligible))
    passed = [s for s in stages if s["eligible"]]
    best = max(passed, key=lambda s: (s["mean_recall1"], -s["level"])) if passed else None
    return stages, best


@torch.inference_mode()
def panel_scores(head, bank):
    def encode(source):
        return torch.cat([head.encode(c, source=source) for c in bank.values.split(256)])
    q, t = encode(True), encode(False)
    ids = torch.as_tensor(bank.panels, device=q.device)
    scores = torch.cat([(q[p[:, :1]] * t[p[:, 1:]]).sum(-1) for p in ids.split(256)]).cpu().numpy()
    if not np.isfinite(scores).all():
        raise ValueError("Nonfinite validation scores")
    return scores


def evaluate(out, device):
    audit = read_json(P09_AUDIT)
    run = Path(audit["run"])
    config = read_json(checked(run / "config.json", audit["config_sha256"]))
    checked(run / "matrix.csv", audit["matrix_sha256"])
    results = []
    for family in ("classical", "mert"):
        data = PairWindows(OUTPUT, P07, "validation", family, cache_tracks=1)
        rows = data.rows
        groups = np.array([r["group"] for r in rows])
        has_intro = np.array([r["intro_drop_control"] is not None for r in rows])
        # Append one diagnostic target after the nine sealed candidates. For
        # missing controls the unused slot duplicates the positive (masked below).
        expanded = [dict(r, candidates=[*r["candidates"], (r["intro_drop_control"] or
                         {"candidate": r["positive"]})["candidate"]]) for r in rows]
        bank = WindowBank(data, expanded, device)
        same = [r["candidates"].index(r["same_control"]) for r in rows]
        n = np.arange(len(rows))
        for row in (r for r in audit["rows"] if r["family"] == family):
            head = load_head(row, run, audit["config_sha256"]).to(device)
            scores = panel_scores(head, bank)
            ranks = (np.argsort(-scores[:, :9], axis=1, kind="stable") ==
                     bank.truth[:, None]).argmax(axis=1) + 1
            pos, neg, contrast = scores[n, bank.truth], scores[n, same], scores[:, 9]
            recall, mrr = macro(ranks == 1, bank.tracks), macro(1 / ranks, bank.tracks)
            label = f'{family}_s{row["level"]}_{row["seed"] or "deterministic"}'
            with checked(run / label / "validation_ranks.csv", row["ranks_sha256"]).open() as f:
                reference = [(r["query_id"], int(r["rank"])) for r in csv.DictReader(f)]
            if (reference != [(r["query_id"], rank) for r, rank in zip(rows, ranks, strict=True)]
                    or not np.allclose([recall, mrr], [row["recall1"], row["mrr"]], atol=1e-12, rtol=0)):
                raise ValueError(f"Sealed P09 retrieval ranks differ for {label}")
            fields = ("family", "level", "seed", "parameters", "best_epoch", "epochs", "checkpoint",
                      "checkpoint_sha256")
            result = {k: row[k] for k in fields}
            result.update(recall1=recall, mrr=mrr, same=control(pos, neg, groups),
                          intro_drop=control(pos[has_intro], contrast[has_intro], groups[has_intro]),
                          queries=len(rows), recordings=len(set(bank.tracks)), same_groups=len(set(groups)),
                          intro_drop_queries=int(has_intro.sum()), intro_drop_groups=len(set(groups[has_intro])))
            results.append(result)
            details = [dict(query_id=r["query_id"], group=r["group"], positive=r["positive"],
                            rank=int(ranks[i]), positive_score=float(pos[i]), same=r["same_control"],
                            same_score=float(neg[i]), positive_section=r["positive_section"],
                            intro_drop=None if not has_intro[i] else r["intro_drop_control"]["candidate"],
                            intro_drop_score=float(contrast[i]) if has_intro[i] else None)
                       for i, r in enumerate(rows)]
            write_csv(out / (label + ".csv"), details)
            print(label, result["same"], result["intro_drop"], flush=True)
        del bank
    write_csv(out / "validation.csv", results)
    stages, best = decision(results)
    result = dict(format_version=1, stages=stages, run=run.as_posix(), config_sha256=audit["config_sha256"],
                  p09_audit_sha256=file_sha256(P09_AUDIT), p08_manifest_sha256=config["dataset_sha256"],
                  validation_sha256=config["split_sha256"]["validation"],
                  validation_table_sha256=file_sha256(out / "validation.csv"))
    if best is None:
        result.update(status="requires_one_train_negative_refinement")
    else:
        selected = next(r for r in results if (r["family"], r["level"], r["seed"]) ==
                        ("mert", best["level"], MODEL_SEEDS[0]))
        result.update(status="selected", selected=selected, ranking_method=METHOD,
                      representation=model_identity(), refinements=0)
    write_json(out / "selection.json", result)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "validation")
    parser.add_argument("--device", default="cuda:0")
    args = parser.parse_args()
    os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
    torch.use_deterministic_algorithms(True)
    torch.set_num_threads(1)
    with publish_dataset(args.output) as stage:
        evaluate(stage, args.device)
