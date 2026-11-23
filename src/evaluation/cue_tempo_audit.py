"""Compare historical BPM-field span errors with the cue regression, using grids only."""

import argparse
from collections import Counter
import csv
from functools import lru_cache
import json
from pathlib import Path

import numpy as np

from src.tempo.cue_alignment import CueAlignmentError, measure_cue_alignment


DATASETS = Path("output/datasets")
P11 = Path("output/review_jp_20261118/p11_hoerversuch/run01")
LISTENING = Path("output/four_models_shared_20pairs_validation_20261105_renderfix")


@lru_cache(maxsize=None)
def cached_grid(directory, sha):
    directory = Path(directory)
    meta = json.loads((directory / "manifest.json").read_bytes())
    if meta["source_sha256"] != sha or meta["sample_rate"] != 44100:
        raise ValueError("Historical feature cache identity or rate mismatch")
    with np.load(directory / meta["data_file"]) as data:
        # Every even half-beat boundary is an observed beat.
        return data["bin_boundaries"][::2]


def measure(row):
    grids, indices = [], []
    for role in ("source", "target"):
        grid = cached_grid(row[role + "_feature_cache"]["directory"], row[role + "_track"]["sha256"])
        sample = row["aligned_" + role + "_cue_sample"]
        index = int(np.argmin(np.abs(grid - sample)))
        if abs(int(grid[index]) - sample) > 2:
            raise ValueError("Historical cue off its cached beat")
        grids.append(grid)
        indices.append(index)
    beats = row["transition_length_bars"] * 4
    # B already includes the historical global BPM correction. A second linear
    # factor estimated on those coordinates is equivalent to fitting native B,
    # to within the single-sample quantization of the stored transformed marks.
    alignment = measure_cue_alignment(*grids, *indices, beats, 44100)
    a, b = grids
    s, t = indices
    before = abs((a[s + beats] - a[s]) - (b[t] - b[t - beats])) * 1000. / 44100
    try:
        alignment.require_valid()
        accepted = True
    except CueAlignmentError:
        accepted = False
    return before, alignment.span_error_ms, accepted


def summarize(rows):
    measures, reasons = [], Counter()
    for row in rows:
        try:
            measures.append(measure(row))
        except (OSError, ValueError) as error:
            reasons[f"{type(error).__name__}: {error}"] += 1
    result = dict(total=len(rows), measured=len(measures), missing=dict(reasons))
    if measures:
        before, after, accepted = np.array(measures).T
        result["passed"] = int(accepted.sum())
        for name, arr in (("bpm_field", before), ("regression_all", after),
                          ("regression_accepted", after[accepted.astype(bool)])):
            if len(arr):
                result[name] = dict(over20=int((arr > 20).sum()), median_ms=float(np.median(arr)),
                                    p95_ms=float(np.quantile(arr, .95)), max_ms=float(arr.max()))
    return result


def panel_rows(panel_path):
    panel = json.loads(panel_path.read_bytes())
    manifest = json.loads(Path(panel["pair_manifest"]).read_bytes())
    selected = set(panel["selectors"].values())
    for row in manifest["candidate_generation"]["candidates"]:
        if row["candidate_id"] in selected:
            for role in ("source", "target"):
                row[role + "_feature_cache"] = {"directory": panel[role + "_feature_directory"]}
                scale = row["target_bpm"] / row["source_bpm"] if role == "target" else 1
                row["aligned_" + role + "_cue_sample"] = round(row[role + "_cutpoint"]["sample"] * scale)
            yield row


def historical_pool_counts(panel_path):
    """Count geometric survivors in an already archived pool without choosing any cue."""
    panel = json.loads(panel_path.read_bytes())
    selection = json.loads(Path(panel["pair_manifest"]).read_bytes())
    reference = selection["candidate_generation"]["candidates"][0]
    grids = [cached_grid(panel[role + "_feature_directory"], reference[role + "_track"]["sha256"])
             for role in ("source", "target")]
    scale = reference["target_bpm"] / reference["source_bpm"]
    eligible = total = 0
    with (panel_path.parent / "pool.csv").open(encoding="utf8") as stream:
        for row in csv.DictReader(stream):
            s, t = int(row["source_beat"]), int(row["target_beat"])
            if (abs(grids[0][s] - int(row["source_sample"])) > 2
                    or abs(grids[1][t] - round(int(row["target_sample"]) * scale)) > 2):
                raise ValueError("Archived candidate and feature grid differ")
            total += 1
            try:
                measure_cue_alignment(*grids, s, t, 16, 44100).require_valid()
            except CueAlignmentError:
                continue
            eligible += 1
    return dict(pair=panel["pair_id"], historical_candidates=total, gate_passed=eligible)


def audit():
    result = {}
    heard_ids = {r["candidate_id"] for r in json.loads((LISTENING / "answer_key.json").read_bytes())["pairs"]}
    for label, name in (("D1", "feature_protocol_v1_top3_4bar_track_split_20260731"),
                        ("D2", "feature_protocol_v1_extended_bpm145_165_top10_4bar_split_20260805"),
                        ("D3", "variable_v2_strict_20260820_selected_roformer_run01"),
                        ("D4", "prive_scantraxx_extension_variable_v2_fp2_roformer_2-4-6-8bar_top1x3_split20260923_run02_local_four_four")):
        root = DATASETS / name
        for split in ("train", "validation"):
            paths = ([root / "examples.jsonl"] if (root / "examples.jsonl").is_file()
                     else sorted((root / "metadata").glob(f"*/{split}.jsonl")))
            if not paths:
                raise FileNotFoundError(root)
            rows = [r for p in paths for line in p.read_bytes().splitlines()
                    if (r := json.loads(line))["split"] == split]
            result[f"{label}_{split}"] = summarize(rows)
            if label == "D2" and split == "validation":
                hearing = [r for r in rows if r["candidate_id"] in heard_ids]
                if len(hearing) != len(heard_ids):
                    raise ValueError("Missing November listening cue in D2")
                result["november_listening"] = summarize(hearing)
    result["P04_development"] = summarize(list(panel_rows(Path("docs/masterarbeit/review_jp_20261118/p04/dev_panel.json"))))
    panels = sorted(P11.glob("P*/panel.json"))
    result["P11_run01"] = summarize([row for p in panels for row in panel_rows(p)])
    result["P11_run01"]["pool_geometry"] = [historical_pool_counts(p) for p in panels]
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    report = audit()
    args.destination.parent.mkdir(parents=True, exist_ok=True)
    with args.destination.open("x", encoding="utf8") as stream:
        json.dump(report, stream, indent=2, allow_nan=False)
    print({k: (v["measured"], v["total"], v.get("passed")) for k,v in report.items()})
