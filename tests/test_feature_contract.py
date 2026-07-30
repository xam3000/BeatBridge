import numpy as np
import pytest

from src.features import (
    FEATURE_DEFINITIONS,
    FEATURE_DIMENSION,
    FEATURE_PROTOCOL_VERSION,
    GLOBAL_FEATURE_DIMENSION,
    SEQUENCE_LENGTH,
    feature_index,
    feature_schema,
    validate_feature_channels,
    validate_feature_array,
    validate_global_feature_array,
)


def test_feature_contract_has_stable_geometry_and_vocal_group():
    assert FEATURE_PROTOCOL_VERSION == 1
    assert SEQUENCE_LENGTH == 32
    assert FEATURE_DIMENSION == 54
    assert GLOBAL_FEATURE_DIMENSION == 16
    assert len({item.name for item in FEATURE_DEFINITIONS}) == FEATURE_DIMENSION
    assert {
        "vocal_activity",
        "vocal_prominence",
        "vocal_onset_probability",
        "vocal_offset_probability",
        "vocal_phrase_progress",
        "vocal_confidence",
        "vocal_valid",
    }.issubset({item.name for item in FEATURE_DEFINITIONS})


def test_feature_indices_and_schema_are_serializable_and_stable():
    schema = feature_schema()

    assert schema["format_version"] == 1
    assert schema["sequence_length"] == 32
    assert schema["feature_dimension"] == 54
    assert schema["features"][feature_index("vocal_activity")]["name"] == "vocal_activity"


def test_feature_array_validation_accepts_batches_and_rejects_bad_values():
    features = np.zeros((2, SEQUENCE_LENGTH, FEATURE_DIMENSION), dtype=np.float32)
    validate_feature_array(features)

    features[0, 0, feature_index("vocal_activity")] = 1.1
    with pytest.raises(ValueError, match="vocal_activity"):
        validate_feature_array(features)

    with pytest.raises(ValueError, match="must end with shape"):
        validate_feature_array(
            np.zeros((SEQUENCE_LENGTH, FEATURE_DIMENSION - 1), dtype=np.float32)
        )

    validate_feature_channels(
        np.zeros((SEQUENCE_LENGTH * 3, FEATURE_DIMENSION), dtype=np.float32)
    )


def test_global_feature_validation_requires_float_and_declared_dimension():
    validate_global_feature_array(
        np.zeros((3, GLOBAL_FEATURE_DIMENSION), dtype=np.float32)
    )

    with pytest.raises(TypeError, match="floating-point"):
        validate_global_feature_array(
            np.zeros(GLOBAL_FEATURE_DIMENSION, dtype=np.int16)
        )


def test_validity_masks_must_be_binary():
    features = np.zeros((SEQUENCE_LENGTH, FEATURE_DIMENSION), dtype=np.float32)
    features[:, feature_index("vocal_valid")] = 0.5

    with pytest.raises(ValueError, match="vocal_valid.*binary"):
        validate_feature_array(features)
