"""Paired source-group bootstrap of the frozen isolated MERT and classical two-tower ranks."""

import argparse
import csv
import json
from pathlib import Path

import numpy as np

from src.features.p07_mert import SAMPLE_RATE, FrozenMert, file_sha256


EVIDENCE = Path("docs/masterarbeit/review_jp_20261118/mert_fenster")
BOOTSTRAP_SEED = 20261125
N_DRAWS = 10_000


def csv_rows(path):
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def recording_counts():
    from src.features.p08_pairs import OUTPUT, parse_location
    from src.features.p08_windows import checked, read_json
    from src.ranking.continuation import P09_AUDIT

    verified = read_json(EVIDENCE / "verified.json")
    selection = read_json(checked(EVIDENCE / "selection.json", verified["selection_sha256"]))
    run = Path(selection["run"])
    config = read_json(checked(run / "config.json", selection["config_sha256"]))
    seeds = config["model_seeds"]
    level = selection["selected"]["level"]
    study_seed = selection["selected"]["seed"]
    panel_file = checked(OUTPUT / "validation.jsonl", selection["validation_sha256"])
    with panel_file.open(encoding="utf-8") as stream:
        panels = [json.loads(line) for line in stream]
    query_ids = [p["query_id"] for p in panels]
    if len(query_ids) != len(set(query_ids)):
        raise ValueError("Duplicate P08 query ID")
    tracks, indices, sizes = np.unique([parse_location(q)[0] for q in query_ids],
                                       return_inverse=True, return_counts=True)
    group_by_track = {}
    for i, p in zip(indices, panels, strict=True):
        if group_by_track.setdefault(i, p["group"]) != p["group"]:
            raise ValueError("A recording belongs to multiple source groups")
    group_ids, group_index = np.unique([group_by_track[i] for i in range(len(tracks))],
                                       return_inverse=True)
    table = csv_rows(checked(run / "validation.csv", selection["validation_table_sha256"]))
    classical = read_json(P09_AUDIT)
    classical_config = read_json(checked(Path(classical["run"]) / "config.json", classical["config_sha256"]))
    if classical_config["split_sha256"] != config["split_sha256"] or classical_config["model_seeds"] != seeds:
        raise ValueError("Different P08 splits or model seeds")
    counts = {}
    ranks_sha = {}
    for family, root, rows in (("mert", run, table), ("classical", Path(classical["run"]), classical["rows"])):
        hits = []
        for seed in seeds:
            row, = [r for r in rows if r["family"] == family and int(r["level"]) == level
                    and int(r["seed"]) == seed]
            rank_file = (root / row["checkpoint"]).with_name("validation_ranks.csv")
            digest = file_sha256(rank_file)
            if "ranks_sha256" in row:
                checked(rank_file, row["ranks_sha256"])
            elif seed == study_seed:
                checked(rank_file, verified["validation_ranks_sha256"])
            ranks_sha[rank_file.as_posix()] = digest
            archived = csv_rows(rank_file)
            if [r["query_id"] for r in archived] != query_ids:
                raise ValueError(f"Unpaired, duplicate or missing query IDs at {rank_file}")
            ranks = np.array([int(r["rank"]) for r in archived])
            if np.any(ranks < 1) or np.any(ranks > [len(p["candidates"]) for p in panels]):
                raise ValueError(f"Rank outside the P08 candidate panel at {rank_file}")
            by_track = np.bincount(indices[ranks == 1], minlength=len(tracks))
            if not np.isclose((by_track / sizes).mean(), float(row["recall1"]), atol=1e-12, rtol=0):
                raise ValueError(f"Recording-macro Recall@1 differs at {rank_file}")
            hits.append(by_track)
        counts[family] = np.array(hits).T

    # Recording hashes stay private. These counts suffice to replay every draw.
    recordings = [[int(group_index[i]), int(sizes[i]), *counts["mert"][i].tolist(),
                   *counts["classical"][i].tolist()] for i in range(len(tracks))]
    return dict(seeds=seeds, study_seed=study_seed, queries=len(query_ids), groups=len(group_ids),
                recording_count_columns=["group_index", "queries",
                                         *[f"mert_hits_{s}" for s in seeds],
                                         *[f"classical_hits_{s}" for s in seeds]],
                recording_counts=recordings, validation_sha256=file_sha256(panel_file), ranks_sha256=ranks_sha)


