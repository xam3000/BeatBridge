"""Deterministic, non-positional Candidate context for Cue-Ranker v1."""

from __future__ import annotations

import hashlib
import math

import numpy as np

from .cue_ranker_model import (
    CUE_RANKER_CONTEXT_DIMENSION,
    CUE_RANKER_GRID_SOURCE_VOCAB_SIZE,
    CUE_RANKER_CONTEXT_VERSION,
)


def build_candidate_context(row, *, group_size=None):
    """Return ``(candidate_context_v1, (source_grid_id, target_grid_id))``.

    Only bar/grid/context metadata is consumed.  In particular, absolute
    samples, audio paths, SHAs, candidate IDs and group IDs are not features.
    Missing optional provenance is represented by deterministic zero/unknown
    values rather than by opening a track or pair manifest.
    """

    candidate = row.get("candidate", row) if isinstance(row, dict) else {}
    source_cut = candidate.get("source_cutpoint", {})
    target_cut = candidate.get("target_cutpoint", {})
    source_grid = candidate.get("source_grid", {})
    target_grid = candidate.get("target_grid", {})
    size = max(1, int(group_size if group_size is not None else row.get("group_size", 1)))
    source_bar = _normalised_bar(source_cut, candidate.get("source_track", {}))
    target_bar = _normalised_bar(target_cut, candidate.get("target_track", {}))
    source_before, source_after = _cue_extent(source_cut)
    target_before, target_after = _cue_extent(target_cut)
    source_count = _log1p_float(_first(candidate, "source_boundary_count", "source_candidate_count", default=0.0))
    target_count = _log1p_float(_first(candidate, "target_boundary_count", "target_candidate_count", default=0.0))
    group_count = math.log1p(float(size))
    length_count = _log1p_float(_first(candidate, "length_candidate_count", default=0.0))
    source_confidence = _finite_float(source_grid.get("confidence", source_grid.get("match_confidence", 0.0)))
    target_confidence = _finite_float(target_grid.get("confidence", target_grid.get("match_confidence", 0.0)))
    source_fallback = float(bool(source_grid.get("fallback_used", False)))
    target_fallback = float(bool(target_grid.get("fallback_used", False)))
    source_meter = _finite_float(source_cut.get("beats_in_bar", 4)) / 4.0
    target_meter = _finite_float(target_cut.get("beats_in_bar", 4)) / 4.0
    source_duration_delta = _finite_float(_first(candidate, "source_local_duration_delta", "source_grid_duration_delta", default=0.0))
    target_duration_delta = _finite_float(_first(candidate, "target_local_duration_delta", "target_grid_duration_delta", default=0.0))
    context = np.asarray(
        [
            source_bar, target_bar, source_before, source_after, target_before, target_after,
            source_count, target_count, group_count, length_count,
            source_confidence, target_confidence, source_fallback, target_fallback,
            source_meter, target_meter, source_duration_delta, target_duration_delta,
            float(bool(source_grid)), float(bool(target_grid)),
        ],
        dtype=np.float32,
    )
    if context.shape != (CUE_RANKER_CONTEXT_DIMENSION,) or not np.isfinite(context).all():
        raise ValueError("candidate_context_v1 is invalid")
    return context, (_grid_id(source_grid), _grid_id(target_grid))


def _normalised_bar(cue, track):
    value = _finite_float(cue.get("bar_index", 0.0))
    total = _first(cue, "track_bar_count", "bar_count", default=None)
    if total is None:
        total = _first(track, "track_bar_count", "bar_count", default=None)
    if total is None or _finite_float(total) <= 0:
        # Format-3 fixtures may omit full-track coverage.  This monotone
        # bounded fallback still distinguishes early/late cue metadata without
        # consulting raw sample positions or opening a track.
        return float(np.clip(value / max(1.0, abs(value) + 1.0), -1.0, 1.0))
    return float(np.clip(value / max(1.0, _finite_float(total)), 0.0, 1.0))


def _cue_extent(cue):
    before = _first(cue, "full_bars_before", "bars_before", default=0.0)
    after = _first(cue, "full_bars_after", "bars_after", default=0.0)
    return (_finite_float(before), _finite_float(after))


def _grid_id(grid):
    name = str(grid.get("grid_source", grid.get("source", "unknown")))
    return int.from_bytes(hashlib.sha256(name.encode("utf-8")).digest()[:4], "big") % CUE_RANKER_GRID_SOURCE_VOCAB_SIZE


def _log1p_float(value):
    value = max(0.0, _finite_float(value))
    return float(math.log1p(value))


def _finite_float(value):
    value = float(value or 0.0)
    return value if math.isfinite(value) else 0.0


def _first(mapping, *keys, default=0.0):
    for key in keys:
        if key in mapping and mapping[key] is not None:
            return mapping[key]
    return default
