"""Cross-check the P10 tables, selected study cue, live batch audio and author shortlist."""

import argparse
import csv
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean

import numpy as np
from scipy.stats import rankdata
import soundfile as sf

from src.evaluation.comparison import write_json
from src.evaluation.p10_validation import ROOT
from src.features.p07_mert import file_sha256
from src.features.p08_pairs import OUTPUT
from src.features.p08_windows import P07, checked, p07_views, read_json
from src.ml.p08_contrastive import read_rows
from src.ranking.continuation import METHOD, SELECTION


def csv_rows(path):
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def require(value, message):
    if not value:
        raise ValueError(message)


def verify(root):
    p, val = root / "pairs", root / "validation"
    hashes = read_json(p / "provenance.json")
    selection = read_json(checked(SELECTION, hashes["selection_sha256"]))
    checked(val / "selection.json", hashes["selection_sha256"])
    table = csv_rows(checked(p / "offline.csv", hashes["offline_table_sha256"]))
    require(len(table) == 14, "Missing offline conditions")
    panels = read_rows(checked(OUTPUT / "validation.jsonl", selection["validation_sha256"]))
    pairs = read_json(p / "pairs.json")["pairs"]
    views = {v["sha256"]: v for v in p07_views(P07)["views"] if v["split"] == "validation"}
    groups = [views[p[k]]["recording_group_id"] for p in pairs for k in ("source", "target")]
    require(len(groups) == len(set(groups)), "Repeated comparison group")
    donors = Counter(views[n.split(":")[0]]["recording_group_id"] for r in panels
                     for n in r["negatives"]["tempo"] + r["negatives"]["foreign"])
    directions = Counter(r["positive_section"] for r in panels if r["intro_drop_control"])
    candidates = defaultdict(list)
    for r in csv_rows(p / "candidate_scores.csv"):
        candidates[r["pair"]].append(r)
    selected = selection["selected"]
    selected_name = f'mert_s{selected["level"]}_{selected["seed"] or "deterministic"}'
    top_ids = {}
    for condition in table:
        name = '{family}_s{level}_{seed}'.format(**dict(condition, seed=condition["seed"] or "deterministic"))
        by_recording, same, intro = defaultdict(list), defaultdict(list), defaultdict(list)
        for row, panel in zip(csv_rows(val / (name + ".csv")), panels, strict=True):
            require(row["query_id"] == panel["query_id"] and row["group"] == panel["group"]
                    and row["positive"] == panel["positive"] and row["same"] == panel["same_control"]
                    and row["intro_drop"] == (panel["intro_drop_control"] or {}).get("candidate", ""),
                    "Validation case provenance differs")
            by_recording[row["query_id"].split(":")[0]].append(int(row["rank"]))
            positive = float(row["positive_score"])
            for k, acc in (("same_score", same), ("intro_drop_score", intro)):
                if row[k]:
                    delta = positive - float(row[k])
                    acc[row["group"]].append(.5 if delta == 0 else int(delta > 0))
        recalculated = [mean(mean(int(v == 1) for v in rs) for rs in by_recording.values()),
                        mean(mean(1 / v for v in rs) for rs in by_recording.values()),
                        mean(map(mean, same.values())), mean(map(mean, intro.values()))]
        matches, correlations = 0, []
        for pair in pairs:
            rows = candidates[pair["pair"]]
            require(len({r["candidate_id"] for r in rows}) == pair["common"], "Wrong common pool")
            def top(column):
                return min(rows, key=lambda r: (-float(r[column]), r["candidate_id"]))["candidate_id"]
            a, b = top(name), top("feature_baseline_v3")
            matches += int(a == b)
            if name == selected_name:
                top_ids[pair["pair"]] = (a, b)
            ranks = [rankdata([float(r[k]) for r in rows]) for k in (name, "feature_baseline_v3")]
            if all(np.ptp(v) > 0 for v in ranks):
                correlations.append(float(np.corrcoef(*ranks)[0, 1]))
        require(matches == int(condition["top1_matches"]) and len(correlations) == int(condition["rho_pairs"]),
                "Top-1 agreement or correlation denominator differs")
        np.testing.assert_allclose([*recalculated, mean(correlations)],
                                   [float(condition[k]) for k in ("recall1", "mrr", "same", "intro_drop",
                                                                 "mean_spearman")], rtol=0, atol=1e-12)
    batch = read_json(root / "batch" / "manifest.json")
    pair = pairs[0]
    require((batch["source_audio_sha256"], batch["target_audio_sha256"]) == (pair["source"], pair["target"])
            and batch["ranking_method"] == METHOD and not batch["failures"]
            and batch["cue_ranking"]["provenance"]["selection_sha256"] == hashes["selection_sha256"]
            and not batch["cue_ranking"]["failures"], "Wrong batch inputs/selection")
    live = {r["candidate_id"]: r["total_score"] for r in batch["cue_ranking"]["scores"]}
    cached = {r["candidate_id"]: float(r[selected_name]) for r in candidates[pair["pair"]]}
    require(live.keys() == cached.keys(), "Different live and cache candidate sets")
    delta = max(abs(value - cached[key]) for key, value in live.items())
    require(delta < 1e-5, "Fresh original-audio MERT scores differ from bar cache")
    ssl, rule = top_ids[pair["pair"]]
    variant, = batch["rendered_variants"]
    require(variant["candidate_id"] == ssl and variant["selection_rank"] == 1 and
            batch["candidate_ranking"]["scores"][0]["candidate_id"] == rule, "Rendered wrong winner")
    cue = next(c for c in batch["candidate_generation"]["candidates"] if c["candidate_id"] == ssl)
    wav = root / "batch" / variant["output_file"]
    pcm, rate = sf.read(wav, always_2d=True)
    bounds = []
    for role in ("source", "target"):
        v = views[pair[role]]
        native = read_json(checked(Path(v["analysis_path"]), v["analysis_sha256"]))["result"]["beat_frames"]
        factor = rate / sf.info(v["path"]).samplerate
        beat = cue[role + "_cutpoint"]["beat_index"]
        ticks = [round(frame[0] * factor) for frame in native]
        require(ticks[beat] == cue[role + "_cutpoint"]["sample"], "Wrong cue sample")
        if role == "source":
            bounds.append(ticks[beat + 16] - ticks[beat])
        else:
            stretch = cue["target_bpm"] / cue["source_bpm"]
            bounds.append(round(ticks[beat] * stretch) - round(ticks[beat - 16] * stretch))
    require(rate == 44100 and pcm.shape == (19 * rate, 2) and np.isfinite(pcm).all() and
            variant["transition_start_sample"] == 5 * rate and
            variant["transition_end_sample"] == 5 * rate + min(bounds), "Incorrect rendered overlap")
    folder = root / "autorensichtung"
    queue = read_json(folder / "zuordnung.json")
    expected = [p for p, (a, b) in top_ids.items() if a != b]
    require(queue["offline_sha256"] == hashes["offline_table_sha256"] and
            queue["available_disagreements"] == len(expected), "Wrong listening source")
    expected_files = {(p, m) for p in expected[:10] for m in ("model", "rule")}
    for clip in queue["clips"]:
        expected_files.remove((clip["pair"], clip["method"]))
        require(clip["candidate_id"] == top_ids[clip["pair"]][int(clip["method"] == "rule")],
                "Wrong listening shortlist cue")
        checked(folder / clip["file"], clip["sha256"])
    require(not expected_files, "Incomplete listening shortlist")
    return dict(format_version=1, result="passed", **hashes, conditions=len(table),
                queries=len(panels), donor_groups=len(donors), max_foreign_reuse=max(donors.values()),
                same_groups=len(same), intro_drop_groups=len(intro), positive_sections=dict(directions),
                pairs=len(pairs), groups=len(groups), cues=sum(map(len, candidates.values())),
                batch_pair=pair["pair"], live_scores=len(live), max_abs_live_score_difference=delta,
                cue=ssl, rule_cue=rule, sample_rate=rate, stereo_frames=len(pcm), bridge_frames=min(bounds),
                wav_sha256=file_sha256(wav), manifest_sha256=file_sha256(root / "batch" / "manifest.json"),
                conflicts=len(expected), prepared_clips=len(queue["clips"]))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    result = verify(args.root)
    write_json(args.root / "verified.json", result)
    print(result)
