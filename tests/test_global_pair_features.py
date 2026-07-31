from types import SimpleNamespace

import numpy as np
import pytest

from src.features import (
    FEATURE_DIMENSION,
    GLOBAL_FEATURE_DIMENSION,
    SEQUENCE_LENGTH,
    build_global_pair_features,
    estimate_key,
    feature_index,
    global_feature_index,
)


def _window(tonic):
    features = np.zeros((SEQUENCE_LENGTH, FEATURE_DIMENSION), dtype=np.float32)
    features[:, feature_index(f"chroma_{tonic:02d}")] = 1.0
    features[:, feature_index("harmonic_ratio")] = 1.0
    features[:, feature_index("audio_valid")] = 1.0
    return features


def _artifact(bin_count=100):
    return SimpleNamespace(
        bin_boundaries=np.arange(bin_count + 1, dtype=np.int64),
        bin_count=bin_count,
    )


def test_global_pair_features_follow_the_16_value_contract():
    features_a = _window(0)
    features_b = _window(7)
    result = build_global_pair_features(
        features_a,
        features_b,
        bpm_a=160.0,
        bpm_b=168.0,
        artifact_a=_artifact(),
        artifact_b=_artifact(),
        cue_sample_a=50,
        cue_sample_b=50,
    )

    assert result.shape == (GLOBAL_FEATURE_DIMENSION,)
    assert result.dtype == np.float32
    assert result[global_feature_index("bpm_a")] == pytest.approx(0.0)
    assert result[global_feature_index("tempo_adjustment_required")] == 1.0
    assert 0.0 <= result[global_feature_index("harmonic_compatibility")] <= 1.0
    assert result[global_feature_index("context_coverage_a")] == 1.0
    assert result[global_feature_index("context_coverage_b")] == 1.0


def test_key_estimate_and_context_coverage_are_explicit():
    estimate = estimate_key(_window(0))
    assert estimate.tonic == 0
    assert estimate.mode in {-1.0, 1.0}
    assert 0.0 <= estimate.confidence <= 1.0

    result = build_global_pair_features(
        _window(0),
        _window(0),
        bpm_a=120.0,
        bpm_b=120.0,
        artifact_a=_artifact(),
        artifact_b=_artifact(),
        cue_sample_a=16,
        cue_sample_b=84,
    )
    assert result[global_feature_index("tempo_adjustment_required")] == 0.0
    assert result[global_feature_index("context_coverage_a")] == pytest.approx(0.75)
    assert result[global_feature_index("context_coverage_b")] == pytest.approx(0.75)


def test_unknown_key_uses_zero_confidence_and_neutral_compatibility():
    silent = np.zeros((SEQUENCE_LENGTH, FEATURE_DIMENSION), dtype=np.float32)
    estimate = estimate_key(silent)
    result = build_global_pair_features(
        silent,
        silent,
        bpm_a=120.0,
        bpm_b=120.0,
        artifact_a=_artifact(),
        artifact_b=_artifact(),
        cue_sample_a=50,
        cue_sample_b=50,
    )

    assert estimate.tonic is None
    assert estimate.mode == 0.0
    assert estimate.confidence == 0.0
    assert result[global_feature_index("harmonic_compatibility")] == pytest.approx(0.5)
