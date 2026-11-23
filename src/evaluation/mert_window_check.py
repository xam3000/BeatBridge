"""Score the frozen P08 validation panels after cutting each window before MERT."""

import argparse
from collections import defaultdict
from pathlib import Path

import numpy as np
import torch

from src.evaluation.p10_validation import control, panel_scores
from src.features.p07_extract import prepare_audio
from src.features.p07_mert import FrozenMert
from src.features.p08_pairs import OUTPUT, location, parse_location, rng_for
from src.features.p08_windows import P07, STRUCTURE_COLUMNS, checked, index_track, read_json
from src.ml.p08_contrastive import PairWindows
from src.ml.p09_train import evaluate, save_json
from src.ml.p09_windows import WindowBank
from src.ranking.continuation import MODEL_DIR, P09_AUDIT, SELECTION, encoder_runtime, load_head


def isolated_mean(encoder, audio, bars):
    """Keep P09's equal bar weights. No samples outside this window reach MERT."""
    if len(bars) != 4 or np.any(bars[:-1, -1] != bars[1:, 0]):
        raise ValueError("Expected four contiguous bars")
    left, right = int(bars[0, 0]), int(bars[-1, -1])
    if not 0 <= left < right <= len(audio):
        raise ValueError("Window outside recording")
    values, _ = encoder.encode(audio[left:right], bars - left)
    return values.mean(axis=0, dtype=np.float32)


def same_section_rows(data, manifest):
    columns = [manifest["classical_columns"].index(key) for key in STRUCTURE_COLUMNS]
    by_track = defaultdict(list)
    for row in data.rows:
        by_track[parse_location(row["query_id"])[0]].append(row)
    controls = []
    for sha, rows in by_track.items():
        track = index_track(data.root, data.views[sha, "original"], columns, data.k,
                            data.manifest["length_bars"])
        for row in rows:
            _, cue = parse_location(row["query_id"])
            _, pos = parse_location(row["positive"])
            choices = [t for t in track.targets if track.sections[t] == track.sections[pos]
                       and max(cue - data.k - (t + data.k), t - (pos + data.k)) > 16]
            if choices:
                rng = rng_for("same-section-control-v1", row["query_id"])
                candidates = [row["positive"], location(sha, rng.choice(choices))]
                rng.shuffle(candidates)
                controls.append(dict(row, candidates=candidates))
    return controls


def run(destination):
    destination.mkdir(parents=True, exist_ok=False)
    runtime = encoder_runtime()
    encoder = FrozenMert(MODEL_DIR, runtime["device"])
    selection = read_json(SELECTION)
    run_dir = Path(selection["run"])
    audit = read_json(checked(P09_AUDIT, selection["p09_audit_sha256"]))
    checked(run_dir / "config.json", selection["config_sha256"])
    data = PairWindows(OUTPUT, P07, "validation", "mert", cache_tracks=1)
    controls = same_section_rows(data, read_json(P07 / "manifest.json"))
    # Include the extra controls in the same per-recording encoder pass.
    all_rows = data.rows + controls
    starts_by_sha = defaultdict(set)
    for row in all_rows:
        sha, cue = parse_location(row["query_id"])
        starts_by_sha[sha].add(cue - data.k)
        for key in row["candidates"]:
            sha, start = parse_location(key)
            starts_by_sha[sha].add(start)
    features = {}
    for i, (sha, starts) in enumerate(sorted(starts_by_sha.items()), 1):
        audio, _, _, bars = prepare_audio(data.views[sha, "original"])
        features[sha] = {s: isolated_mean(encoder, audio, bars[s:s + data.k]) for s in sorted(starts)}
        print(f"{i}/{len(starts_by_sha)}: {len(starts)} windows", flush=True)
    del encoder

    def isolated(sha, variant, starts):
        return np.stack([features[sha][s] for s in starts])

    results = []
    for family in ("mert", "classical"):
        family_data = data if family == "mert" else PairWindows(OUTPUT, P07, "validation", family, cache_tracks=1)
        for encoding in (("historical", "isolated") if family == "mert" else ("local_classical",)):
            loader = isolated if encoding == "isolated" else None
            banks = [WindowBank(family_data, rows, "cpu", window_means=loader) for rows in (data.rows, controls)]
            for row in audit["rows"]:
                if (row["family"] != family or row["level"] == 1
                        or (family == "classical" and row["level"] == 0)):
                    continue
                condition = f'{family}_s{row["level"]}_{row["seed"] or "deterministic"}'
                model = load_head(row, run_dir, selection["config_sha256"])
                metrics, _ = evaluate(model, banks[0])
                if encoding != "isolated" and not np.isclose(metrics["recall1"], row["recall1"], atol=1e-5):
                    raise ValueError(f"Historical replay differs for {condition}")
                scores = panel_scores(model, banks[1])
                i = np.arange(len(controls))
                positive = banks[1].truth
                success = control(scores[i, positive], scores[i, 1-positive], [r["group"] for r in controls])
                results.append(dict(condition=condition, encoding=encoding, **metrics,
                                    same_section=success,
                                    checkpoint_sha256=row["checkpoint_sha256"]))
            del banks
    report = dict(format_version=2, validation_sha256=data.manifest["files"]["validation.jsonl"],
                  p07_manifest_sha256=data.manifest["p07_manifest_sha256"],
                  config_sha256=selection["config_sha256"], model_revision=selection["representation"]["revision"],
                  runtime=runtime, queries=len(data.rows), recordings=len(features),
                  windows=sum(map(len, features.values())), same_section_queries=len(controls),
                  same_section_recordings=len({parse_location(r["query_id"])[0] for r in controls}),
                  same_section_groups=len({r["group"] for r in controls}),
                  results=results)
    save_json(destination / "comparison.json", report)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    torch.set_num_threads(1)
    print(run(args.output))
