"""Generate renderer-ready candidates from annotated beat grids."""

from dataclasses import dataclass
import hashlib
import json
from typing import Sequence

from src.analysis.models import BeatGridMetadata, unknown_grid_metadata

from .models import (
    CandidateGenerationResult,
    CandidateRejection,
    CutPoint,
    TrackReference,
    TransitionCandidate,
)


GENERATOR_NAME = "bar_grid_v1"


@dataclass(frozen=True)
class CandidateGenerationConfig:
    """Hard constraints for the first bar-grid candidate baseline."""

    transition_lengths_bars: tuple[int, ...] = (2, 4)
    source_boundary_count: int | None = None
    target_boundary_count: int | None = None
    max_tempo_relative_difference: float = 0.15
    approximate_grid_policy: str = "reject"

    def __post_init__(self):
        lengths = tuple(int(length) for length in self.transition_lengths_bars)
        if not lengths or any(length <= 0 for length in lengths):
            raise ValueError("transition_lengths_bars must contain positive bar counts")
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
        object.__setattr__(self, "transition_lengths_bars", tuple(sorted(lengths)))


@dataclass(frozen=True)
class _Beat:
    sample: int
    count_in_bar: int
    beats_in_bar: int


@dataclass(frozen=True)
class _Boundary:
    beat_index: int
    bar_index: int
    sample: int
    beats_in_bar: int


@dataclass(frozen=True)
class _Grid:
    boundaries: tuple[_Boundary, ...]
    complete_bar_indices: frozenset[int]


class _InvalidGrid(ValueError):
    pass


