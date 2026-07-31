"""Persistent ratings for blinded control-comparison studies."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import uuid


CONTROL_STUDY_RATINGS_FORMAT_VERSION = 2
RATING_CRITERIA = (
    "cleanliness",
    "energy_shape",
    "low_end_handover",
    "rhythmic_stability",
    "vocal_clarity",
    "artifact_freedom",
)
PREFERENCES = ("A", "B", "tie")
ISSUE_TAGS = (
    "returning_source",
    "abrupt_gain",
    "bass_clash",
    "rhythm",
    "artifacts",
    "tempo_mismatch",
    "vocal_clash",
    "cut_lyrics",
    "other",
)


def create_control_study_ratings(study_directory):
    """Create an unrated sidecar from a blind public manifest."""
    study_directory = Path(study_directory)
    ratings_path = study_directory / "ratings.json"
    if ratings_path.exists():
        raise FileExistsError(f"Ratings sidecar already exists: {ratings_path}")
    manifest = _read_json(study_directory / "manifest.json")
    if not manifest.get("blind"):
        raise ValueError("Control-study ratings require a blind study manifest")
    payload = {
        "format_version": CONTROL_STUDY_RATINGS_FORMAT_VERSION,
        "study_manifest": "manifest.json",
        "created_at_utc": _utc_now(),
        "updated_at_utc": None,
        "status": "unrated",
        "criteria": list(RATING_CRITERIA),
        "score_scale": {"minimum": 1, "maximum": 5},
        "preferences": list(PREFERENCES),
        "issue_tags": list(ISSUE_TAGS),
        "study_notes": [],
        "ratings": [
            {
                "pair_index": int(pair["index"]),
                "directory": pair["directory"],
                "status": "unrated",
                "preferred": None,
                "scores": {
                    "A": {criterion: None for criterion in RATING_CRITERIA},
                    "B": {criterion: None for criterion in RATING_CRITERIA},
                },
                "issues": {"A": [], "B": []},
                "notes": "",
                "rated_at_utc": None,
            }
            for pair in manifest["pairs"]
        ],
    }
    _write_json_atomic(ratings_path, payload)
    return ratings_path


def add_control_study_note(study_directory, note):
    """Append one timestamped note that applies to the complete study."""
    study_directory = Path(study_directory)
    ratings_path = study_directory / "ratings.json"
    payload = _read_json(ratings_path)
    notes = payload.setdefault("study_notes", [])
    notes.append({"created_at_utc": _utc_now(), "note": str(note)})
    payload["updated_at_utc"] = _utc_now()
    _write_json_atomic(ratings_path, payload)
    return ratings_path


def rate_control_study_pair(
    study_directory,
    pair_index,
    *,
    preferred,
    scores_a,
    scores_b,
    issues_a=(),
    issues_b=(),
    notes="",
):
    """Upsert one complete blinded A/B rating."""
    study_directory = Path(study_directory)
    ratings_path = study_directory / "ratings.json"
    payload = _read_json(ratings_path)
    if int(payload.get("format_version", 0)) not in {1, 2}:
        raise ValueError("Unsupported control-study ratings format_version")
    if preferred not in PREFERENCES:
        raise ValueError(f"preferred must be one of: {', '.join(PREFERENCES)}")
    criteria = tuple(payload["criteria"])
    issue_tags = tuple(payload["issue_tags"])
    scores_a = _validate_scores(scores_a, "scores_a", criteria)
    scores_b = _validate_scores(scores_b, "scores_b", criteria)
    issues_a = _validate_issues(issues_a, "issues_a", issue_tags)
    issues_b = _validate_issues(issues_b, "issues_b", issue_tags)

    pair_index = int(pair_index)
    entry = next(
        (item for item in payload["ratings"] if int(item["pair_index"]) == pair_index),
        None,
    )
    if entry is None:
        raise ValueError(f"Unknown pair_index: {pair_index}")
    entry.update(
        {
            "status": "rated",
            "preferred": preferred,
            "scores": {"A": scores_a, "B": scores_b},
            "issues": {"A": list(issues_a), "B": list(issues_b)},
            "notes": str(notes),
            "rated_at_utc": _utc_now(),
        }
    )
    rated_count = sum(item["status"] == "rated" for item in payload["ratings"])
    payload["status"] = (
        "completed" if rated_count == len(payload["ratings"]) else "in_progress"
    )
    payload["updated_at_utc"] = _utc_now()
    _write_json_atomic(ratings_path, payload)
    return ratings_path


def ratings_summary(study_directory):
    payload = _read_json(Path(study_directory) / "ratings.json")
    rated = [entry for entry in payload["ratings"] if entry["status"] == "rated"]
    preference_counts = {
        preference: sum(entry["preferred"] == preference for entry in rated)
        for preference in PREFERENCES
    }
    return {
        "status": payload["status"],
        "rated_count": len(rated),
        "pair_count": len(payload["ratings"]),
        "preference_counts": preference_counts,
    }


def _validate_scores(scores, name, criteria=RATING_CRITERIA):
    if set(scores) != set(criteria):
        raise ValueError(
            f"{name} must contain exactly these criteria: {', '.join(criteria)}"
        )
    validated = {}
    for criterion in criteria:
        value = int(scores[criterion])
        if not 1 <= value <= 5:
            raise ValueError(f"{name}.{criterion} must be between 1 and 5")
        validated[criterion] = value
    return validated


def _validate_issues(issues, name, issue_tags=ISSUE_TAGS):
    issues = tuple(str(issue) for issue in issues)
    unknown = sorted(set(issues).difference(issue_tags))
    if unknown:
        raise ValueError(f"Unknown {name}: {', '.join(unknown)}")
    if len(set(issues)) != len(issues):
        raise ValueError(f"{name} must not contain duplicates")
    return issues


def _score_dict(args, prefix):
    return {
        criterion: getattr(args, f"{prefix}_{criterion}")
        for criterion in RATING_CRITERIA
    }


def _read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _write_json_atomic(path, payload):
    temporary_path = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        temporary_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def build_argument_parser():
    parser = argparse.ArgumentParser(description="Rate or summarize a blind control study.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    rate_parser = subparsers.add_parser("rate")
    rate_parser.add_argument("study_directory")
    rate_parser.add_argument("pair_index", type=int)
    rate_parser.add_argument("--preferred", choices=PREFERENCES, required=True)
    for variant in ("a", "b"):
        for criterion in RATING_CRITERIA:
            rate_parser.add_argument(
                f"--{variant}-{criterion.replace('_', '-')}",
                dest=f"{variant}_{criterion}",
                type=int,
                choices=range(1, 6),
                required=True,
            )
    rate_parser.add_argument("--issues-a", nargs="*", choices=ISSUE_TAGS, default=())
    rate_parser.add_argument("--issues-b", nargs="*", choices=ISSUE_TAGS, default=())
    rate_parser.add_argument("--notes", default="")

    show_parser = subparsers.add_parser("show")
    show_parser.add_argument("study_directory")
    return parser


def main():
    args = build_argument_parser().parse_args()
    if args.command == "show":
        print(json.dumps(ratings_summary(args.study_directory), ensure_ascii=False, indent=2))
        return 0
    rate_control_study_pair(
        args.study_directory,
        args.pair_index,
        preferred=args.preferred,
        scores_a=_score_dict(args, "a"),
        scores_b=_score_dict(args, "b"),
        issues_a=args.issues_a,
        issues_b=args.issues_b,
        notes=args.notes,
    )
    print(json.dumps(ratings_summary(args.study_directory), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
