import torch

from src.control import (
    DifferentiableTransitionObjective,
    DifferentiableTwoBandRenderer,
    maximum_control_increment,
)
from src.features import FEATURE_DIMENSION, GLOBAL_FEATURE_DIMENSION, SEQUENCE_LENGTH
from src.ml import (
    FeatureControlMLP,
    collate_feature_control_examples,
    self_supervised_batch_loss,
)


def _model_inputs(batch_size=2):
    return (
        torch.zeros((batch_size, SEQUENCE_LENGTH, FEATURE_DIMENSION)),
        torch.zeros((batch_size, SEQUENCE_LENGTH, FEATURE_DIMENSION)),
        torch.zeros((batch_size, GLOBAL_FEATURE_DIMENSION)),
    )


def test_time_shared_mlp_starts_exactly_at_equal_power_controls():
    model = FeatureControlMLP()
    features_a, features_b, global_features = _model_inputs()

    output = model(features_a, features_b, global_features)

    expected = torch.linspace(0.0, 1.0, SEQUENCE_LENGTH).expand(2, -1)
    torch.testing.assert_close(output.mix_position, expected, atol=1e-6, rtol=1e-6)
    torch.testing.assert_close(output.low_end_position, expected, atol=1e-6, rtol=1e-6)
    assert model.parameter_count == 10_394
    assert torch.all(torch.diff(output.mix_position, dim=-1) > 0)
    assert float(torch.max(torch.diff(output.mix_position, dim=-1)).detach()) <= (
        maximum_control_increment(SEQUENCE_LENGTH) + 1e-6
    )


def test_self_supervised_batch_loss_supports_variable_audio_lengths_and_gradients():
    torch.manual_seed(7)
    examples = []
    for index, samples in enumerate((4_000, 5_000)):
        features_a = torch.rand((SEQUENCE_LENGTH, FEATURE_DIMENSION))
        features_b = torch.rand((SEQUENCE_LENGTH, FEATURE_DIMENSION))
        features_a[:, -3:] = 0.0
        features_b[:, -3:] = 0.0
        source = 0.1 * torch.randn((2, samples))
        target = 0.1 * torch.randn((2, samples))
        examples.append(
            {
                "example_id": f"example-{index}",
                "features_a": features_a,
                "features_b": features_b,
                "global_features": torch.zeros(GLOBAL_FEATURE_DIMENSION),
                "source_audio": source,
                "target_audio": target,
                "waveform_cache_hit": True,
            }
        )
    batch = collate_feature_control_examples(examples)
    model = FeatureControlMLP()
    renderer = DifferentiableTwoBandRenderer(
        sample_rate=8_000,
        lowpass_cutoff_hz=180.0,
        lowpass_kernel_size=127,
    )
    objective = DifferentiableTransitionObjective(energy_frames=SEQUENCE_LENGTH)

    result = self_supervised_batch_loss(
        model,
        batch,
        renderer=renderer,
        objective=objective,
    )
    result.terms["loss"].backward()

    assert torch.isfinite(result.terms["loss"])
    assert result.controls.mix_position.shape == (2, SEQUENCE_LENGTH)
    gradients = [parameter.grad for parameter in model.parameters()]
    assert any(gradient is not None and torch.count_nonzero(gradient) for gradient in gradients)
    assert all(gradient is None or torch.isfinite(gradient).all() for gradient in gradients)
