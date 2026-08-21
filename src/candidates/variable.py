"""Additive variable-length candidate generation contract."""

from dataclasses import dataclass
import hashlib
import json
import math
from numbers import Real
from typing import Sequence

from src.analysis.models import BeatGridMetadata, unknown_grid_metadata

from .generation import (
    _Grid,
    _following_window_beats,
    _parse_grid,
    _to_cutpoint,
    _window_beats,
)
from .models import (
    CandidateGenerationResult,
    CandidateRejection,
    TrackReference,
    TransitionCandidate,
)


VARIABLE_CANDIDATE_FORMAT_VERSION = 2
VARIABLE_GENERATOR_NAME = "bar_grid_v2_length_specific"
SUPPORTED_VARIABLE_LENGTHS = (2, 4, 6, 8)


@dataclass(frozen=True)
class VariableCandidateGenerationConfig:
    """Hard constraints for the additive 2/4/6/8-bar candidate contract."""

    transition_lengths_bars: tuple[int, ...] = (2, 4)
    source_boundary_count: int | None = None
    target_boundary_count: int | None = None
    max_tempo_relative_difference: float = 0.15
    approximate_grid_policy: str = "reject"
    format_version: int = VARIABLE_CANDIDATE_FORMAT_VERSION

    def __post_init__(self):
        lengths = tuple(
            _strict_variable_length(length)
            for length in self.transition_lengths_bars
        )
        if not lengths:
            raise ValueError("transition_lengths_bars must not be empty")
        if any(length not in SUPPORTED_VARIABLE_LENGTHS for length in lengths):
            allowed = ", ".join(str(length) for length in SUPPORTED_VARIABLE_LENGTHS)
            raise ValueError(
                f"variable transition_lengths_bars must be one of {{{allowed}}}"
            )
        if len(set(lengths)) != len(lengths):
            raise ValueError("transition_lengths_bars must not contain duplicates")
        if self.source_boundary_count is not None and self.source_boundary_count <= 0:
            raise ValueError("source_boundary_count must be greater than 0 or None")
        if self.target_boundary_count is not None and self.target_boundary_count <= 0:
            raise ValueError("target_boundary_count must be greater than 0 or None")
        if not 0.0 <= self.max_tempo_relative_difference < 1.0:
            raise ValueError("max_tempo_relative_difference must be in [0, 1)")
        if self.approximate_grid_policy not in {"reject", "allow"}:
            raise ValueError("approximate_grid_policy must be 'reject' or 'allow'")
        if int(self.format_version) != VARIABLE_CANDIDATE_FORMAT_VERSION:
            raise ValueError(
                f"variable candidate format_version must be {VARIABLE_CANDIDATE_FORMAT_VERSION}"
            )
        object.__setattr__(self, "transition_lengths_bars", tuple(sorted(lengths)))


