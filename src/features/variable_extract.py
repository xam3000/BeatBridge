"""Variable Feature Protocol 2 window extraction from immutable artifacts."""

from __future__ import annotations

from .extract_track import FeatureNormalizationStats, TrackFeatureArtifact
from .variable_contract import geometry_for_length, validate_variable_feature_array


VARIABLE_FEATURE_EXTRACTOR_VERSION = 1


def extract_variable_track_window(
    artifact: TrackFeatureArtifact,
    cue_sample,
    *,
    role,
    normalization: FeatureNormalizationStats,
    transition_length_bars,
    sequence_length=None,
):
    """Extract an explicit v2 Source-postroll or Target-preroll window."""
    geometry = geometry_for_length(
        transition_length_bars,
        sequence_length=sequence_length,
    )
    window = artifact.model_window(
        cue_sample,
        role=role,
        normalization=normalization,
        transition_length_bars=geometry.transition_length_bars,
        sequence_length=geometry.sequence_length,
    )
    return validate_variable_feature_array(
        window,
        transition_length_bars=geometry.transition_length_bars,
        sequence_length=geometry.sequence_length,
        name=f"{role}_features",
    )
