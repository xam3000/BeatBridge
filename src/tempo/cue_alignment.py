"""Estimate a single target stretch from local beat times and check its residuals."""

from dataclasses import asdict, dataclass, replace
from functools import lru_cache

import numpy as np
from src.candidates.models import CandidateRejection


CUE_ALIGNMENT = "cue_grid_regression_v3"
LEGACY_ALIGNMENT = "global_bpm_v1"
FIT_BEATS = 64
MAX_ERROR_MS = 20.0


class CueAlignmentError(ValueError):
    """The measured beat grid does not support this transition."""


@dataclass(frozen=True)
class CueAlignment:
    source_period: float
    target_period: float
    source_fit_beats: int
    target_fit_beats: int
    source_residual_ms: float
    target_residual_ms: float
    beat_offset_ms: float
    span_error_ms: float

    @property
    def tempo_factor(self):
        return self.target_period / self.source_period

    def require_valid(self):
        peak = max(self.source_residual_ms, self.target_residual_ms, self.beat_offset_ms)
        if peak > MAX_ERROR_MS + 1e-8:
            raise CueAlignmentError(
                f"Local beat grid exceeds {MAX_ERROR_MS:g} ms: source residual "
                f"{self.source_residual_ms:.1f}, target residual {self.target_residual_ms:.1f}, "
                f"cross-track offset {self.beat_offset_ms:.1f} ms"
            )

    def to_dict(self):
        return dict(contract=CUE_ALIGNMENT, **asdict(self), tempo_factor=self.tempo_factor,
                    max_error_ms=MAX_ERROR_MS)


def _fit(frames, cue, first, last):
    samples = np.asarray(frames, dtype=np.float64)
    if samples.ndim == 2:
        samples = samples[:, 0]
    if (samples.ndim != 1 or len(samples) < 2 or first < 0 or last >= len(samples)
            or not first <= cue <= last):
        raise CueAlignmentError("Incomplete beat window for cue regression")
    start = max(0, min(cue - FIT_BEATS // 2, len(samples) - FIT_BEATS))
    observed = samples[start:start + FIT_BEATS]
    bridge = samples[first:last + 1]
    if (not np.isfinite(observed).all() or np.any(np.diff(observed) <= 0)
            or not np.isfinite(bridge).all() or np.any(np.diff(bridge) <= 0)):
        raise CueAlignmentError("Beat times must be finite and strictly increasing")
    x = np.arange(len(observed), dtype=np.float64)
    x -= x.mean()
    period = float(np.dot(x, observed - observed.mean()) / np.dot(x, x))
    predicted = observed.mean() + period * (np.arange(first, last + 1) - start - (len(x)-1)/2)
    return period, len(observed), float(np.abs(bridge - predicted).max()), bridge


def measure_cue_alignment(source_frames, target_frames, source_index, target_index, beats, sample_rate):
    """Measure in output time, anchoring the target cue to the end of A's bridge."""
    if beats < 0 or sample_rate <= 0:
        raise ValueError("Invalid transition length or sample rate")
    source = _fit(source_frames, source_index, source_index, source_index + beats)
    target = _fit(target_frames, target_index, target_index - beats, target_index)
    return _compare_fits(source, target, sample_rate)


def _compare_fits(source, target, sample_rate):
    a, na, err_a, sa = source
    b, nb, err_b, sb = target
    scale = a / b
    # Use observed times throughout. Building target marks from source knots would
    # make this gate pass even when the target tracker misses a beat.
    offsets = (sb - sb[-1]) * scale - (sa - sa[-1])
    ms = 1000. / sample_rate
    return CueAlignment(a, b, na, nb, err_a * ms, err_b * scale * ms,
                        float(np.abs(offsets).max()) * ms, float(abs(offsets[0])) * ms)


def require_observed_grid(metadata):
    if metadata is None:
        return
    origin = metadata.get("grid_source") if isinstance(metadata, dict) else metadata.grid_source
    if origin == "fallback_from_bpm":
        raise CueAlignmentError("BPM-only grid has no observed beat times")


def filter_candidate_grids(generation, source_frames, target_frames, rate, *, source_metadata=None, target_metadata=None):
    """Remove unstable candidates before ranking or taking a top-K subset."""
    grids = []
    for frames in (source_frames, target_frames):
        array = np.asarray(frames, dtype=np.float64)
        grids.append(array[:, 0] if array.ndim == 2 else array)

    @lru_cache(maxsize=None)
    def fit(role, index, beats):
        start = index if role == 0 else index - beats
        return _fit(grids[role], index, start, start + beats)

    accepted = []
    try:
        require_observed_grid(source_metadata or generation.source_grid)
        require_observed_grid(target_metadata or generation.target_grid)
    except CueAlignmentError as error:
        reason = CandidateRejection(CUE_ALIGNMENT, str(error))
        return replace(generation, candidates=(), rejections=(*generation.rejections, reason))
    for candidate in generation.candidates:
        length = candidate.transition_length_beats
        try:
            source = fit(0, candidate.source_cutpoint.beat_index, length)
            target = fit(1, candidate.target_cutpoint.beat_index, length)
            if (source[3][0] != candidate.source_cutpoint.sample
                    or target[3][-1] != candidate.target_cutpoint.sample):
                continue
            _compare_fits(source, target, rate).require_valid()
        except CueAlignmentError:
            continue
        accepted.append(candidate)
    count = len(generation.candidates) - len(accepted)
    if not count:
        return generation
    reason = CandidateRejection(CUE_ALIGNMENT, f"{count} candidate grids failed the {MAX_ERROR_MS:g} ms cue gate")
    return replace(generation, candidates=tuple(accepted), rejections=(*generation.rejections, reason))


def check_feature_cue(source_artifact, target_artifact, source_cue, target_cue, beats, rate):
    """Screen cached half-beat grids at export. B's prior linear scale cancels in the fit."""
    grids = []
    for artifact in (source_artifact, target_artifact):
        require_observed_grid(artifact.manifest.get("beat_grid_metadata"))
        grids.append(artifact.bin_boundaries[::2])
    indices = []
    for grid, sample in zip(grids, (source_cue, target_cue), strict=True):
        if len(grid) < 2:
            raise CueAlignmentError("Feature grid has too few observed beats")
        index = int(np.argmin(np.abs(grid - sample)))
        if abs(int(grid[index]) - sample) > 2:
            raise CueAlignmentError("Candidate cue is not an observed beat on the feature grid")
        indices.append(index)
    measure_cue_alignment(*grids, *indices, beats, rate).require_valid()
