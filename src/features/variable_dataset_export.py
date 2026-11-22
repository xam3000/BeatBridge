"""Dataset Format 2 export with homogeneous, length-specific NPZ shards."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import io
import json
import math
import os
from pathlib import Path
import shutil
import uuid
import zipfile

import numpy as np

from src.analysis.pre_analysis import PartialPreAnalysis
from src.dataset import DEFAULT_TRACK_EXCLUSIONS_PATH, is_track_excluded, load_track_exclusions
from src.features.contract import FEATURE_DIMENSION, GLOBAL_FEATURE_DIMENSION
from src.features.extract_track import (
    DEFAULT_ANALYSIS_ROOT,
    DEFAULT_FEATURE_CACHE_ROOT,
    extract_or_load_track_features,
    normalization_stats_from_training_artifacts,
)
from src.features.global_pair import GLOBAL_PAIR_EXTRACTOR_VERSION
from src.features.variable_contract import (
    SUPPORTED_VARIABLE_LENGTHS,
    geometry_for_length,
    geometry_from_candidate,
    variable_feature_schema,
    validate_length_condition,
    validate_variable_feature_array,
)
from src.features.variable_extract import extract_variable_track_window
from src.features.variable_global_pair import (
    VARIABLE_GLOBAL_PAIR_EXTRACTOR_VERSION,
    build_variable_global_pair_features,
)
from src.features.variable_split import (
    VariableSplitAuthority,
    authority_from_mapping,
    build_variable_split_authority,
    load_variable_split_authority,
)
from src.features.vocal import DEFAULT_ROFORMER_MODEL, DEFAULT_VOCAL_BACKEND
from src.pipeline import DEFAULT_SAMPLE_RATE
from src.features.dataset_export import SPLIT_NAMES, SplitConfig
from src.tempo.coordinates import aligned_cue_sample


DATASET_FORMAT_VERSION = 2
VARIABLE_DATASET_EXPORTER_VERSION = 1
PROJECT_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class VariableCandidateRecord:
    example_id: str
    candidate: dict
    candidate_rank: int
    candidate_score: float
    pair_manifest_path: Path
    pair_manifest_sha256: str
    transition_length_bars: int

    @property
    def source_hash(self):
        return str(self.candidate["source_track"]["sha256"]).lower()

    @property
    def target_hash(self):
        return str(self.candidate["target_track"]["sha256"]).lower()


@dataclass(frozen=True)
class VariableDatasetExportResult:
    output_directory: Path
    manifest_path: Path
    example_count: int
    split_counts: dict
    split_authority: VariableSplitAuthority


def export_variable_feature_dataset(
    source_manifest,
    output_directory,
    *,
    transition_lengths_bars=SUPPORTED_VARIABLE_LENGTHS,
    cache_root=DEFAULT_FEATURE_CACHE_ROOT,
    analysis=None,
    analysis_root=DEFAULT_ANALYSIS_ROOT,
    sample_rate=DEFAULT_SAMPLE_RATE,
    top_k_per_pair=3,
    split_config=None,
    split_map_path=None,
    split_authority=None,
    vocal_backend=DEFAULT_VOCAL_BACKEND,
    vocal_model=DEFAULT_ROFORMER_MODEL,
    track_exclusions_path=DEFAULT_TRACK_EXCLUSIONS_PATH,
    minimum_bpm=None,
    maximum_bpm=None,
    max_pairs=None,
    track_feature_loader=None,
):
    """Export all requested lengths in one run without changing v1 exports."""
    source_manifest = Path(source_manifest)
    output_directory = Path(output_directory)
    if not source_manifest.is_file():
        raise FileNotFoundError(f"Source manifest does not exist: {source_manifest}")
    if output_directory.exists():
        raise FileExistsError(f"Dataset output path already exists: {output_directory}")
    if int(top_k_per_pair) <= 0:
        raise ValueError("top_k_per_pair must be greater than 0")
    lengths = tuple(
        geometry_for_length(length).transition_length_bars
        for length in transition_lengths_bars
    )
    if len(set(lengths)) != len(lengths):
        raise ValueError("transition_lengths_bars must not contain duplicates")
    lengths = tuple(sorted(lengths))
    _validate_bpm_bounds(minimum_bpm, maximum_bpm)
    split_config = split_config or SplitConfig()
    track_feature_loader = track_feature_loader or extract_or_load_track_features
    # Candidate-v2 uses the Partial-Merge-v2 beat grid. Build Feature Protocol
    # 2 artifacts on that same grid so cue boundaries and cached feature bins
    # share one analysis authority (and can reuse the producer's analysis cache).
    analysis = analysis or PartialPreAnalysis(str(Path(analysis_root)) + os.sep)
    pair_manifests = _discover_pair_manifests(source_manifest)
    if max_pairs is not None:
        if int(max_pairs) <= 0:
            raise ValueError("max_pairs must be greater than 0")
        pair_manifests = pair_manifests[: int(max_pairs)]
    records = _select_variable_candidate_records(
        pair_manifests,
        lengths=lengths,
        top_k_per_pair=int(top_k_per_pair),
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
        raise ValueError("No selected variable candidates remain after exclusions")

    tracks = _track_catalog(records)
    pair_weights = _pair_weights(records)
    source_manifest_sha256 = _file_sha256(source_manifest)
    if split_authority is not None and split_map_path is not None:
        raise ValueError("Provide split_authority or split_map_path, not both")
    if split_map_path is not None:
        authority = load_variable_split_authority(
            split_map_path,
            tracks,
            source_manifest_sha256=source_manifest_sha256,
        )
    elif split_authority is not None:
        authority = _coerce_authority(
            split_authority,
            tracks,
            source_manifest_sha256=source_manifest_sha256,
        )
    else:
        authority = build_variable_split_authority(
            tracks,
            pair_weights,
            split_config=split_config,
            source_manifest_sha256=source_manifest_sha256,
        )
    assignments = authority.assignments
    retained_records = [
        record
        for record in records
        if assignments[record.source_hash] == assignments[record.target_hash]
    ]

    prepared = []
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
        geometry = geometry_from_candidate(candidate)
        source_cue = _scale_cue(candidate["source_cutpoint"]["sample"], sample_rate)
        target_cue = _scale_cue(candidate["target_cutpoint"]["sample"], sample_rate)
        target_cue = aligned_cue_sample(
            target_cue,
            original_bpm=candidate["target_bpm"],
            aligned_bpm=candidate["source_bpm"],
        )
        prepared.append((record, geometry, source_artifact, target_artifact, source_cue, target_cue))

    training_artifacts = []
    seen_training_artifacts = set()
    for record, _, source_artifact, target_artifact, _, _ in prepared:
        if assignments[record.source_hash] != "train":
            continue
        for artifact in (source_artifact, target_artifact):
            key = str(artifact.cache_directory)
            if key not in seen_training_artifacts:
                seen_training_artifacts.add(key)
                training_artifacts.append(artifact)
    if not training_artifacts:
        raise ValueError("Variable export has no retained training artifacts for normalization")
    stats_id = _normalization_stats_id(training_artifacts, assignments)
    normalization = normalization_stats_from_training_artifacts(
        training_artifacts,
        stats_id=stats_id,
    )

    payloads = {
        length: {split: [] for split in SPLIT_NAMES}
        for length in lengths
    }
    metadata = {
        length: {split: [] for split in SPLIT_NAMES}
        for length in lengths
    }
    for record, geometry, source_artifact, target_artifact, source_cue, target_cue in prepared:
        split_name = assignments[record.source_hash]
        features_a = extract_variable_track_window(
            source_artifact,
            source_cue,
            role="source",
            normalization=normalization,
            transition_length_bars=geometry.transition_length_bars,
            sequence_length=geometry.sequence_length,
        )
        features_b = extract_variable_track_window(
            target_artifact,
            target_cue,
            role="target",
            normalization=normalization,
            transition_length_bars=geometry.transition_length_bars,
            sequence_length=geometry.sequence_length,
        )
        global_features = build_variable_global_pair_features(
            features_a,
            features_b,
            transition_length_bars=geometry.transition_length_bars,
            sequence_length=geometry.sequence_length,
            bpm_a=float(record.candidate["source_bpm"]),
            bpm_b=float(record.candidate["target_bpm"]),
            artifact_a=source_artifact,
            artifact_b=target_artifact,
            cue_sample_a=source_cue,
            cue_sample_b=target_cue,
        )
        length_condition = np.asarray([geometry.length_condition], dtype=np.float32)
        validate_length_condition(length_condition, transition_length_bars=geometry.transition_length_bars)
        payloads[geometry.transition_length_bars][split_name].append(
            (record.example_id, features_a, features_b, global_features, length_condition)
        )
        metadata[geometry.transition_length_bars][split_name].append(
            _example_metadata(
                record,
                geometry,
                split_name,
                source_artifact,
                target_artifact,
                source_cue,
                target_cue,
            )
        )

    split_counts = {
        str(length): {
            split: len(payloads[length][split]) for split in SPLIT_NAMES
        }
        for length in lengths
    }
    dataset_config = {
        "format_version": DATASET_FORMAT_VERSION,
        "exporter_version": VARIABLE_DATASET_EXPORTER_VERSION,
        "feature_protocol_version": 2,
        "beat_grid_analysis_contract": "partial_merge_v2",
        "global_pair_extractor_version": VARIABLE_GLOBAL_PAIR_EXTRACTOR_VERSION,
        "v1_global_pair_extractor_version": GLOBAL_PAIR_EXTRACTOR_VERSION,
        "supported_lengths": list(lengths),
        "sequence_lengths": {
            str(length): geometry_for_length(length).sequence_length for length in lengths
        },
        "feature_dimension": FEATURE_DIMENSION,
        "global_feature_dimension": GLOBAL_FEATURE_DIMENSION,
        "length_condition_dimension": 1,
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
        "split_authority": {
            "source": authority.source,
            "source_manifest_sha256": authority.source_manifest_sha256,
            "mapping_sha256": authority.mapping_sha256,
            "policy": authority.policy,
        },
        "normalization": {
            "stats_id": normalization.stats_id,
            "fit_scope": "training_tracks_only",
            "spectral_flux_log1p_p99": normalization.spectral_flux_log1p_p99,
            "onset_strength_log1p_p99": normalization.onset_strength_log1p_p99,
        },
    }
    dataset_id = hashlib.sha256(
        json.dumps(
            {
                "config": dataset_config,
                "source_manifest_sha256": source_manifest_sha256,
                "pair_manifests": [
                    _file_sha256(path) for path in pair_manifests
                ],
                "examples": [
                    item[0]
                    for length in lengths
                    for split in SPLIT_NAMES
                    for item in payloads[length][split]
                ],
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()[:20]
    manifest = {
        **dataset_config,
        "dataset_id": dataset_id,
        "source_manifest": str(source_manifest),
        "source_manifest_sha256": source_manifest_sha256,
        "pair_manifests": [
            {"path": str(path), "sha256": _file_sha256(path)} for path in pair_manifests
        ],
        "feature_schema": variable_feature_schema(),
        "track_assignments": authority.to_dict()["track_assignments"],
        "selection": {
            "selected_before_exclusions": selected_before_exclusions,
            "excluded_by_training_policy": len(excluded_records),
            "excluded_by_bpm_filter": len(bpm_excluded_records),
            "discarded_cross_split": len(records) - len(retained_records),
            "exported": len(retained_records),
            "per_length": split_counts,
        },
        "excluded_examples": excluded_records + bpm_excluded_records,
        "split_counts": split_counts,
        "shards": {},
        "files": {},
        "reproducibility": {
            "wall_clock_fields_omitted": True,
            "npz_compression": "zip_deflate_level_9_fixed_timestamp",
            "json_sort_keys": True,
            "source_manifest_and_pair_hashes_bound": True,
        },
    }

    temporary_directory = output_directory.with_name(
        f".{output_directory.name}.{uuid.uuid4().hex}.tmp"
    )
    temporary_directory.mkdir(parents=True)
    try:
        for length in lengths:
            geometry = geometry_for_length(length)
            length_key = str(length)
            manifest["shards"][length_key] = {}
            for split in SPLIT_NAMES:
                base = Path("lengths") / f"{length}bar"
                npz_relative = base / f"{split}.npz"
                metadata_relative = Path("metadata") / f"{length}bar" / f"{split}.jsonl"
                npz_path = temporary_directory / npz_relative
                metadata_path = temporary_directory / metadata_relative
                npz_path.parent.mkdir(parents=True, exist_ok=True)
                metadata_path.parent.mkdir(parents=True, exist_ok=True)
                _write_variable_shard(npz_path, payloads[length][split], geometry)
                metadata_path.write_text(
                    "".join(
                        json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n"
                        for item in metadata[length][split]
                    ),
                    encoding="utf-8",
                )
                npz_hash = _file_sha256(npz_path)
                metadata_hash = _file_sha256(metadata_path)
                npz_name = f"{length_key}bar_{split}_npz"
                metadata_name = f"{length_key}bar_{split}_metadata"
                manifest["files"][npz_name] = {
                    "path": npz_relative.as_posix(),
                    "sha256": npz_hash,
                    "kind": "npz",
                }
                manifest["files"][metadata_name] = {
                    "path": metadata_relative.as_posix(),
                    "sha256": metadata_hash,
                    "kind": "jsonl",
                }
                count = len(payloads[length][split])
                manifest["shards"][length_key][split] = {
                    "sequence_length": geometry.sequence_length,
                    "transition_length_bars": length,
                    "transition_length_beats": geometry.transition_length_beats,
                    "count": count,
                    "empty": count == 0,
                    "empty_reason": (
                        None
                        if count
                        else "no retained examples for this length and split"
                    ),
                    "npz_file": npz_name,
                    "metadata_file": metadata_name,
                    "arrays": {
                        "features_a": [count, geometry.sequence_length, FEATURE_DIMENSION],
                        "features_b": [count, geometry.sequence_length, FEATURE_DIMENSION],
                        "global_features": [count, GLOBAL_FEATURE_DIMENSION],
                        "length_condition": [count, 1],
                        "example_ids": [count],
                        "transition_length_bars": [count],
                        "sequence_length": [count],
                    },
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
    return VariableDatasetExportResult(
        output_directory=output_directory,
        manifest_path=output_directory / "manifest.json",
        example_count=len(retained_records),
        split_counts=split_counts,
        split_authority=authority,
    )


def _select_variable_candidate_records(pair_manifests, *, lengths, top_k_per_pair):
    choices_by_pair_and_length = {}
    for manifest_path in pair_manifests:
        payload = _read_json(manifest_path)
        candidates = {
            item["candidate_id"]: item
            for item in payload.get("candidate_generation", {}).get("candidates", [])
        }
        for score in sorted(
            payload.get("candidate_ranking", {}).get("scores", []),
            key=lambda item: (int(item["rank"]), item["candidate_id"]),
        ):
            candidate = candidates.get(score["candidate_id"])
            if candidate is None:
                continue
            try:
                geometry = geometry_from_candidate(candidate)
            except (TypeError, ValueError):
                continue
            if geometry.transition_length_bars not in lengths:
                continue
            pair_key = (
                str(candidate["source_track"]["sha256"]).lower(),
                str(candidate["target_track"]["sha256"]).lower(),
                geometry.transition_length_bars,
            )
            choices_by_pair_and_length.setdefault(pair_key, []).append(
                (score, candidate, geometry, manifest_path, _file_sha256(manifest_path))
            )

    records = []
    seen_examples = set()
    for pair_key, choices in sorted(choices_by_pair_and_length.items()):
        choices = sorted(
            choices,
            key=lambda item: (
                int(item[0]["rank"]),
                item[0]["candidate_id"],
                str(item[3]),
            ),
        )
        for score, candidate, geometry, manifest_path, manifest_sha256 in choices[:top_k_per_pair]:
            example_id = _example_id(candidate, geometry.transition_length_bars)
            if example_id in seen_examples:
                continue
            seen_examples.add(example_id)
            records.append(
                VariableCandidateRecord(
                    example_id=example_id,
                    candidate=candidate,
                    candidate_rank=int(score["rank"]),
                    candidate_score=float(score["total_score"]),
                    pair_manifest_path=manifest_path,
                    pair_manifest_sha256=manifest_sha256,
                    transition_length_bars=geometry.transition_length_bars,
                )
            )
    return records


def _write_variable_shard(path, payload, geometry):
    if payload:
        example_ids = np.asarray([item[0] for item in payload])
        features_a = np.stack([item[1] for item in payload]).astype(np.float32, copy=False)
        features_b = np.stack([item[2] for item in payload]).astype(np.float32, copy=False)
        global_features = np.stack([item[3] for item in payload]).astype(np.float32, copy=False)
        length_condition = np.stack([item[4] for item in payload]).astype(np.float32, copy=False)
    else:
        example_ids = np.asarray([], dtype="<U1")
        features_a = np.empty((0, geometry.sequence_length, FEATURE_DIMENSION), dtype=np.float32)
        features_b = np.empty((0, geometry.sequence_length, FEATURE_DIMENSION), dtype=np.float32)
        global_features = np.empty((0, GLOBAL_FEATURE_DIMENSION), dtype=np.float32)
        length_condition = np.empty((0, 1), dtype=np.float32)
    transition_length_bars = np.full(
        (len(example_ids),), geometry.transition_length_bars, dtype=np.int16
    )
    sequence_length = np.full(
        (len(example_ids),), geometry.sequence_length, dtype=np.int16
    )
    validate_variable_feature_array(
        features_a[0],
        transition_length_bars=geometry.transition_length_bars,
    ) if payload else None
    _write_deterministic_npz(
        path,
        example_ids=example_ids,
        features_a=features_a,
        features_b=features_b,
        global_features=global_features,
        length_condition=length_condition,
        transition_length_bars=transition_length_bars,
        sequence_length=sequence_length,
    )


def _write_deterministic_npz(path, **arrays):
    """Write an NPZ without wall-clock ZIP metadata."""
    with zipfile.ZipFile(
        path,
        mode="w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
    ) as archive:
        for name in sorted(arrays):
            buffer = io.BytesIO()
            np.lib.format.write_array(
                buffer,
                np.asarray(arrays[name]),
                allow_pickle=False,
            )
            info = zipfile.ZipInfo(f"{name}.npy", date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 0
            info.external_attr = 0
            archive.writestr(info, buffer.getvalue(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)


def _example_metadata(record, geometry, split_name, source_artifact, target_artifact, source_cue, target_cue):
    candidate = record.candidate
    return {
        "example_id": record.example_id,
        "split": split_name,
        "feature_protocol_version": 2,
        "dataset_format_version": DATASET_FORMAT_VERSION,
        "candidate_id": candidate["candidate_id"],
        "candidate_format_version": int(candidate.get("format_version", 1)),
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
        "aligned_source_cue_sample": int(source_cue),
        "aligned_target_cue_sample": int(target_cue),
        "source_bpm": float(candidate["source_bpm"]),
        "target_bpm": float(candidate["target_bpm"]),
        "transition_length_bars": geometry.transition_length_bars,
        "transition_length_beats": geometry.transition_length_beats,
        "sequence_length": geometry.sequence_length,
        "length_condition": float(geometry.length_condition),
        "source_feature_cache": _artifact_metadata(source_artifact),
        "target_feature_cache": _artifact_metadata(target_artifact),
    }


def _artifact_metadata(artifact):
    manifest = dict(artifact.manifest)
    canonical = json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return {
        "directory": str(artifact.cache_directory),
        "cache_id": manifest.get("cache_id"),
        "manifest_sha256": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
        "source_sha256": manifest.get("source_sha256"),
        "aligned_bpm": manifest.get("aligned_bpm"),
        "sample_rate": manifest.get("sample_rate"),
    }


def _load_artifact(track, *, target_bpm, artifact_cache, loader, cache_root, analysis, analysis_root, sample_rate, vocal_backend, vocal_model):
    path = _resolve_track_path(track["path"])
    key = (str(path), None if target_bpm is None else float(target_bpm), str(vocal_backend), str(vocal_model))
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
        if str(artifact.manifest["source_sha256"]).lower() != str(track["sha256"]).lower():
            raise ValueError(f"Track hash differs from candidate manifest: {path}")
        artifact_cache[key] = artifact
    return artifact_cache[key]


def _coerce_authority(value, required_tracks, *, source_manifest_sha256):
    if isinstance(value, VariableSplitAuthority):
        if value.source_manifest_sha256 not in {None, source_manifest_sha256}:
            raise ValueError("Split authority source manifest hash differs")
        return authority_from_mapping(
            value.assignments,
            required_tracks,
            source_manifest_sha256=value.source_manifest_sha256 or source_manifest_sha256,
            source=value.source,
            policy=value.policy,
        )
    return authority_from_mapping(
        value,
        required_tracks,
        source_manifest_sha256=source_manifest_sha256,
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
            declared_sha256 = pair.get("pair_manifest_sha256")
            if declared_sha256 is not None and str(declared_sha256).lower() != _file_sha256(path):
                raise ValueError(f"Pair manifest SHA-256 differs: {path}")
            paths.append(path)
    if not paths:
        raise ValueError("Manifest contains no completed pair manifests")
    return tuple(paths)


def _apply_training_exclusions(records, exclusions):
    allowed, rejected = [], []
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


def _apply_bpm_filter(records, *, minimum_bpm, maximum_bpm):
    allowed, rejected = [], []
    for record in records:
        matches = []
        for role in ("source", "target"):
            bpm = float(record.candidate[f"{role}_bpm"])
            if minimum_bpm is not None and bpm < float(minimum_bpm):
                matches.append({"role": role, "bpm": bpm, "reason": "below_minimum_bpm"})
            elif maximum_bpm is not None and bpm > float(maximum_bpm):
                matches.append({"role": role, "bpm": bpm, "reason": "above_maximum_bpm"})
        if matches:
            rejected.append({"example_id": record.example_id, "exclusion_type": "bpm_filter", "matches": matches})
        else:
            allowed.append(record)
    return allowed, rejected


def _validate_bpm_bounds(minimum_bpm, maximum_bpm):
    for name, value in (("minimum_bpm", minimum_bpm), ("maximum_bpm", maximum_bpm)):
        if value is not None and (not math.isfinite(float(value)) or float(value) <= 0):
            raise ValueError(f"{name} must be finite and greater than 0")
    if minimum_bpm is not None and maximum_bpm is not None and float(minimum_bpm) > float(maximum_bpm):
        raise ValueError("minimum_bpm must be less than or equal to maximum_bpm")


def _track_catalog(records):
    tracks = {}
    for record in records:
        for role in ("source", "target"):
            track = record.candidate[role + "_track"]
            tracks.setdefault(str(track["sha256"]).lower(), str(track["path"]))
    return tracks


def _pair_weights(records):
    weights = {}
    for record in records:
        key = (record.source_hash, record.target_hash)
        weights[key] = weights.get(key, 0) + 1
    return weights


def _normalization_stats_id(training_artifacts, assignments):
    payload = {
        "protocol": 2,
        "training_artifacts": sorted(artifact.manifest["cache_id"] for artifact in training_artifacts),
        "training_tracks": sorted(key for key, split in assignments.items() if split == "train"),
    }
    return "train-v2-" + hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()[:16]


def _example_id(candidate, transition_length_bars):
    payload = {
        "candidate_id": candidate["candidate_id"],
        "source_sha256": candidate["source_track"]["sha256"],
        "target_sha256": candidate["target_track"]["sha256"],
        "source_cutpoint": candidate["source_cutpoint"]["sample"],
        "target_cutpoint": candidate["target_cutpoint"]["sample"],
        "transition_length_bars": int(transition_length_bars),
    }
    return "variable-example-" + hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()[:16]


def _scale_cue(sample, sample_rate):
    return int(round(int(sample) * int(sample_rate) / DEFAULT_SAMPLE_RATE))


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