def generate_variable_candidates_from_grids(
    source_track: TrackReference,
    source_bpm: float,
    source_beat_frames: Sequence[object],
    target_track: TrackReference,
    target_bpm: float,
    target_beat_frames: Sequence[object],
    *,
    source_grid_metadata: BeatGridMetadata | None = None,
    target_grid_metadata: BeatGridMetadata | None = None,
    config: VariableCandidateGenerationConfig | None = None,
) -> CandidateGenerationResult:
    """Generate candidates with independent eligibility per requested length."""
    config = VariableCandidateGenerationConfig() if config is None else config
    rejections: list[CandidateRejection] = []
    source_grid_metadata = source_grid_metadata or unknown_grid_metadata()
    target_grid_metadata = target_grid_metadata or unknown_grid_metadata()

    def result(candidates=()):
        return CandidateGenerationResult(
            tuple(candidates),
            tuple(rejections),
            format_version=VARIABLE_CANDIDATE_FORMAT_VERSION,
            source_grid=source_grid_metadata,
            target_grid=target_grid_metadata,
            approximate_grid_policy=config.approximate_grid_policy,
        )

    try:
        source_grid = _parse_grid(source_beat_frames, strict_contiguity=True)
    except ValueError as error:
        rejections.append(CandidateRejection("invalid_source_grid", str(error)))
        return result()

    try:
        target_grid = _parse_grid(target_beat_frames, strict_contiguity=True)
    except ValueError as error:
        rejections.append(CandidateRejection("invalid_target_grid", str(error)))
        return result()

    if any(
        boundary.beats_in_bar != 4
        for grid in (source_grid, target_grid)
        for boundary in grid.boundaries
    ):
        rejections.append(
            CandidateRejection(
                "unsupported_meter",
                "Variable Candidate Protocol 2 currently requires a 4/4 beat grid.",
            )
        )
        return result()

    if config.approximate_grid_policy == "reject":
        if not source_grid_metadata.is_verified_detection:
            rejections.append(
                CandidateRejection(
                    "source_grid_provenance_rejected",
                    f"The source grid source {source_grid_metadata.grid_source!r} is fallback or unknown; "
                    "set approximate_grid_policy='allow' to opt in explicitly.",
                )
            )
        if not target_grid_metadata.is_verified_detection:
            rejections.append(
                CandidateRejection(
                    "target_grid_provenance_rejected",
                    f"The target grid source {target_grid_metadata.grid_source!r} is fallback or unknown; "
                    "set approximate_grid_policy='allow' to opt in explicitly.",
                )
            )
        if rejections:
            return result()

    source_bpm = float(source_bpm)
    target_bpm = float(target_bpm)
    if source_bpm <= 0 or target_bpm <= 0:
        rejections.append(
            CandidateRejection(
                "invalid_tempo",
                "Both tracks need a BPM value greater than 0.",
            )
        )
        return result()

    tempo_difference = abs(source_bpm - target_bpm) / max(source_bpm, target_bpm)
    if tempo_difference > config.max_tempo_relative_difference:
        rejections.append(
            CandidateRejection(
                "tempo_difference_exceeds_limit",
                "The relative BPM difference "
                f"({tempo_difference:.3f}) exceeds the configured limit "
                f"({config.max_tempo_relative_difference:.3f}).",
            )
        )
        return result()

    candidates: list[TransitionCandidate] = []
    for length_bars in config.transition_lengths_bars:
        source_boundaries = _eligible_boundaries(source_grid, length_bars)
        target_boundaries = _eligible_boundaries(target_grid, length_bars)
        if config.source_boundary_count is not None:
            source_boundaries = source_boundaries[-config.source_boundary_count :]
        if config.target_boundary_count is not None:
            target_boundaries = target_boundaries[: config.target_boundary_count]

        if not source_boundaries:
            rejections.append(
                CandidateRejection(
                    "insufficient_source_bars",
                    f"The source track has no complete {length_bars}-bar windows before and after a boundary.",
                    transition_length_bars=length_bars,
                )
            )
        if not target_boundaries:
            rejections.append(
                CandidateRejection(
                    "insufficient_target_preroll",
                    f"The target track has no complete {length_bars}-bar windows before and after a boundary.",
                    transition_length_bars=length_bars,
                )
            )
        if not source_boundaries or not target_boundaries:
            continue

        for source_boundary in source_boundaries:
            for target_boundary in target_boundaries:
                window_beats = (
                    _window_beats(source_grid, source_boundary.bar_index, length_bars),
                    _following_window_beats(
                        source_grid, source_boundary.bar_index, length_bars
                    ),
                    _window_beats(target_grid, target_boundary.bar_index, length_bars),
                    _following_window_beats(
                        target_grid, target_boundary.bar_index, length_bars
                    ),
                )
                if any(value is None or int(value) <= 0 for value in window_beats):
                    rejections.append(
                        CandidateRejection(
                            "incomplete_transition_window",
                            f"The {length_bars}-bar candidate window is incomplete at the requested boundaries.",
                            transition_length_bars=length_bars,
                        )
                    )
                    continue
                if len({int(value) for value in window_beats}) != 1:
                    rejections.append(
                        CandidateRejection(
                            "incompatible_transition_meter",
                            f"The four windows do not derive one beat count for {length_bars} bars.",
                            transition_length_bars=length_bars,
                        )
                    )
                    continue

                transition_beats = int(window_beats[1])
                source_cutpoint = _to_cutpoint(source_boundary)
                target_cutpoint = _to_cutpoint(target_boundary)
                candidates.append(
                    TransitionCandidate(
                        candidate_id=_candidate_id(
                            source_track,
                            target_track,
                            source_cutpoint,
                            target_cutpoint,
                            length_bars,
                        ),
                        source_track=source_track,
                        target_track=target_track,
                        source_cutpoint=source_cutpoint,
                        target_cutpoint=target_cutpoint,
                        transition_length_bars=length_bars,
                        transition_length_beats=transition_beats,
                        source_bpm=source_bpm,
                        target_bpm=target_bpm,
                        tempo_relative_difference=tempo_difference,
                        generator=VARIABLE_GENERATOR_NAME,
                        format_version=VARIABLE_CANDIDATE_FORMAT_VERSION,
                        source_grid=source_grid_metadata,
                        target_grid=target_grid_metadata,
                    )
                )

    if not candidates and not rejections:
        rejections.append(
            CandidateRejection(
                "no_compatible_candidates",
                "No compatible variable-length bar-grid candidates were found.",
            )
        )
    return result(candidates)


def _eligible_boundaries(grid: _Grid, length_bars: int):
    return [
        boundary
        for boundary in grid.boundaries
        if _window_beats(grid, boundary.bar_index, length_bars) is not None
        and _following_window_beats(grid, boundary.bar_index, length_bars) is not None
    ]


def _candidate_id(source_track, target_track, source_cutpoint, target_cutpoint, length_bars):
    payload = {
        "generator": VARIABLE_GENERATOR_NAME,
        "source_sha256": source_track.sha256,
        "target_sha256": target_track.sha256,
        "source_sample": source_cutpoint.sample,
        "target_sample": target_cutpoint.sample,
        "length_bars": int(length_bars),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return f"candidate-{hashlib.sha256(encoded).hexdigest()[:16]}"


def _strict_variable_length(value):
    if isinstance(value, bool) or value is None:
        raise ValueError("transition_length_bars must be an integer")
    if isinstance(value, Real) and (
        not math.isfinite(float(value)) or not float(value).is_integer()
    ):
        raise ValueError("transition_length_bars must be an integer")
    try:
        parsed = int(value)
    except (TypeError, ValueError, OverflowError) as error:
        raise ValueError("transition_length_bars must be an integer") from error
    if isinstance(value, str) and value.strip() != str(parsed):
        raise ValueError("transition_length_bars must be an integer")
    return parsed
