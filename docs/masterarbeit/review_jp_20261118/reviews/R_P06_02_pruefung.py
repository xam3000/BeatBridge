"""Unabhängige Nachrechnung für den Review R_P06_02 (nur Lesezugriff auf P06-Rohtabellen)."""

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

BASE = Path(__file__).resolve().parents[1]
REPO = Path(__file__).resolve().parents[4]
P06 = BASE / "p06"
EXPOSURE = BASE / "p01" / "exposure_tracks.csv"


def rows(path):
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def find(parent, x):
    while parent[x] != x:
        parent[x] = parent[parent[x]]
        x = parent[x]
    return x


def group_of_track():
    mapping = {}
    for row in rows(EXPOSURE):
        if row["recording_group_id"]:
            mapping[row["sha256"]] = row["recording_group_id"]
    return mapping


def pair_table(profile, bars, seed, init):
    pairs = [r for r in rows(P06 / "pairs.csv")
             if r["profile"] == profile and r["bars"] == str(bars) and int(r["seed"]) == seed
             and r["model_initialization"] == init and r["condition"] == "swapped"]
    m_rows = [r for r in rows(P06 / "pairs.csv")
              if r["profile"] == profile and r["bars"] == str(bars) and int(r["seed"]) == seed
              and r["model_initialization"] == init and r["condition"] == "M"]
    assert [(r["source"], r["target"]) for r in pairs] == [(r["source"], r["target"]) for r in m_rows]
    return [(r["source"], r["target"]) for r in pairs], np.array([float(r["delta_vs_M"]) for r in pairs])


def components(edges, groups):
    parent = {}

    def add(x):
        parent.setdefault(x, x)

    for a, b in edges:
        add(a)
        add(b)
        parent[find(parent, a)] = find(parent, b)
    roots = defaultdict(list)
    for i, (a, _) in enumerate(edges):
        roots[find(parent, a)].append(i)
    return list(roots.values()), parent


def describe(label, edges_tracks, delta, groups):
    missing = sum(1 for pair in edges_tracks for t in pair if t not in groups)
    edges = [(groups.get(a, "?" + a), groups.get(b, "?" + b)) for a, b in edges_tracks]
    comps, _ = components(edges, groups)
    counts = Counter(g for pair in edges for g in pair)
    print(f"{label}: Kanten={len(edges)}, Gruppen={len(counts)}, Komponenten={len(comps)}, "
          f"größte Komponente={max(len(c) for c in comps)} Kanten, max. Wiederverwendung={max(counts.values())}, "
          f"fehlende Trackzuordnungen={missing}, Punktschätzer={delta.mean():.6f}")
    return edges, comps


def pair_bootstrap(delta):
    rng = np.random.default_rng(20261121)
    draws = rng.integers(len(delta), size=(10000, len(delta)))
    return np.quantile(delta[draws].mean(1), [0.025, 0.975])


def component_bootstrap(delta, comps):
    rng = np.random.default_rng(20261121)
    draws = rng.integers(len(comps), size=(10000, len(comps)))
    means = np.empty(10000)
    for n, draw in enumerate(draws):
        idx = [i for k in draw for i in comps[k]]
        means[n] = delta[idx].mean()
    return np.quantile(means, [0.025, 0.975])


def matrix_value(profile, bars, init, condition):
    for r in rows(P06 / "matrix.csv"):
        if (r["profile"] == profile and r["bars"] == str(bars) and r["model_initialization"] == init
                and r["condition"] == condition and int(r["seed"]) == 20260926):
            return float(r["loss"])
    raise KeyError((profile, bars, init, condition))


def shares():
    e = matrix_value("R3", 4, "equal_power_v1", "E")
    d = matrix_value("R3", 4, "equal_power_v1", "D")
    m = matrix_value("R3", 4, "equal_power_v1", "M")
    f = matrix_value("R3", 4, "equal_power_v1", "F")
    start = 1.938311
    print(f"R3 EP-v1: M-Anteil an E-D = {100 * (e - m) / (e - d):.2f} %, F-Anteil = {100 * (e - f) / (e - d):.2f} %")
    print(f"R3 EP-v1: F-Anteil an gedämpftem Start-D = {100 * (start - f) / (start - d):.2f} %")
    for bars in (2, 4, 6, 8):
        e = matrix_value("R4", bars, "legacy", "E")
        d = matrix_value("R4", bars, "legacy", "D")
        m = matrix_value("R4", bars, "legacy", "M")
        f = matrix_value("R4", bars, "legacy", "F")
        print(f"R4 {bars} Takte legacy: M-Anteil {100 * (e - m) / (e - d):.2f} %, F-Anteil {100 * (e - f) / (e - d):.2f} %")


