"""Machine-readable feature contract for the first feature-to-control model."""

from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np


FEATURE_PROTOCOL_VERSION = 1
TRANSITION_BARS = 4
BEATS_PER_BAR = 4
STEPS_PER_BEAT = 2
SEQUENCE_LENGTH = TRANSITION_BARS * BEATS_PER_BAR * STEPS_PER_BEAT
ANALYSIS_CONTEXT_BARS_BEFORE = 4
ANALYSIS_CONTEXT_BARS_AFTER = 4


@dataclass(frozen=True)
class FeatureDefinition:
    """One scalar channel in a versioned feature tensor."""

    name: str
    group: str
    minimum: float
    maximum: float
    normalization: str
    description: str


def _feature(name, group, minimum, maximum, normalization, description):
    return FeatureDefinition(
        name=name,
        group=group,
        minimum=float(minimum),
        maximum=float(maximum),
        normalization=normalization,
        description=description,
    )


FEATURE_DEFINITIONS = (
    _feature(
        "transition_position",
        "timing",
        0,
        1,
        "(bin_index + 0.5) / 32",
        "Normalized position inside the four-bar control window.",
    ),
    _feature("beat_phase_sin", "timing", -1, 1, "sin(2*pi*beat_phase)", "Beat phase sine."),
    _feature("beat_phase_cos", "timing", -1, 1, "cos(2*pi*beat_phase)", "Beat phase cosine."),
    _feature("bar_phase_sin", "timing", -1, 1, "sin(2*pi*bar_phase)", "Four-beat bar phase sine."),
    _feature("bar_phase_cos", "timing", -1, 1, "cos(2*pi*bar_phase)", "Four-beat bar phase cosine."),
    _feature(
        "phrase_phase_sin",
        "timing",
        -1,
        1,
        "sin(2*pi*position_in_8_bar_phrase)",
        "Eight-bar phrase phase sine; zero when phrase_valid is zero.",
    ),
    _feature(
        "phrase_phase_cos",
        "timing",
        -1,
        1,
        "cos(2*pi*position_in_8_bar_phrase)",
        "Eight-bar phrase phase cosine; zero when phrase_valid is zero.",
    ),
    _feature(
        "distance_to_phrase_boundary",
        "timing",
        0,
        1,
        "clip(distance_in_bars / 4, 0, 1)",
        "Distance to the nearest detected phrase boundary.",
    ),
    _feature(
        "phrase_confidence",
        "timing",
        0,
        1,
        "detector probability",
        "Confidence of the phrase phase and boundary features.",
    ),
    _feature(
        "rms_dbfs",
        "energy",
        -1,
        1,
        "2 * clip((dbfs + 60) / 60, 0, 1) - 1",
        "Absolute half-beat RMS on a clipped -60 to 0 dBFS scale.",
    ),
    _feature(
        "rms_db_relative",
        "energy",
        -1,
        1,
        "clip((bin_dbfs - track_median_dbfs) / 24, -1, 1)",
        "Energy relative to the track median.",
    ),
    _feature(
        "loudness_slope",
        "energy",
        -1,
        1,
        "clip(delta_db_per_half_beat / 12, -1, 1)",
        "Signed local energy change.",
    ),
    _feature("low_energy_ratio", "energy", 0, 1, "band_power / total_power", "Power below 180 Hz."),
    _feature(
        "mid_energy_ratio",
        "energy",
        0,
        1,
        "band_power / total_power",
        "Power from 180 Hz to 4 kHz.",
    ),
    _feature(
        "high_energy_ratio",
        "energy",
        0,
        1,
        "band_power / total_power",
        "Power above 4 kHz.",
    ),
    _feature(
        "local_energy_percentile",
        "energy",
        0,
        1,
        "empirical CDF within the complete track",
        "Mastering-robust energy rank.",
    ),
    _feature(
        "crest_factor",
        "energy",
        0,
        1,
        "clip((peak_to_rms - 1) / 19, 0, 1)",
        "Transient-to-average amplitude ratio.",
    ),
    _feature(
        "silence_probability",
        "energy",
        0,
        1,
        "calibrated silence detector probability",
        "Probability that the bin contains no musically relevant signal.",
    ),
    _feature(
        "spectral_centroid",
        "spectral_rhythm",
        0,
        1,
        "centroid_hz / nyquist_hz",
        "Normalized spectral centroid.",
    ),
    _feature(
        "spectral_bandwidth",
        "spectral_rhythm",
        0,
        1,
        "bandwidth_hz / nyquist_hz",
        "Normalized spectral bandwidth.",
    ),
    _feature(
        "spectral_rolloff",
        "spectral_rhythm",
        0,
        1,
        "rolloff_hz / nyquist_hz",
        "Normalized 85-percent spectral rolloff.",
    ),
    _feature("spectral_flatness", "spectral_rhythm", 0, 1, "native ratio", "Spectral flatness."),
    _feature(
        "spectral_flux",
        "spectral_rhythm",
        0,
        1,
        "clip(log1p(flux) / max(train_split_p99, epsilon), 0, 1)",
        "Positive spectral change, normalized with training-split statistics.",
    ),
    _feature(
        "onset_strength",
        "spectral_rhythm",
        0,
        1,
        "clip(log1p(onset) / max(train_split_p99, epsilon), 0, 1)",
        "Half-beat onset strength.",
    ),
    _feature(
        "kick_prominence",
        "spectral_rhythm",
        0,
        1,
        "calibrated kick detector probability",
        "Prominence of a kick or hard transient.",
    ),
    _feature(
        "beat_pulse_confidence",
        "spectral_rhythm",
        0,
        1,
        "beat tracker confidence",
        "Confidence that the local pulse follows the aligned beat grid.",
    ),
    *(
        _feature(
            f"chroma_{pitch_class:02d}",
            "harmonic",
            0,
            1,
            "L1-normalized chroma vector",
            f"Pitch-class energy channel {pitch_class}.",
        )
        for pitch_class in range(12)
    ),
    *(
        _feature(
            f"tonnetz_{axis}",
            "harmonic",
            -1,
            1,
            "native tonal-centroid coordinate",
            f"Tonal centroid axis {axis}.",
        )
        for axis in range(6)
    ),
    _feature(
        "harmonic_ratio",
        "harmonic",
        0,
        1,
        "harmonic_power / total_power",
        "Fraction of energy attributed to the harmonic component.",
    ),
    _feature(
        "vocal_activity",
        "vocal",
        0,
        1,
        "bounded Demucs stem-energy activity score",
        "Uncalibrated score indicating active vocals.",
    ),
    _feature(
        "vocal_prominence",
        "vocal",
        0,
        1,
        "clip((vocal_to_mix_db + 36) / 36, 0, 1)",
        "Vocal prominence relative to the complete mix.",
    ),
    _feature(
        "vocal_onset_probability",
        "vocal",
        0,
        1,
        "positive change of smoothed activity / 0.35",
        "Uncalibrated onset score for a sung phrase.",
    ),
    _feature(
        "vocal_offset_probability",
        "vocal",
        0,
        1,
        "negative change of smoothed activity / 0.35",
        "Uncalibrated offset score for a sung phrase.",
    ),
    _feature(
        "vocal_phrase_progress",
        "vocal",
        0,
        1,
        "elapsed_frames / detected_phrase_frames",
        "Progress through the active sung phrase; zero outside a phrase.",
    ),
    _feature(
        "vocal_confidence",
        "vocal",
        0,
        1,
        "2 * abs(vocal_activity - 0.5)",
        "Margin confidence of the derived activity score.",
    ),
    _feature(
        "audio_valid",
        "validity",
        0,
        1,
        "binary mask",
        "One when the complete half-beat audio bin exists.",
    ),
    _feature(
        "phrase_valid",
        "validity",
        0,
        1,
        "binary mask",
        "One when phrase features come from a valid detector result.",
    ),
    _feature(
        "vocal_valid",
        "validity",
        0,
        1,
        "binary mask",
        "One when vocal features come from a valid extractor result.",
    ),
)


