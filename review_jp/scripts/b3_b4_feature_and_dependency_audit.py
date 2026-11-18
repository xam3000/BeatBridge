"""B3 Feature-Audit und B4 Abhängigkeits-Audit (nur train/validation).

B3: pro Kanal Mittelwert, Std, Anteil exakter Nullen, Wertebereich, und zwei
    Zusatzgrößen, die "tot" genauer fassen als die Gesamtvarianz:
      * between_std: Std über Beispiele der pro-Beispiel-Zeitmittel
      * step_std:    mittlere Std über Beispiele an fester Zeitposition
    Ein Kanal, der an jeder Zeitposition für alle Beispiele denselben Wert hat
    (step_std == 0), trägt keine Information über die Musik, auch wenn er über
    die Zeit variiert (z. B. transition_position).
B4: eindeutige Tracks/Paare, Beispiele pro Track, gerichtete/ungerichtete
    Paare, Umkehrpaare, Cues pro Paar.

Start: review_jp/.venv/bin/python review_jp/scripts/b3_b4_feature_and_dependency_audit.py
"""

from __future__ import annotations

from collections import Counter, defaultdict

import numpy as np

from common import TOP3, TOP10, dump_json, load_metadata, load_split
from src.features.contract import FEATURE_DEFINITIONS, GLOBAL_FEATURE_DEFINITIONS

DATASETS = {"top3_20260731": TOP3, "top10_20260805": TOP10}


def channel_stats(array: np.ndarray, definitions) -> list[dict]:
    """array: (N, T, F) für Sequenzkanäle oder (N, F) für globale Kanäle."""
    rows = []
    for index, definition in enumerate(definitions):
        values = array[..., index].astype(np.float64)
        row = {
            "index": index,
            "name": definition.name,
            "group": definition.group,
            "declared_range": [definition.minimum, definition.maximum],
            "mean": float(values.mean()),
            "std": float(values.std()),
            "min": float(values.min()),
            "max": float(values.max()),
            "zero_fraction": float(np.mean(values == 0.0)),
            "unique_values": int(np.unique(np.round(values, 6)).size),
        }
        if values.ndim == 2:  # (N, T)
            row["between_std"] = float(values.mean(axis=1).std())
            row["step_std"] = float(values.std(axis=0).mean())
        else:
            row["between_std"] = row["std"]
            row["step_std"] = row["std"]
        span = definition.maximum - definition.minimum
        row["step_std_over_range"] = row["step_std"] / span
        if row["step_std"] < 1e-7:
            row["verdict"] = "tot (für alle Beispiele identisch)"
        elif row["step_std_over_range"] < 0.01:
            row["verdict"] = "praktisch tot (<1 % des Wertebereichs)"
        elif row["step_std_over_range"] < 0.03:
            row["verdict"] = "schwach (<3 % des Wertebereichs)"
        else:
            row["verdict"] = "variiert"
        rows.append(row)
    return rows


def dependency_stats(metadata: dict, split: str) -> dict:
    rows = [row for row in metadata.values() if row["split"] == split]
    per_track = Counter()
    directed = Counter()
    for row in rows:
        source = row["source_track"]["sha256"]
        target = row["target_track"]["sha256"]
        per_track[source] += 1
        per_track[target] += 1
        directed[(source, target)] += 1
    undirected = defaultdict(int)
    for (source, target), count in directed.items():
        undirected[tuple(sorted((source, target)))] += count
    reversed_pairs = sum(1 for (s, t) in directed if (t, s) in directed) // 2
    counts = np.asarray(sorted(per_track.values()))
    cues = np.asarray(sorted(directed.values()))
    source_cues = Counter(
        (row["source_track"]["sha256"], row["source_cutpoint"]["sample"]) for row in rows
    )
    target_cues = Counter(
        (row["target_track"]["sha256"], row["target_cutpoint"]["sample"]) for row in rows
    )
    return {
        "examples": len(rows),
        "unique_tracks": len(per_track),
        "unique_directed_pairs": len(directed),
        "unique_undirected_pairs": len(undirected),
        "undirected_pairs_present_in_both_directions": reversed_pairs,
        "examples_per_track_median": float(np.median(counts)),
        "examples_per_track_max": int(counts.max()),
        "examples_per_track_min": int(counts.min()),
        "cues_per_directed_pair_median": float(np.median(cues)),
        "cues_per_directed_pair_max": int(cues.max()),
        "unique_source_cues": len(source_cues),
        "unique_target_cues": len(target_cues),
        "max_reuse_of_one_source_cue": max(source_cues.values()),
        "max_reuse_of_one_target_cue": max(target_cues.values()),
        "candidate_rank_max": max(int(row["candidate_rank"]) for row in rows),
    }


def main():
    report = {}
    for name, directory in DATASETS.items():
        train = load_split(directory, "train")
        validation = load_split(directory, "validation")
        sequence = np.concatenate(
            (train["features_a"], train["features_b"],
             validation["features_a"], validation["features_b"]),
            axis=0,
        )
        global_features = np.concatenate(
            (train["global_features"], validation["global_features"]), axis=0
        )
        metadata = load_metadata(directory)
        train_tracks = {
            h for row in metadata.values() if row["split"] == "train"
            for h in (row["source_track"]["sha256"], row["target_track"]["sha256"])
        }
        validation_tracks = {
            h for row in metadata.values() if row["split"] == "validation"
            for h in (row["source_track"]["sha256"], row["target_track"]["sha256"])
        }
        report[name] = {
            "windows_in_audit": int(sequence.shape[0]),
            "sequence_channels": channel_stats(sequence, FEATURE_DEFINITIONS),
            "global_channels": channel_stats(global_features, GLOBAL_FEATURE_DEFINITIONS),
            "dependency": {
                "train": dependency_stats(metadata, "train"),
                "validation": dependency_stats(metadata, "validation"),
                "tracks_in_train_and_validation": len(train_tracks & validation_tracks),
            },
        }

        print(f"\n===== {name}: {sequence.shape[0]} Fenster (A+B, train+validation) =====")
        print(f"{'idx':>3} {'Kanal':28} {'mean':>8} {'std':>8} {'step_std':>9} "
              f"{'zero%':>6}  Urteil")
        for row in report[name]["sequence_channels"]:
            print(f"{row['index']:>3} {row['name']:28} {row['mean']:8.4f} {row['std']:8.4f} "
                  f"{row['step_std']:9.5f} {100 * row['zero_fraction']:6.1f}  {row['verdict']}")
        print("--- global ---")
        for row in report[name]["global_channels"]:
            print(f"{row['index']:>3} {row['name']:28} {row['mean']:8.4f} {row['std']:8.4f} "
                  f"{row['step_std']:9.5f} {100 * row['zero_fraction']:6.1f}  {row['verdict']}")
        for split in ("train", "validation"):
            print(split, report[name]["dependency"][split])
        print("Tracks in train UND validation:",
              report[name]["dependency"]["tracks_in_train_and_validation"])
    path = dump_json("b3_b4_feature_and_dependency_audit.json", report)
    print("\ngeschrieben:", path)


if __name__ == "__main__":
    main()
