"""Batch rendering for accepted transition candidates."""

import argparse
from dataclasses import dataclass, replace
import hashlib
import json
import os
from pathlib import Path
import uuid
import sys

import soundfile as sf

from src.analysis.pre_analysis import PreAnalysis
from src.candidates import CandidateGenerationConfig, CandidateGenerationResult, TransitionCandidate
from src.candidates.variable import BASELINE_LENGTHS, BaselineCandidateGenerationConfig, VariableCandidateGenerationConfig
from src.pipeline import (
    CUTTERS,
    DEFAULT_SAMPLE_RATE,
    RENDER_RESULT_FORMAT_VERSION,
    DEFAULT_PREVIEW_SECONDS_AFTER,
    DEFAULT_PREVIEW_SECONDS_BEFORE,
    generate_transition_candidates,
    render_transition,
)
from src.ranking import (
    CandidateRankingResult,
    FeatureRankingConfig,
    RenderedTransitionInput,
    RenderedTransitionMetricConfig,
    RenderedTransitionRankingResult,
    rank_candidates,
    rank_rendered_transitions,
    load_learned_cue_ranker,
    rank_candidates_learned,
)
from src.variable_rendering import render_variable_transition


BATCH_MANIFEST_FORMAT_VERSION = 1
DEFAULT_RENDERERS = ("simple", "fade", "equal_power")
RANKING_METHODS = ("feature_baseline_v3", "learned_cue_ranker_v1", "mert_continuation_v1")


@dataclass(frozen=True)
class RenderedVariant:
    candidate_id: str
    renderer: str
    output_file: str
    sample_rate: int
    sample_count: int
    transition_start_sample: int
    transition_end_sample: int
    tempo_backend: str
    candidate_rank: int | None
    candidate_score: float | None
    transition_rank: int | None = None
    transition_score: float | None = None
    transition_length_bars: int | None = None
    transition_length_beats: int | None = None
    selection_rank: int | None = None
    selection_score: float | None = None
    selection_method: str = "feature_baseline_v3"

    def to_dict(self):
        payload = {
            "candidate_id": self.candidate_id,
            "renderer": self.renderer,
            "output_file": self.output_file,
            "sample_rate": self.sample_rate,
            "sample_count": self.sample_count,
            "transition_start_sample": self.transition_start_sample,
            "transition_end_sample": self.transition_end_sample,
            "tempo_backend": self.tempo_backend,
            "candidate_rank": self.candidate_rank,
            "candidate_score": self.candidate_score,
            "transition_rank": self.transition_rank,
            "transition_score": self.transition_score,
            "selection_rank": self.selection_rank,
            "selection_score": self.selection_score,
            "selection_method": self.selection_method,
            "status": "rendered",
        }
        if self.transition_length_bars is not None:
            payload["transition_length_bars"] = int(self.transition_length_bars)
            payload["transition_length_beats"] = int(self.transition_length_beats)
        return payload


@dataclass(frozen=True)
class RenderFailure:
    candidate_id: str
    renderer: str
    error_type: str
    message: str

    def to_dict(self):
        return {
            "candidate_id": self.candidate_id,
            "renderer": self.renderer,
            "error_type": self.error_type,
            "message": self.message,
            "status": "failed",
        }


@dataclass(frozen=True)
class BatchRenderResult:
    output_directory: Path
    manifest_path: Path
    candidate_generation: CandidateGenerationResult
    candidate_ranking: CandidateRankingResult
    rendered_transition_ranking: RenderedTransitionRankingResult
    rendered_variants: tuple[RenderedVariant, ...]
    failures: tuple[RenderFailure, ...]
    top_k: int | None
    preview_seconds_before: float | None
    preview_seconds_after: float | None
    ranking_method: str = "feature_baseline_v3"
    cue_ranking: object | None = None
    candidate_request_config: dict | None = None


