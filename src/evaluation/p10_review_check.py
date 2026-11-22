"""Recompute R_P10_01 descriptive statistics and compare the corrected dev01 batch."""

from collections import defaultdict
import json
from pathlib import Path

import numpy as np
from scipy.stats import t

from src.evaluation.comparison_study import final_ssl_provenance
from src.evaluation.p10_verify import csv_rows, require
from src.features.p07_mert import file_sha256
from src.features.p08_windows import read_json


def audit(original, corrected):
    rows = csv_rows(original / "validation/mert_s2_20260926.csv")
    recordings, groups = defaultdict(list), defaultdict(list)
    for row in rows:
        hit = int(row["rank"]) == 1
        recordings[row["query_id"].split(":")[0]].append(hit)
        groups[row["group"]].append(hit)
    rates = np.array([np.mean(recordings[k]) for k in sorted(recordings)])
    boot = np.random.default_rng(20261119).choice(rates, size=(10000, len(rates))).mean(axis=1)
    pairs = [r for r in csv_rows(original / "pairs/pair_metrics.csv")
             if (r["family"], r["level"], r["seed"]) == ("mert", "2", "20260926")]
    rho = np.array([float(r["spearman"]) for r in pairs])
    pools = np.array([int(r["candidates"]) for r in pairs])
    manifests = [read_json(p / "batch/manifest.json") for p in (original, corrected)]
    old, new = manifests
    cue = new["render_selection"]["candidate_ids"][0]
    provenance = final_ssl_provenance(new, cue)
    require(old["cue_ranking"]["scores"] == new["cue_ranking"]["scores"] and
            old["candidate_ranking"] == new["candidate_ranking"] and
            old["rendered_variants"] == new["rendered_variants"], "dev01 changed")
    audio = Path(new["rendered_variants"][0]["output_file"])
    digest = file_sha256(corrected / "batch" / audio)
    require(digest == file_sha256(original / "batch" / audio), "Audio changed")
    return dict(queries=len(rows), recordings=len(rates), groups=len(groups),
                track_recall=rates.mean(), group_recall=np.mean([np.mean(x) for x in groups.values()]),
                recording_bootstrap_ci=np.quantile(boot, [.025, .975]).tolist(), seed=20261119,
                pair_count=len(pairs), mean_rho=rho.mean(), sd_rho=rho.std(ddof=1),
                rho_range=[rho.min(), rho.max()], t_ci=list(t.interval(.95, len(rho)-1, loc=rho.mean(),
                          scale=rho.std(ddof=1)/np.sqrt(len(rho)))), expected_matches=(1/pools).sum(),
                chance_zero=np.prod(1-1/pools), matches=sum(int(r["agreement"]) for r in pairs),
                batch_scores=len(new["cue_ranking"]["scores"]), winner=cue, wav_sha256=digest,
                manifest_sha256=file_sha256(corrected / "batch/manifest.json"),
                encoder_runtime=provenance["encoder_runtime"])


if __name__ == "__main__":
    base = Path("output/review_jp_20261118/p10_ranking")
    result = audit(base / "run01", base / "run02")
    with (base / "run02/review_check.json").open("x", encoding="utf-8") as f:
        json.dump(result, f, indent=2, allow_nan=False)
    print(result)
