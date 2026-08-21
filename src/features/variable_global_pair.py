"""Length-aware Global-Pair v2 extraction with the v1 16 values intact."""

from __future__ import annotations

import math

import numpy as np

from .contract import (
    GLOBAL_FEATURE_DIMENSION,
    feature_index,
    global_feature_index,
    validate_global_feature_array,
)
from .global_pair import (
    EPSILON,
    KeyEstimate,
    _MAJOR_PROFILE,
    _MINOR_PROFILE,
    _cosine,
    context_coverage,
)
from .variable_contract import geometry_for_length, validate_variable_feature_array


VARIABLE_GLOBAL_PAIR_EXTRACTOR_VERSION = 2


def build_variable_global_pair_features(
    features_a,
    features_b,
    *,
    transition_length_bars,
    sequence_length=None,
    bpm_a,
    bpm_b,
    artifact_a,
    artifact_b,
    cue_sample_a,
    cue_sample_b,
):
    """Build the unchanged 16-value global vector over a variable local window."""
    geometry = geometry_for_length(
        transition_length_bars,
        sequence_length=sequence_length,
    )
    features_a = validate_variable_feature_array(
        features_a,
        transition_length_bars=geometry.transition_length_bars,
        sequence_length=geometry.sequence_length,
        name="features_a",
    )
    features_b = validate_variable_feature_array(
        features_b,
        transition_length_bars=geometry.transition_length_bars,
        sequence_length=geometry.sequence_length,
        name="features_b",
    )
    bpm_a = _positive_finite(bpm_a, "bpm_a")
    bpm_b = _positive_finite(bpm_b, "bpm_b")
    key_a = estimate_variable_key(features_a, transition_length_bars=geometry.transition_length_bars)
    key_b = estimate_variable_key(features_b, transition_length_bars=geometry.transition_length_bars)
    vector = np.zeros(GLOBAL_FEATURE_DIMENSION, dtype=np.float32)
    _set(vector, "bpm_a", _normalise_bpm(bpm_a))
    _set(vector, "bpm_b", _normalise_bpm(bpm_b))
    ratio = bpm_b / bpm_a
    _set(vector, "tempo_ratio_b_over_a", np.clip(math.log2(ratio) / 0.25, -1, 1))
    _set(vector, "tempo_change_abs", np.clip(abs(ratio - 1.0) / 0.25, 0, 1))
    _set(vector, "tempo_adjustment_required", float(not np.isclose(bpm_a, bpm_b)))
    _set_key(vector, "a", key_a)
    _set_key(vector, "b", key_b)
    _set(vector, "harmonic_compatibility", harmonic_compatibility_variable(features_a, features_b))
    _set(vector, "context_coverage_a", context_coverage(artifact_a, cue_sample_a))
    _set(vector, "context_coverage_b", context_coverage(artifact_b, cue_sample_b))
    return validate_global_feature_array(vector)


def estimate_variable_key(features, *, transition_length_bars):
    """Estimate key using all explicitly requested local bins."""
    features = validate_variable_feature_array(
        features,
        transition_length_bars=transition_length_bars,
        name="features",
    )
    chroma = np.asarray(
        features[:, [feature_index(f"chroma_{index:02d}") for index in range(12)]],
        dtype=np.float64,
    )
    weights = 0.25 + 0.75 * np.asarray(
        features[:, feature_index("harmonic_ratio")], dtype=np.float64
    )
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


def harmonic_compatibility_variable(features_a, features_b):
    indices = [feature_index(f"chroma_{index:02d}") for index in range(12)]
    profile_a = np.mean(np.asarray(features_a[:, indices], dtype=np.float64), axis=0)
    profile_b = np.mean(np.asarray(features_b[:, indices], dtype=np.float64), axis=0)
    if np.linalg.norm(profile_a) <= EPSILON or np.linalg.norm(profile_b) <= EPSILON:
        return 0.5
    return float(np.clip(_cosine(profile_a, profile_b), 0.0, 1.0))


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