def render_candidate_batch(
    candidate_generation: CandidateGenerationResult,
    output_directory,
    *,
    renderers=DEFAULT_RENDERERS,
    target_sample_rate=DEFAULT_SAMPLE_RATE,
    analysis=None,
    analysis_location=None,
    ranking_config=None,
    transition_metric_config=None,
    top_k=5,
    overwrite=False,
    preview_seconds_before=DEFAULT_PREVIEW_SECONDS_BEFORE,
    preview_seconds_after=DEFAULT_PREVIEW_SECONDS_AFTER,
    ranking_method="feature_baseline_v3",
    cue_ranker_run=None,
    cue_ranker_dataset=None,
    cue_ranker_feature_cache_root="output/feature_cache",
    cue_ranker_analysis_root="output/pre_analysis",
    cue_ranker_vocal_backend="disabled",
    cue_ranker_vocal_model=None,
    cue_ranker=None,
    candidate_request_config=None,
) -> BatchRenderResult:
    """Rank candidates and render all or the requested top K with each baseline.

    The function creates ``manifest.json`` even when no candidate was accepted,
    so hard-filter outcomes remain auditable. Existing output files are never
    overwritten unless ``overwrite=True`` is explicitly requested.
    """
    renderers = _validate_renderers(renderers)
    ranking_method = _validate_ranking_method(ranking_method)
    if ranking_method == "mert_continuation_v1" and (
        candidate_generation.approximate_grid_policy != "reject" or
        any((c.transition_length_bars, c.transition_length_beats) != (4, 16)
            for c in candidate_generation.candidates)
    ):
        raise ValueError("mert_continuation_v1 requires detected grids and four 4/4 bars")
    if ranking_method == "learned_cue_ranker_v1":
        if int(candidate_generation.format_version) != 2:
            raise ValueError("learned_cue_ranker_v1 requires Candidate-v2 generation")
        if candidate_generation.approximate_grid_policy != "reject":
            raise ValueError("learned_cue_ranker_v1 requires approximate_grid_policy='reject'")
    if top_k is not None and int(top_k) <= 0:
        raise ValueError("top_k must be greater than 0")
    top_k = None if top_k is None else int(top_k)
    if ranking_config is None:
        ranking_config = FeatureRankingConfig()
    if transition_metric_config is None:
        transition_metric_config = RenderedTransitionMetricConfig()
    _validate_preview_durations(preview_seconds_before, preview_seconds_after)
    loaded_ranker = None
    if ranking_method == "learned_cue_ranker_v1":
        loaded_ranker = cue_ranker or load_learned_cue_ranker(
            cue_ranker_run,
            dataset_manifest_path=cue_ranker_dataset,
        )

    cue_ranking = None
    common_candidates = candidate_generation.candidates
    if ranking_method == "mert_continuation_v1":
        from src.ranking.continuation import rank_continuations
        if analysis is None:
            analysis = _continuation_analysis(analysis_location)
        cue_ranking = rank_continuations(common_candidates, analysis, target_sample_rate)
        eligible_ids = {score.candidate_id for score in cue_ranking.scores}
        common_candidates = [c for c in common_candidates if c.candidate_id in eligible_ids]
    candidate_ranking = rank_candidates(
        common_candidates,
        target_sample_rate=target_sample_rate,
        config=ranking_config,
    )
    if ranking_method == "learned_cue_ranker_v1":
        cue_ranking = rank_candidates_learned(
            candidate_generation.candidates,
            loaded_ranker=loaded_ranker,
            target_sample_rate=target_sample_rate,
            analysis=analysis,
            analysis_root=cue_ranker_analysis_root,
            feature_cache_root=cue_ranker_feature_cache_root,
            vocal_backend=cue_ranker_vocal_backend,
            vocal_model=cue_ranker_vocal_model,
        )
    selection_ranking = cue_ranking if cue_ranking is not None else candidate_ranking
    rank_by_id = {score.candidate_id: score for score in candidate_ranking.scores}
    selection_by_id = {score.candidate_id: score for score in selection_ranking.scores}
    candidate_by_id = {
        candidate.candidate_id: candidate for candidate in candidate_generation.candidates
    }
    ranked_candidates = [
        candidate_by_id[score.candidate_id] for score in selection_ranking.scores
    ]
    ranked_ids = {candidate.candidate_id for candidate in ranked_candidates}
    if ranking_method == "feature_baseline_v3":
        ranked_candidates.extend(
            candidate
            for candidate in candidate_generation.candidates
            if candidate.candidate_id not in ranked_ids
        )
    selected_candidates = ranked_candidates if top_k is None else ranked_candidates[:top_k]
    # The learned contract backfills a candidate that cannot be rendered.  A
    # baseline batch keeps its historical fixed top-K behaviour unchanged.
    candidates_to_attempt = (
        ranked_candidates
        if ranking_method == "learned_cue_ranker_v1"
        else selected_candidates
    )

    output_directory = Path(output_directory)
    manifest_path = output_directory / "manifest.json"
    output_targets = [
        output_directory / "rendered" / _rendered_filename(index, candidate, renderer)
        for index, candidate in enumerate(candidates_to_attempt, start=1)
        for renderer in renderers
    ]
    _preflight_output_paths([manifest_path, *output_targets], overwrite=overwrite)

    output_directory.mkdir(parents=True, exist_ok=True)
    rendered_directory = output_directory / "rendered"
    rendered_directory.mkdir(parents=True, exist_ok=True)

    rendered_variants = []
    rendered_transition_inputs = []
    failures = []
    learned_selected_candidate_ids = []
    learned_attempted_candidate_ids = []
    learned_skipped_candidate_ids = []
    learned_renderability = []
    for index, candidate in enumerate(candidates_to_attempt, start=1):
        if (
            ranking_method == "learned_cue_ranker_v1"
            and top_k is not None
            and len(learned_selected_candidate_ids) >= top_k
        ):
            break
        rendered_before_candidate = len(rendered_variants)
        candidate_score = rank_by_id.get(candidate.candidate_id)
        for renderer in renderers:
            output_path = rendered_directory / _rendered_filename(index, candidate, renderer)
            try:
                if int(getattr(candidate, "format_version", 1)) == 2:
                    result = render_variable_transition(
                        candidate,
                        renderer=renderer,
                        target_sample_rate=target_sample_rate,
                        analysis=analysis,
                        analysis_location=analysis_location,
                        preview_seconds_before=preview_seconds_before,
                        preview_seconds_after=preview_seconds_after,
                    )
                else:
                    result = render_transition(
                        candidate.source_track.path,
                        candidate.target_track.path,
                        candidate.source_cutpoint.sample,
                        candidate.target_cutpoint.sample,
                        renderer=renderer,
                        fade_beats=candidate.transition_length_beats,
                        baseline_bars=candidate.transition_length_bars if candidate.format_version == 3 else None,
                        target_sample_rate=target_sample_rate,
                        analysis=analysis,
                        analysis_location=analysis_location,
                        source_bpm=candidate.source_bpm,
                        target_bpm=candidate.target_bpm,
                        preview_seconds_before=preview_seconds_before,
                        preview_seconds_after=preview_seconds_after,
                    )
                _write_audio_atomic(output_path, result.audio, result.sample_rate)
                rendered_variants.append(
                    RenderedVariant(
                        candidate_id=candidate.candidate_id,
                        renderer=renderer,
                        output_file=str(output_path.relative_to(output_directory)),
                        sample_rate=result.sample_rate,
                        sample_count=int(result.audio.shape[-1]),
                        transition_start_sample=result.transition_start_sample,
                        transition_end_sample=result.transition_end_sample,
                        tempo_backend=result.tempo_backend,
                        candidate_rank=(
                            None if candidate_score is None else candidate_score.rank
                        ),
                        candidate_score=(
                            None if candidate_score is None else candidate_score.total_score
                        ),
                        transition_length_bars=(
                            int(candidate.transition_length_bars)
                            if candidate.format_version >= 2
                            else None
                        ),
                        transition_length_beats=(
                            int(candidate.transition_length_beats)
                            if candidate.format_version >= 2
                            else None
                        ),
                        selection_rank=(
                            None
                            if selection_by_id.get(candidate.candidate_id) is None
                            else selection_by_id[candidate.candidate_id].rank
                        ),
                        selection_score=(
                            None
                            if selection_by_id.get(candidate.candidate_id) is None
                            else selection_by_id[candidate.candidate_id].total_score
                        ),
                        selection_method=ranking_method,
                    )
                )
                rendered_transition_inputs.append(
                    RenderedTransitionInput(
                        candidate_id=candidate.candidate_id,
                        renderer=renderer,
                        audio=result.audio,
                        sample_rate=result.sample_rate,
                        transition_start_sample=result.transition_start_sample,
                        transition_end_sample=result.transition_end_sample,
                        transition_length_beats=candidate.transition_length_beats,
                        bpm=candidate.source_bpm,
                    )
                )
            except Exception as error:  # Export all independent variants and record each failure.
                failures.append(
                    RenderFailure(
                        candidate_id=candidate.candidate_id,
                        renderer=renderer,
                        error_type=type(error).__name__,
                        message=str(error),
                    )
                )
        if ranking_method == "learned_cue_ranker_v1":
            learned_attempted_candidate_ids.append(candidate.candidate_id)
            if len(rendered_variants) > rendered_before_candidate:
                learned_selected_candidate_ids.append(candidate.candidate_id)
                learned_renderability.append(
                    {"candidate_id": candidate.candidate_id, "status": "rendered"}
                )
            else:
                learned_skipped_candidate_ids.append(candidate.candidate_id)
                learned_renderability.append(
                    {"candidate_id": candidate.candidate_id, "status": "render_failed"}
                )

    rendered_transition_ranking = rank_rendered_transitions(
        rendered_transition_inputs,
        config=transition_metric_config,
    )
    transition_score_by_variant = {
        (score.candidate_id, score.renderer): score
        for score in rendered_transition_ranking.scores
    }
    rendered_variants = [
        replace(
            variant,
            transition_rank=transition_score_by_variant[
                (variant.candidate_id, variant.renderer)
            ].rank,
            transition_score=transition_score_by_variant[
                (variant.candidate_id, variant.renderer)
            ].total_score,
        )
        if (variant.candidate_id, variant.renderer) in transition_score_by_variant
        else variant
        for variant in rendered_variants
    ]

    batch_result = BatchRenderResult(
        output_directory=output_directory,
        manifest_path=manifest_path,
        candidate_generation=candidate_generation,
        candidate_ranking=candidate_ranking,
        rendered_transition_ranking=rendered_transition_ranking,
        rendered_variants=tuple(rendered_variants),
        failures=tuple(failures),
        top_k=top_k,
        preview_seconds_before=preview_seconds_before,
        preview_seconds_after=preview_seconds_after,
        ranking_method=ranking_method,
        cue_ranking=(
            cue_ranking
            if ranking_method != "learned_cue_ranker_v1"
            else cue_ranking.with_selection(
                learned_selected_candidate_ids,
                renderability_preflight=learned_renderability
                + [
                    {
                        "candidate_id": candidate.candidate_id,
                        "status": "not_attempted_after_top_k",
                    }
                    for candidate in ranked_candidates
                    if candidate.candidate_id not in learned_attempted_candidate_ids
                ]
                + [
                    {
                        "candidate_id": failure.candidate_id,
                        "status": "score_failed",
                        "error_type": failure.error_type,
                        "message": failure.message,
                    }
                    for failure in cue_ranking.failures
                ],
                backfill={
                    "requested_top_k": top_k,
                    "selected_count": len(learned_selected_candidate_ids),
                    "partial": len(learned_selected_candidate_ids) < (
                        len(candidate_generation.candidates) if top_k is None else top_k
                    ),
                    "attempted_candidate_ids": learned_attempted_candidate_ids,
                    "skipped_candidate_ids": learned_skipped_candidate_ids,
                },
            )
        ),
        candidate_request_config=candidate_request_config,
    )
    _write_json_atomic(manifest_path, _manifest_payload(batch_result, renderers))
    return batch_result