def generate_candidates(
    source_track: TrackReference,
    source_bpm: float,
    source_beat_frames: Sequence[object],
    target_track: TrackReference,
    target_bpm: float,
    target_beat_frames: Sequence[object],
    *,
    source_grid_metadata: BeatGridMetadata | None = None,
    target_grid_metadata: BeatGridMetadata | None = None,
    config: CandidateGenerationConfig | None = None,
) -> CandidateGenerationResult:
    """Return accepted candidates and auditable hard-filter outcomes.

    Beat samples must already be expressed on the rendering target sample-rate
    grid. Bridge renderers use audio after the source cutpoint and before the
    target cutpoint. Both cutpoints need complete bars before and after them:
    source post-roll
    and target pre-roll form the bridge transition, while source pre-roll and
    target post-roll contain the two non-overlapping high-power sections.
    """
    config = CandidateGenerationConfig() if config is None else config
    rejections = []
    source_grid_metadata = source_grid_metadata or unknown_grid_metadata()
    target_grid_metadata = target_grid_metadata or unknown_grid_metadata()

    def result(candidates=()):
        return CandidateGenerationResult(
            tuple(candidates),
            tuple(rejections),
            source_grid=source_grid_metadata,
            target_grid=target_grid_metadata,
            approximate_grid_policy=config.approximate_grid_policy,
        )

    try:
        source_grid = _parse_grid(source_beat_frames)
    except _InvalidGrid as error:
        rejections.append(CandidateRejection("invalid_source_grid", str(error)))
        return result()

    try:
        target_grid = _parse_grid(target_beat_frames)
    except _InvalidGrid as error:
        rejections.append(CandidateRejection("invalid_target_grid", str(error)))
        return result()

    if config.approximate_grid_policy == "reject":
        if not source_grid_metadata.is_verified_detection:
            rejections.append(_grid_provenance_rejection("source", source_grid_metadata))
        if not target_grid_metadata.is_verified_detection:
            rejections.append(_grid_provenance_rejection("target", target_grid_metadata))
        if rejections:
            return result()

    source_bpm = float(source_bpm)
    target_bpm = float(target_bpm)
    if source_bpm <= 0 or target_bpm <= 0:
        rejections.append(
            CandidateRejection("invalid_tempo", "Both tracks need a BPM value greater than 0.")
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

    source_boundaries = _eligible_bridge_boundaries(
        source_grid,
        config.transition_lengths_bars,
    )
    target_boundaries = _eligible_target_boundaries(
        target_grid,
        config.transition_lengths_bars,
    )
    if config.source_boundary_count is not None:
        source_boundaries = source_boundaries[-config.source_boundary_count :]
    if config.target_boundary_count is not None:
        target_boundaries = target_boundaries[: config.target_boundary_count]

    if not source_boundaries:
        rejections.append(
            CandidateRejection(
                "insufficient_source_bars",
                "The source track has no downbeat with enough complete bars before and after it.",
            )
        )
    if not target_boundaries:
        rejections.append(
            CandidateRejection(
                "insufficient_target_preroll",
                "The target track has no downbeat with enough complete bars before and after it.",
            )
        )
    if rejections:
        return result()

    candidates = []
    for source_boundary in source_boundaries:
        for target_boundary in target_boundaries:
            for length_bars in config.transition_lengths_bars:
                source_fade_beats = _window_beats(source_grid, source_boundary.bar_index, length_bars)
                target_fade_beats = _window_beats(target_grid, target_boundary.bar_index, length_bars)
                source_transition_beats = _following_window_beats(
                    source_grid,
                    source_boundary.bar_index,
                    length_bars,
                )
                target_high_power_beats = _following_window_beats(
                    target_grid,
                    target_boundary.bar_index,
                    length_bars,
                )
                if len(
                    {
                        source_fade_beats,
                        source_transition_beats,
                        target_fade_beats,
                        target_high_power_beats,
                    }
                ) != 1:
                    rejections.append(
                        CandidateRejection(
                            "incompatible_transition_meter",
                            "The four drop/transition windows require different beat counts for the same bar length.",
                        )
                    )
                    continue

                source_cutpoint = _to_cutpoint(source_boundary)
                target_cutpoint = _to_cutpoint(target_boundary)
                candidate_id = _candidate_id(
                    source_track,
                    target_track,
                    source_cutpoint,
                    target_cutpoint,
                    length_bars,
                )
                candidates.append(
                    TransitionCandidate(
                        candidate_id=candidate_id,
                        source_track=source_track,
                        target_track=target_track,
                        source_cutpoint=source_cutpoint,
                        target_cutpoint=target_cutpoint,
                        transition_length_bars=length_bars,
                        transition_length_beats=source_fade_beats,
                        source_bpm=source_bpm,
                        target_bpm=target_bpm,
                        tempo_relative_difference=tempo_difference,
                        generator=GENERATOR_NAME,
                        source_grid=source_grid_metadata,
                        target_grid=target_grid_metadata,
                    )
                )

    if not candidates and not rejections:
        rejections.append(
            CandidateRejection("no_compatible_candidates", "No compatible bar-grid candidates were found."))
    return result(candidates)


def _grid_provenance_rejection(role, metadata):
    return CandidateRejection(
        f"{role}_grid_provenance_rejected",
        f"The {role} grid source {metadata.grid_source!r} is fallback or unknown; "
        "set approximate_grid_policy='allow' to opt in explicitly.",
    )


def _parse_grid(beat_frames: Sequence[object]) -> _Grid:
    beats = []
    for index, frame in enumerate(beat_frames):
        if not isinstance(frame, (tuple, list)) or len(frame) != 3:
            raise _InvalidGrid(
                f"Beat frame {index} lacks required (sample, count_in_bar, beats_in_bar) metadata."
            )
        sample, count_in_bar, beats_in_bar = (int(value) for value in frame)
        if sample < 0 or count_in_bar < 1 or beats_in_bar < 1 or count_in_bar > beats_in_bar:
            raise _InvalidGrid(f"Beat frame {index} contains invalid bar metadata.")
        if beats and sample <= beats[-1].sample:
            raise _InvalidGrid("Beat samples must be strictly increasing.")
        beats.append(_Beat(sample, count_in_bar, beats_in_bar))

    downbeat_indices = [index for index, beat in enumerate(beats) if beat.count_in_bar == 1]
    if len(downbeat_indices) < 2:
        raise _InvalidGrid("At least two downbeats are required to establish complete bars.")

    boundaries = tuple(
        _Boundary(
            beat_index=beat_index,
            bar_index=bar_index,
            sample=beats[beat_index].sample,
            beats_in_bar=beats[beat_index].beats_in_bar,
        )
        for bar_index, beat_index in enumerate(downbeat_indices)
    )
    complete_bar_indices = set()
    for boundary, next_boundary in zip(boundaries, boundaries[1:]):
        bar_beats = beats[boundary.beat_index : next_boundary.beat_index]
        expected_counts = list(range(1, boundary.beats_in_bar + 1))
        if (
            len(bar_beats) == boundary.beats_in_bar
            and [beat.count_in_bar for beat in bar_beats] == expected_counts
            and all(beat.beats_in_bar == boundary.beats_in_bar for beat in bar_beats)
        ):
            complete_bar_indices.add(boundary.bar_index)

    if not complete_bar_indices:
        raise _InvalidGrid("No complete bars with a consistent beat count were found.")
    return _Grid(boundaries, frozenset(complete_bar_indices))


def _eligible_boundaries(grid: _Grid, lengths_bars: tuple[int, ...]) -> list[_Boundary]:
    return [
        boundary
        for boundary in grid.boundaries
        if all(_window_beats(grid, boundary.bar_index, length) is not None for length in lengths_bars)
    ]


def _eligible_target_boundaries(
    grid: _Grid,
    lengths_bars: tuple[int, ...],
) -> list[_Boundary]:
    return [
        boundary
        for boundary in grid.boundaries
        if all(
            _window_beats(grid, boundary.bar_index, length) is not None
            and _following_window_beats(grid, boundary.bar_index, length) is not None
            for length in lengths_bars
        )
    ]


def _eligible_bridge_boundaries(
    grid: _Grid,
    lengths_bars: tuple[int, ...],
) -> list[_Boundary]:
    return [
        boundary
        for boundary in grid.boundaries
        if all(
            _window_beats(grid, boundary.bar_index, length) is not None
            and _following_window_beats(grid, boundary.bar_index, length) is not None
            for length in lengths_bars
        )
    ]


def _window_beats(grid: _Grid, boundary_index: int, length_bars: int) -> int | None:
    start_index = boundary_index - length_bars
    if start_index < 0:
        return None
    preceding_bars = grid.boundaries[start_index:boundary_index]
    if len(preceding_bars) != length_bars:
        return None
    if any(bar.bar_index not in grid.complete_bar_indices for bar in preceding_bars):
        return None
    beats_per_bar = {bar.beats_in_bar for bar in preceding_bars}
    if len(beats_per_bar) != 1:
        return None
    return sum(bar.beats_in_bar for bar in preceding_bars)


def _following_window_beats(
    grid: _Grid,
    boundary_index: int,
    length_bars: int,
) -> int | None:
    following_bars = grid.boundaries[boundary_index : boundary_index + length_bars]
    if len(following_bars) != length_bars:
        return None
    if any(bar.bar_index not in grid.complete_bar_indices for bar in following_bars):
        return None
    beats_per_bar = {bar.beats_in_bar for bar in following_bars}
    if len(beats_per_bar) != 1:
        return None
    return sum(bar.beats_in_bar for bar in following_bars)


def _to_cutpoint(boundary: _Boundary) -> CutPoint:
    return CutPoint(
        sample=boundary.sample,
        beat_index=boundary.beat_index,
        bar_index=boundary.bar_index,
        count_in_bar=1,
        beats_in_bar=boundary.beats_in_bar,
    )


def _candidate_id(
    source_track: TrackReference,
    target_track: TrackReference,
    source_cutpoint: CutPoint,
    target_cutpoint: CutPoint,
    length_bars: int,
) -> str:
    payload = {
        "generator": GENERATOR_NAME,
        "source_sha256": source_track.sha256,
        "target_sha256": target_track.sha256,
        "source_sample": source_cutpoint.sample,
        "target_sample": target_cutpoint.sample,
        "length_bars": length_bars,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return f"candidate-{hashlib.sha256(encoded).hexdigest()[:16]}"
