"""Persist simple human ratings next to a rendered candidate batch."""

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import uuid


RATINGS_FORMAT_VERSION = 1
ISSUE_TAGS = (
    "rhythm",
    "phrasing",
    "harmony",
    "energy",
    "loudness",
    "vocals",
    "artifacts",
    "other",
)


def load_ratings(batch_directory):
    """Return a validated ratings payload, or an empty versioned payload."""
    batch_directory = Path(batch_directory)
    ratings_path = batch_directory / "ratings.json"
    if not ratings_path.is_file():
        return {
            "format_version": RATINGS_FORMAT_VERSION,
            "batch_manifest": "manifest.json",
            "ratings": [],
        }
    payload = json.loads(ratings_path.read_text(encoding="utf-8"))
    if payload.get("format_version") != RATINGS_FORMAT_VERSION:
        raise ValueError(
            f"Unsupported ratings format_version: {payload.get('format_version')}"
        )
    if not isinstance(payload.get("ratings"), list):
        raise ValueError("ratings.json must contain a ratings list")
    return payload


def save_rating(
    batch_directory,
    candidate_id,
    renderer,
    overall,
    *,
    issues=(),
    notes="",
):
    """Create or update one 1--5 rating for a rendered candidate variant."""
    batch_directory = Path(batch_directory)
    manifest_path = batch_directory / "manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"Batch manifest not found: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    overall = int(overall)
    if not 1 <= overall <= 5:
        raise ValueError("overall must be an integer from 1 to 5")
    # A single tag is commonly passed as ``issues="phrasing"`` (or as the
    # notebook equivalent ``issues=("phrasing")``).  Treat it as one tag;
    # otherwise iterating over it would validate individual characters.
    if isinstance(issues, str):
        issues = (issues,)
    issues = tuple(dict.fromkeys(str(issue) for issue in issues))
    unknown_issues = [issue for issue in issues if issue not in ISSUE_TAGS]
    if unknown_issues:
        raise ValueError(
            f"Unknown issue tag(s): {', '.join(unknown_issues)}; "
            f"allowed: {', '.join(ISSUE_TAGS)}"
        )

    matching_variant = next(
        (
            variant
            for variant in manifest.get("rendered_variants", [])
            if variant.get("candidate_id") == candidate_id
            and variant.get("renderer") == renderer
        ),
        None,
    )
    if matching_variant is None:
        raise ValueError(
            f"No rendered variant for candidate {candidate_id!r} and renderer {renderer!r}"
        )

    payload = load_ratings(batch_directory)
    rating = {
        "candidate_id": candidate_id,
        "renderer": renderer,
        "output_file": matching_variant["output_file"],
        "overall": overall,
        "issues": list(issues),
        "notes": str(notes),
        "updated_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    retained = [
        item
        for item in payload["ratings"]
        if not (
            item.get("candidate_id") == candidate_id
            and item.get("renderer") == renderer
        )
    ]
    payload["ratings"] = sorted(
        [*retained, rating],
        key=lambda item: (item["candidate_id"], item["renderer"]),
    )
    _write_json_atomic(batch_directory / "ratings.json", payload)
    return rating


def rating_summary(batch_directory):
    """Return compact rows suitable for display in a notebook or terminal."""
    payload = load_ratings(batch_directory)
    return [
        {
            "candidate_id": item["candidate_id"],
            "renderer": item["renderer"],
            "overall": item["overall"],
            "issues": ", ".join(item.get("issues", [])),
            "notes": item.get("notes", ""),
        }
        for item in payload["ratings"]
    ]


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


def build_argument_parser():
    parser = argparse.ArgumentParser(description="Rate one rendered BeatBridge variant.")
    parser.add_argument("batch_directory", help="Directory containing manifest.json")
    parser.add_argument("candidate_id")
    parser.add_argument("renderer")
    parser.add_argument("overall", type=int, help="Overall rating from 1 (bad) to 5 (good)")
    parser.add_argument("--issues", nargs="*", choices=ISSUE_TAGS, default=())
    parser.add_argument("--notes", default="")
    return parser


def main():
    args = build_argument_parser().parse_args()
    rating = save_rating(
        args.batch_directory,
        args.candidate_id,
        args.renderer,
        args.overall,
        issues=args.issues,
        notes=args.notes,
    )
    print(
        f"Saved rating {rating['overall']}/5 for "
        f"{rating['candidate_id']} ({rating['renderer']})"
    )


if __name__ == "__main__":
    main()
