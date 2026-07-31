"""Deterministic 16-value pair features for Feature Protocol 1."""

from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np

from src.features.contract import (
    ANALYSIS_CONTEXT_BARS_AFTER,
    ANALYSIS_CONTEXT_BARS_BEFORE,
    BEATS_PER_BAR,
    FEATURE_DIMENSION,
    GLOBAL_FEATURE_DIMENSION,
    SEQUENCE_LENGTH,
    STEPS_PER_BEAT,
    feature_index,
    global_feature_index,
    validate_feature_array,
    validate_global_feature_array,
)


GLOBAL_PAIR_EXTRACTOR_VERSION = 1
EPSILON = 1e-10

_MAJOR_PROFILE = np.asarray(
    [6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88],
    dtype=np.float64,
)
_MINOR_PROFILE = np.asarray(
    [6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17],
    dtype=np.float64,
)


@dataclass(frozen=True)
class KeyEstimate:
    """One local key estimate; mode is -1 minor, +1 major, 0 unknown."""

    tonic: int | None
    mode: float
    confidence: float


def build_global_pair_features(
    features_a,
    features_b,
    *,
    bpm_a,
    bpm_b,
    artifact_a,
    artifact_b,
    cue_sample_a,
    cue_sample_b,
):
    """Build the contract-valid global vector for one aligned candidate."""
    features_a = validate_feature_array(features_a, name="features_a")
    features_b = validate_feature_array(features_b, name="features_b")
    if features_a.shape != (SEQUENCE_LENGTH, FEATURE_DIMENSION) or features_b.shape != (
        SEQUENCE_LENGTH,
        FEATURE_DIMENSION,
    ):
        raise ValueError("Global pair features require unbatched 32-step windows")
    bpm_a = _positive_finite(bpm_a, "bpm_a")
    bpm_b = _positive_finite(bpm_b, "bpm_b")

    key_a = estimate_key(features_a)
    key_b = estimate_key(features_b)
    vector = np.zeros(GLOBAL_FEATURE_DIMENSION, dtype=np.float32)
    _set(vector, "bpm_a", _normalise_bpm(bpm_a))
    _set(vector, "bpm_b", _normalise_bpm(bpm_b))
    ratio = bpm_b / bpm_a
    _set(vector, "tempo_ratio_b_over_a", np.clip(math.log2(ratio) / 0.25, -1, 1))
    _set(vector, "tempo_change_abs", np.clip(abs(ratio - 1.0) / 0.25, 0, 1))
    _set(vector, "tempo_adjustment_required", float(not np.isclose(bpm_a, bpm_b)))
    _set_key(vector, "a", key_a)
    _set_key(vector, "b", key_b)
    _set(vector, "harmonic_compatibility", harmonic_compatibility(features_a, features_b))
    _set(
        vector,
        "context_coverage_a",
        context_coverage(artifact_a, cue_sample_a),
    )
    _set(
        vector,
        "context_coverage_b",
        context_coverage(artifact_b, cue_sample_b),
    )
    return validate_global_feature_array(vector)


def estimate_key(features):
    """Estimate local tonic/mode from the 32 beat-synchronous chroma bins."""
    features = validate_feature_array(features)
    chroma = np.asarray(
        features[:, [feature_index(f"chroma_{index:02d}") for index in range(12)]],
        dtype=np.float64,
    )
    harmonic_weight = np.asarray(
        features[:, feature_index("harmonic_ratio")],
        dtype=np.float64,
    )
    weights = 0.25 + 0.75 * harmonic_weight
    profile = np.sum(chroma * weights[:, None], axis=0)
    if float(np.sum(profile)) <= EPSILON:
        return KeyEstimate(None, 0.0, 0.0)
    profile /= float(np.sum(profile))
    scores = []
    for mode, template in ((1.0, _MAJOR_PROFILE), (-1.0, _MINOR_PROFILE)):
        for tonic in range(12):
            scores.append((_cosine(profile, np.roll(template, tonic)), tonic, mode))
    scores.sort(key=lambda item: (-item[0], item[1], -item[2]))
    best, second = scores[0], scores[1]
    confidence = np.clip((best[0] - second[0]) / 0.12, 0.0, 1.0)
    return KeyEstimate(int(best[1]), float(best[2]), float(confidence))


def harmonic_compatibility(features_a, features_b):
    """Cosine compatibility of local chroma, neutral when evidence is absent."""
    indices = [feature_index(f"chroma_{index:02d}") for index in range(12)]
    profile_a = np.mean(np.asarray(features_a[:, indices], dtype=np.float64), axis=0)
    profile_b = np.mean(np.asarray(features_b[:, indices], dtype=np.float64), axis=0)
    if np.linalg.norm(profile_a) <= EPSILON or np.linalg.norm(profile_b) <= EPSILON:
        return 0.5
    return float(np.clip(_cosine(profile_a, profile_b), 0.0, 1.0))


def context_coverage(artifact, cue_sample):
    """Fraction of the requested four-bars-before/four-bars-after context."""
    boundaries = np.asarray(artifact.bin_boundaries, dtype=np.int64)
    cue_sample = int(cue_sample)
    boundary_index = int(np.argmin(np.abs(boundaries - cue_sample)))
    if int(boundaries[boundary_index]) != cue_sample:
        raise ValueError(f"Cue sample is not an exact cached half-beat boundary: {cue_sample}")
    before_requested = ANALYSIS_CONTEXT_BARS_BEFORE * BEATS_PER_BAR * STEPS_PER_BEAT
    after_requested = ANALYSIS_CONTEXT_BARS_AFTER * BEATS_PER_BAR * STEPS_PER_BEAT
    available_before = min(boundary_index, before_requested)
    available_after = min(int(artifact.bin_count) - boundary_index, after_requested)
    return float(
        (available_before + available_after) / (before_requested + after_requested)
    )


def _set_key(vector, suffix, estimate):
    if estimate.tonic is None:
        sine = cosine = 0.0
    else:
        angle = 2.0 * math.pi * estimate.tonic / 12.0
        sine, cosine = math.sin(angle), math.cos(angle)
    _set(vector, f"key_tonic_{suffix}_sin", sine)
    _set(vector, f"key_tonic_{suffix}_cos", cosine)
    _set(vector, f"key_mode_{suffix}", estimate.mode)
    _set(vector, f"key_confidence_{suffix}", estimate.confidence)


def _set(vector, name, value):
    vector[global_feature_index(name)] = np.float32(value)


def _normalise_bpm(bpm):
    return float(np.clip(math.log2(float(bpm) / 160.0), -1.0, 1.0))


def _positive_finite(value, name):
    value = float(value)
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be a finite value above 0")
    return value


def _cosine(left, right):
    denominator = float(np.linalg.norm(left) * np.linalg.norm(right))
    if denominator <= EPSILON:
        return 0.0
    return float(np.dot(left, right) / denominator)
