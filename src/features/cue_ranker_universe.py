"""Sealed, complete Candidate-v2 universe for Cue-Ranker Dataset Format 3.

This module deliberately has no discovery fallback: a pre-filtered pair index
is required before any pair manifest can be opened.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import uuid

import numpy as np

from .variable_contract import geometry_for_length


CUE_RANKER_DATASET_FORMAT_VERSION = 3
CUE_RANKER_UNIVERSE_FORMAT_VERSION = 1
CUE_RANKER_PAIR_INDEX_FORMAT_VERSION = 1
CUE_RANKER_GROUP_NAMESPACE = "cue_ranker_group_v1"
CUE_RANKER_SAMPLING_VERSION = 1
_ALLOWED_SPLITS = ("train", "validation")
_QUANTILE_STRATA = (
    ("baseline_q00_q10", 0.10),
    ("baseline_q10_q40", 0.20),
    ("baseline_q40_q70", 0.30),
    ("baseline_q70_q90", 0.25),
    ("baseline_q90_q100", 0.15),
)
_UNSCORED_STRATUM = "baseline_unscored"


@dataclass(frozen=True)
class CueRankerUniverseResult:
    output_directory: Path
    manifest_path: Path
    group_counts: dict[str, int]
    candidate_counts: dict[str, int]


def canonical_json_sha256(value) -> str:
    return hashlib.sha256(_canonical_json(value)).hexdigest()


def write_cue_ranker_pair_index(pair_records, output_path, *, split_map, source_description="split_authorized_pair_index"):
    """Write an index containing only same-split train/validation pairs.

    ``pair_records`` must originate from the split-authorized batch producer.
    The helper intentionally does not inspect a batch root or discover files.
    """
    output_path = Path(output_path)
    if output_path.exists():
        raise FileExistsError(f"Pair-index output already exists: {output_path}")
    assignments = _normalise_split_map(split_map)
    retained = []
    for raw in pair_records:
        item = dict(raw)
        source_sha = _sha(item.get("source_audio_sha256"), "source_audio_sha256")
        target_sha = _sha(item.get("target_audio_sha256"), "target_audio_sha256")
        source_split, target_split = assignments.get(source_sha), assignments.get(target_sha)
        if source_split not in _ALLOWED_SPLITS or source_split != target_split:
            continue
        pair_path = item.get("pair_manifest_path")
        pair_sha = _sha(item.get("pair_manifest_sha256"), "pair_manifest_sha256")
        request_sha = _sha(item.get("candidate_request_config_sha256"), "candidate_request_config_sha256")
        generator = str(item.get("candidate_generator", ""))
        if not pair_path or not generator:
            raise ValueError("Pair-index record requires pair_manifest_path and candidate_generator")
        retained.append({
            "pair_manifest_path": str(pair_path),
            "pair_manifest_sha256": pair_sha,
            "source_audio_sha256": source_sha,
            "target_audio_sha256": target_sha,
            "split": source_split,
            "candidate_generator": generator,
            "candidate_request_config_sha256": request_sha,
        })
    retained.sort(key=lambda item: (item["split"], item["source_audio_sha256"], item["target_audio_sha256"], item["pair_manifest_path"]))
    if len({(p["source_audio_sha256"], p["target_audio_sha256"], p["pair_manifest_sha256"]) for p in retained}) != len(retained):
        raise ValueError("pair_index_duplicate_pair")
    payload = {
        "format_version": CUE_RANKER_PAIR_INDEX_FORMAT_VERSION,
        "source": str(source_description),
        "split_map_sha256": canonical_json_sha256(assignments),
        "pairs": retained,
    }
    _atomic_json_write(output_path, payload)
    return output_path


def build_cue_ranker_universe(pair_index_path, output_directory, *, split_map, sampling_seed=20260825):
    """Build complete train/validation Candidate-v2 indexes without test I/O."""
    pair_index_path, output_directory = Path(pair_index_path), Path(output_directory)
    if output_directory.exists():
        raise FileExistsError(f"Universe output already exists: {output_directory}")
    assignments = _normalise_split_map(split_map)
    pair_index = _load_verified_pair_index(pair_index_path, assignments)
    entries_by_split = {split: [] for split in _ALLOWED_SPLITS}
    groups_by_split = {split: [] for split in _ALLOWED_SPLITS}
    for pair in pair_index["pairs"]:
        split = pair["split"]
        # This is the test-I/O guard: only verified pair-index rows reach here.
        payload = _read_verified_json(Path(pair["pair_manifest_path"]), pair["pair_manifest_sha256"])
        candidates = _validated_pair_candidates(payload, pair)
        group_id, member_identities = _group_id(pair, candidates)
        baseline = _baseline_scores(payload)
        records = []
        for candidate, identity in zip(candidates, member_identities, strict=True):
            record = _candidate_record(candidate, identity, pair, group_id, baseline.get(candidate["candidate_id"]))
            records.append(record)
        _assign_sampling(records, group_id=group_id, seed=int(sampling_seed))
        start = len(entries_by_split[split])
        for local_index, record in enumerate(records):
            record["row_id"] = start + local_index
            entries_by_split[split].append(record)
        groups_by_split[split].append({
            "group_id": group_id,
            "split": split,
            "source_audio_sha256": pair["source_audio_sha256"],
            "target_audio_sha256": pair["target_audio_sha256"],
            "candidate_generator": pair["candidate_generator"],
            "candidate_request_config_sha256": pair["candidate_request_config_sha256"],
            "pair_manifest_path": pair["pair_manifest_path"],
            "pair_manifest_sha256": pair["pair_manifest_sha256"],
            "universe_size": len(records),
            "label_sample_size": sum(bool(row["label_selected"]) for row in records),
            "member_row_ids": list(range(start, start + len(records))),
            "sampling": _sampling_summary(records, int(sampling_seed)),
        })
    temporary = output_directory.with_name(f".{output_directory.name}.{uuid.uuid4().hex}.tmp")
    temporary.mkdir(parents=True)
    try:
        files = {}
        for split in _ALLOWED_SPLITS:
            records, groups = entries_by_split[split], groups_by_split[split]
            groups.sort(key=lambda group: group["group_id"])
            records.sort(key=lambda row: (row["group_id"], row["candidate_id"], row["candidate_identity_sha256"]))
            for row_id, row in enumerate(records):
                row["row_id"] = row_id
            offsets, member_rows = _ragged_rows(groups, records)
            groups_path = temporary / "groups" / f"{split}.jsonl"
            _write_jsonl(groups_path, groups)
            candidates_path = temporary / "index" / f"{split}-candidates-00000.npz"
            ragged_path = temporary / "index" / f"{split}-ragged-groups.npz"
            _write_record_npz(candidates_path, records)
            _write_ragged_npz(ragged_path, groups, offsets, member_rows)
            for name, path, kind in (
                (f"{split}_groups", groups_path, "jsonl"),
                (f"{split}_candidates", candidates_path, "npz"),
                (f"{split}_ragged_groups", ragged_path, "npz"),
            ):
                files[name] = _file_record(path, temporary, kind)
        manifest = {
            "format_version": CUE_RANKER_UNIVERSE_FORMAT_VERSION,
            "dataset_format_version": CUE_RANKER_DATASET_FORMAT_VERSION,
            "pair_index": _file_record(pair_index_path, pair_index_path.parent, "json"),
            "pair_index_sha256": _file_sha256(pair_index_path),
            "split_map_sha256": canonical_json_sha256(assignments),
            "candidate_contract": {"format_version": 2, "generator": "bar_grid_v2_length_specific", "approximate_grid_policy": "reject"},
            "sampling": {"version": CUE_RANKER_SAMPLING_VERSION, "seed": int(sampling_seed), "hard_negative_policy": "lowest_baseline_quantile_as_deterministic_listwise_anchor_no_candidatewise_mining_v1"},
            "counts": {split: {"groups": len(groups_by_split[split]), "candidates": len(entries_by_split[split]), "label_selected": sum(bool(row["label_selected"]) for row in entries_by_split[split])} for split in _ALLOWED_SPLITS},
            "files": files,
            "test": {"state": "sealed_not_materialized"},
        }
        _atomic_json_write(temporary / "manifest.json", manifest)
        os.replace(temporary, output_directory)
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise
    return CueRankerUniverseResult(output_directory, output_directory / "manifest.json", {s: len(groups_by_split[s]) for s in _ALLOWED_SPLITS}, {s: len(entries_by_split[s]) for s in _ALLOWED_SPLITS})


def load_cue_ranker_universe_rows(universe_directory, split):
    if split not in _ALLOWED_SPLITS:
        raise ValueError("Cue-Ranker only exposes train and validation")
    root = Path(universe_directory)
    manifest = _read_json(root / "manifest.json")
    if manifest.get("format_version") != CUE_RANKER_UNIVERSE_FORMAT_VERSION:
        raise ValueError("Unsupported Cue-Ranker universe format")
    file_info = manifest["files"][f"{split}_candidates"]
    path = root / file_info["path"]
    _verify_file(path, file_info["sha256"])
    with np.load(path, allow_pickle=False) as payload:
        return [json.loads(value) for value in payload["row_json"].tolist()]


def _load_verified_pair_index(path, assignments):
    if not path.is_file():
        raise ValueError("sealed_test_pair_index_required")
    payload = _read_json(path)
    if int(payload.get("format_version", -1)) != CUE_RANKER_PAIR_INDEX_FORMAT_VERSION:
        raise ValueError("sealed_test_pair_index_required")
    if payload.get("split_map_sha256") != canonical_json_sha256(assignments):
        raise ValueError("pair_index_split_map_sha256_mismatch")
    pairs = payload.get("pairs")
    if not isinstance(pairs, list):
        raise ValueError("pair_index_pairs_missing")
    for pair in pairs:
        if pair.get("split") not in _ALLOWED_SPLITS:
            raise ValueError("pair_index_contains_non_materializable_split")
        source, target = _sha(pair.get("source_audio_sha256"), "source_audio_sha256"), _sha(pair.get("target_audio_sha256"), "target_audio_sha256")
        if assignments.get(source) != pair["split"] or assignments.get(target) != pair["split"]:
            raise ValueError("pair_index_split_isolation_violation")
        _sha(pair.get("pair_manifest_sha256"), "pair_manifest_sha256")
        _sha(pair.get("candidate_request_config_sha256"), "candidate_request_config_sha256")
    return payload


def _validated_pair_candidates(payload, pair):
    generation = payload.get("candidate_generation", {})
    if generation.get("approximate_grid_policy") != "reject":
        raise ValueError("candidate_grid_policy_not_reject")
    candidates = []
    identities = {}
    for candidate in generation.get("candidates", []):
        _validate_candidate(candidate, pair)
        candidate_id = str(candidate["candidate_id"])
        identity = canonical_json_sha256(_full_member_identity(candidate))
        previous = identities.get(candidate_id)
        if previous is not None and previous != identity:
            raise ValueError("candidate_id_collision")
        if previous is None:
            identities[candidate_id] = identity
            candidates.append(candidate)
    if not candidates:
        raise ValueError("pair_has_no_accepted_v2_candidates")
    return sorted(candidates, key=lambda item: (str(item["candidate_id"]), canonical_json_sha256(_full_member_identity(item))))


def _validate_candidate(candidate, pair):
    if int(candidate.get("format_version", -1)) != 2 or candidate.get("generator") != "bar_grid_v2_length_specific":
        raise ValueError("candidate_v2_contract_required")
    if candidate.get("filter_status") != "accepted":
        raise ValueError("candidate_not_accepted")
    if _sha(candidate.get("source_track", {}).get("sha256"), "candidate_source_audio_sha256") != pair["source_audio_sha256"] or _sha(candidate.get("target_track", {}).get("sha256"), "candidate_target_audio_sha256") != pair["target_audio_sha256"]:
        raise ValueError("candidate_pair_audio_sha_mismatch")
    geometry = geometry_for_length(candidate.get("transition_length_bars"))
    if int(candidate.get("transition_length_beats", -1)) != geometry.transition_length_beats:
        raise ValueError("candidate_transition_geometry_mismatch")
    for side in ("source", "target"):
        cue = candidate.get(f"{side}_cutpoint", {})
        if int(cue.get("beats_in_bar", -1)) != 4 or int(cue.get("count_in_bar", -1)) != 1:
            raise ValueError("candidate_non_4_4_downbeat")
        grid = candidate.get(f"{side}_grid") or {}
        if grid.get("fallback_used") is not False or not grid.get("beat_grid_sha256"):
            raise ValueError("candidate_grid_provenance_rejected")
        _sha(grid["beat_grid_sha256"], f"{side}_grid_sha256")


def _full_member_identity(candidate):
    return {
        "generator": candidate["generator"],
        "source_audio_sha256": candidate["source_track"]["sha256"].lower(),
        "target_audio_sha256": candidate["target_track"]["sha256"].lower(),
        "source_cutpoint": candidate["source_cutpoint"],
        "target_cutpoint": candidate["target_cutpoint"],
        "transition_length_bars": int(candidate["transition_length_bars"]),
        "transition_length_beats": int(candidate["transition_length_beats"]),
        "source_grid_sha256": candidate["source_grid"]["beat_grid_sha256"].lower(),
        "target_grid_sha256": candidate["target_grid"]["beat_grid_sha256"].lower(),
    }


def _group_id(pair, candidates):
    identities = [canonical_json_sha256(_full_member_identity(candidate)) for candidate in candidates]
    member_set_sha = canonical_json_sha256(sorted(identities))
    material = "|".join((CUE_RANKER_GROUP_NAMESPACE, pair["source_audio_sha256"], pair["target_audio_sha256"], pair["candidate_generator"], pair["candidate_request_config_sha256"], member_set_sha))
    return hashlib.sha256(material.encode("utf-8")).hexdigest(), identities


def _baseline_scores(payload):
    scores = {}
    for item in payload.get("candidate_ranking", {}).get("scores", []):
        candidate_id = item.get("candidate_id")
        value = item.get("total_score")
        if candidate_id is None or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
            continue
        scores[str(candidate_id)] = float(value)
    return scores


def _candidate_record(candidate, identity_sha, pair, group_id, baseline_score):
    geometry = geometry_for_length(candidate["transition_length_bars"])
    return {
        "group_id": group_id,
        "candidate_id": str(candidate["candidate_id"]),
        "candidate_identity_sha256": identity_sha,
        "candidate": candidate,
        "source_audio_sha256": pair["source_audio_sha256"],
        "target_audio_sha256": pair["target_audio_sha256"],
        "pair_manifest_path": pair["pair_manifest_path"],
        "pair_manifest_sha256": pair["pair_manifest_sha256"],
        "candidate_request_config_sha256": pair["candidate_request_config_sha256"],
        "transition_length_bars": geometry.transition_length_bars,
        "transition_length_beats": geometry.transition_length_beats,
        "sequence_length": geometry.sequence_length,
        "length_condition": float(geometry.length_condition),
        "baseline_status": "scored" if baseline_score is not None else "unscored",
        "feature_baseline_v3_score": baseline_score,
        "teacher_status": "unlabeled",
    }


def _assign_sampling(rows, *, group_id, seed):
    scored = sorted((row for row in rows if row["baseline_status"] == "scored"), key=lambda item: (float(item["feature_baseline_v3_score"]), item["candidate_id"], item["candidate_identity_sha256"]))
    buckets = {name: [] for name, _ in _QUANTILE_STRATA}
    for index, row in enumerate(scored):
        fraction = index / len(scored)
        if fraction < .1: name = _QUANTILE_STRATA[0][0]
        elif fraction < .4: name = _QUANTILE_STRATA[1][0]
        elif fraction < .7: name = _QUANTILE_STRATA[2][0]
        elif fraction < .9: name = _QUANTILE_STRATA[3][0]
        else: name = _QUANTILE_STRATA[4][0]
        buckets[name].append(row)
    buckets[_UNSCORED_STRATUM] = [row for row in rows if row["baseline_status"] == "unscored"]
    n = len(rows)
    slots = min(n, min(512, max(128, math.ceil(16 * math.sqrt(n)))))
    quotas = _allocate_quotas(buckets, slots)
    for stratum, members in buckets.items():
        q = quotas.get(stratum, 0)
        selected = {id(item) for item in sorted(members, key=lambda item: _priority(seed, group_id, stratum, item["candidate_id"]))[:q]}
        probability = q / len(members) if members else 0.0
        for row in members:
            row["sampling_stratum"] = stratum
            row["stratum_size"] = len(members)
            row["stratum_quota"] = q
            row["sampling_seed"] = seed
            row["p_inclusion"] = probability if id(row) in selected else 0.0
            row["label_selected"] = id(row) in selected
            row["hard_negative_anchor"] = (
                stratum == _QUANTILE_STRATA[0][0] and row["label_selected"]
            )


def _allocate_quotas(buckets, slots):
    active = [(name, weight) for name, weight in _QUANTILE_STRATA if buckets[name]]
    if buckets[_UNSCORED_STRATUM]:
        active.append((_UNSCORED_STRATUM, .05))
    if not active:
        return {}
    weights = {name: weight for name, weight in active}
    total = sum(weights.values())
    raw = {name: slots * weight / total for name, weight in weights.items()}
    quotas = {name: min(len(buckets[name]), int(math.floor(raw[name]))) for name in weights}
    remaining = slots - sum(quotas.values())
    while remaining:
        eligible = [name for name in weights if quotas[name] < len(buckets[name])]
        if not eligible: break
        name = sorted(eligible, key=lambda key: (-(raw[key] - math.floor(raw[key])), key))[0]
        quotas[name] += 1
        remaining -= 1
    return quotas


def _sampling_summary(rows, seed):
    strata = {}
    for row in rows:
        item = strata.setdefault(row["sampling_stratum"], {"size": row["stratum_size"], "quota": row["stratum_quota"], "selected": 0})
        item["selected"] += int(bool(row["label_selected"]))
    return {"seed": seed, "strata": strata}


def _ragged_rows(groups, records):
    by_group = {}
    for row in records: by_group.setdefault(row["group_id"], []).append(int(row["row_id"]))
    offsets, members = [0], []
    for group in groups:
        ids = by_group[group["group_id"]]
        group["member_row_ids"] = ids
        members.extend(ids); offsets.append(len(members))
    return offsets, members


def _priority(seed, group_id, stratum, candidate_id):
    return hashlib.sha256(f"{seed}|{group_id}|{stratum}|{candidate_id}".encode("utf-8")).hexdigest()


def _normalise_split_map(split_map):
    if isinstance(split_map, (str, Path)):
        split_map = _read_json(Path(split_map))
    if isinstance(split_map, dict) and "track_assignments" in split_map:
        value = split_map["track_assignments"]
        if isinstance(value, list): split_map = {item.get("sha256", item.get("audio_sha256")): item.get("split") for item in value}
    if not isinstance(split_map, dict): raise ValueError("split_map must be a mapping or split-authority JSON")
    output = {}
    for key, value in split_map.items():
        if value not in {"train", "validation", "test"}: raise ValueError("split_map contains unsupported split")
        output[_sha(key, "split_audio_sha256")] = value
    return dict(sorted(output.items()))


def _write_record_npz(path, records):
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(path, row_json=np.asarray([json.dumps(row, sort_keys=True, separators=(",", ":")) for row in records], dtype=str))


def _write_ragged_npz(path, groups, offsets, members):
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(path, group_ids=np.asarray([group["group_id"] for group in groups], dtype=str), group_offsets=np.asarray(offsets, dtype=np.int64), member_row_ids=np.asarray(members, dtype=np.int64))


def _write_jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n" for row in rows), encoding="utf-8")


def _atomic_json_write(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        temporary.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _read_verified_json(path, expected_sha):
    _verify_file(path, expected_sha)
    return _read_json(path)


def _verify_file(path, expected_sha):
    if not path.is_file(): raise FileNotFoundError(path)
    if _file_sha256(path) != expected_sha: raise ValueError(f"sha256_mismatch:{path}")


def _file_record(path, relative_to, kind):
    return {"path": str(Path(path).relative_to(relative_to)).replace("\\", "/"), "sha256": _file_sha256(path), "bytes": Path(path).stat().st_size, "kind": kind}


def _read_json(path): return json.loads(Path(path).read_text(encoding="utf-8"))
def _canonical_json(value): return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
def _file_sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""): digest.update(block)
    return digest.hexdigest()
def _sha(value, name):
    value = str(value or "").lower()
    if len(value) != 64 or any(char not in "0123456789abcdef" for char in value): raise ValueError(f"{name} must be a SHA-256 hex digest")
    return value
