import math

import pytest
import torch

from src.control import (
    CONTROL_PROTOCOL_VERSION,
    DifferentiableTransitionObjective,
    DifferentiableTwoBandRenderer,
    OptimizableControlCurves,
    optimize_control_curves,
)


def _tone(frequency, *, sample_rate=8_000, seconds=1.0, amplitude=0.25):
    time = torch.arange(
        int(sample_rate * seconds),
        dtype=torch.float32,
    ) / sample_rate
    return amplitude * torch.sin(2.0 * math.pi * frequency * time)


def test_renderer_returns_finite_audio_and_complementary_gains():
    source = torch.stack((_tone(80.0), _tone(440.0)))
    target = torch.stack((_tone(120.0), _tone(660.0)))
    control = torch.linspace(0.0, 1.0, 32)
    renderer = DifferentiableTwoBandRenderer(
        sample_rate=8_000,
        lowpass_cutoff_hz=180.0,
        lowpass_kernel_size=127,
    )

    result = renderer(source, target, control, control)

    assert result.format_version == CONTROL_PROTOCOL_VERSION
    assert result.audio.shape == source.shape
    assert torch.isfinite(result.audio).all()
    torch.testing.assert_close(
        result.gain_a**2 + result.gain_b**2,
        torch.ones_like(result.gain_a),
        atol=1e-6,
        rtol=1e-6,
    )
    torch.testing.assert_close(
        result.low_gain_a**2 + result.low_gain_b**2,
        torch.ones_like(result.low_gain_a),
        atol=1e-6,
        rtol=1e-6,
    )
    assert result.gain_a[0, 0] == pytest.approx(1.0)
    assert result.gain_b[0, -1] == pytest.approx(1.0)


def test_low_end_curve_changes_bass_without_replacing_high_band_mix():
    source = torch.stack((_tone(80.0), _tone(80.0)))
    target = torch.stack((_tone(880.0), _tone(880.0)))
    mix = torch.zeros(32)
    keep_source_low = torch.zeros(32)
    hand_low_to_target = torch.ones(32)
    renderer = DifferentiableTwoBandRenderer(
        sample_rate=8_000,
        lowpass_cutoff_hz=180.0,
        lowpass_kernel_size=127,
    )

    source_low_result = renderer(source, target, mix, keep_source_low).audio
    target_low_result = renderer(source, target, mix, hand_low_to_target).audio

    assert torch.sqrt(torch.mean(source_low_result**2)) > torch.sqrt(
        torch.mean(target_low_result**2)
    )


def test_renderer_and_objective_propagate_finite_control_gradients():
    source = torch.stack((_tone(220.0), _tone(330.0)))
    target = torch.stack((_tone(550.0), _tone(660.0)))
    mix_logits = torch.zeros(32, requires_grad=True)
    low_logits = torch.zeros(32, requires_grad=True)
    renderer = DifferentiableTwoBandRenderer(
        sample_rate=8_000,
        lowpass_cutoff_hz=180.0,
        lowpass_kernel_size=127,
    )
    objective = DifferentiableTransitionObjective(energy_frames=32)

    result = renderer(
        source,
        target,
        torch.sigmoid(mix_logits),
        torch.sigmoid(low_logits),
    )
    loss = objective(result, source, target)["loss"]
    loss.backward()

    assert torch.isfinite(loss)
    assert mix_logits.grad is not None
    assert low_logits.grad is not None
    assert torch.isfinite(mix_logits.grad).all()
    assert torch.isfinite(low_logits.grad).all()
    assert torch.count_nonzero(mix_logits.grad) > 0
    assert torch.count_nonzero(low_logits.grad) > 0


def test_direct_curve_optimization_reduces_the_proxy_objective():
    base = _tone(440.0, amplitude=0.2)
    bass = _tone(80.0, amplitude=0.15)
    source = torch.stack((base + bass, base + bass))
    target = torch.stack((base + bass, base + bass))
    renderer = DifferentiableTwoBandRenderer(
        sample_rate=8_000,
        lowpass_cutoff_hz=180.0,
        lowpass_kernel_size=127,
    )
    objective = DifferentiableTransitionObjective(energy_frames=32)

    result = optimize_control_curves(
        source,
        target,
        renderer=renderer,
        objective=objective,
        control_points=32,
        steps=40,
        learning_rate=0.08,
    )

    assert result.format_version == CONTROL_PROTOCOL_VERSION
    assert result.final_loss < result.initial_loss
    assert result.final_loss <= result.initial_loss * 0.95
    assert result.mix_position[0] == pytest.approx(0.0)
    assert result.mix_position[-1] == pytest.approx(1.0)
    assert result.low_end_position[0] == pytest.approx(0.0)
    assert result.low_end_position[-1] == pytest.approx(1.0)
    assert torch.all(torch.diff(result.mix_position) >= 0.0)
    assert torch.all(torch.diff(result.low_end_position) >= 0.0)
    assert torch.isfinite(result.audio).all()


def test_optimizable_curves_are_strictly_monotone_by_construction():
    curves = OptimizableControlCurves(control_points=32)
    with torch.no_grad():
        curves.mix_increment_logits.copy_(torch.linspace(-4.0, 4.0, 31))
        curves.low_end_increment_logits.copy_(torch.linspace(4.0, -4.0, 31))

    mix_position, low_end_position = curves()

    assert float(mix_position[0].detach()) == pytest.approx(0.0)
    assert float(mix_position[-1].detach()) == pytest.approx(1.0)
    assert float(low_end_position[0].detach()) == pytest.approx(0.0)
    assert float(low_end_position[-1].detach()) == pytest.approx(1.0)
    assert torch.all(torch.diff(mix_position) > 0.0)
    assert torch.all(torch.diff(low_end_position) > 0.0)
