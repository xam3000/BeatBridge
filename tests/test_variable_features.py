from dataclasses import replace

import numpy as np
import pytest

from src.features import FEATURE_DIMENSION, feature_index
from src.features.extract_track import FeatureNormalizationStats, TrackFeatureArtifact
from src.features.variable_contract import (
    geometry_for_length,
    variable_feature_schema,
    validate_length_condition,
    validate_variable_feature_array,
)
from src.features.variable_extract import extract_variable_track_window
from src.features.variable_global_pair import build_variable_global_pair_features


def _artifact(bin_count=100):
    base = np.zeros((bin_count, FEATURE_DIMENSION), dtype=np.float32)
    base[:, feature_index("audio_valid")] = 1.0
    base[:, feature_index("beat_pulse_confidence")] = 1.0
    return TrackFeatureArtifact(
        cache_directory=__import__("pathlib").Path("synthetic-cache"),
        manifest={
            "cache_id": "synthetic",
            "source_sha256": "a" * 64,
            "aligned_bpm": 120.0,
            "sample_rate": 44_100,
        },
        base_features=base,
        bin_boundaries=np.arange(bin_count + 1, dtype=np.int64),
        spectral_flux_raw=np.ones(bin_count, dtype=np.float32),
        onset_strength_raw=np.ones(bin_count, dtype=np.float32),
        cache_hit=True,
    )


@pytest.mark.parametrize("length,expected_steps", [(2, 16), (4, 32), (6, 48), (8, 64)])
def test_variable_windows_and_transition_position_use_explicit_geometry(length, expected_steps):
    artifact = _artifact()
    stats = FeatureNormalizationStats(1.0, 1.0, "synthetic-train")
    source = extract_variable_track_window(
        artifact,
        20,
        role="source",
        normalization=stats,
        transition_length_bars=length,
    )
    target = extract_variable_track_window(
        artifact,
        80,
        role="target",
        normalization=stats,
        transition_length_bars=length,
    )
    assert source.shape == (expected_steps, FEATURE_DIMENSION)
    assert target.shape == (expected_steps, FEATURE_DIMENSION)
    position = source[:, feature_index("transition_position")]
    assert position[0] == pytest.approx(0.5 / expected_steps)
    assert position[-1] == pytest.approx((expected_steps - 0.5) / expected_steps)
    assert np.all(source[:, feature_index("audio_valid")] == 1.0)


def test_track_feature_artifact_keeps_default_v1_window():
    artifact = _artifact()
    stats = FeatureNormalizationStats(1.0, 1.0, "synthetic-train")
    window = artifact.model_window(32, role="source", normalization=stats)
    assert window.shape == (32, FEATURE_DIMENSION)
    assert window[0, feature_index("transition_position")] == pytest.approx(0.5 / 32)


def test_variable_geometry_and_validation_reject_mismatches():
    with pytest.raises(ValueError):
        geometry_for_length(4, sequence_length=16)
    with pytest.raises(ValueError):
        geometry_for_length(3)
    with pytest.raises(ValueError):
        validate_length_condition(np.asarray([[0.0]], dtype=np.float32), transition_length_bars=2)
    features = np.zeros((16, FEATURE_DIMENSION), dtype=np.float32)
    with pytest.raises(ValueError, match="transition_position"):
        validate_variable_feature_array(
            features,
            transition_length_bars=2,
        )


def test_variable_global_pair_preserves_the_16_global_semantics():
    artifact = _artifact()
    stats = FeatureNormalizationStats(1.0, 1.0, "synthetic-train")
    source = artifact.model_window(
        20,
        role="source",
        normalization=stats,
        transition_length_bars=6,
    )
    target = artifact.model_window(
        80,
        role="target",
        normalization=stats,
        transition_length_bars=6,
    )
    global_features = build_variable_global_pair_features(
        source,
        target,
        transition_length_bars=6,
        bpm_a=120.0,
        bpm_b=120.0,
        artifact_a=artifact,
        artifact_b=artifact,
        cue_sample_a=20,
        cue_sample_b=80,
    )
    assert global_features.shape == (16,)
    assert global_features.dtype == np.float32
    schema = variable_feature_schema()
    assert schema["format_version"] == 2
    assert schema["feature_dimension"] == 54
    assert schema["global_feature_dimension"] == 16
    assert schema["features"][feature_index("transition_position")]["normalization"].endswith("sequence_length")