def generate_and_render_batch(
    song1,
    song2,
    output_directory,
    *,
    candidate_config=None,
    renderers=DEFAULT_RENDERERS,
    target_sample_rate=DEFAULT_SAMPLE_RATE,
    analysis=None,
    analysis_location=None,
    ranking_config=None,
    transition_metric_config=None,
    top_k=5,
    overwrite=False,
    preview_seconds_before=DEFAULT_PREVIEW_SECONDS_BEFORE,
    preview_seconds_after=DEFAULT_PREVIEW_SECONDS_AFTER,
    ranking_method="feature_baseline_v3",
    cue_ranker_run=None,
    cue_ranker_dataset=None,
    cue_ranker_feature_cache_root="output/feature_cache",
    cue_ranker_analysis_root="output/pre_analysis",
    cue_ranker_vocal_backend="disabled",
    cue_ranker_vocal_model=None,
) -> BatchRenderResult:
    """Generate, rank, and render accepted candidate variants."""
    ranking_method = _validate_ranking_method(ranking_method)
    if candidate_config is None:
        if ranking_method == "learned_cue_ranker_v1":
            candidate_config = VariableCandidateGenerationConfig(transition_lengths_bars=(2, 4))
        elif ranking_method == "mert_continuation_v1":
            candidate_config = BaselineCandidateGenerationConfig(transition_lengths_bars=(4,))
        else:
            candidate_config = CandidateGenerationConfig()
    if ranking_method == "learned_cue_ranker_v1" and int(getattr(candidate_config, "format_version", 1)) != 2:
        raise ValueError(
            "learned_cue_ranker_v1 requires Candidate-v2 generation; use "
            "VariableCandidateGenerationConfig with transition lengths 2/4/6/8"
        )
    if ranking_method == "mert_continuation_v1":
        if candidate_config.transition_lengths_bars != (4,) or candidate_config.approximate_grid_policy != "reject":
            raise ValueError("mert_continuation_v1 requires detected grids and four 4/4 bars")
        if analysis is None:
            analysis = _continuation_analysis(analysis_location)
    if analysis is None:
        cache_path = Path("output") / "pre_analysis" if analysis_location is None else Path(analysis_location)
        analysis = PreAnalysis(str(cache_path) + os.sep)

    candidate_generation = generate_transition_candidates(
        song1,
        song2,
        analysis=analysis,
        target_sample_rate=target_sample_rate,
        config=candidate_config,
    )
    return render_candidate_batch(
        candidate_generation,
        output_directory,
        renderers=renderers,
        target_sample_rate=target_sample_rate,
        analysis=analysis,
        ranking_config=ranking_config,
        transition_metric_config=transition_metric_config,
        top_k=top_k,
        overwrite=overwrite,
        preview_seconds_before=preview_seconds_before,
        preview_seconds_after=preview_seconds_after,
        ranking_method=ranking_method,
        cue_ranker_run=cue_ranker_run,
        cue_ranker_dataset=cue_ranker_dataset,
        cue_ranker_feature_cache_root=cue_ranker_feature_cache_root,
        cue_ranker_analysis_root=cue_ranker_analysis_root,
        cue_ranker_vocal_backend=cue_ranker_vocal_backend,
        cue_ranker_vocal_model=cue_ranker_vocal_model,
        candidate_request_config=_candidate_request_config(candidate_config),
    )


