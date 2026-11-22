"""Compare all P09 heads with feature_baseline_v3 on directed development pairs."""

import argparse
import csv
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr
import soundfile as sf
import torch
from threadpoolctl import threadpool_limits

from src.analysis.models import AnalysisResult, BeatGridMetadata
from src.candidates import BaselineCandidateGenerationConfig
from src.evaluation.comparison import write_json
from src.evaluation.p10_validation import ROOT, write_csv
from src.features.p07_mert import file_sha256
from src.features.p08_pairs import publish_dataset
from src.features.p08_windows import P07, checked, p07_views, read_json
from src.pipeline import generate_transition_candidates
from src.ranking.continuation import BarWindows, P09_AUDIT, candidate_windows, load_head, score_pair
from src.ranking.feature_baseline import FeatureRankingConfig, rank_candidates


RATE = 44100
CONFIG = BaselineCandidateGenerationConfig(transition_lengths_bars=(4,), source_boundary_count=12,
                                          target_boundary_count=12, approximate_grid_policy="reject")


def development_views():
    groups = {}
    for v in sorted(p07_views(P07)["views"], key=lambda v: v["sha256"]):
        if v["split"] == "validation" and v["variant"] == "original":
            groups.setdefault(v["recording_group_id"], v)
    return [v for _, v in sorted(groups.items())]


def native_analysis(view):
    data = read_json(checked(Path(view["analysis_path"]), view["analysis_sha256"]))
    if data["source_audio"]["sha256"] != view["sha256"]:
        raise ValueError("Development grid identity differs")
    r = data["result"]
    return AnalysisResult(r["bpm"], r["beat_frames"], BeatGridMetadata.from_dict(r["grid_metadata"]))


def pair_generation(a, b):
    analyses = {Path(v["path"]): native_analysis(v) for v in (a, b)}
    def analysis(path):
        return analyses[Path(path)]
    generated = generate_transition_candidates(a["path"], b["path"], analysis=analysis,
                                               target_sample_rate=RATE, config=CONFIG)
    return generated, analysis


def load_features(view, analysis):
    archive = (P07 / view["entry"]).with_name("bars.npz")
    with np.load(checked(archive, view["sha256_files"]["bars.npz"])) as z:
        windows = BarWindows.from_bars(z["bar_start_beat_index"], z["bar_boundaries_24k"], z["mert"],
                                       analysis.beat_frames, analysis.grid_metadata.beat_grid_sha256,
                                       RATE / sf.info(view["path"]).samplerate)
    with np.load(checked(P07 / view["classical_scaled"], view["classical_scaled_sha256"])) as z:
        classic = z["classical"]
    return windows, {"mert": windows.bars, "classical": classic}


def compare(out, validation):
    selection = read_json(validation / "selection.json")
    audit = read_json(checked(P09_AUDIT, selection["p09_audit_sha256"]))
    run = Path(audit["run"])
    heads = []
    for row in audit["rows"]:
        heads.append((row, load_head(row, run, audit["config_sha256"])))
    views = development_views()
    records, cases, scores, excluded = [], [], [], []
    for number, (a, b) in enumerate(zip(views[::2], views[1::2]), 1):
        pair = f"dev{number:02d}"
        generation, analysis = pair_generation(a, b)
        manifest = dict(pair=pair, source=a["sha256"], target=b["sha256"],
                        source_group=a["recording_group_id"], target_group=b["recording_group_id"],
                        source_path=a["path"], target_path=b["path"])
        if not generation.candidates:
            excluded.append(dict(**manifest, reasons=[r.to_dict() for r in generation.rejections]))
            continue
        aw, af = load_features(a, analysis(a["path"]))
        bw, bf = load_features(b, analysis(b["path"]))
        # A native 24-kHz P07 bar must exist on either side of the renderer cue.
        candidates, indices, skipped = candidate_windows(generation.candidates, {a["sha256"]: aw, b["sha256"]: bw})
        if not candidates:
            excluded.append(dict(**manifest, reasons=["no_common_complete_P07_windows"]))
            continue
        rule = rank_candidates(candidates, target_sample_rate=RATE)
        if rule.failures or len(rule.scores) != len(candidates):
            raise ValueError(f"Incomplete rule scores for {pair}: {rule.failures}")
        by_id = {s.candidate_id: s.total_score for s in rule.scores}
        rule_scores = [by_id[c.candidate_id] for c in candidates]
        rule_top = rule.scores[0].candidate_id
        case_rows = [dict(pair=pair, candidate_id=c.candidate_id, source_beat=c.source_cutpoint.beat_index,
                          target_beat=c.target_cutpoint.beat_index, source_sample=c.source_cutpoint.sample,
                          target_sample=c.target_cutpoint.sample, feature_baseline_v3=s)
                     for c, s in zip(candidates, rule_scores, strict=True)]
        manifest.update(generated=len(generation.candidates), common=len(candidates), rule_top=rule_top,
                        skipped=[s.to_dict() for s in skipped])
        cases.append(manifest)
        for row, head in heads:
            family = row["family"]
            values = score_pair(head, indices, af[family], bf[family])
            top = min(range(len(values)), key=lambda i: (-values[i], candidates[i].candidate_id))
            top_id = candidates[top].candidate_id
            rho = None
            if len(set(rule_scores)) > 1 and len(set(values)) > 1:
                rho = float(spearmanr(rule_scores, values).statistic)
            records.append(dict(pair=pair, family=family, level=row["level"], seed=row["seed"],
                                candidates=len(values), rule_top=rule_top, model_top=top_id,
                                agreement=int(top_id == rule_top), spearman=rho))
            name = f'{family}_s{row["level"]}_{row["seed"] or "deterministic"}'
            for case, s in zip(case_rows, values, strict=True):
                case[name] = float(s)
        scores.extend(case_rows)
        print(pair, manifest["common"], flush=True)
    write_json(out / "pairs.json", dict(split="validation/original", pairs=cases, excluded=excluded,
               unpaired_group=views[-1]["recording_group_id"] if len(views) % 2 else None,
               generator=vars(CONFIG), rule=FeatureRankingConfig().to_dict(), sample_rate=RATE))
    write_csv(out / "candidate_scores.csv", scores)
    write_csv(out / "pair_metrics.csv", records)
    table_path = checked(validation / "validation.csv", selection["validation_table_sha256"])
    with table_path.open(encoding="utf-8") as f:
        matrix = list(csv.DictReader(f))
    for line in matrix:
        same = [r for r in records if (r["family"], str(r["level"]), str(r["seed"] or "")) ==
                (line["family"], line["level"], line["seed"])]
        corrs = [r["spearman"] for r in same if r["spearman"] is not None]
        line.update(pairs=len(same), cues=sum(r["candidates"] for r in same),
                    top1_matches=sum(r["agreement"] for r in same),
                    top1_agreement=float(np.mean([r["agreement"] for r in same])),
                    rho_pairs=len(corrs), mean_spearman=float(np.mean(corrs)) if corrs else None)
    write_csv(out / "offline.csv", matrix)
    write_json(out / "provenance.json", dict(p07_manifest_sha256=file_sha256(P07 / "manifest.json"),
               p09_audit_sha256=file_sha256(P09_AUDIT), validation_table_sha256=file_sha256(table_path),
               selection_sha256=file_sha256(validation / "selection.json"),
               offline_table_sha256=file_sha256(out / "offline.csv")))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "pairs")
    parser.add_argument("--validation", type=Path, default=ROOT / "validation")
    args = parser.parse_args()
    torch.set_num_threads(1)
    with publish_dataset(args.output) as stage, threadpool_limits(limits=1):
        compare(stage, args.validation)
