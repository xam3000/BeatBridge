"""Inference adapter for the verified ``learned_cue_ranker_v1`` model.

The adapter deliberately sits after candidate generation.  It never creates
or edits a candidate and it never replaces the historical feature ranking;
callers use the returned scores only as an additive selection authority.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import torch

from src.candidates import TransitionCandidate
from src.features.extract_track import FeatureNormalizationStats, extract_or_load_track_features
from src.features.variable_extract import extract_variable_track_window
from src.features.variable_global_pair import build_variable_global_pair_features
from src.features.variable_contract import geometry_for_length
from src.ml.cue_ranker_context import build_candidate_context
from src.ml.cue_ranker_model import CueRankerTemporalConfig, CueRankerTemporalModel
from src.ml.cue_ranker_model import CUE_RANKER_CONTEXT_VERSION, CUE_RANKER_MODEL_FORMAT_VERSION, CUE_RANKER_MODEL_NAME
from src.ml.cue_ranker_runner import CUE_RANKER_RUN_FORMAT_VERSION, CUE_RANKER_RUNNER_NAME
from src.ranking.feature_baseline import CandidateScore, RankingFailure


LEARNED_CUE_RANKER_FORMAT_VERSION = 1
LEARNED_CUE_RANKER_NAME = CUE_RANKER_MODEL_NAME
LEARNED_CUE_RANKER_GENERATOR = "bar_grid_v2_length_specific"


@dataclass(frozen=True)
class LearnedRankingConfig:
    """Small serialisable description kept in the common ranking shape."""

    target_sample_rate: int = 44_100
    context_version: str = CUE_RANKER_CONTEXT_VERSION

    def to_dict(self):
        return {
            "target_sample_rate": int(self.target_sample_rate),
            "context_version": self.context_version,
        }


@dataclass(frozen=True)
class LearnedCueRankingResult:
    scores: tuple[CandidateScore, ...]
    failures: tuple[RankingFailure, ...]
    provenance: dict
    selection_candidate_ids: tuple[str, ...] = ()
    renderability_preflight: tuple[dict, ...] = ()
    backfill: dict | None = None
    format_version: int = LEARNED_CUE_RANKER_FORMAT_VERSION
    ranker: str = LEARNED_CUE_RANKER_NAME
    config: LearnedRankingConfig = LearnedRankingConfig()

    def with_selection(self, candidate_ids, *, renderability_preflight, backfill):
        return replace(
            self,
            selection_candidate_ids=tuple(candidate_ids),
            renderability_preflight=tuple(renderability_preflight),
            backfill=dict(backfill),
        )

    def to_dict(self):
        checkpoint = self.provenance.get("checkpoint", {})
        dataset = self.provenance.get("dataset", {})
        teacher = self.provenance.get("teacher", {})
        return {
            "format_version": int(self.format_version),
            "ranker": self.ranker,
            "model_name": self.ranker,
            "config": self.config.to_dict(),
            **self.provenance,
            "checkpoint_sha256": checkpoint.get("sha256"),
            "dataset_manifest_sha256": dataset.get("sha256"),
            "teacher_contract": teacher,
            "scores": [score.to_dict() for score in self.scores],
            "failures": [failure.to_dict() for failure in self.failures],
            "selection_candidate_ids": list(self.selection_candidate_ids),
            "renderability_preflight": list(self.renderability_preflight),
            "backfill": self.backfill,
        }


@dataclass(frozen=True)
class LoadedCueRanker:
    model: CueRankerTemporalModel
    run_manifest: dict
    run_manifest_path: Path
    checkpoint_path: Path
    checkpoint_sha256: str
    dataset_manifest: dict
    dataset_manifest_path: Path
    dataset_manifest_sha256: str
    normalizer: FeatureNormalizationStats

    @property
    def provenance(self):
        dataset = self.dataset_manifest
        return {
            "checkpoint": {
                "path": str(self.checkpoint_path.resolve()),
                "sha256": self.checkpoint_sha256,
                "format_version": CUE_RANKER_MODEL_FORMAT_VERSION,
            },
            "run_manifest": {
                "path": str(self.run_manifest_path.resolve()),
                "sha256": _file_sha256(self.run_manifest_path),
                "format_version": self.run_manifest.get("format_version"),
                "run_id": self.run_manifest.get("run_id"),
            },
            "dataset": {
                "path": str(self.dataset_manifest_path.resolve()),
                "sha256": self.dataset_manifest_sha256,
                "format_version": dataset.get("format_version"),
                "dataset_id": dataset.get("dataset_id"),
                "test": dataset.get("test"),
            },
            "teacher": {
                "manifest_sha256": dataset.get("teacher_manifest_sha256"),
                "release_sha256": dataset.get("teacher_release_sha256"),
                "contract_sha256": dataset.get("teacher_contract_sha256"),
                "alignment_contract": dataset.get("teacher_alignment_contract"),
            },
            "input_contract": self.run_manifest.get("contract", {}).get("input_contract"),
        }


def load_learned_cue_ranker(run_or_checkpoint, *, dataset_manifest_path=None):
    """Load and verify a learned ranker before any model weights are used.

    ``run_or_checkpoint`` may be a training-run directory, its ``best.pt``,
    or a run manifest.  A Dataset-3 manifest is mandatory: the run contract
    binds its SHA, and it supplies the train-only normalizer and teacher
    contract provenance.
    """

    if run_or_checkpoint is None:
        raise FileNotFoundError("Cue-Ranker run/checkpoint must be specified for learned inference")
    supplied = Path(run_or_checkpoint)
    if supplied.is_dir():
        run_manifest_path = supplied / "manifest.json"
        checkpoint_path = supplied / "best.pt"
        if not checkpoint_path.is_file():
            checkpoint_path = supplied / "checkpoints" / "best.pt"
    elif supplied.name == "manifest.json":
        run_manifest_path = supplied
        checkpoint_path = supplied.parent / "best.pt"
        if not checkpoint_path.is_file():
            checkpoint_path = supplied.parent / "checkpoints" / "best.pt"
    else:
        checkpoint_path = supplied
        run_manifest_path = supplied.parent / "manifest.json"

    if not run_manifest_path.is_file():
        raise FileNotFoundError(f"Cue-Ranker run manifest is missing: {run_manifest_path}")
    if not checkpoint_path.is_file():
        raise FileNotFoundError(f"Cue-Ranker best checkpoint is missing: {checkpoint_path}")
    run_manifest = _read_json(run_manifest_path, "Cue-Ranker run manifest")
    if int(run_manifest.get("format_version", -1)) != CUE_RANKER_RUN_FORMAT_VERSION:
        raise ValueError("Cue-Ranker run manifest format is unsupported")
    if run_manifest.get("runner_name") != CUE_RANKER_RUNNER_NAME:
        raise ValueError("Cue-Ranker run manifest runner is not learned_cue_ranker_v1")
    if run_manifest.get("status") != "completed":
        raise ValueError("Cue-Ranker run is not completed")
    contract = run_manifest.get("contract")
    if not isinstance(contract, dict) or contract.get("model_name") != LEARNED_CUE_RANKER_NAME:
        raise ValueError("Cue-Ranker run contract model is invalid")
    declared_manifest_sha = run_manifest_path.with_name("manifest.sha256")
    if declared_manifest_sha.is_file():
        declared = declared_manifest_sha.read_text(encoding="utf-8").strip().split()[0]
        if declared != _file_sha256(run_manifest_path):
            raise ValueError("Cue-Ranker run manifest SHA-256 differs from manifest.sha256")
    checkpoint_sha = _file_sha256(checkpoint_path)
    best_record = run_manifest.get("files", {}).get("best") or run_manifest.get("files", {}).get("best_checkpoint")
    if not best_record:
        raise ValueError("Cue-Ranker run manifest does not record the best checkpoint")
    expected_checkpoint = run_manifest_path.parent / str(best_record.get("path", ""))
    if expected_checkpoint.resolve() != checkpoint_path.resolve():
        raise ValueError("Cue-Ranker best checkpoint path differs from the run manifest")
    if checkpoint_sha != best_record.get("sha256"):
        raise ValueError("Cue-Ranker best checkpoint SHA-256 differs from the run manifest")

    dataset_path = Path(dataset_manifest_path) if dataset_manifest_path is not None else None
    if dataset_path is None:
        embedded = contract.get("dataset_manifest_path")
        if embedded:
            dataset_path = Path(embedded)
            if not dataset_path.is_absolute():
                dataset_path = run_manifest_path.parent / dataset_path
    if dataset_path is None or not dataset_path.is_file():
        raise FileNotFoundError("Cue-Ranker Dataset-3 manifest is required for learned inference")
    dataset_sha = _file_sha256(dataset_path)
    if dataset_sha != contract.get("dataset_manifest_sha256"):
        raise ValueError("Cue-Ranker dataset manifest SHA-256 differs from the run contract")
    dataset = _read_json(dataset_path, "Cue-Ranker dataset manifest")
    _validate_dataset_manifest(dataset)
    normalizer = _load_normalizer(dataset_path, dataset)

    try:
        model_config = dict(contract["model"]["config"])
        if "encoder_channels" in model_config:
            model_config["encoder_channels"] = tuple(model_config["encoder_channels"])
        model = CueRankerTemporalModel(CueRankerTemporalConfig(**model_config))
        checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=True)
        _validate_checkpoint(checkpoint, contract, run_manifest.get("run_id"))
        model.load_state_dict(checkpoint["model_state_dict"])
    except Exception as error:
        if isinstance(error, (ValueError, FileNotFoundError)):
            raise
        raise ValueError(f"Cue-Ranker checkpoint cannot be loaded: {error}") from error
    model.eval()
    return LoadedCueRanker(
        model=model,
        run_manifest=run_manifest,
        run_manifest_path=run_manifest_path,
        checkpoint_path=checkpoint_path,
        checkpoint_sha256=checkpoint_sha,
        dataset_manifest=dataset,
        dataset_manifest_path=dataset_path,
        dataset_manifest_sha256=dataset_sha,
        normalizer=normalizer,
    )


def rank_candidates_learned(
    candidates,
    *,
    loaded_ranker: LoadedCueRanker,
    target_sample_rate=44_100,
    analysis=None,
    analysis_root="output/pre_analysis",
    feature_cache_root="output/feature_cache",
    vocal_backend="disabled",
    vocal_model=None,
):
    """Score every accepted Candidate-v2 entry and sort deterministically."""

    candidates = tuple(candidates)
    _validate_hard_filter_contract(candidates)
    candidate_ids = [str(candidate.candidate_id) for candidate in candidates]
    if len(candidate_ids) != len(set(candidate_ids)):
        raise ValueError("learned_cue_ranker_v1 requires unique candidate IDs")
    target_sample_rate = int(target_sample_rate)
    if target_sample_rate <= 0:
        raise ValueError("target_sample_rate must be greater than 0")
    artifacts = {}
    scores = []
    failures = []
    model = loaded_ranker.model
    for candidate in candidates:
        try:
            payload = _candidate_payload(
                candidate,
                candidates,
                loaded_ranker,
                artifacts,
                target_sample_rate=target_sample_rate,
                analysis=analysis,
                analysis_root=analysis_root,
                feature_cache_root=feature_cache_root,
                vocal_backend=vocal_backend,
                vocal_model=vocal_model,
            )
            with torch.no_grad():
                score = float(model(
                    payload["features_a"], payload["features_b"],
                    payload["global_features"], payload["length_condition"],
                    payload["candidate_context"], payload["grid_source_ids"],
                ).item())
            if not math.isfinite(score):
                raise ValueError("Cue-Ranker produced a non-finite candidate score")
            scores.append({"candidate_id": candidate.candidate_id, "score": score})
        except Exception as error:
            failures.append(RankingFailure(candidate.candidate_id, type(error).__name__, str(error)))
    ordered = sorted(scores, key=lambda item: (-item["score"], item["candidate_id"]))
    ranked = tuple(
        CandidateScore(
            candidate_id=item["candidate_id"],
            rank=index,
            total_score=float(item["score"]),
            component_scores={"model_score": float(item["score"])},
            measurements={},
        )
        for index, item in enumerate(ordered, start=1)
    )
    return LearnedCueRankingResult(
        scores=ranked,
        failures=tuple(failures),
        provenance=loaded_ranker.provenance,
        config=LearnedRankingConfig(target_sample_rate=target_sample_rate),
    )


def rank_candidates(*args, **kwargs):
    """Compatibility alias for callers that import a ranker-local function."""

    return rank_candidates_learned(*args, **kwargs)


def _candidate_payload(candidate, all_candidates, loaded_ranker, artifacts, *, target_sample_rate, analysis, analysis_root, feature_cache_root, vocal_backend, vocal_model):
    geometry = geometry_for_length(candidate.transition_length_bars)
    source_key = (candidate.source_track.path, None)
    target_key = (candidate.target_track.path, float(candidate.source_bpm))
    for key, track, bpm in (
        (source_key, candidate.source_track, None),
        (target_key, candidate.target_track, float(candidate.source_bpm)),
    ):
        if key not in artifacts:
            artifacts[key] = extract_or_load_track_features(
                track.path,
                cache_root=feature_cache_root,
                analysis=analysis,
                analysis_root=analysis_root,
                sample_rate=target_sample_rate,
                target_bpm=bpm,
                vocal_backend=vocal_backend,
                vocal_model=vocal_model,
            )
    source_cue = _scale_sample(candidate.source_cutpoint.sample, target_sample_rate)
    target_cue = _scale_sample(candidate.target_cutpoint.sample, target_sample_rate)
    target_cue = int(round(target_cue * float(candidate.target_bpm) / float(candidate.source_bpm)))
    features_a = extract_variable_track_window(
        artifacts[source_key], source_cue, role="source", normalization=loaded_ranker.normalizer,
        transition_length_bars=geometry.transition_length_bars, sequence_length=geometry.sequence_length,
    )
    features_b = extract_variable_track_window(
        artifacts[target_key], target_cue, role="target", normalization=loaded_ranker.normalizer,
        transition_length_bars=geometry.transition_length_bars, sequence_length=geometry.sequence_length,
    )
    global_features = build_variable_global_pair_features(
        features_a, features_b, transition_length_bars=geometry.transition_length_bars,
        sequence_length=geometry.sequence_length, bpm_a=candidate.source_bpm, bpm_b=candidate.target_bpm,
        artifact_a=artifacts[source_key], artifact_b=artifacts[target_key], cue_sample_a=source_cue, cue_sample_b=target_cue,
    )
    row = candidate.to_dict()
    row["group_size"] = len(all_candidates)
    context, grid_ids = build_candidate_context(row, group_size=len(all_candidates))
    return {
        "features_a": torch.as_tensor(features_a, dtype=torch.float32).unsqueeze(0),
        "features_b": torch.as_tensor(features_b, dtype=torch.float32).unsqueeze(0),
        "global_features": torch.as_tensor(global_features, dtype=torch.float32).reshape(1, -1),
        "length_condition": torch.tensor([[geometry.length_condition]], dtype=torch.float32),
        "candidate_context": torch.as_tensor(context, dtype=torch.float32).reshape(1, -1),
        "grid_source_ids": torch.tensor([grid_ids], dtype=torch.long),
    }


def _validate_hard_filter_contract(candidates):
    for candidate in candidates:
        if int(getattr(candidate, "format_version", -1)) != 2:
            raise ValueError("learned_cue_ranker_v1 requires Candidate-v2 entries")
        if candidate.generator != LEARNED_CUE_RANKER_GENERATOR:
            raise ValueError("learned_cue_ranker_v1 requires bar_grid_v2_length_specific candidates")
        if candidate.filter_status != "accepted":
            raise ValueError("learned_cue_ranker_v1 received a non-accepted candidate")
        if candidate.source_cutpoint.count_in_bar != 1 or candidate.target_cutpoint.count_in_bar != 1:
            raise ValueError("learned_cue_ranker_v1 requires downbeat cutpoints")
        if candidate.source_cutpoint.beats_in_bar != 4 or candidate.target_cutpoint.beats_in_bar != 4:
            raise ValueError("learned_cue_ranker_v1 requires 4/4 candidates")
        for grid in (candidate.source_grid, candidate.target_grid):
            if grid is None or grid.fallback_used is not False or not grid.beat_grid_sha256:
                raise ValueError("learned_cue_ranker_v1 requires verified non-fallback grid provenance")


def _validate_dataset_manifest(manifest):
    if int(manifest.get("format_version", -1)) != 3:
        raise ValueError("Cue-Ranker inference requires Dataset Format 3")
    if manifest.get("test") != {"state": "sealed_not_materialized"}:
        raise ValueError("Cue-Ranker dataset is not sealed against test access")
    if not manifest.get("teacher_manifest_sha256") or not manifest.get("teacher_release_sha256") or not manifest.get("teacher_contract_sha256"):
        raise ValueError("Cue-Ranker dataset is missing teacher contract provenance")
    if not manifest.get("teacher_alignment_contract"):
        raise ValueError("Cue-Ranker dataset is missing its teacher alignment contract")
    normalization = manifest.get("normalization", {})
    if normalization.get("fit_scope") != "training_tracks_only":
        raise ValueError("Cue-Ranker normalizer is not training-only")


def _load_normalizer(dataset_path, manifest):
    info = manifest.get("files", {}).get("train_only_normalizer")
    if not info:
        raise ValueError("Cue-Ranker dataset is missing its train-only normalizer")
    path = dataset_path.parent / str(info["path"])
    if _file_sha256(path) != info.get("sha256"):
        raise ValueError("Cue-Ranker train-only normalizer SHA-256 differs from the dataset manifest")
    if manifest.get("normalization", {}).get("sha256") != info.get("sha256"):
        raise ValueError("Cue-Ranker normalization manifest SHA-256 differs from its file record")
    payload = _read_json(path, "Cue-Ranker normalizer")
    statistics = payload.get("statistics", payload)
    if not isinstance(statistics, dict) or statistics.get("fit_scope") != "training_tracks_only":
        raise ValueError("Cue-Ranker train-only normalizer payload has an invalid fit scope")
    expected_universe = manifest.get("universe_manifest_sha256")
    if (
        not _is_sha256(expected_universe)
        or statistics.get("input_universe_manifest_sha256") != expected_universe
    ):
        raise ValueError("Cue-Ranker train-only normalizer universe SHA-256 differs from the dataset")
    expected_source = manifest.get("normalization", {}).get("source_sha256")
    if (
        not _is_sha256(expected_source)
        or statistics.get("source_sha256") != expected_source
    ):
        raise ValueError("Cue-Ranker train-only normalizer source SHA-256 differs from the dataset")
    training_audio_sha256 = statistics.get("training_audio_sha256")
    if (
        not isinstance(training_audio_sha256, list)
        or not training_audio_sha256
        or any(not _is_sha256(value) for value in training_audio_sha256)
    ):
        raise ValueError("Cue-Ranker train-only normalizer training scope is invalid")
    try:
        return FeatureNormalizationStats(
            spectral_flux_log1p_p99=statistics["spectral_flux_log1p_p99"],
            onset_strength_log1p_p99=statistics["onset_strength_log1p_p99"],
            stats_id=statistics["stats_id"],
        )
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("Cue-Ranker train-only normalizer is incomplete") from error


def _validate_checkpoint(checkpoint, contract, run_id):
    if not isinstance(checkpoint, dict) or checkpoint.get("format_version") != CUE_RANKER_RUN_FORMAT_VERSION:
        raise ValueError("Cue-Ranker checkpoint format is invalid")
    if checkpoint.get("runner_name") != CUE_RANKER_RUNNER_NAME or checkpoint.get("model_name") != LEARNED_CUE_RANKER_NAME:
        raise ValueError("Cue-Ranker checkpoint model contract is invalid")
    if checkpoint.get("run_id") != run_id or checkpoint.get("contract") != contract:
        raise ValueError("Cue-Ranker checkpoint contract differs from its run manifest")
    if not isinstance(checkpoint.get("model_state_dict"), dict):
        raise ValueError("Cue-Ranker checkpoint has no model_state_dict")


def _scale_sample(sample, sample_rate):
    return int(round(int(sample) * int(sample_rate) / 44_100))


def _read_json(path, label):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception as error:
        raise ValueError(f"{label} is unreadable: {path}") from error


def _file_sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _is_sha256(value):
    value = str(value or "").lower()
    return len(value) == 64 and all(character in "0123456789abcdef" for character in value)


__all__ = [
    "LEARNED_CUE_RANKER_FORMAT_VERSION",
    "LEARNED_CUE_RANKER_NAME",
    "LearnedCueRankingResult",
    "LoadedCueRanker",
    "load_learned_cue_ranker",
    "rank_candidates",
    "rank_candidates_learned",
]
