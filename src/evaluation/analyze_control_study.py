"""Unblind and summarize a completed control A/B listening study."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import uuid


CONTROL_STUDY_RESULTS_FORMAT_VERSION = 1
METHODS = ("baseline_equal_power", "optimized_proxy")


def analyze_control_study(study_directory, output_path=None):
    """Create a reproducible method-level result from completed blind ratings."""
    study_directory = Path(study_directory)
    manifest = _read_json(study_directory / "manifest.json")
    ratings = _read_json(study_directory / "ratings.json")
    answer_key = _read_json(study_directory / "answer_key.json")

    if not manifest.get("blind"):
        raise ValueError("Expected a blind control-study manifest")
    if ratings.get("status") != "completed":
        raise ValueError("Ratings must be completed before the study is unblinded")

    manifest_pairs = _index_pairs(manifest["pairs"], "manifest")
    rating_pairs = _index_pairs(ratings["ratings"], "ratings")
    answer_pairs = _index_pairs(answer_key["pairs"], "answer_key")
    if not (set(manifest_pairs) == set(rating_pairs) == set(answer_pairs)):
        raise ValueError("Pair indices differ between manifest, ratings, and answer key")

    criteria = tuple(ratings["criteria"])
    values = {
        method: {criterion: [] for criterion in criteria}
        for method in METHODS
    }
    preference_counts = {method: 0 for method in METHODS}
    preference_counts["tie"] = 0
    pair_results = []

    for pair_index in sorted(manifest_pairs):
        public_pair = manifest_pairs[pair_index]
        rating = rating_pairs[pair_index]
        answer = answer_pairs[pair_index]
        _validate_pair_identity(public_pair, rating, answer)
        mapping = answer["mapping"]
        if set(mapping) != {"A", "B"} or set(mapping.values()) != set(METHODS):
            raise ValueError(f"Invalid A/B method mapping for pair {pair_index}")
        if rating.get("status") != "rated":
            raise ValueError(f"Pair {pair_index} is not rated")

        scores_by_method = {}
        issues_by_method = {}
        for label, method in mapping.items():
            method_scores = rating["scores"][label]
            if set(method_scores) != set(criteria):
                raise ValueError(f"Invalid score criteria for pair {pair_index}, label {label}")
            scores_by_method[method] = {
                criterion: int(method_scores[criterion]) for criterion in criteria
            }
            issues_by_method[method] = list(rating["issues"][label])
            for criterion in criteria:
                values[method][criterion].append(int(method_scores[criterion]))

        preferred_label = rating["preferred"]
        preferred_method = "tie" if preferred_label == "tie" else mapping[preferred_label]
        preference_counts[preferred_method] += 1
        pair_results.append(
            {
                "pair_index": pair_index,
                "directory": public_pair["directory"],
                "source_track": public_pair.get("source_track"),
                "target_track": public_pair.get("target_track"),
                "mapping": dict(mapping),
                "preferred_label": preferred_label,
                "preferred_method": preferred_method,
                "scores": scores_by_method,
                "issues": issues_by_method,
                "notes": rating.get("notes", ""),
            }
        )

    criterion_summary = {}
    for method in METHODS:
        criterion_summary[method] = {
            criterion: _summary(values[method][criterion])
            for criterion in criteria
        }
        all_scores = [
            score
            for criterion in criteria
            for score in values[method][criterion]
        ]
        criterion_summary[method]["overall"] = _summary(all_scores)

    paired_deltas = {}
    for criterion in criteria:
        deltas = [
            optimized - baseline
            for optimized, baseline in zip(
                values["optimized_proxy"][criterion],
                values["baseline_equal_power"][criterion],
                strict=True,
            )
        ]
        paired_deltas[criterion] = _summary(deltas)
    overall_deltas = [
        optimized - baseline
        for criterion in criteria
        for optimized, baseline in zip(
            values["optimized_proxy"][criterion],
            values["baseline_equal_power"][criterion],
            strict=True,
        )
    ]
    paired_deltas["overall"] = _summary(overall_deltas)

    decisive_count = len(pair_results) - preference_counts["tie"]
    payload = {
        "format_version": CONTROL_STUDY_RESULTS_FORMAT_VERSION,
        "analysis": "blind_control_study_v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_files": {
            "manifest": "manifest.json",
            "ratings": "ratings.json",
            "answer_key": "answer_key.json",
        },
        "sample": {
            "pair_count": len(pair_results),
            "completed_rating_sets": 1,
            "rater_count": 1,
        },
        "methods": list(METHODS),
        "criteria": list(criteria),
        "preference_counts": preference_counts,
        "preference_rates_excluding_ties": {
            method: (
                preference_counts[method] / decisive_count if decisive_count else None
            )
            for method in METHODS
        },
        "criterion_summary": criterion_summary,
        "paired_delta_optimized_minus_baseline": paired_deltas,
        "pairs": pair_results,
        "study_notes": list(ratings.get("study_notes", [])),
        "interpretation_limits": [
            "One completed rating set from one rater.",
            "The selected pairs are not an independent random sample.",
            "Scores of 5 mean that no negative issue was noticed, not perfection.",
        ],
    }
    output_path = (
        Path(output_path) if output_path else study_directory / "study_results.json"
    )
    _write_json_atomic(output_path, payload)
    return output_path


def _index_pairs(pairs, source_name):
    indexed = {}
    for pair in pairs:
        pair_index = int(pair.get("index", pair.get("pair_index")))
        if pair_index in indexed:
            raise ValueError(f"Duplicate pair index {pair_index} in {source_name}")
        indexed[pair_index] = pair
    return indexed


def _validate_pair_identity(public_pair, rating, answer):
    pair_index = int(public_pair["index"])
    expected_directory = public_pair["directory"]
    if rating["directory"] != expected_directory or answer["directory"] != expected_directory:
        raise ValueError(f"Directory mismatch for pair {pair_index}")


def _summary(values):
    values = list(values)
    return {
        "count": len(values),
        "sum": sum(values),
        "mean": sum(values) / len(values) if values else None,
        "minimum": min(values) if values else None,
        "maximum": max(values) if values else None,
    }


def _read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _write_json_atomic(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        temporary_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)


def build_argument_parser():
    parser = argparse.ArgumentParser(
        description="Unblind and summarize a completed control A/B study."
    )
    parser.add_argument("study_directory")
    parser.add_argument("--output")
    return parser


def main():
    args = build_argument_parser().parse_args()
    output_path = analyze_control_study(args.study_directory, args.output)
    result = _read_json(output_path)
    print(
        json.dumps(
            {
                "output": str(output_path),
                "preference_counts": result["preference_counts"],
                "overall_means": {
                    method: result["criterion_summary"][method]["overall"]["mean"]
                    for method in METHODS
                },
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
