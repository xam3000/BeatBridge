"""Versioned Feature Protocol 1 dataset export with track-disjoint splits."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import random
import shutil
import uuid

import numpy as np
from src.tempo.cue_alignment import CUE_ALIGNMENT, CueAlignmentError, check_feature_cue

from src.dataset import (
    DEFAULT_TRACK_EXCLUSIONS_PATH,
    is_track_excluded,
    load_track_exclusions,
)
from src.features.contract import (
    FEATURE_DIMENSION,
    FEATURE_PROTOCOL_VERSION,
    GLOBAL_FEATURE_DIMENSION,
    SEQUENCE_LENGTH,
    feature_schema,
)
from src.features.extract_track import (
    DEFAULT_ANALYSIS_ROOT,
    DEFAULT_FEATURE_CACHE_ROOT,
    extract_or_load_track_features,
    normalization_stats_from_training_artifacts,
)
from src.features.global_pair import (
    GLOBAL_PAIR_EXTRACTOR_VERSION,
    build_global_pair_features,
)
from src.features.vocal import (
    DEFAULT_ROFORMER_MODEL,
    DEFAULT_VOCAL_BACKEND,
)
from src.pipeline import DEFAULT_SAMPLE_RATE
from src.tempo.coordinates import aligned_cue_sample


DATASET_FORMAT_VERSION = 1
SPLIT_POLICY_VERSION = 1
DEFAULT_SPLIT_SEED = 20260731
DEFAULT_TOP_K_PER_PAIR = 3
SPLIT_NAMES = ("train", "validation", "test")
PROJECT_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class SplitConfig:
    """Deterministic track-level split proportions and search settings."""

    train: float = 0.70
    validation: float = 0.15
    test: float = 0.15
    seed: int = DEFAULT_SPLIT_SEED
    search_attempts: int = 4096

    def __post_init__(self):
        ratios = self.ratios
        if any(not math.isfinite(value) or value < 0 for value in ratios.values()):
            raise ValueError("Split ratios must be finite and non-negative")
        if not math.isclose(sum(ratios.values()), 1.0, abs_tol=1e-9):
            raise ValueError("Split ratios must sum to 1")
        if self.train <= 0:
            raise ValueError("The training split must be greater than 0")
        if int(self.search_attempts) <= 0:
            raise ValueError("search_attempts must be greater than 0")

    @property
    def ratios(self):
        return {
            "train": float(self.train),
            "validation": float(self.validation),
            "test": float(self.test),
        }

    def to_dict(self):
        return {
            "policy_version": SPLIT_POLICY_VERSION,
            "ratios": self.ratios,
            "seed": int(self.seed),
            "search_attempts": int(self.search_attempts),
            "identity": "audio_sha256",
            "cross_split_pair_policy": "discard",
        }


@dataclass(frozen=True)
class CandidateRecord:
    """One selected four-bar candidate before split filtering."""

    example_id: str
    candidate: dict
    candidate_rank: int
    candidate_score: float
    pair_manifest_path: Path
    pair_manifest_sha256: str

    @property
    def source_hash(self):
        return str(self.candidate["source_track"]["sha256"]).lower()

    @property
    def target_hash(self):
        return str(self.candidate["target_track"]["sha256"]).lower()


@dataclass(frozen=True)
class DatasetExportResult:
    output_directory: Path
    manifest_path: Path
    example_count: int
    split_counts: dict


def assign_track_disjoint_splits(track_hashes, pair_weights, *, config=None):
    """Assign every audio hash to exactly one split using a seeded graph search."""
    config = config or SplitConfig()
    tracks = tuple(sorted({str(value).lower() for value in track_hashes}))
    if not tracks:
        raise ValueError("At least one track is required for splitting")
    active_splits = [name for name in SPLIT_NAMES if config.ratios[name] > 0]
    if len(tracks) < len(active_splits):
        raise ValueError(
            f"At least {len(active_splits)} tracks are required for the active splits"
        )
    sizes = _split_sizes(len(tracks), config.ratios)
    normalised_weights = {
        (str(left).lower(), str(right).lower()): int(weight)
        for (left, right), weight in pair_weights.items()
        if int(weight) > 0
    }
    rng = random.Random(int(config.seed))
    best_assignment = None
    best_key = None
    for attempt in range(int(config.search_attempts)):
        permutation = list(tracks)
        if attempt:
            rng.shuffle(permutation)
        assignment = {}
        offset = 0
        for split_name in SPLIT_NAMES:
            end = offset + sizes[split_name]
            assignment.update({track: split_name for track in permutation[offset:end]})
            offset = end
        retained = _retained_weights(assignment, normalised_weights)
        nonempty = sum(retained[name] > 0 for name in active_splits)
        retained_total = sum(retained.values())
        if retained_total:
            ratio_error = sum(
                abs(retained[name] / retained_total - config.ratios[name])
                for name in active_splits
            )
        else:
            ratio_error = float("inf")
        key = (nonempty, -ratio_error, retained_total)
        if best_key is None or key > best_key:
            best_key = key
            best_assignment = assignment
    retained = _retained_weights(best_assignment, normalised_weights)
    missing = [name for name in active_splits if retained[name] == 0]
    if missing:
        raise ValueError(
            "Could not create non-empty track-disjoint example splits for: "
            + ", ".join(missing)
        )
    return best_assignment


def export_feature_dataset(
    source_manifest,
    output_directory,
    *,
    cache_root=DEFAULT_FEATURE_CACHE_ROOT,
    analysis=None,
    analysis_root=DEFAULT_ANALYSIS_ROOT,
    sample_rate=DEFAULT_SAMPLE_RATE,
    top_k_per_pair=DEFAULT_TOP_K_PER_PAIR,
    transition_bars=4,
    split_config=None,
    vocal_backend=DEFAULT_VOCAL_BACKEND,
    vocal_model=DEFAULT_ROFORMER_MODEL,
    track_exclusions_path=DEFAULT_TRACK_EXCLUSIONS_PATH,
    minimum_bpm=None,
    maximum_bpm=None,
    max_pairs=None,
    track_feature_loader=None,
):
    """Export model inputs selected from one regular or multi-batch manifest."""
    source_manifest = Path(source_manifest)
    output_directory = Path(output_directory)
    if not source_manifest.is_file():
        raise FileNotFoundError(f"Source manifest does not exist: {source_manifest}")
    if output_directory.exists():
        raise FileExistsError(f"Dataset output path already exists: {output_directory}")
    if int(top_k_per_pair) <= 0:
        raise ValueError("top_k_per_pair must be greater than 0")
    if int(transition_bars) <= 0:
        raise ValueError("transition_bars must be greater than 0")
    if max_pairs is not None and int(max_pairs) <= 0:
        raise ValueError("max_pairs must be greater than 0")
    _validate_bpm_bounds(minimum_bpm, maximum_bpm)
    split_config = split_config or SplitConfig()
    track_feature_loader = track_feature_loader or extract_or_load_track_features

    pair_manifests = _discover_pair_manifests(source_manifest)
    if max_pairs is not None:
        pair_manifests = pair_manifests[: int(max_pairs)]
    records = _select_candidate_records(
        pair_manifests,
        top_k_per_pair=int(top_k_per_pair),
        transition_bars=int(transition_bars),
    )
    exclusions = load_track_exclusions(track_exclusions_path)
    selected_before_exclusions = len(records)
    records, excluded_records = _apply_training_exclusions(records, exclusions)
    records, bpm_excluded_records = _apply_bpm_filter(
        records,
        minimum_bpm=minimum_bpm,
        maximum_bpm=maximum_bpm,
    )
    if not records:
        raise ValueError("No selected candidates remain after training and BPM exclusions")

    tracks = _track_catalog(records)
    pair_weights = _pair_weights(records)
    assignments = assign_track_disjoint_splits(
        tracks,
        pair_weights,
        config=split_config,
    )
    retained_records = [
        record
        for record in records
        if assignments[record.source_hash] == assignments[record.target_hash]
    ]
    if not retained_records:
        raise ValueError("Track-disjoint filtering retained no candidates")

    prepared = []
    tempo_rejections = []
    artifact_cache = {}
    for record in retained_records:
        candidate = record.candidate
        source_artifact = _load_artifact(
            candidate["source_track"],
            target_bpm=None,
            artifact_cache=artifact_cache,
            loader=track_feature_loader,
            cache_root=cache_root,
            analysis=analysis,
            analysis_root=analysis_root,
            sample_rate=sample_rate,
            vocal_backend=vocal_backend,
            vocal_model=vocal_model,
        )
        target_artifact = _load_artifact(
            candidate["target_track"],
            target_bpm=float(candidate["source_bpm"]),
            artifact_cache=artifact_cache,
            loader=track_feature_loader,
            cache_root=cache_root,
            analysis=analysis,
            analysis_root=analysis_root,
            sample_rate=sample_rate,
            vocal_backend=vocal_backend,
            vocal_model=vocal_model,
        )
        cue_rate = candidate.get("cue_sample_rate", sample_rate)
        source_cue = round(candidate["source_cutpoint"]["sample"] * sample_rate / cue_rate)
        target_cue = aligned_cue_sample(
            round(candidate["target_cutpoint"]["sample"] * sample_rate / cue_rate),
            original_bpm=candidate["target_bpm"],
            aligned_bpm=candidate["source_bpm"],
        )
        try:
            check_feature_cue(source_artifact, target_artifact, source_cue, target_cue,
                              int(candidate["transition_length_bars"]) * 4, sample_rate)
        except CueAlignmentError as error:
            tempo_rejections.append(dict(example_id=record.example_id, exclusion_type=CUE_ALIGNMENT, reason=str(error)))
            continue
        prepared.append((record, source_artifact, target_artifact, source_cue, target_cue))

    training_artifacts = []
    seen_training_artifacts = set()
    for record, source_artifact, target_artifact, _, _ in prepared:
        if assignments[record.source_hash] != "train":
            continue
        for artifact in (source_artifact, target_artifact):
            key = str(artifact.cache_directory)
            if key not in seen_training_artifacts:
                seen_training_artifacts.add(key)
                training_artifacts.append(artifact)
    if not training_artifacts:
        raise ValueError(f"No training cues available for normalization after the tempo check "
                         f"({len(tempo_rejections)} candidates rejected)")
    stats_id = _normalization_stats_id(training_artifacts, assignments)
    normalization = normalization_stats_from_training_artifacts(
        training_artifacts,
        stats_id=stats_id,
    )

    split_payloads = {name: [] for name in SPLIT_NAMES}
    example_metadata = []
    for record, source_artifact, target_artifact, source_cue, target_cue in prepared:
        split_name = assignments[record.source_hash]
        features_a = source_artifact.model_window(
            source_cue,
            role="source",
            normalization=normalization,
        )
        features_b = target_artifact.model_window(
            target_cue,
            role="target",
            normalization=normalization,
        )
        global_features = build_global_pair_features(
            features_a,
            features_b,
            bpm_a=float(record.candidate["source_bpm"]),
            bpm_b=float(record.candidate["target_bpm"]),
            artifact_a=source_artifact,
            artifact_b=target_artifact,
            cue_sample_a=source_cue,
            cue_sample_b=target_cue,
        )
        split_payloads[split_name].append(
            (record.example_id, features_a, features_b, global_features)
        )
        example_metadata.append(
            _example_metadata(
                record,
                split_name,
                source_artifact,
                target_artifact,
                source_cue,
                target_cue,
                analysis_root,
            )
        )

    dataset_config = {
        "waveform_alignment": CUE_ALIGNMENT,
        "format_version": DATASET_FORMAT_VERSION,
        "feature_protocol_version": FEATURE_PROTOCOL_VERSION,
        "global_pair_extractor_version": GLOBAL_PAIR_EXTRACTOR_VERSION,
        "transition_bars": int(transition_bars),
        "top_k_per_pair": int(top_k_per_pair),
        "sample_rate": int(sample_rate),
        "vocal_backend": str(vocal_backend),
        "vocal_model": str(vocal_model) if vocal_backend != "disabled" else None,
        "bpm_filter": {
            "minimum_bpm": None if minimum_bpm is None else float(minimum_bpm),
            "maximum_bpm": None if maximum_bpm is None else float(maximum_bpm),
            "bounds_inclusive": True,
        },
        "split": split_config.to_dict(),
    }
    dataset_id = hashlib.sha256(
        json.dumps(
            {
                "config": dataset_config,
                "examples": [item["example_id"] for item in example_metadata],
                "source_manifests": [_file_sha256(path) for path in pair_manifests],
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()[:20]
    split_counts = {name: len(split_payloads[name]) for name in SPLIT_NAMES}
    manifest = {
        **dataset_config,
        "dataset_id": dataset_id,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_manifest": str(source_manifest),
        "source_manifest_sha256": _file_sha256(source_manifest),
        "pair_manifests": [
            {"path": str(path), "sha256": _file_sha256(path)} for path in pair_manifests
        ],
        "feature_schema": feature_schema(),
        "normalization": {
            "stats_id": normalization.stats_id,
            "fit_scope": "training_tracks_only",
            "spectral_flux_log1p_p99": normalization.spectral_flux_log1p_p99,
            "onset_strength_log1p_p99": normalization.onset_strength_log1p_p99,
        },
        "selection": {
            "selected_before_exclusions": selected_before_exclusions,
            "excluded_by_training_policy": len(excluded_records),
            "excluded_by_bpm_filter": len(bpm_excluded_records),
            "discarded_cross_split": len(records) - len(retained_records),
            "excluded_by_tempo_grid": len(tempo_rejections),
            "exported": len(prepared),
        },
        "excluded_examples": excluded_records + bpm_excluded_records + tempo_rejections,
        "track_assignments": [
            {
                "sha256": track_hash,
                "path": tracks[track_hash],
                "split": assignments[track_hash],
            }
            for track_hash in sorted(tracks)
        ],
        "split_counts": split_counts,
        "files": {},
    }

    temporary_directory = output_directory.with_name(
        f".{output_directory.name}.{uuid.uuid4().hex}.tmp"
    )
    temporary_directory.mkdir(parents=True)
    try:
        for split_name in SPLIT_NAMES:
            file_path = temporary_directory / f"{split_name}.npz"
            _write_split(file_path, split_payloads[split_name])
            manifest["files"][split_name] = {
                "path": file_path.name,
                "sha256": _file_sha256(file_path),
                "example_count": split_counts[split_name],
            }
        examples_path = temporary_directory / "examples.jsonl"
        examples_path.write_text(
            "".join(
                json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n"
                for item in example_metadata
            ),
            encoding="utf-8",
        )
        manifest["files"]["examples"] = {
            "path": examples_path.name,
            "sha256": _file_sha256(examples_path),
            "example_count": len(example_metadata),
        }
        manifest_path = temporary_directory / "manifest.json"
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        output_directory.parent.mkdir(parents=True, exist_ok=True)
        os.replace(temporary_directory, output_directory)
    except Exception:
        shutil.rmtree(temporary_directory, ignore_errors=True)
        raise
    return DatasetExportResult(
        output_directory=output_directory,
        manifest_path=output_directory / "manifest.json",
        example_count=len(example_metadata),
        split_counts=split_counts,
    )


def _discover_pair_manifests(source_manifest):
    payload = _read_json(source_manifest)
    if "candidate_generation" in payload:
        return (source_manifest.resolve(),)
    paths = []
    for source in payload.get("sources", ()):
        for pair in source.get("pairs", ()):
            if pair.get("status") != "completed" or not pair.get("manifest_path"):
                continue
            path = (source_manifest.parent / pair["manifest_path"]).resolve()
            if not path.is_file():
                raise FileNotFoundError(f"Pair manifest does not exist: {path}")
            paths.append(path)
    if not paths:
        raise ValueError("Manifest contains no completed pair manifests")
    return tuple(paths)


def _manifest_cue_rate(payload):
    if "cue_sample_rate" in payload:
        return int(payload["cue_sample_rate"])
    rates = {int(v["sample_rate"]) for v in payload.get("rendered_variants", []) if "sample_rate" in v}
    if len(rates) > 1:
        raise ValueError("Conflicting sample rates in historical pair manifest")
    return next(iter(rates), None)


def _select_candidate_records(pair_manifests, *, top_k_per_pair, transition_bars):
    records = []
    seen_examples = set()
    for manifest_path in pair_manifests:
        payload = _read_json(manifest_path)
        cue_rate = _manifest_cue_rate(payload)
        candidates = {
            item["candidate_id"]: (dict(item, cue_sample_rate=cue_rate) if cue_rate else item)
            for item in payload["candidate_generation"]["candidates"]
        }
        selected = 0
        for score in sorted(
            payload["candidate_ranking"]["scores"],
            key=lambda item: (int(item["rank"]), item["candidate_id"]),
        ):
            candidate = candidates.get(score["candidate_id"])
            if candidate is None or int(candidate["transition_length_bars"]) != transition_bars:
                continue
            example_id = _example_id(candidate)
            if example_id in seen_examples:
                continue
            seen_examples.add(example_id)
            records.append(
                CandidateRecord(
                    example_id=example_id,
                    candidate=candidate,
                    candidate_rank=int(score["rank"]),
                    candidate_score=float(score["total_score"]),
                    pair_manifest_path=manifest_path,
                    pair_manifest_sha256=_file_sha256(manifest_path),
                )
            )
            selected += 1
            if selected >= top_k_per_pair:
                break
    if not records:
        raise ValueError(
            f"No ranked {transition_bars}-bar candidates found in the source manifests"
        )
    return records


def _apply_training_exclusions(records, exclusions):
    allowed = []
    rejected = []
    for record in records:
        matches = []
        for role in ("source", "target"):
            track = record.candidate[f"{role}_track"]
            exclusion = is_track_excluded(
                track["path"],
                sha256=track["sha256"],
                scope="training",
                exclusions=exclusions,
            )
            if exclusion is not None:
                matches.append({"role": role, "policy": exclusion.to_dict()})
        if matches:
            rejected.append({"example_id": record.example_id, "matches": matches})
        else:
            allowed.append(record)
    return allowed, rejected


def _validate_bpm_bounds(minimum_bpm, maximum_bpm):
    for name, value in (("minimum_bpm", minimum_bpm), ("maximum_bpm", maximum_bpm)):
        if value is not None and (not math.isfinite(float(value)) or float(value) <= 0):
            raise ValueError(f"{name} must be finite and greater than 0")
    if (
        minimum_bpm is not None
        and maximum_bpm is not None
        and float(minimum_bpm) > float(maximum_bpm)
    ):
        raise ValueError("minimum_bpm must be less than or equal to maximum_bpm")


def _apply_bpm_filter(records, *, minimum_bpm=None, maximum_bpm=None):
    allowed = []
    rejected = []
    for record in records:
        source_bpm = float(record.candidate["source_bpm"])
        target_bpm = float(record.candidate["target_bpm"])
        matches = []
        for role, bpm in (("source", source_bpm), ("target", target_bpm)):
            reason = None
            if minimum_bpm is not None and bpm < float(minimum_bpm):
                reason = "below_minimum_bpm"
            elif maximum_bpm is not None and bpm > float(maximum_bpm):
                reason = "above_maximum_bpm"
            if reason is not None:
                matches.append({"role": role, "bpm": bpm, "reason": reason})
        if matches:
            rejected.append(
                {
                    "example_id": record.example_id,
                    "exclusion_type": "bpm_filter",
                    "matches": matches,
                }
            )
        else:
            allowed.append(record)
    return allowed, rejected


def _track_catalog(records):
    tracks = {}
    for record in records:
        for role in ("source", "target"):
            track = record.candidate[f"{role}_track"]
            track_hash = str(track["sha256"]).lower()
            previous = tracks.setdefault(track_hash, str(track["path"]))
            if previous != str(track["path"]):
                # Same content at another path is one split identity; retain first path.
                continue
    return tracks


def _pair_weights(records):
    weights = {}
    for record in records:
        key = (record.source_hash, record.target_hash)
        weights[key] = weights.get(key, 0) + 1
    return weights


def _load_artifact(
    track,
    *,
    target_bpm,
    artifact_cache,
    loader,
    cache_root,
    analysis,
    analysis_root,
    sample_rate,
    vocal_backend,
    vocal_model,
):
    path = _resolve_track_path(track["path"])
    key = (str(path), None if target_bpm is None else float(target_bpm), vocal_backend, vocal_model)
    if key not in artifact_cache:
        artifact = loader(
            path,
            cache_root=cache_root,
            analysis=analysis,
            analysis_root=analysis_root,
            sample_rate=sample_rate,
            target_bpm=target_bpm,
            vocal_backend=vocal_backend,
            vocal_model=vocal_model,
        )
        if artifact.manifest["source_sha256"].lower() != str(track["sha256"]).lower():
            raise ValueError(f"Track hash differs from candidate manifest: {path}")
        artifact_cache[key] = artifact
    return artifact_cache[key]


def _normalization_stats_id(training_artifacts, assignments):
    payload = {
        "training_artifacts": sorted(
            artifact.manifest["cache_id"] for artifact in training_artifacts
        ),
        "training_tracks": sorted(
            track_hash for track_hash, split in assignments.items() if split == "train"
        ),
    }
    return "train-" + hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()[:16]


def _example_metadata(
    record,
    split_name,
    source_artifact,
    target_artifact,
    source_cue,
    target_cue,
    analysis_root,
):
    candidate = record.candidate
    return {
        "example_id": record.example_id,
        "waveform_alignment": CUE_ALIGNMENT,
        "waveform_analysis_root": Path(analysis_root).as_posix(),
        "cue_sample_rate": int(candidate.get("cue_sample_rate", source_artifact.manifest["sample_rate"])),
        "split": split_name,
        "candidate_id": candidate["candidate_id"],
        "candidate_rank": record.candidate_rank,
        "candidate_score": record.candidate_score,
        "pair_manifest_path": str(record.pair_manifest_path),
        "pair_manifest_sha256": record.pair_manifest_sha256,
        "source_track": candidate["source_track"],
        "target_track": candidate["target_track"],
        "source_cutpoint": candidate["source_cutpoint"],
        "target_cutpoint": candidate["target_cutpoint"],
        "source_grid": candidate.get("source_grid"),
        "target_grid": candidate.get("target_grid"),
        "waveform_grid_sha256": {
            role: (artifact.manifest.get("beat_grid_metadata") or {}).get("beat_grid_sha256")
            for role, artifact in (("source", source_artifact), ("target", target_artifact))
        },
        "aligned_source_cue_sample": int(source_cue),
        "aligned_target_cue_sample": int(target_cue),
        "source_bpm": float(candidate["source_bpm"]),
        "target_bpm": float(candidate["target_bpm"]),
        "transition_length_bars": int(candidate["transition_length_bars"]),
        "source_feature_cache": {
            "directory": str(source_artifact.cache_directory),
            "cache_id": source_artifact.manifest["cache_id"],
        },
        "target_feature_cache": {
            "directory": str(target_artifact.cache_directory),
            "cache_id": target_artifact.manifest["cache_id"],
        },
    }


def _write_split(path, payload):
    if payload:
        example_ids = np.asarray([item[0] for item in payload])
        features_a = np.stack([item[1] for item in payload]).astype(np.float32, copy=False)
        features_b = np.stack([item[2] for item in payload]).astype(np.float32, copy=False)
        global_features = np.stack([item[3] for item in payload]).astype(
            np.float32,
            copy=False,
        )
    else:
        example_ids = np.asarray([], dtype="<U1")
        features_a = np.empty((0, SEQUENCE_LENGTH, FEATURE_DIMENSION), dtype=np.float32)
        features_b = np.empty((0, SEQUENCE_LENGTH, FEATURE_DIMENSION), dtype=np.float32)
        global_features = np.empty((0, GLOBAL_FEATURE_DIMENSION), dtype=np.float32)
    np.savez_compressed(
        path,
        example_ids=example_ids,
        features_a=features_a,
        features_b=features_b,
        global_features=global_features,
    )


def _split_sizes(track_count, ratios):
    raw = {name: track_count * ratios[name] for name in SPLIT_NAMES}
    sizes = {name: int(math.floor(raw[name])) for name in SPLIT_NAMES}
    for name in sorted(SPLIT_NAMES, key=lambda item: (-(raw[item] - sizes[item]), item)):
        if sum(sizes.values()) >= track_count:
            break
        sizes[name] += 1
    active = [name for name in SPLIT_NAMES if ratios[name] > 0]
    for name in active:
        if sizes[name] > 0:
            continue
        donor = max(active, key=lambda item: sizes[item])
        if sizes[donor] <= 1:
            raise ValueError("Not enough tracks to populate every active split")
        sizes[donor] -= 1
        sizes[name] += 1
    return sizes


def _retained_weights(assignment, pair_weights):
    retained = {name: 0 for name in SPLIT_NAMES}
    for (left, right), weight in pair_weights.items():
        if assignment.get(left) == assignment.get(right):
            retained[assignment[left]] += weight
    return retained


def _example_id(candidate):
    payload = {
        "source_sha256": candidate["source_track"]["sha256"],
        "target_sha256": candidate["target_track"]["sha256"],
        "source_cutpoint": candidate["source_cutpoint"]["sample"],
        "target_cutpoint": candidate["target_cutpoint"]["sample"],
        "transition_length_bars": candidate["transition_length_bars"],
    }
    return "example-" + hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()[:16]


def _resolve_track_path(path):
    path = Path(path)
    return path if path.is_absolute() else PROJECT_ROOT / path


def _read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _file_sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_argument_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_manifest")
    parser.add_argument("output_directory")
    parser.add_argument("--cache-root", default=str(DEFAULT_FEATURE_CACHE_ROOT))
    parser.add_argument("--analysis-root", default=str(DEFAULT_ANALYSIS_ROOT))
    parser.add_argument("--sample-rate", type=int, default=DEFAULT_SAMPLE_RATE)
    parser.add_argument("--top-k-per-pair", type=int, default=DEFAULT_TOP_K_PER_PAIR)
    parser.add_argument("--transition-bars", type=int, default=4)
    parser.add_argument("--train-ratio", type=float, default=0.70)
    parser.add_argument("--validation-ratio", type=float, default=0.15)
    parser.add_argument("--test-ratio", type=float, default=0.15)
    parser.add_argument("--split-seed", type=int, default=DEFAULT_SPLIT_SEED)
    parser.add_argument("--split-search-attempts", type=int, default=4096)
    parser.add_argument("--max-pairs", type=int)
    parser.add_argument("--min-bpm", type=float)
    parser.add_argument("--max-bpm", type=float)
    parser.add_argument(
        "--vocal-backend",
        choices=("disabled", "demucs", "roformer"),
        default=DEFAULT_VOCAL_BACKEND,
    )
    parser.add_argument("--vocal-model", default=DEFAULT_ROFORMER_MODEL)
    parser.add_argument(
        "--track-exclusions",
        default=str(DEFAULT_TRACK_EXCLUSIONS_PATH),
    )
    return parser


def main():
    args = build_argument_parser().parse_args()
    result = export_feature_dataset(
        args.source_manifest,
        args.output_directory,
        cache_root=args.cache_root,
        analysis_root=args.analysis_root,
        sample_rate=args.sample_rate,
        top_k_per_pair=args.top_k_per_pair,
        transition_bars=args.transition_bars,
        split_config=SplitConfig(
            train=args.train_ratio,
            validation=args.validation_ratio,
            test=args.test_ratio,
            seed=args.split_seed,
            search_attempts=args.split_search_attempts,
        ),
        vocal_backend=args.vocal_backend,
        vocal_model=args.vocal_model,
        track_exclusions_path=args.track_exclusions,
        minimum_bpm=args.min_bpm,
        maximum_bpm=args.max_bpm,
        max_pairs=args.max_pairs,
    )
    print(
        json.dumps(
            {
                "output_directory": str(result.output_directory),
                "manifest_path": str(result.manifest_path),
                "example_count": result.example_count,
                "split_counts": result.split_counts,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