GLOBAL_FEATURE_DEFINITIONS = (
    _feature("bpm_a", "tempo", -1, 1, "clip(log2(bpm / 160), -1, 1)", "Source tempo."),
    _feature("bpm_b", "tempo", -1, 1, "clip(log2(bpm / 160), -1, 1)", "Original target tempo."),
    _feature(
        "tempo_ratio_b_over_a",
        "tempo",
        -1,
        1,
        "clip(log2(bpm_b / bpm_a) / 0.25, -1, 1)",
        "Signed tempo mismatch before target alignment.",
    ),
    _feature(
        "tempo_change_abs",
        "tempo",
        0,
        1,
        "clip(abs(bpm_b / bpm_a - 1) / 0.25, 0, 1)",
        "Magnitude of the target tempo adjustment.",
    ),
    _feature(
        "tempo_adjustment_required",
        "tempo",
        0,
        1,
        "binary mask",
        "One when target audio is time-stretched.",
    ),
    _feature("key_tonic_a_sin", "key", -1, 1, "sin(2*pi*tonic/12)", "Source tonic sine."),
    _feature("key_tonic_a_cos", "key", -1, 1, "cos(2*pi*tonic/12)", "Source tonic cosine."),
    _feature("key_tonic_b_sin", "key", -1, 1, "sin(2*pi*tonic/12)", "Target tonic sine."),
    _feature("key_tonic_b_cos", "key", -1, 1, "cos(2*pi*tonic/12)", "Target tonic cosine."),
    _feature(
        "key_mode_a",
        "key",
        -1,
        1,
        "-1 minor, +1 major, 0 unknown",
        "Source key mode.",
    ),
    _feature(
        "key_mode_b",
        "key",
        -1,
        1,
        "-1 minor, +1 major, 0 unknown",
        "Target key mode.",
    ),
    _feature("key_confidence_a", "key", 0, 1, "key detector confidence", "Source key confidence."),
    _feature("key_confidence_b", "key", 0, 1, "key detector confidence", "Target key confidence."),
    _feature(
        "harmonic_compatibility",
        "pair",
        0,
        1,
        "versioned compatibility score",
        "Pairwise harmonic compatibility.",
    ),
    _feature(
        "context_coverage_a",
        "validity",
        0,
        1,
        "available_samples / requested_context_samples",
        "Coverage of the eight-bar source analysis context.",
    ),
    _feature(
        "context_coverage_b",
        "validity",
        0,
        1,
        "available_samples / requested_context_samples",
        "Coverage of the eight-bar target analysis context.",
    ),
)


