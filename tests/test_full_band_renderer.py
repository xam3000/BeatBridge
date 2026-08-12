import pytest
import torch

from src.control import (
    DifferentiableFullBandTransitionRenderer,
    FULL_BAND_CONTROL_PROTOCOL_VERSION,
)
from src.features import FEATURE_DIMENSION, GLOBAL_FEATURE_DIMENSION, SEQUENCE_LENGTH
from src.ml import (
    TCNBiLSTMTransitionControl,
    full_band_self_supervised_batch_loss,
)
from src.control import DifferentiableTransitionObjective


def _audio(seed=12, samples=800):
    generator = torch.Generator().manual_seed(seed)
    return torch.randn(2, samples, generator=generator) * 0.1


def _controls(*, requires_grad=False):
    position = torch.linspace(0.0, 1.0, SEQUENCE_LENGTH)
    values = {
        "gain_a": torch.cos(position * torch.pi / 2),
        "gain_b": torch.sin(position * torch.pi / 2),
        "eq_low_a": torch.full((SEQUENCE_LENGTH,), 0.9),
        "eq_low_b": torch.full((SEQUENCE_LENGTH,), 0.9),
        "eq_mid_a": torch.full((SEQUENCE_LENGTH,), 0.9),
        "eq_mid_b": torch.full((SEQUENCE_LENGTH,), 0.9),
        "eq_high_a": torch.full((SEQUENCE_LENGTH,), 0.9),
        "eq_high_b": torch.full((SEQUENCE_LENGTH,), 0.9),
        "low_end_ownership": position,
        "vocal_ducking": torch.zeros(SEQUENCE_LENGTH),
    }
    if requires_grad:
        values = {
            name: value.clone().requires_grad_()
            for name, value in values.items()
        }
    return values


def _render(renderer, source, target, controls, **kwargs):
    return renderer(source, target, **controls, **kwargs)


def test_full_band_renderer_uses_all_ten_controls_and_backpropagates():
    source = _audio(1)
    target = _audio(2)
    renderer = DifferentiableFullBandTransitionRenderer(
        sample_rate=8_000,
        lowpass_kernel_size=127,
    )
    controls = _controls(requires_grad=True)

    result = _render(renderer, source, target, controls)
    result.audio.square().mean().backward()

    assert result.format_version == FULL_BAND_CONTROL_PROTOCOL_VERSION
    assert result.audio.shape == source.shape
    assert result.mix_position.shape == (1, source.shape[-1])
    assert result.low_end_position.shape == (1, source.shape[-1])
    assert torch.isfinite(result.audio).all()
    for name, value in controls.items():
        assert value.grad is not None, name
        assert torch.isfinite(value.grad).all(), name
        assert torch.count_nonzero(value.grad) > 0, name


def test_full_band_renderer_applies_vocal_ducking_to_stems():
    source_vocal = _audio(3)
    target_vocal = _audio(4)
    source = source_vocal + _audio(5)
    target = target_vocal + _audio(6)
    renderer = DifferentiableFullBandTransitionRenderer(
        sample_rate=8_000,
        lowpass_kernel_size=127,
    )
    controls = _controls()
    no_duck = _render(
        renderer,
        source,
        target,
        controls,
        source_vocal_audio=source_vocal,
        target_vocal_audio=target_vocal,
    )
    ducked_controls = dict(controls)
    ducked_controls["vocal_ducking"] = 0.8 * torch.sin(
        torch.pi * torch.linspace(0.0, 1.0, SEQUENCE_LENGTH)
    )
    ducked = _render(
        renderer,
        source,
        target,
        ducked_controls,
        source_vocal_audio=source_vocal,
        target_vocal_audio=target_vocal,
    )

    assert torch.all(ducked.vocal_gain_a <= no_duck.vocal_gain_a + 1e-6)
    assert torch.all(ducked.vocal_gain_b <= no_duck.vocal_gain_b + 1e-6)
    assert not torch.allclose(ducked.audio, no_duck.audio)


def test_full_band_renderer_requires_both_vocal_stems():
    renderer = DifferentiableFullBandTransitionRenderer(
        sample_rate=8_000,
        lowpass_kernel_size=127,
    )
    with pytest.raises(ValueError, match="Both vocal stems"):
        _render(
            renderer,
            _audio(7),
            _audio(8),
            _controls(),
            source_vocal_audio=_audio(9),
        )


def test_full_band_loss_connects_tcn_controls_to_objective():
    generator = torch.Generator().manual_seed(99)
    examples = []
    for index in range(2):
        examples.append({
            "features_a": torch.randn(
                SEQUENCE_LENGTH,
                FEATURE_DIMENSION,
                generator=generator,
            ),
            "features_b": torch.randn(
                SEQUENCE_LENGTH,
                FEATURE_DIMENSION,
                generator=generator,
            ),
            "global_features": torch.randn(
                GLOBAL_FEATURE_DIMENSION,
                generator=generator,
            ),
            "source_audio": _audio(20 + index),
            "target_audio": _audio(30 + index),
        })
    batch = {
        "features_a": torch.stack([item["features_a"] for item in examples]),
        "features_b": torch.stack([item["features_b"] for item in examples]),
        "global_features": torch.stack([item["global_features"] for item in examples]),
        "source_audio": tuple(item["source_audio"] for item in examples),
        "target_audio": tuple(item["target_audio"] for item in examples),
    }
    model = TCNBiLSTMTransitionControl()
    renderer = DifferentiableFullBandTransitionRenderer(
        sample_rate=8_000,
        lowpass_kernel_size=127,
    )
    objective = DifferentiableTransitionObjective(energy_frames=SEQUENCE_LENGTH)

    result = full_band_self_supervised_batch_loss(
        model,
        batch,
        renderer=renderer,
        objective=objective,
    )
    result.terms["loss"].backward()

    assert torch.isfinite(result.terms["loss"])
    assert result.controls.controls.shape == (2, SEQUENCE_LENGTH, 10)
    assert any(
        parameter.grad is not None and torch.count_nonzero(parameter.grad) > 0
        for parameter in model.parameters()
    )