def bootstrap(data):
    seeds = data["seeds"]
    counts = np.array(data["recording_counts"])
    group, queries = counts[:, 0], counts[:, 1]
    mert, classical = np.split(counts[:, 2:], 2, axis=1)
    groups = data["groups"]
    rng = np.random.Generator(np.random.PCG64(data["bootstrap_seed"]))
    draws = rng.integers(groups, size=(data["draws"], groups))
    results = {}
    for name, delta in (("study_seed", (mert - classical)[:, seeds.index(data["study_seed"])]),
                        ("seed_mean", (mert - classical).mean(axis=1))):
        # Hit-count differences and denominators per sampled cluster. Source groups
        # containing two recordings must keep both when the cluster is sampled.
        hit_diff = np.bincount(group, weights=delta)
        n_queries = np.bincount(group, weights=queries)
        weights = {
            "recording_macro": (np.bincount(group, weights=delta / queries), np.bincount(group)),
            "group_macro": (hit_diff / n_queries, np.ones(groups)),
            "query_micro": (hit_diff, n_queries),
        }
        result = {}
        for metric, (numer, denom) in weights.items():
            values = 100 * numer[draws].sum(axis=1) / denom[draws].sum(axis=1)
            result[metric] = dict(difference_pp=float(100 * numer.sum() / denom.sum()),
                                  interval95_pp=np.quantile(values, data["quantiles"], method="linear").tolist())
        results[name] = result
    return results


def normalization_probe():
    import torch

    from src.ranking.continuation import MODEL_DIR

    # Capture the input to the actual model in isolated_means, including batching.
    torch.set_num_threads(2)
    encoder = FrozenMert(MODEL_DIR, "cpu")
    t = np.arange(153_600) / SAMPLE_RATE
    x = (.45 * np.sin(2 * np.pi * 220 * t) + .2 * np.sin(2 * np.pi * 440 * t) + .05).astype("float32")
    audio = np.concatenate([x, x / 2])
    bars = np.arange(8)[:, None] * 38_400 + np.arange(9) * 4_800
    received = []

    def capture(module, args):
        received.append(args[0].detach().cpu().numpy())

    handle = encoder.model.register_forward_pre_hook(capture)
    try:
        encoder.isolated_means(audio, bars, np.array([0, 4]))
    finally:
        handle.remove()
    normalized, = received
    raw = audio.reshape(2, -1)
    expected = (raw - raw.mean(axis=1, keepdims=True)) / np.sqrt(raw.var(axis=1, keepdims=True) + 1e-7)
    if not encoder.processor.do_normalize or not np.allclose(normalized, expected, rtol=0, atol=1e-6):
        raise ValueError("Actual MERT inputs differ from the per-window normalization")
    return dict(preprocessor_sha256=file_sha256(MODEL_DIR / "preprocessor_config.json"),
                do_normalize=encoder.processor.do_normalize, sample_rate=SAMPLE_RATE,
                window_samples=len(x), gain_db=float(20 * np.log10(.5)), device="cpu",
                input_means=normalized.mean(axis=1).tolist(), input_variances=normalized.var(axis=1).tolist(),
                max_abs_input_difference=float(np.abs(normalized[0] - normalized[1]).max()),
                max_abs_formula_error=float(np.abs(normalized - expected).max()))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--output", type=Path, help="Create evidence from the local panels, ranks and model")
    action.add_argument("--replay", type=Path, help="Reproduce the bootstrap from the public recording counts")
    args = parser.parse_args()
    if args.replay:
        data = json.loads(args.replay.read_bytes())
        results = bootstrap(data)
        if results != data["results"]:
            raise ValueError("Bootstrap replay differs from archived results")
    else:
        data = recording_counts()
        data.update(format_version=1, draws=N_DRAWS, bootstrap_seed=BOOTSTRAP_SEED,
                    rng="PCG64", quantiles=[.025, .975])
        results = bootstrap(data)
        data.update(results=results, normalization=normalization_probe())
        with args.output.open("x", encoding="utf-8", newline="\n") as stream:
            json.dump(data, stream, indent=2, allow_nan=False)
            stream.write("\n")
    print(json.dumps(results, indent=2))
