"""Batch rendering for accepted transition candidates."""

import argparse
from dataclasses import dataclass, replace
import json
import os
from pathlib import Path
import uuid

import soundfile as sf

from src.analysis.pre_analysis import PreAnalysis
from src.candidates import CandidateGenerationConfig, CandidateGenerationResult, TransitionCandidate
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
)


BATCH_MANIFEST_FORMAT_VERSION = 1
DEFAULT_RENDERERS = ("simple", "fade", "equal_power", "tempo_fade")


@dataclass(frozen=True)
class RenderedVariant:
    candidate_id: str
    renderer: str
    output_file: str
    sample_rate: int
    sample_count: int
    transition_start_sample: int
    transition_end_sample: int
    candidate_rank: int | None
    candidate_score: float | None
    transition_rank: int | None = None
    transition_score: float | None = None

    def to_dict(self):
        return {
            "candidate_id": self.candidate_id,
            "renderer": self.renderer,
            "output_file": self.output_file,
            "sample_rate": self.sample_rate,
            "sample_count": self.sample_count,
            "transition_start_sample": self.transition_start_sample,
            "transition_end_sample": self.transition_end_sample,
            "candidate_rank": self.candidate_rank,
            "candidate_score": self.candidate_score,
            "transition_rank": self.transition_rank,
            "transition_score": self.transition_score,
            "status": "rendered",
        }


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
) -> BatchRenderResult:
    """Rank candidates and render all or the requested top K with each baseline.

    The function creates ``manifest.json`` even when no candidate was accepted,
    so hard-filter outcomes remain auditable. Existing output files are never
    overwritten unless ``overwrite=True`` is explicitly requested.
    """
    renderers = _validate_renderers(renderers)
    if top_k is not None and int(top_k) <= 0:
        raise ValueError("top_k must be greater than 0")
    top_k = None if top_k is None else int(top_k)
    if ranking_config is None:
        ranking_config = FeatureRankingConfig()
    if transition_metric_config is None:
        transition_metric_config = RenderedTransitionMetricConfig()
    _validate_preview_durations(preview_seconds_before, preview_seconds_after)

    candidate_ranking = rank_candidates(
        candidate_generation.candidates,
        target_sample_rate=target_sample_rate,
        config=ranking_config,
    )
    rank_by_id = {score.candidate_id: score for score in candidate_ranking.scores}
    candidate_by_id = {
        candidate.candidate_id: candidate for candidate in candidate_generation.candidates
    }
    ranked_candidates = [
        candidate_by_id[score.candidate_id] for score in candidate_ranking.scores
    ]
    ranked_ids = {candidate.candidate_id for candidate in ranked_candidates}
    ranked_candidates.extend(
        candidate
        for candidate in candidate_generation.candidates
        if candidate.candidate_id not in ranked_ids
    )
    selected_candidates = ranked_candidates if top_k is None else ranked_candidates[:top_k]

    output_directory = Path(output_directory)
    manifest_path = output_directory / "manifest.json"
    output_targets = [
        output_directory / "rendered" / _rendered_filename(index, candidate, renderer)
        for index, candidate in enumerate(selected_candidates, start=1)
        for renderer in renderers
    ]
    _preflight_output_paths([manifest_path, *output_targets], overwrite=overwrite)

    output_directory.mkdir(parents=True, exist_ok=True)
    rendered_directory = output_directory / "rendered"
    rendered_directory.mkdir(parents=True, exist_ok=True)

    rendered_variants = []
    rendered_transition_inputs = []
    failures = []
    for index, candidate in enumerate(selected_candidates, start=1):
        candidate_score = rank_by_id.get(candidate.candidate_id)
        for renderer in renderers:
            output_path = rendered_directory / _rendered_filename(index, candidate, renderer)
            try:
                result = render_transition(
                    candidate.source_track.path,
                    candidate.target_track.path,
                    candidate.source_cutpoint.sample,
                    candidate.target_cutpoint.sample,
                    renderer=renderer,
                    fade_beats=candidate.transition_length_beats,
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
                        candidate_rank=(
                            None if candidate_score is None else candidate_score.rank
                        ),
                        candidate_score=(
                            None if candidate_score is None else candidate_score.total_score
                        ),
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
) -> BatchRenderResult:
    """Generate, rank, and render accepted candidate variants."""
    if candidate_config is None:
        candidate_config = CandidateGenerationConfig()
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
    )


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
    return {
        "format_version": BATCH_MANIFEST_FORMAT_VERSION,
        "render_protocol_version": RENDER_RESULT_FORMAT_VERSION,
        "renderers": list(renderers),
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
        "--renderers",
        nargs="+",
        choices=DEFAULT_RENDERERS,
        default=DEFAULT_RENDERERS,
        help="Renderers to export (default: all baselines).",
    )
    parser.add_argument(
        "--transition-bars",
        nargs="+",
        type=int,
        default=(2, 4),
        help="Candidate transition lengths in bars (default: 2 4).",
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
        "--top-k",
        type=int,
        default=5,
        help="Render only the top K feature-ranked candidates (default: 5).",
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
    candidate_config = CandidateGenerationConfig(
        transition_lengths_bars=tuple(args.transition_bars),
        source_boundary_count=args.source_boundaries,
        target_boundary_count=args.target_boundaries,
        max_tempo_relative_difference=args.max_tempo_difference,
    )
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
        preview_seconds_before=args.preview_before_seconds,
        preview_seconds_after=args.preview_after_seconds,
    )
    print(
        f"Generated {len(result.candidate_generation.candidates)} candidates; "
        f"rendered {len(result.rendered_variants)} WAV files; "
        f"recorded {len(result.failures)} render failures and "
        f"{len(result.rendered_transition_ranking.failures)} transition-metric failures."
    )
    print(f"Manifest: {result.manifest_path}")
    for score in result.candidate_ranking.scores[:3]:
        print(f"Rank {score.rank}: {score.candidate_id} (score={score.total_score:.3f})")
    for score in result.rendered_transition_ranking.scores[:3]:
        print(
            f"Rendered rank {score.rank}: {score.variant_id} "
            f"(score={score.total_score:.3f})"
        )
    if result.failures or result.rendered_transition_ranking.failures:
        return 1
    if not result.candidate_generation.candidates:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
