"""Reproduce the descriptive analysis of the completed renderfix listening set.

Pair 11 was explicitly excluded by the rater on 2026-11-06 because of a
perceived tempo mismatch. Original ratings, manifests and audio stay read-only.
Run from the repository root with the repository's virtualenv Python.
"""

from collections import Counter, defaultdict
from datetime import datetime, timezone
from hashlib import sha256
from itertools import combinations
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STUDY = ROOT / "output/four_models_shared_20pairs_validation_20261105_renderfix"
OUTPUT = ROOT / "docs/LISTENING_STUDY_ANALYSE_20261106.json"
EXCLUSIONS = {11: "Rater confirmed on 2026-11-06: leave unranked because of tempo mismatch."}


def digest(path):
    hasher = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def read_json(name):
    return json.loads((STUDY / name).read_text(encoding="utf-8"))


def indexed(entries, field):
    result = {entry[field]: entry for entry in entries}
    if len(result) != len(entries):
        raise ValueError(f"Duplicate {field}")
    return result


def main():
    input_hashes = {name: digest(STUDY / name) for name in
                    ("manifest.json", "ratings.json", "answer_key.json", "index.html")}
    manifest, ratings = read_json("manifest.json"), read_json("ratings.json")
    public = indexed(manifest["pairs"], "index")
    responses = indexed(ratings["ratings"], "pair_index")
    if set(public) != set(responses) or ratings["study_manifest"] != "manifest.json":
        raise ValueError("Rating identities do not match the public manifest")
    if len(public) != manifest["pair_count"] or not set(EXCLUSIONS) <= set(public):
        raise ValueError("Pair count or exclusions do not match")
    for index, pair in public.items():
        ranks = responses[index]["ranks"]
        if set(ranks) != set(pair["labels"]):
            raise ValueError(f"Pair {index}: labels do not match")
        if index in EXCLUSIONS:
            if any(value is not None for value in ranks.values()):
                raise ValueError(f"Pair {index}: confirmed unranked exclusion has ranks")
        elif any(type(value) is not int or not 1 <= value <= len(ranks)
                 for value in ranks.values()):
            raise ValueError(f"Pair {index}: missing or invalid ranks")

    # Unblind only after all nonexcluded responses passed completeness checks.
    key = read_json("answer_key.json")
    keyed = indexed(key["pairs"], "index")
    methods = {item["method_id"]: item["display_name"] for item in key["methods"]}
    if set(keyed) != set(public) or len(methods) != manifest["method_count"]:
        raise ValueError("Answer key does not match the public study")
    totals = {method: {"entered_places": [], "midranks": [],
                       "sole_best_count": 0, "shared_best_count": 0} for method in methods}
    comparisons = {pair: Counter(win=0, tie=0, loss=0) for pair in combinations(methods, 2)}
    groups = defaultdict(lambda: {"examples": [], "ranked": [], "excluded": []})
    rows, audio_checks = [], []
    for index, pair in public.items():
        answer, response = keyed[index], responses[index]
        if answer["directory"] != pair["directory"]:
            raise ValueError(f"Pair {index}: directory mismatch")
        mapping = answer["mapping"]
        if set(mapping) != set(pair["labels"]) or set(mapping.values()) != set(methods):
            raise ValueError(f"Pair {index}: method mapping is not a bijection")
        group_id = (answer["source_track_sha256"], answer["target_track_sha256"])
        group = groups[group_id]
        group["source_track"], group["target_track"] = pair["source_track"], pair["target_track"]
        group["examples"].append(index)
        group["excluded" if index in EXCLUSIONS else "ranked"].append(index)
        ranks = {mapping[label]: value for label, value in response["ranks"].items()}
        row = {"pair_index": index, "directory": pair["directory"],
               "source_track": pair["source_track"], "target_track": pair["target_track"],
               "tempo_adjustment_fraction": pair["tempo_adjustment_fraction"],
               "ranks_by_method": ranks, "notes": response.get("notes", ""),
               "excluded_reason": EXCLUSIONS.get(index)}
        if index not in EXCLUSIONS:
            minimum = min(ranks.values())
            best = [method for method, rank in ranks.items() if rank == minimum]
            midranks = {}
            for method, rank in ranks.items():
                # Tied candidates occupy the average of their ordinal positions.
                midrank = 1 + sum(other < rank for other in ranks.values())
                midrank += (sum(other == rank for other in ranks.values()) - 1) / 2
                midranks[method] = midrank
                totals[method]["entered_places"].append(rank)
                totals[method]["midranks"].append(midrank)
                if method in best:
                    totals[method]["sole_best_count" if len(best) == 1 else "shared_best_count"] += 1
            for (left, right), counts in comparisons.items():
                counts["win" if ranks[left] < ranks[right] else
                       "loss" if ranks[left] > ranks[right] else "tie"] += 1
            row["midranks_by_method"] = midranks
        rows.append(row)
        for label, metadata in pair["files"].items():
            path = STUDY / pair["directory"] / metadata["path"]
            actual = digest(path)
            if actual != metadata["sha256"]:
                raise ValueError(f"Audio hash mismatch: {path}")
            audio_checks.append({"pair_index": index, "label": label, "sha256": actual})

    ranked_rows = [row for row in rows if row["excluded_reason"] is None]
    for method, counts in totals.items():
        counts["display_name"] = methods[method]
        counts["ranked_example_count"] = len(counts["entered_places"])
        counts["mean_entered_place"] = sum(counts["entered_places"]) / len(ranked_rows)
        counts["mean_midrank"] = sum(counts["midranks"]) / len(ranked_rows)
    unchanged = {name: digest(STUDY / name) for name in input_hashes} == input_hashes
    if not unchanged:
        raise ValueError("Study input changed during analysis")
    result = {
        "analysis_date": "2026-11-06", "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "study_directory": STUDY.relative_to(ROOT).as_posix(),
        "ratings_exported_at_utc": ratings["exported_at_utc"],
        "input_sha256": input_hashes, "analysis_script_sha256": digest(Path(__file__)),
        "status": "listening_finished_one_confirmed_unranked_exclusion",
        "pair_count": len(rows), "ranked_pair_count": len(ranked_rows),
        "valid_explicit_rank_count": sum(v is not None for row in rows for v in row["ranks_by_method"].values()),
        "excluded_pairs": {str(k): v for k, v in EXCLUSIONS.items()},
        "full_five_way_tie_count": sum(len(set(row["ranks_by_method"].values())) == 1 for row in ranked_rows),
        "directed_track_pair_count": len(groups),
        "unique_track_hash_count": len({value for group in groups for value in group}),
        "method_summaries": totals,
        "pairwise": [{"left": a, "right": b, **counts} for (a, b), counts in comparisons.items()],
        "track_pair_groups": [{"source_sha256": a, "target_sha256": b, **value}
                              for (a, b), value in groups.items()],
        "examples": rows, "audio_sha256_checks": audio_checks,
        "audio_sha256_match_count": len(audio_checks), "study_input_hashes_unchanged": unchanged,
        "interpretation": "No observed preference among the five methods on 19 ranked cues; no equivalence or absolute quality claim.",
        "inference": "Descriptive only: one rater, repeated track pairs, all pairwise outcomes tied; no informative non-tied comparisons.",
    }
    # Exclusive creation prevents silently replacing a prior analysis snapshot.
    with OUTPUT.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    print(json.dumps({key: result[key] for key in ("ranked_pair_count", "valid_explicit_rank_count",
        "full_five_way_tie_count", "directed_track_pair_count", "unique_track_hash_count",
        "audio_sha256_match_count", "study_input_hashes_unchanged")}, indent=2))
    print(OUTPUT)


if __name__ == "__main__":
    main()
