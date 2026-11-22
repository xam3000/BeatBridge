"""Audit the released pairs using P07 bar boundaries and real rendered cue metadata."""

import argparse
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import soundfile as sf

from src.evaluation.comparison import write_json
from src.features.p07_mert import file_sha256
from src.features.p08_pairs import GROUP_CAP, K, LENGTH, OUTPUT, parse_location, sample_split
from src.features.p08_windows import (
    P07, STRUCTURE_COLUMNS, VARIANTS, checked, index_track, p07_views, read_json,
)
from src.ml.p08_contrastive import read_rows


def require(ok, message):
    if not ok:
        raise ValueError(message)


def renderer_example():
    path = Path("output/review_jp_20261118/p13_laengen/run03/manifest.json")
    raw = read_json(path)
    result, = [r for r in raw["rendered_variants"] if r["transition_length_bars"] == LENGTH]
    cue, = [c for c in raw["candidate_generation"]["candidates"] if c["candidate_id"] == result["candidate_id"]]
    reference = Path("docs/masterarbeit/review_jp_20261118/p13/verified.json")
    prior = read_json(reference)
    four, = [r for r in prior["lengths"] if r["bars"] == LENGTH]
    windows = {}
    for role in ("source", "target"):
        tr, cp = cue[f"{role}_track"], cue[f"{role}_cutpoint"]
        base = Path("output/pre_analysis_variable_v2_strict_20260820_retry01/v2") / tr["sha256"]
        analysis = read_json(base / cue[f"{role}_grid"]["analysis_id"] / "analysis.json")
        require(analysis["source_audio"]["sha256"] == tr["sha256"], "Wrong cue analysis")
        grid = np.array(analysis["result"]["beat_frames"])
        grid[:, 0] = np.rint(grid[:, 0] * (result["sample_rate"] / sf.info(tr["path"]).samplerate))
        i = cp["beat_index"]
        indices = np.arange(i - 4*K, i + 4*K + 1, 4)
        require(cp["sample"] == grid[i, 0] and np.all(grid[indices, 1:] == [1, 4]), "Cue off grid")
        windows[role] = dict(bar_index=cp["bar_index"], beat_index=i, downbeats=grid[indices, 0].tolist())
    a, b = (windows[role]["downbeats"] for role in ("source", "target"))
    n = min(a[-1] - a[K], b[K] - b[0])
    require(cue["source_bpm"] == cue["target_bpm"] and result["tempo_backend"] == "not_needed",
            "Fixture needs a tempo-coordinate conversion")
    require([a[K], a[-1]] == four["source_window"] and [b[0], b[K]] == four["target_window_original"]
            and n == four["overlap_samples"] == result["transition_end_sample"] - result["transition_start_sample"],
            "Beat offsets differ from the real render")
    return dict(raw_manifest=path.as_posix(), raw_sha256=file_sha256(path), cue=cue["candidate_id"],
                rate=result["sample_rate"], **windows, overlap=n,
                effective_source=[a[K], a[K]+n], effective_target=[b[K]-n, b[K]],
                preview=[result["transition_start_sample"], result["transition_end_sample"]])


def check_span(track, start, end):
    beats, bars = track.beats[start:end], track.bars[start:end]
    require(start >= 0 and len(beats) == end-start and np.all(np.diff(beats) == 4)
            and np.array_equal(bars[:-1, -1], bars[1:, 0]), "Broken real bar sequence")


