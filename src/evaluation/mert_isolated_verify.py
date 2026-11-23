"""Replay the selected isolated-window head and compare it to the development cue rule."""

import argparse
import csv
import os
from pathlib import Path

import numpy as np
import soundfile as sf
import torch
from scipy.stats import spearmanr
from threadpoolctl import threadpool_limits

from src.evaluation.p10_pairs import RATE, development_views, pair_generation
from src.evaluation.p10_validation import decision, write_csv
from src.features.p07_mert import file_sha256
from src.features.p08_pairs import OUTPUT, publish_dataset
from src.features.p08_windows import P07, checked, read_json
from src.ml.p08_contrastive import PairWindows
from src.ml.p09_train import evaluate, save_json
from src.ml.p09_windows import WindowBank
from src.ranking.continuation import (BarWindows, ISOLATED_METHOD, candidate_windows, load_head,
                                      rank_continuations, score_pair)
from src.ranking.feature_baseline import rank_candidates


def verify(selection_path, cache, output):
    selection = read_json(selection_path)
    if selection["status"] != "selected" or selection["ranking_method"] != ISOLATED_METHOD:
        raise ValueError("Expected a selected isolated-window head")
    row = selection["selected"]
    run = Path(selection["run"])
    config = read_json(checked(run / "config.json", selection["config_sha256"]))
    receipts = read_json(checked(run / "cache.json", config["cache_sha256"]))["validation"]
    data = PairWindows(OUTPUT, P07, "validation", "mert", cache_tracks=1)
    head = load_head(row, run, selection["config_sha256"])
    table = checked(run / "validation.csv", selection["validation_table_sha256"])
    with table.open(encoding="utf-8", newline="") as stream:
        trained = [r for r in csv.DictReader(stream) if r["seed"]]
    for r in trained:
        for name in ("level", "seed", "same_groups", "intro_drop_groups"):
            r[name] = int(r[name])
        for name in ("recall1", "same", "intro_drop"):
            r[name] = float(r[name]) if r[name] else None
    stages, best = decision(trained)
    if (config["input_encoding"] != ISOLATED_METHOD or stages != selection["stages"] or best is None
            or best["level"] != row["level"] or row["seed"] != config["model_seeds"][0]
            or config["split_sha256"]["validation"] != data.manifest["files"]["validation.jsonl"]):
        raise ValueError("Isolated head selection differs on replay")

    def cached(view):
        key = view["cache_id"]
        directory = cache / key
        receipt = read_json(checked(directory / "receipt.json", receipts[key]))
        if receipt["binding"]["view"] != key or receipt["binding"]["method"] != ISOLATED_METHOD:
            raise ValueError(f"Unbound window features: {key}")
        with np.load(checked(directory / "means.npz", receipt["sha256"])) as z:
            return z["starts"], z["means"]

    def window_means(sha, variant, rows):
        starts, values = cached(data.views[sha, variant])
        indexes = np.searchsorted(starts, rows)
        if np.any(indexes == len(starts)) or not np.array_equal(starts[indexes], rows):
            raise ValueError("Validation window missing")
        return values[indexes]

    bank = WindowBank(data, data.rows, config["device"], window_means=window_means)
    metrics, ranks = evaluate(head.to(config["device"]), bank)
    head.cpu()
    archived_ranks = (run / row["checkpoint"]).with_name("validation_ranks.csv")
    with archived_ranks.open(encoding="utf-8", newline="") as stream:
        archived = [(r["query_id"], int(r["rank"])) for r in csv.DictReader(stream)]
    if archived != [(r["query_id"], int(rank)) for r, rank in zip(data.rows, ranks, strict=True)]:
        raise ValueError("Validation ranks differ from the archived checkpoint replay")
    if any(row[name] != value for name, value in metrics.items()):
        raise ValueError("Validation metrics differ")
    del bank

    def cue_features(view, analysis):
        frames = analysis(view["path"]).beat_frames
        with np.load(checked((P07 / view["entry"]).with_name("bars.npz"), view["sha256_files"]["bars.npz"])) as z:
            beats, bounds = z["bar_start_beat_index"], z["bar_boundaries_24k"]
        starts, means = cached(view)
        dense = np.full((len(bounds), *means.shape[1:]), np.nan, dtype=np.float32)
        dense[starts] = means
        return BarWindows.from_bars(beats, bounds, dense, frames, analysis(view["path"]).grid_metadata.beat_grid_sha256,
                                    RATE / sf.info(view["path"]).samplerate)

    views = development_views()
    pairs = []
    scores = []
    for i, (a, b) in enumerate(zip(views[:-1:2], views[1::2], strict=True), 1):
        generated, analysis = pair_generation(a, b)
        windows = {view["sha256"]: cue_features(view, analysis) for view in (a, b)}
        cues, indices, _ = candidate_windows(generated.candidates, windows)
        if not cues:
            raise ValueError(f"No eligible candidates on development pair {i}")
        values = score_pair(head, indices, windows[a["sha256"]].bars, windows[b["sha256"]].bars, isolated=True)
        by_id = {c.candidate_id: float(v) for c, v in zip(cues, values, strict=True)}
        rule = rank_candidates(cues, target_sample_rate=RATE)
        rule_values = {s.candidate_id: s.total_score for s in rule.scores}
        if rule.failures or rule_values.keys() != by_id.keys():
            raise ValueError("Cue methods cover different candidates")
        ids = sorted(by_id)
        rho = spearmanr([by_id[k] for k in ids], [rule_values[k] for k in ids]).statistic
        top = min(ids, key=lambda k: (-by_id[k], k))
        pairs.append(dict(pair=i, source=a["sha256"], target=b["sha256"], cues=len(cues),
                          ssl_top=top, rule_top=rule.scores[0].candidate_id,
                          rho=float(rho) if np.isfinite(rho) else None))
        scores.extend(dict(pair=i, cue=k, ssl=by_id[k], rule=rule_values[k]) for k in ids)
        if i == 1:
            live = rank_continuations(generated.candidates, analysis, RATE, selection_path=selection_path)
            replay = {s.candidate_id: s.total_score for s in live.scores}
            if live.method != ISOLATED_METHOD or replay.keys() != by_id.keys() or live.scores[0].candidate_id != top:
                raise ValueError("Live and cached retrieval differ")
            live_error = max(abs(replay[k] - by_id[k]) for k in ids)
            if live_error > 1e-5:
                raise ValueError(f"Live score replay exceeded tolerance: {live_error}")
    write_csv(output / "candidate_scores.csv", scores)
    write_csv(output / "pairs.csv", pairs)
    result = dict(result="passed", selection_sha256=file_sha256(selection_path),
                  validation_ranks_sha256=file_sha256(archived_ranks),
                  ranks_replayed=len(ranks), **metrics, development_pairs=len(pairs), cues=len(scores),
                  agreements=sum(p["ssl_top"] == p["rule_top"] for p in pairs),
                  mean_rho=float(np.mean([p["rho"] for p in pairs if p["rho"] is not None])),
                  live_pair=1, live_candidates=pairs[0]["cues"], max_live_score_error=live_error,
                  pair_table_sha256=file_sha256(output / "pairs.csv"),
                  unpaired_group=views[-1]["recording_group_id"] if len(views) % 2 else None)
    save_json(output / "verified.json", result)
    print(result)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("selection", type=Path)
    parser.add_argument("cache", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    with publish_dataset(args.output) as stage, threadpool_limits(limits=1):
        verify(args.selection, args.cache, stage)
