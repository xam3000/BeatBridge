"""Verify all historical P06 inputs before fitting controls or starting repetitions."""

import argparse
import csv
from collections import Counter
from pathlib import Path

import numpy as np
import torch

from src.evaluation.comparison import new_output, write_json
from src.evaluation.comparison_native import FAMILIES, RUNS, MODEL_RUNS, load_json, native_setup
from src.evaluation.ml_control_study import _file_sha256
from src.features.contract import FEATURE_DEFINITIONS, GLOBAL_FEATURE_DEFINITIONS


PLAN = Path("docs/masterarbeit/review_jp_20261118/p05/p06_configs.json")
GROUPS = Path("docs/masterarbeit/review_jp_20261118/p01/exposure_tracks.csv")


def historical(profile):
    return RUNS / MODEL_RUNS[FAMILIES[profile]]


def verify_run(run):
    manifest = load_json(run / "manifest.json")
    if manifest["status"] not in {"completed", "early_stopped"}:
        raise ValueError(f"Incomplete run: {run}")
    for file in manifest["files"].values():
        path = run / file["path"]
        if path.stat().st_size != file["bytes"] or _file_sha256(path) != file["sha256"]:
            raise ValueError(f"Invalid run artifact: {path}")
    return manifest


def audit_split(split, groups):
    pairs = Counter()
    manifests = {}
    for i in range(len(split)):
        item = split[i]  # native loader validates the waveform file and its manifest
        pairs[item["pair"]] += 1
        manifests[item["example_id"]] = item["geometry"]["cache_manifest_sha256"]
    tracks = sorted({h for pair in pairs for h in pair})
    data = split.data
    sequence = np.concatenate((data.features_a, data.features_b)).astype(np.float64)
    globals_ = data.global_features.astype(np.float64)
    step_std = sequence.std(axis=0).mean(axis=0)
    names = [d.name for d in FEATURE_DEFINITIONS]
    return dict(examples=len(split), pairs=len(pairs), tracks=tracks,
                groups=sorted({groups[h] for h in tracks}), manifests=manifests,
                cues_per_pair_range=[min(pairs.values()), max(pairs.values())],
                constant_at_each_step=[n for n, s in zip(names, step_std) if s < 1e-7],
                constant_globals=[d.name for d, s in zip(GLOBAL_FEATURE_DEFINITIONS, globals_.std(axis=0))
                                  if s < 1e-7],
                key_confidence={d.name: float(globals_[:, i].mean())
                                for i, d in enumerate(GLOBAL_FEATURE_DEFINITIONS)
                                if d.name.startswith("key_confidence_")})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    torch.set_num_threads(1)
    plan = load_json(PLAN)
    if _file_sha256(Path(plan["dataset"]) / "manifest.json") != plan["dataset_manifest_sha256"]:
        raise ValueError("D2 differs from frozen P05 plan")
    with GROUPS.open(encoding="utf-8-sig", newline="") as stream:
        groups = {r["sha256"]: r["recording_group_id"] for r in csv.DictReader(stream)}
    with new_output(args.output) as out:
        for profile in FAMILIES:
            run = historical(profile)
            manifest = verify_run(run)
            if profile in plan["profiles"] and manifest["run_id"] != plan["profiles"][profile]["reference_run_id"]:
                raise ValueError("Reference run differs from plan")
            for bars in ((2, 4, 6, 8) if profile == "R4" else (4,)):
                _, _, splits, protocol = native_setup(profile, bars, run, None, None, None)
                audit = {name: audit_split(split, groups) for name, split in splits.items()}
                for field in ("groups", "tracks"):
                    audit["overlap_" + field] = sorted(set(audit["train"][field]) & set(audit["validation"][field]))
                write_json(out / f"{profile}_{bars}.json", {**protocol, **audit, "run_files": manifest["files"]})
                print(profile, bars, {s: audit[s]["examples"] for s in splits}, flush=True)


if __name__ == "__main__":
    main()
