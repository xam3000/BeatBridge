import pytest
import torch

from src.features import FEATURE_DIMENSION, GLOBAL_FEATURE_DIMENSION, SEQUENCE_LENGTH
from src.ml import (
    TCNBiLSTMTransitionControl,
    TCNBiLSTMTransitionControlConfig,
    TRANSITION_CONTROL_MODEL_FORMAT_VERSION,
    TRANSITION_CONTROL_MODEL_NAME,
    TRANSITION_CONTROL_OUTPUT_NAMES,
)


def _model_inputs(batch_size=3):
    generator = torch.Generator().manual_seed(20260812)
    return (
        torch.randn(batch_size, SEQUENCE_LENGTH, FEATURE_DIMENSION, generator=generator),
        torch.randn(batch_size, SEQUENCE_LENGTH, FEATURE_DIMENSION, generator=generator),
        torch.randn(batch_size, GLOBAL_FEATURE_DIMENSION, generator=generator),
    )


def test_tcn_bilstm_model_has_requested_architecture_and_output_shape():
    model = TCNBiLSTMTransitionControl()
    features_a, features_b, global_features = _model_inputs()

    output = model(features_a, features_b, global_features)

    assert output.format_version == TRANSITION_CONTROL_MODEL_FORMAT_VERSION
    assert output.model_name == TRANSITION_CONTROL_MODEL_NAME
    assert output.controls.shape == (3, SEQUENCE_LENGTH, 10)
    assert output.controller_logits.shape == (3, SEQUENCE_LENGTH, 10)
    assert TRANSITION_CONTROL_OUTPUT_NAMES == (
        "gain_A",
        "gain_B",
        "eq_low_A",
        "eq_low_B",
        "eq_mid_A",
        "eq_mid_B",
        "eq_high_A",
        "eq_high_B",
        "low_end_ownership",
        "vocal_ducking",
    )
    assert model.shared_tcn_encoder[0].in_channels == FEATURE_DIMENSION
    assert model.shared_tcn_encoder[0].out_channels == 64
    assert model.shared_tcn_encoder[2].out_channels == 128
    assert model.fusion[0].in_features == 4 * 128
    assert model.fusion[0].out_features == 256
    assert model.controller.input_size == 256
    assert model.controller.hidden_size == 128
    assert model.controller.num_layers == 2
    assert model.controller.bidirectional is True
    assert torch.isfinite(output.controls).all()
    assert torch.all((output.controls >= 0.0) & (output.controls <= 1.0))


def test_tcn_bilstm_model_uses_shared_encoder_and_backpropagates():
    model = TCNBiLSTMTransitionControl()
    features_a, features_b, global_features = _model_inputs(batch_size=2)

    assert model.shared_tcn_encoder is not None
    output = model(features_a, features_b, global_features)
    output.controls.square().mean().backward()

    assert all(parameter.grad is not None for parameter in model.parameters())
    assert model.parameter_count > 20_821


def test_tcn_bilstm_model_supports_single_example_inputs():
    model = TCNBiLSTMTransitionControl()
    features_a, features_b, global_features = _model_inputs(batch_size=1)

    output = model(features_a[0], features_b[0], global_features[0])

    assert output.controls.shape == (SEQUENCE_LENGTH, 10)
    torch.testing.assert_close(output.gain_a, output.controls[..., 0])
    torch.testing.assert_close(output["vocal_ducking"], output.controls[..., 9])


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("tcn_kernel_size", 3.0),
        ("tcn_dilation", 2.9),
        ("fusion_dimension", 256.0),
        ("controller_hidden_size", "128"),
        ("controller_layers", True),
        ("output_dimension", "10"),
    ),
)
def test_tcn_bilstm_config_rejects_non_integer_architecture_fields(field, value):
    with pytest.raises(ValueError, match=field):
        TCNBiLSTMTransitionControlConfig(**{field: value})


def test_tcn_bilstm_config_rejects_non_integer_encoder_channels():
    with pytest.raises(ValueError, match="encoder_channels"):
        TCNBiLSTMTransitionControlConfig(encoder_channels=(32, 128))
    with pytest.raises(ValueError, match="encoder_channels"):
        TCNBiLSTMTransitionControlConfig(encoder_channels=(64.0, 128))
    with pytest.raises(ValueError, match="encoder_channels"):
        TCNBiLSTMTransitionControlConfig(encoder_channels=("64", 128))