def check_rows(rows, tracks, split):
    src = {t.sha: t for t in tracks}
    near_n, extra_n, same_n = (4, 2, 2) if split == "validation" else (2, 1, 1)
    counts, summary = Counter(), Counter()
    example = None
    unique = set()
    min_gap, max_bpm_delta = None, 0.
    for r in rows:
        sha, d = parse_location(r["query_id"])
        track = src[sha]
        t = d + LENGTH
        check_span(track, d-K, t+K)
        require(r["query_id"] not in unique and r["group"] == track.group
                and (sha, t) == parse_location(r["positive"])
                and (track.beats[d], track.beats[t]) == (r["d_beat"], r["t_beat"]), "Invalid positive")
        unique.add(r["query_id"])
        counts[track.group] += 1
        neg = r["negatives"]
        require([len(neg[key]) for key in ("tempo", "foreign", "same")] == [near_n, extra_n, same_n],
                "Wrong composition")
        group_ids = set()
        for key in ("tempo", "foreign"):
            for n in neg[key]:
                donor_sha, start = parse_location(n)
                donor = src[donor_sha]
                check_span(donor, start-LENGTH, start+K)
                require(donor.group != track.group and donor.group not in group_ids, "Foreign identity collision")
                group_ids.add(donor.group)
                if key == "tempo":
                    delta = abs(track.bpm-donor.bpm)/max(track.bpm, donor.bpm)
                    require(delta <= .05, "Tempo exceeds 5%")
                    max_bpm_delta = max(max_bpm_delta, delta)
                summary[key] += 1
        same = list(neg["same"])
        summary["same"] += len(same)
        if split == "validation":
            pool = [r["positive"], *neg["tempo"], *neg["foreign"], *same]
            require(len(set(pool)) == 9 and sorted(pool) == sorted(r["candidates"])
                    and r["same_control"] == same[0], "Bad fixed retrieval panel")
            require(r["positive_section"] == track.sections[t], "Wrong positive section")
            control = r["intro_drop_control"]
            if control:
                sha2, start = parse_location(control["candidate"])
                require(sha2 == sha and control["section"] == track.sections[start]
                        and {r["positive_section"], control["section"]} == {"intro_like", "drop_like"},
                        "Wrong section control")
                same.append(control["candidate"])
                summary["intro_drop"] += 1
        for n in same:
            donor_sha, start = parse_location(n)
            require(donor_sha == sha, "Same-track candidate changed recording")
            check_span(track, start-LENGTH, start+K)
            gap = d-K-start-K if start < d else start-t-K
            differences = np.abs(track.structure[start] - track.structure[t])
            require(gap > 16 and sum(differences >= 1.) >= 2, "Nearby or repetitive candidate")
            min_gap = gap if min_gap is None else min(min_gap, gap)
        if example is None:
            example = dict(query=r["query_id"], bar_rows=[d-K, d, t, t+K],
                           native_beats=[int(track.beats[i]) for i in (d-K, d, t)] + [int(track.beats[t+K-1]+4)],
                           samples_24k=[int(track.bars[i, 0]) for i in (d-K, d, t)] + [int(track.bars[t+K-1, -1])])
    require(max(counts.values()) <= GROUP_CAP, "Group budget violated")
    return dict(queries=len(unique), groups=len(counts), negatives=dict(summary), example=example,
                min_complete_bars_between=min_gap, max_relative_bpm_difference=max_bpm_delta)


def verify(dataset, root):
    source = p07_views(root)
    release = read_json(dataset / "manifest.json")
    checked(root / "manifest.json", release["p07_manifest_sha256"])
    for name, digest in release["files"].items():
        checked(dataset / name, digest)
    columns = [source["classical_columns"].index(c) for c in STRUCTURE_COLUMNS]
    originals = {r["sha256"]: index_track(root, r, columns, K, LENGTH) for r in source["views"]
                 if r["variant"] == "original"}
    variants = defaultdict(list)
    for r in source["views"]:
        tr = originals[r["sha256"]]
        require((r["recording_group_id"], r["split"]) == (tr.group, tr.split), "Variant identity mismatch")
        variants[tr.sha].append(r["variant"])
        if r["variant"] != "original":
            path = (root / r["entry"]).with_name("bars.npz")
            with np.load(checked(path, r["sha256_files"]["bars.npz"])) as archive:
                np.testing.assert_array_equal(tr.beats, archive["bar_start_beat_index"])
                np.testing.assert_array_equal(tr.bars, archive["bar_boundaries_24k"])
    require(all(sorted(variants[t.sha]) == sorted(VARIANTS if t.split == "train" else ["original"])
                for t in originals.values()), "Wrong production set")
    verified = {}
    for split in ("train", "validation"):
        tracks = [t for t in originals.values() if t.split == split]
        rows = read_rows(dataset / f"{split}.jsonl")
        replay, excluded, budget = sample_split(tracks, K, LENGTH)
        require(rows == replay and excluded == read_rows(dataset / f"{split}_excluded.jsonl")
                and budget == read_json(dataset / f"{split}_budget.json"), "Sampling replay mismatch")
        verified[split] = check_rows(rows, tracks, split)
    return dict(format_version=1, result="passed", manifest_sha256=file_sha256(dataset / "manifest.json"),
                files=release["files"], views=len(source["views"]), splits=verified, renderer=renderer_example())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=OUTPUT)
    parser.add_argument("--p07", type=Path, default=P07)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    if args.receipt.exists():
        raise FileExistsError(args.receipt)
    result = verify(args.dataset, args.p07)
    write_json(args.receipt, result)
    print(result["splits"], result["renderer"])