def training():
    by_run = defaultdict(list)
    for r in rows(P06 / "training.csv"):
        by_run[(r["profile"], r["model_initialization"], r["seed"])].append(r)
    for key, epochs in sorted(by_run.items()):
        best = min(epochs, key=lambda r: float(r["validation_loss"]))
        selected = [r for r in epochs if r["selected"] == "True"]
        last = epochs[-1]
        near = [int(r["epoch"]) for r in epochs if float(r["validation_loss"]) <= float(best["validation_loss"]) + 0.0001]
        print(f"{key}: Epochen={len(epochs)}, Auswahl={[r['epoch'] for r in selected]}, "
              f"Minimum E{best['epoch']} ({float(best['validation_loss']):.6f}), letzte E{last['epoch']} "
              f"({float(last['validation_loss']):.6f}), Epochen innerhalb 0,0001 des Minimums={near}")


def leakage(label, files, groups):
    by_split = defaultdict(lambda: {"groups": set(), "tracks": set(), "unmapped": 0, "examples": 0})
    for split, path in files.items():
        with path.open(encoding="utf-8") as stream:
            for line in stream:
                ex = json.loads(line)
                if ex.get("split", split) != split:
                    continue
                by_split[split]["examples"] += 1
                for role in ("source_track", "target_track"):
                    sha = ex[role]["sha256"]
                    entry = by_split[split]
                    entry["tracks"].add(sha)
                    if sha in groups:
                        entry["groups"].add(groups[sha])
                    else:
                        entry["unmapped"] += 1
    train, val = by_split["train"], by_split["validation"]
    print(f"{label}: train Beispiele={train['examples']}, val Beispiele={val['examples']}, "
          f"Gruppen train/val={len(train['groups'])}/{len(val['groups'])}, "
          f"Schnittmenge Gruppen={len(train['groups'] & val['groups'])}, "
          f"Schnittmenge Tracks={len(train['tracks'] & val['tracks'])}, "
          f"nicht zugeordnete Trackreferenzen train/val={train['unmapped']}/{val['unmapped']}")


def main():
    groups = group_of_track()
    print(f"Trackzuordnungen aus exposure_tracks.csv: {len(groups)}")
    d2 = REPO / "output" / "datasets" / "feature_protocol_v1_extended_bpm145_165_top10_4bar_split_20260805" / "examples.jsonl"
    leakage("D2", {"train": d2, "validation": d2}, groups)
    d4 = REPO / "output" / "datasets" / "prive_scantraxx_extension_variable_v2_fp2_roformer_2-4-6-8bar_top1x3_split20260923_run02_local_four_four" / "metadata"
    for bars in (2, 4, 6, 8):
        files = {"train": d4 / f"{bars}bar" / "train.jsonl", "validation": d4 / f"{bars}bar" / "validation.jsonl"}
        leakage(f"D4 {bars} Takte", files, groups)
    shares()
    training()
    for profile, bars in [("R1", 4), ("R2", 4), ("R3", 4), ("R4", 2), ("R4", 4), ("R4", 6), ("R4", 8)]:
        init = "equal_power_v1" if profile == "R3" else "legacy"
        seed = 20260926
        edges_tracks, delta = pair_table(profile, bars, seed, init)
        edges, comps = describe(f"{profile} {bars} Takte {init}", edges_tracks, delta, groups)
        lo, hi = pair_bootstrap(delta)
        clo, chi = component_bootstrap(delta, comps)
        print(f"  S-M Paar-Bootstrap: {lo:.6f} bis {hi:.6f}")
        print(f"  S-M Komponenten-Bootstrap: {clo:.6f} bis {chi:.6f}")


if __name__ == "__main__":
    main()