def _continuation_analysis(location):
    from src.analysis.pre_analysis import PartialPreAnalysis
    from src.features.p07_extract import ANALYSIS
    return PartialPreAnalysis(str(location or ANALYSIS.parent))


def _validate_renderers(renderers):
    renderers = tuple(renderers)
    if not renderers:
        raise ValueError("At least one renderer must be requested")
    unknown = [renderer for renderer in renderers if renderer not in CUTTERS]
    if unknown:
        raise ValueError(f"Unknown renderer(s): {', '.join(unknown)}")
    if len(set(renderers)) != len(renderers):
        raise ValueError("Renderers must not contain duplicates")
    return renderers


def _validate_ranking_method(ranking_method):
    ranking_method = str(ranking_method)
    if ranking_method not in RANKING_METHODS:
        raise ValueError(
            f"Unknown ranking method {ranking_method!r}; choose one of {', '.join(RANKING_METHODS)}"
        )
    return ranking_method


def _validate_preview_durations(seconds_before, seconds_after):
    if seconds_before is None and seconds_after is None:
        return
    if seconds_before is None or seconds_after is None:
        raise ValueError(
            "preview_seconds_before and preview_seconds_after must both be set or both be None"
        )
    if seconds_before < 0 or seconds_after < 0:
        raise ValueError("Preview durations must be greater than or equal to 0")
    if seconds_before == 0 and seconds_after == 0:
        raise ValueError("Preview needs audio before or after the cutpoint")


