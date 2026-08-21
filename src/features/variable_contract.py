"""Additive Feature Protocol 2 geometry and validation."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import math

import numpy as np

from src.features.contract import (
    BEATS_PER_BAR,
    FEATURE_DEFINITIONS,
    FEATURE_DIMENSION,
    FEATURE_PROTOCOL_VERSION,
    GLOBAL_FEATURE_DEFINITIONS,
    GLOBAL_FEATURE_DIMENSION,
    STEPS_PER_BEAT,
    feature_index,
    validate_feature_channels,
    validate_global_feature_array,
)


VARIABLE_FEATURE_PROTOCOL_VERSION = 2
SUPPORTED_VARIABLE_LENGTHS = (2, 4, 6, 8)
LENGTH_CONDITION_DIMENSION = 1
ANALYSIS_CONTEXT_BARS_BEFORE = 4
ANALYSIS_CONTEXT_BARS_AFTER = 4


@dataclass(frozen=True)
class VariableTransitionGeometry:
    """Externally requested 4/4 transition geometry."""

    transition_length_bars: int
    transition_length_beats: int
    sequence_length: int
    meter_numerator: int = 4
    meter_denominator: int = 4
    steps_per_beat: int = STEPS_PER_BEAT

    @property
    def length_condition(self):
        return np.float32(self.transition_length_bars / max(SUPPORTED_VARIABLE_LENGTHS))

    def to_dict(self):
        return {
            "transition_length_bars": self.transition_length_bars,
            "transition_length_beats": self.transition_length_beats,
            "sequence_length": self.sequence_length,
            "meter_numerator": self.meter_numerator,
            "meter_denominator": self.meter_denominator,
            "steps_per_beat": self.steps_per_beat,
            "length_condition": float(self.length_condition),
        }


def geometry_for_length(transition_length_bars, *, sequence_length=None, transition_length_beats=None):
    """Return validated geometry without inferring length from an array shape."""
    length = _strict_integer(transition_length_bars, "transition_length_bars")
    if length not in SUPPORTED_VARIABLE_LENGTHS:
        raise ValueError(
            "transition_length_bars must be one of "
            + ", ".join(str(item) for item in SUPPORTED_VARIABLE_LENGTHS)
        )
    expected_beats = length * BEATS_PER_BAR
    expected_steps = expected_beats * STEPS_PER_BEAT
    if transition_length_beats is not None:
        beats = _strict_integer(transition_length_beats, "transition_length_beats")
        if beats != expected_beats:
            raise ValueError(
                "transition_length_beats does not match transition_length_bars: "
                f"expected {expected_beats}, got {beats}"
            )
    if sequence_length is not None:
        steps = _strict_integer(sequence_length, "sequence_length")
        if steps != expected_steps:
            raise ValueError(
                "sequence_length does not match transition_length_bars: "
                f"expected {expected_steps}, got {steps}"
            )
    return VariableTransitionGeometry(length, expected_beats, expected_steps)


def geometry_from_candidate(candidate):
    """Validate explicit candidate fields and return their v2 geometry."""
    if not isinstance(candidate, dict):
        raise TypeError("candidate must be a dictionary")
    return geometry_for_length(
        candidate.get("transition_length_bars"),
        sequence_length=candidate.get("sequence_length"),
        transition_length_beats=candidate.get("transition_length_beats"),
    )


def validate_variable_feature_array(
    features,
    *,
    transition_length_bars,
    sequence_length=None,
    name="features",
):
    """Validate one v2 window against explicit L and T fields."""
    geometry = geometry_for_length(
        transition_length_bars,
        sequence_length=sequence_length,
    )
    array = np.asarray(features)
    if array.shape != (geometry.sequence_length, FEATURE_DIMENSION):
        raise ValueError(
            f"{name} must have shape "
            f"({geometry.sequence_length}, {FEATURE_DIMENSION}) for "
            f"{geometry.transition_length_bars} bars; got {array.shape}"
        )
    validate_feature_channels(array, name=name)
    position = np.asarray(array[:, feature_index("transition_position")], dtype=np.float64)
    expected = (np.arange(geometry.sequence_length, dtype=np.float64) + 0.5) / geometry.sequence_length
    if not np.allclose(position, expected, rtol=0.0, atol=1e-6):
        raise ValueError(f"{name}.transition_position is not normalized by sequence_length")
    return array


def validate_variable_feature_batch(
    features,
    *,
    transition_length_bars,
    sequence_length=None,
    name="features",
):
    """Validate a batch whose final two dimensions are one v2 window."""
    geometry = geometry_for_length(
        transition_length_bars,
        sequence_length=sequence_length,
    )
    array = np.asarray(features)
    if array.ndim < 3 or array.shape[-2:] != (geometry.sequence_length, FEATURE_DIMENSION):
        raise ValueError(
            f"{name} must end with shape "
            f"({geometry.sequence_length}, {FEATURE_DIMENSION}); got {array.shape}"
        )
    validate_feature_channels(array, name=name)
    expected = (np.arange(geometry.sequence_length, dtype=np.float64) + 0.5) / geometry.sequence_length
    if not np.allclose(array[..., feature_index("transition_position")], expected, rtol=0.0, atol=1e-6):
        raise ValueError(f"{name}.transition_position is not normalized by sequence_length")
    return array


def validate_length_condition(value, *, transition_length_bars, name="length_condition"):
    """Validate the separate normalized length-conditioning tensor."""
    geometry = geometry_for_length(transition_length_bars)
    array = np.asarray(value)
    if array.shape[-1:] != (LENGTH_CONDITION_DIMENSION,):
        raise ValueError(f"{name} must end with shape (1,); got {array.shape}")
    if not np.issubdtype(array.dtype, np.floating):
        raise TypeError(f"{name} must use a floating-point dtype")
    if not np.isfinite(array).all():
        raise ValueError(f"{name} must contain only finite values")
    if np.any(array < 0.0) or np.any(array > 1.0):
        raise ValueError(f"{name} must be within [0, 1]")
    if not np.allclose(array, geometry.length_condition, rtol=0.0, atol=1e-6):
        raise ValueError(
            f"{name} does not match transition_length_bars={geometry.transition_length_bars}"
        )
    return array


def variable_feature_schema():
    """Return the complete, serializable Feature Protocol 2 schema."""
    features = []
    for definition in FEATURE_DEFINITIONS:
        item = asdict(definition)
        if item["name"] == "transition_position":
            item["normalization"] = "(bin_index + 0.5) / sequence_length"
            item["description"] = "Normalized local position inside the requested transition window."
        features.append(item)
    return {
        "format_version": VARIABLE_FEATURE_PROTOCOL_VERSION,
        "compatibility": {
            "v1_feature_protocol_version": FEATURE_PROTOCOL_VERSION,
            "channel_order_unchanged": True,
            "feature_dimension": FEATURE_DIMENSION,
            "global_feature_dimension": GLOBAL_FEATURE_DIMENSION,
        },
        "supported_lengths": list(SUPPORTED_VARIABLE_LENGTHS),
        "sequence_lengths": {
            str(length): geometry_for_length(length).sequence_length
            for length in SUPPORTED_VARIABLE_LENGTHS
        },
        "beats_per_bar": BEATS_PER_BAR,
        "steps_per_beat": STEPS_PER_BEAT,
        "analysis_context_bars_before": ANALYSIS_CONTEXT_BARS_BEFORE,
        "analysis_context_bars_after": ANALYSIS_CONTEXT_BARS_AFTER,
        "feature_dimension": FEATURE_DIMENSION,
        "global_feature_dimension": GLOBAL_FEATURE_DIMENSION,
        "length_condition": {
            "shape": [LENGTH_CONDITION_DIMENSION],
            "dtype": "float32",
            "normalization": "transition_length_bars / 8",
        },
        "features": features,
        "global_features": [asdict(item) for item in GLOBAL_FEATURE_DEFINITIONS],
    }


def _strict_integer(value, name):
    if isinstance(value, bool) or value is None:
        raise ValueError(f"{name} must be an integer")
    if isinstance(value, float) and (not math.isfinite(value) or not value.is_integer()):
        raise ValueError(f"{name} must be an integer")
    try:
        parsed = int(value)
    except (TypeError, ValueError, OverflowError) as error:
        raise ValueError(f"{name} must be an integer") from error
    if isinstance(value, str) and str(value).strip() != str(parsed):
        raise ValueError(f"{name} must be an integer")
    return parsed
