"""Freeze P08 continuation queries, explicit negatives and validation tie order."""

import argparse
from collections import Counter, defaultdict
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import random
import shutil
from uuid import uuid4

from src.evaluation.comparison import write_json
from src.features.p07_mert import file_sha256
from src.features.p08_windows import (
    P07, STRUCTURE_COLUMNS, index_track, p07_views, same_track_pool,
)


OUTPUT = Path("output/review_jp_20261118/p08_paare/run02")
SEED = 20261118
K = 4
LENGTH = 4
GROUP_CAP = 64
MODEL_SEEDS = (20260926, 20260927, 20260928)
TEMPERATURE = 0.2
PRIOR = 0.05


def rng_for(*parts, seed=SEED):
    data = json.dumps([seed, *parts], separators=(",", ":")).encode()
    return random.Random(int.from_bytes(hashlib.sha256(data).digest(), "big"))


def location(sha, row):
    return f"{sha}:{int(row):06d}"


def parse_location(key):
    sha, row = key.split(":")
    return sha, int(row)


def tempo_close(a, b):
    return abs(a - b) <= .05 * max(a, b)


def foreign_pools(source, tracks):
    all_groups, near = defaultdict(list), defaultdict(list)
    for donor in tracks:
        if donor.group == source.group or donor.split != source.split or not len(donor.targets):
            continue
        all_groups[donor.group].append(donor)
        if tempo_close(source.bpm, donor.bpm):
            near[donor.group].append(donor)
    return all_groups, near


def draw_foreign(groups, names, rng):
    result = []
    for group in names:
        donor = rng.choice(sorted(groups[group], key=lambda track: track.sha))
        result.append(location(donor.sha, rng.choice(donor.targets)))
    return result


def sample_row(track, d, pools, k, length):
    validation = track.split == "validation"
    near_count, extra_count, same_count = (4, 2, 2) if validation else (2, 1, 1)
    qid = location(track.sha, d)
    rng = rng_for("negative", qid)
    all_groups, near = pools
    eligible = same_track_pool(track, d, k, length)
    missing = []
    if len(near) < near_count:
        missing.append("insufficient_tempo_groups")
    if len(all_groups) < near_count + extra_count:
        missing.append("insufficient_foreign_groups")
    if len(eligible) < same_count:
        missing.append("insufficient_distant_structural_windows")
    if missing:
        return None, missing
    near_groups = rng.sample(sorted(near), near_count)
    extra_groups = rng.sample(sorted(all_groups.keys() - set(near_groups)), extra_count)
    negative = dict(tempo=draw_foreign(near, near_groups, rng),
                    foreign=draw_foreign(all_groups, extra_groups, rng),
                    same=[location(track.sha, t) for t in rng.sample(list(eligible), same_count)])
    t = d + length
    positive = location(track.sha, t)
    row = dict(query_id=qid, group=track.group, d_beat=int(track.beats[d]),
               t_beat=int(track.beats[t]), positive=positive, negatives=negative)
    if validation:
        candidates = sorted([positive, *negative["tempo"], *negative["foreign"], *negative["same"]])
        rng_for("tie", qid).shuffle(candidates)
        section = track.sections[t]
        opposite = {"intro_like": "drop_like", "drop_like": "intro_like"}.get(section)
        choices = [n for n in eligible if track.sections[n] == opposite]
        row.update(candidates=candidates, positive_section=str(section),
                   same_control=negative["same"][0], intro_drop_control=None)
        if choices:
            n = rng_for("intro-drop", qid).choice(choices)
            row["intro_drop_control"] = dict(candidate=location(track.sha, n), section=opposite)
    return row, []


def write_rows(path, rows):
    with path.open("wb") as out:
        for row in rows:
            out.write(json.dumps(row, separators=(",", ":"), sort_keys=True).encode() + b"\n")


@contextmanager
def publish_dataset(destination):
    """Inherit the project ACL before atomic publication (also on Windows)."""
    if destination.exists():
        raise FileExistsError(destination)
    stage = destination.with_name(f".{destination.name}-{uuid4().hex}")
    stage.mkdir(parents=True)
    try:
        yield stage
        stage.rename(destination)
    finally:
        if stage.exists():
            shutil.rmtree(stage)


def sample_split(tracks, k, length):
    pool = defaultdict(list)
    tracks = sorted(tracks, key=lambda track: track.sha)
    by_sha = {track.sha: track for track in tracks}
    donors = {}
    for track in tracks:
        pool[track.group].extend((track.sha, int(d)) for d in track.cues)
        donors[track.sha] = foreign_pools(track, tracks)
    rows, excluded, budget = [], [], {}
    for group, cues in sorted(pool.items()):
        selected = sorted(rng_for("budget", group).sample(cues, min(GROUP_CAP, len(cues))))
        budget[group] = dict(eligible=len(cues), drawn=len(selected))
        for sha, d in selected:
            row, missing = sample_row(by_sha[sha], d, donors[sha], k, length)
            if missing:
                excluded.append(dict(query_id=location(sha, d), group=group, reasons=missing))
            else:
                rows.append(row)
    return rows, excluded, budget


def build(root, destination):
    manifest = p07_views(root)
    columns = [manifest["classical_columns"].index(name) for name in STRUCTURE_COLUMNS]
    tracks = [index_track(root, row, columns, K, LENGTH) for row in manifest["views"]
              if row["variant"] == "original"]
    sha_group = {t.sha: t.group for t in tracks}
    with publish_dataset(destination) as out:
        summary = {}
        for split in ("train", "validation"):
            selected = [t for t in tracks if t.split == split]
            rows, excluded, budget = sample_split(selected, K, LENGTH)
            write_rows(out / f"{split}.jsonl", rows)
            write_rows(out / f"{split}_excluded.jsonl", excluded)
            write_json(out / f"{split}_budget.json", budget)
            if not rows:
                raise ValueError(f"No eligible {split} queries")
            donors = Counter(sha_group[parse_location(key)[0]] for row in rows
                             for key in row["negatives"]["tempo"] + row["negatives"]["foreign"])
            summary[split] = dict(
                original_tracks=len(selected), input_groups=len(budget),
                geometric_queries=sum(b["eligible"] for b in budget.values()),
                drawn=sum(b["drawn"] for b in budget.values()), retained=len(rows),
                source_groups=len({r["group"] for r in rows}),
                source_tracks=len({parse_location(r["query_id"])[0] for r in rows}),
                excluded=len(excluded), reasons=dict(Counter(reason for r in excluded for reason in r["reasons"])),
                foreign_group_uses=dict(sorted(donors.items())),
            )
            if split == "validation":
                controls = [r for r in rows if r["intro_drop_control"]]
                summary[split]["intro_drop"] = dict(
                    queries=len(controls), groups=len({r["group"] for r in controls}),
                    directions=dict(Counter(str(r["positive_section"]) for r in controls)),
                )
        write_json(out / "manifest.json", dict(
            format_version=1, p07_manifest_sha256=file_sha256(root / "manifest.json"),
            freeze_commit=manifest["freeze_commit"], scaler_id=manifest["scaler_id"],
            k=K, length_bars=LENGTH, group_cap=GROUP_CAP, sampling_seed=SEED,
            model_seeds=MODEL_SEEDS, batch_size=32, epochs=30, temperature=TEMPERATURE,
            tau_plus=PRIOR, structure_columns=STRUCTURE_COLUMNS, splits=summary,
            files={p.name: file_sha256(p) for p in sorted(out.iterdir())},
        ))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--p07", type=Path, default=P07)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    build(args.p07, args.output)
    print(args.output / "manifest.json")