FEATURE_DIMENSION = len(FEATURE_DEFINITIONS)
GLOBAL_FEATURE_DIMENSION = len(GLOBAL_FEATURE_DEFINITIONS)
_FEATURE_INDEX = {item.name: index for index, item in enumerate(FEATURE_DEFINITIONS)}
_GLOBAL_FEATURE_INDEX = {
    item.name: index for index, item in enumerate(GLOBAL_FEATURE_DEFINITIONS)
}
_BINARY_FEATURE_NAMES = {"audio_valid", "phrase_valid", "vocal_valid"}
_BINARY_GLOBAL_FEATURE_NAMES = {"tempo_adjustment_required"}

if len(_FEATURE_INDEX) != FEATURE_DIMENSION:
    raise RuntimeError("Feature contract contains duplicate feature names")
if len(_GLOBAL_FEATURE_INDEX) != GLOBAL_FEATURE_DIMENSION:
    raise RuntimeError("Feature contract contains duplicate global feature names")


def feature_index(name: str) -> int:
    """Return the stable channel index of one per-track feature."""
    try:
        return _FEATURE_INDEX[str(name)]
    except KeyError as error:
        raise KeyError(f"Unknown feature: {name}") from error


def global_feature_index(name: str) -> int:
    """Return the stable channel index of one global feature."""
    try:
        return _GLOBAL_FEATURE_INDEX[str(name)]
    except KeyError as error:
        raise KeyError(f"Unknown global feature: {name}") from error


def validate_feature_array(features, *, name="features"):
    """Validate shape, finiteness, and declared channel ranges."""
    array = np.asarray(features)
    if array.ndim < 2 or array.shape[-2:] != (SEQUENCE_LENGTH, FEATURE_DIMENSION):
        raise ValueError(
            f"{name} must end with shape "
            f"({SEQUENCE_LENGTH}, {FEATURE_DIMENSION}); got {array.shape}"
        )
    return validate_feature_channels(array, name=name)


def validate_feature_channels(features, *, name="features"):
    """Validate any sequence length against the declared feature channels."""
    array = np.asarray(features)
    if array.ndim < 1 or array.shape[-1] != FEATURE_DIMENSION:
        raise ValueError(
            f"{name} must end with shape ({FEATURE_DIMENSION},); got {array.shape}"
        )
    _validate_values(
        array,
        FEATURE_DEFINITIONS,
        name,
        binary_names=_BINARY_FEATURE_NAMES,
    )
    return array


def validate_global_feature_array(features, *, name="global_features"):
    """Validate global feature shape, finiteness, and ranges."""
    array = np.asarray(features)
    if array.ndim < 1 or array.shape[-1] != GLOBAL_FEATURE_DIMENSION:
        raise ValueError(
            f"{name} must end with shape ({GLOBAL_FEATURE_DIMENSION},); "
            f"got {array.shape}"
        )
    _validate_values(
        array,
        GLOBAL_FEATURE_DEFINITIONS,
        name,
        binary_names=_BINARY_GLOBAL_FEATURE_NAMES,
    )
    return array


def _validate_values(array, definitions, name, *, binary_names):
    if not np.issubdtype(array.dtype, np.floating):
        raise TypeError(f"{name} must use a floating-point dtype")
    if not np.isfinite(array).all():
        raise ValueError(f"{name} must contain only finite values")
    for index, definition in enumerate(definitions):
        values = array[..., index]
        if np.any(values < definition.minimum) or np.any(values > definition.maximum):
            raise ValueError(
                f"{name}.{definition.name} must be within "
                f"[{definition.minimum}, {definition.maximum}]"
            )
        if definition.name in binary_names and np.any(
            np.logical_and(values != 0.0, values != 1.0)
        ):
            raise ValueError(f"{name}.{definition.name} must be binary")


def feature_schema():
    """Return a JSON-serializable description for dataset manifests."""
    return {
        "format_version": FEATURE_PROTOCOL_VERSION,
        "transition_bars": TRANSITION_BARS,
        "beats_per_bar": BEATS_PER_BAR,
        "steps_per_beat": STEPS_PER_BEAT,
        "sequence_length": SEQUENCE_LENGTH,
        "analysis_context_bars_before": ANALYSIS_CONTEXT_BARS_BEFORE,
        "analysis_context_bars_after": ANALYSIS_CONTEXT_BARS_AFTER,
        "feature_dimension": FEATURE_DIMENSION,
        "global_feature_dimension": GLOBAL_FEATURE_DIMENSION,
        "features": [asdict(item) for item in FEATURE_DEFINITIONS],
        "global_features": [asdict(item) for item in GLOBAL_FEATURE_DEFINITIONS],
    }