def _rendered_filename(index, candidate: TransitionCandidate, renderer):
    return f"{index:04d}__{candidate.candidate_id}__{renderer}.wav"


def _preflight_output_paths(paths, *, overwrite):
    if overwrite:
        return
    existing_paths = [path for path in paths if path.exists()]
    if existing_paths:
        joined_paths = ", ".join(str(path) for path in existing_paths[:3])
        raise FileExistsError(
            "Batch output already exists. Choose a new output directory or pass overwrite=True: "
            f"{joined_paths}"
        )


def _write_audio_atomic(path, audio, sample_rate):
    temporary_path = _temporary_path(path)
    try:
        sf.write(str(temporary_path), audio.T, int(sample_rate), format="WAV")
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)


def _write_json_atomic(path, payload):
    temporary_path = _temporary_path(path)
    try:
        temporary_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)


def _temporary_path(path):
    return path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")


def _manifest_payload(batch_result, renderers):
    variable_contract = int(batch_result.candidate_generation.format_version) == 2
    payload = {
        "format_version": 2 if variable_contract else BATCH_MANIFEST_FORMAT_VERSION,
        "render_protocol_version": 6 if variable_contract else RENDER_RESULT_FORMAT_VERSION,
        "renderers": list(renderers),
        "ranking_method": batch_result.ranking_method,
        "candidate_generation": batch_result.candidate_generation.to_dict(),
        "candidate_ranking": batch_result.candidate_ranking.to_dict(),
        "rendered_transition_ranking": batch_result.rendered_transition_ranking.to_dict(),
        "render_selection": {
            "top_k": batch_result.top_k,
            "candidate_ids": list(
                dict.fromkeys(
                    variant.candidate_id for variant in batch_result.rendered_variants
                )
            ),
        },
        "render_preview": {
            "seconds_before_source_cutpoint": batch_result.preview_seconds_before,
            "seconds_after_source_cutpoint": batch_result.preview_seconds_after,
        },
        "rendered_variants": [variant.to_dict() for variant in batch_result.rendered_variants],
        "failures": [failure.to_dict() for failure in batch_result.failures],
    }
    if batch_result.candidate_request_config is not None:
        payload["candidate_request_config"] = dict(batch_result.candidate_request_config)
        payload["candidate_request_config_sha256"] = _canonical_json_sha256(
            batch_result.candidate_request_config
        )
    if batch_result.candidate_generation.candidates:
        first_candidate = batch_result.candidate_generation.candidates[0]
        payload["source_audio_sha256"] = str(first_candidate.source_track.sha256).lower()
        payload["target_audio_sha256"] = str(first_candidate.target_track.sha256).lower()
    if batch_result.cue_ranking is not None:
        payload["cue_ranking"] = batch_result.cue_ranking.to_dict()
    return payload


