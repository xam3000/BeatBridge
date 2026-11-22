"""Bind Phase 2 development audio to the committed P01 and September splits."""

import csv
import hashlib
import io
import json
from collections import defaultdict
from pathlib import Path
import subprocess

from src.evaluation.audit_exposure import CORPUS, PUBLIC, sha


FREEZE = "2a70dc185bbcf62806d5d426783e03f347c01dd6"
PROTOCOL = Path("docs/EVALUATION_PROTOCOL.md")
POPULATION = PUBLIC / "evaluation_population.json"
ELIGIBLE = CORPUS / "eligible_corpus_manifest.json"
ELIGIBLE_SHA256 = "7bcf4a79db6943d78bf53d60f5adbf273245f31c7378a3aaacf360df6dc95be3"
AUTHORITY = CORPUS / "split_authority.json"


def committed(path, commit=FREEZE):
    return subprocess.check_output(["git", "show", f"{commit}:{path.as_posix()}"])


def check_freeze():
    subprocess.run(["git", "merge-base", "--is-ancestor", FREEZE, "HEAD"], check=True)
    receipt = json.loads(committed(PUBLIC / "FREEZE_RECEIPT.json"))
    if receipt["freeze_status"] != "frozen_by_containing_commit":
        raise ValueError("P01 freeze receipt does not establish a freeze")
    for path, expected in receipt["files"].items():
        data = committed(Path(path))
        if len(data) != expected["bytes"] or hashlib.sha256(data).hexdigest() != expected["sha256"]:
            raise ValueError(f"P01 frozen blob mismatch at {path}")
    for path in (PROTOCOL, POPULATION):
        if committed(path, "HEAD") != committed(path) or subprocess.run(
            ["git", "diff", "--quiet", "HEAD", "--", path.as_posix()]
        ).returncode:
            raise ValueError(f"P01 binding changed at {path}")
    return receipt


def allocate(tracks, catalog, assignments, final_groups, final_shas):
    """Apply exclusions to entire P01 recording components before any audio I/O."""
    groups = {row["sha256"]: row["recording_group_id"] for row in catalog}
    historical_tests = {
        row["recording_group_id"] for row in catalog
        if any(tag.endswith("/test") for tag in row["direct_evidence"].split())
    }
    splits = defaultdict(set)
    for digest, split in assignments.items():
        splits[groups[digest]].add(split)
    included, excluded = [], []
    seen = set()
    for track in sorted(tracks, key=lambda row: row["sha256"]):
        digest = track["sha256"]
        group = groups[digest]
        split = assignments[digest]
        path = Path(track["path"])
        row = dict(sha256=digest, recording_group_id=group, split=split, path=path.as_posix())
        if path.is_absolute() or path.parts[0] != "musik" or ".." in path.parts:
            raise ValueError(f"Unexpected audio path: {path}")
        if digest in seen:
            raise ValueError(f"Duplicate SHA in September corpus: {digest}")
        seen.add(digest)
        reasons = []
        if group in final_groups or digest in final_shas or path.parts[1].casefold() == "erweiterung":
            reasons.append("p01_population_or_delivery")
        if group in historical_tests or split == "test":
            reasons.append("historical_test_component")
        if len(splits[group]) > 1:
            reasons.append("september_split_conflict")
        if reasons:
            excluded.append({**row, "reasons": reasons})
        elif split in ("train", "validation"):
            included.append(row)
        else:
            raise ValueError(f"Unrecognized development split: {split}")
    validate_groups(included)
    return included, excluded


def validate_groups(rows):
    by_identity = {}
    for row in rows:
        split = row["split"]
        if split not in ("train", "validation") or (
            split == "validation" and row.get("variant", "original") != "original"
        ):
            raise ValueError("Only training may contain augmented views")
        for field in ("sha256", "recording_group_id"):
            key = (field, row[field])
            if by_identity.setdefault(key, split) != split:
                raise ValueError(f"Cross-split identity: {key}")


def development_population():
    receipt = check_freeze()
    catalog = list(csv.DictReader(io.StringIO(committed(PUBLIC / "exposure_tracks.csv").decode("utf-8"))))
    population = json.loads(committed(POPULATION))
    final_groups = {row["recording_group_id"] for row in population["eligible_groups"]}
    final_shas = {row["sha256"] for row in population["eligible_groups"]}
    if len(final_groups) != len(final_shas) or len(final_groups) != receipt["eligible_recording_groups"]:
        raise ValueError("P01 population identity count is inconsistent")
    sources = json.loads(committed(PUBLIC / "exposure_sources.json"))
    # The receipt binds the catalog, which records all historical test assignments.
    authority = json.loads(AUTHORITY.read_bytes())
    eligible = json.loads(ELIGIBLE.read_bytes())
    expected_authority = next(
        row["sha256"] for row in sources["sources"].values()
        if row["path"] == AUTHORITY.as_posix()
    )
    if sha(AUTHORITY) != expected_authority:
        raise ValueError("September split authority differs from P01")
    if sha(ELIGIBLE) != ELIGIBLE_SHA256:
        raise ValueError("September BPM-eligible manifest has changed")
    if sha(CORPUS / "corpus_manifest.json") != eligible["source_corpus_manifest_sha256"]:
        raise ValueError("September eligible list has the wrong corpus source")
    assignments = {row["sha256"]: row["split"] for row in authority["track_assignments"]}
    tracks, excluded = allocate(eligible["tracks"], catalog, assignments, final_groups, final_shas)
    bindings = {
        "freeze_commit": FREEZE,
        "p01_bindings": {path.as_posix(): receipt["files"][path.as_posix()]["sha256"]
                         for path in (PROTOCOL, POPULATION, PUBLIC / "exposure_tracks.csv")},
        "september_split_sha256": expected_authority,
        "september_bpm_eligible_sha256": ELIGIBLE_SHA256,
    }
    return tracks, excluded, bindings