def _candidate_request_config(candidate_config):
    generator = getattr(candidate_config, "generator", "bar_grid_v1")
    return {
        "format_version": int(getattr(candidate_config, "format_version", 1)),
        "candidate_generator": generator,
        "transition_lengths_bars": [int(value) for value in candidate_config.transition_lengths_bars],
        "source_boundary_count": getattr(candidate_config, "source_boundary_count", None),
        "target_boundary_count": getattr(candidate_config, "target_boundary_count", None),
        "max_tempo_relative_difference": float(candidate_config.max_tempo_relative_difference),
        "approximate_grid_policy": str(candidate_config.approximate_grid_policy),
    }


def _canonical_json_sha256(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def build_argument_parser():
    parser = argparse.ArgumentParser(
        description="Generate bar-aligned transition candidates and render them as a batch.",
    )
    parser.add_argument("song1", help="Source track: audio before each transition.")
    parser.add_argument("song2", help="Target track: audio after each transition.")
    parser.add_argument(
        "--output-dir",
        required=True,
        help="New or empty directory for rendered WAV files and manifest.json.",
    )
    parser.add_argument(
        "--ranking-method",
        choices=RANKING_METHODS,
        default="feature_baseline_v3",
        help="Candidate selection method (default: feature_baseline_v3).",
    )
    parser.add_argument(
        "--cue-ranker-run",
        help="Completed learned_cue_ranker_v1 run directory or best checkpoint.",
    )
    parser.add_argument(
        "--cue-ranker-dataset",
        help="SHA-bound Cue-Ranker Dataset-3 manifest required for learned inference.",
    )
    parser.add_argument(
        "--cue-ranker-feature-cache-root",
        default="output/feature_cache",
        help="Feature-cache root for learned inference.",
    )
    parser.add_argument(
        "--cue-ranker-vocal-backend",
        choices=("disabled", "demucs", "roformer"),
        default="disabled",
        help="Vocal feature backend for learned inference (default: disabled).",
    )
    parser.add_argument(
        "--renderers",
        nargs="+",
        choices=tuple(CUTTERS),
        default=DEFAULT_RENDERERS,
        help="Renderers to export (default: all baselines).",
    )
    lengths = parser.add_mutually_exclusive_group()
    lengths.add_argument("--baseline-bars", nargs="+", type=int, choices=BASELINE_LENGTHS,
                         help="Baseline 4/4 windows with common overlap at each requested length.")
    lengths.add_argument(
        "--transition-bars",
        nargs="+",
        type=int,
        help="Candidate lengths (default: 4 for MERT continuation, otherwise 2 4).",
    )
    parser.add_argument(
        "--source-boundaries",
        type=int,
        help="Limit the source search to the last N usable boundaries (default: all).",
    )
    parser.add_argument(
        "--target-boundaries",
        type=int,
        help="Limit the target downbeat search to the first N usable boundaries (default: all).",
    )
    parser.add_argument(
        "--max-tempo-difference",
        type=float,
        default=0.15,
        help="Maximum symmetric relative BPM difference, e.g. 0.15 for 15%% (default: 0.15).",
    )
    parser.add_argument(
        "--approximate-grid-policy",
        choices=("reject", "allow"),
        default="reject",
        help="Reject fallback/unknown downbeat grids or allow them explicitly (default: reject).",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Render only the top K candidates selected by --ranking-method (default: 5).",
    )
    parser.add_argument(
        "--target-sample-rate",
        type=int,
        default=DEFAULT_SAMPLE_RATE,
        help=f"Internal/output sample rate (default: {DEFAULT_SAMPLE_RATE}).",
    )
    parser.add_argument(
        "--analysis-location",
        help="Optional analysis-cache directory (default: output/pre_analysis).",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Allow replacing same-named exported files in --output-dir.",
    )
    parser.add_argument(
        "--preview-before-seconds",
        type=float,
        default=DEFAULT_PREVIEW_SECONDS_BEFORE,
        help=f"Seconds to retain before each source cutpoint (default: {DEFAULT_PREVIEW_SECONDS_BEFORE:g}).",
    )
    parser.add_argument(
        "--preview-after-seconds",
        type=float,
        default=DEFAULT_PREVIEW_SECONDS_AFTER,
        help=f"Seconds to retain after each source cutpoint (default: {DEFAULT_PREVIEW_SECONDS_AFTER:g}).",
    )
    return parser


def main():
    args = build_argument_parser().parse_args()
    if args.transition_bars is None:
        args.transition_bars = (4,) if args.ranking_method == "mert_continuation_v1" else (2, 4)
    config_type = (BaselineCandidateGenerationConfig if args.baseline_bars is not None
                   or args.ranking_method == "mert_continuation_v1"
                   or any(n in (1, 3) for n in args.transition_bars) else VariableCandidateGenerationConfig)
    candidate_config = config_type(
        transition_lengths_bars=tuple(args.baseline_bars or args.transition_bars),
        source_boundary_count=args.source_boundaries,
        target_boundary_count=args.target_boundaries,
        max_tempo_relative_difference=args.max_tempo_difference,
        approximate_grid_policy=args.approximate_grid_policy,
    )
    try:
        result = generate_and_render_batch(
            args.song1,
            args.song2,
            args.output_dir,
            candidate_config=candidate_config,
            renderers=tuple(args.renderers),
            target_sample_rate=args.target_sample_rate,
            analysis_location=args.analysis_location,
            top_k=args.top_k,
            overwrite=args.overwrite,
            ranking_method=args.ranking_method,
            cue_ranker_run=args.cue_ranker_run,
            cue_ranker_dataset=args.cue_ranker_dataset,
            cue_ranker_feature_cache_root=args.cue_ranker_feature_cache_root,
            cue_ranker_analysis_root=args.analysis_location or "output/pre_analysis",
            cue_ranker_vocal_backend=args.cue_ranker_vocal_backend,
            preview_seconds_before=args.preview_before_seconds,
            preview_seconds_after=args.preview_after_seconds,
        )
    except (FileNotFoundError, ValueError) as error:
        if args.ranking_method != "learned_cue_ranker_v1":
            raise
        print(
            f"learned_cue_ranker_v1 preflight failed: {type(error).__name__}: {error}",
            file=sys.stderr,
        )
        return 1
    print(
        f"Generated {len(result.candidate_generation.candidates)} candidates; "
        f"rendered {len(result.rendered_variants)} WAV files; "
        f"recorded {len(result.failures)} render failures and "
        f"{len(result.rendered_transition_ranking.failures)} transition-metric failures."
    )
    print(f"Manifest: {result.manifest_path}")
    for score in (result.cue_ranking or result.candidate_ranking).scores[:3]:
        print(f"Rank {score.rank}: {score.candidate_id} (score={score.total_score:.3f})")
    for score in result.rendered_transition_ranking.scores[:3]:
        print(
            f"Rendered rank {score.rank}: {score.variant_id} "
            f"(score={score.total_score:.3f})"
        )
    if result.failures or result.rendered_transition_ranking.failures or (result.cue_ranking and result.cue_ranking.failures):
        return 1
    if not result.candidate_generation.candidates:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
