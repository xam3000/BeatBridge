import math

import pytest
import torch

from src.control import (
    CONTROL_PROTOCOL_VERSION,
    DEFAULT_INCREMENT_LOGIT_BOUND,
    DifferentiableTransitionObjective,
    DifferentiableTransitionObjectiveConfig,
    DifferentiableTwoBandRenderer,
    OptimizableControlCurves,
    maximum_control_increment,
    optimize_control_curves,
)
from src.features.contract import FEATURE_DIMENSION, feature_index


def _tone(frequency, *, sample_rate=8_000, seconds=1.0, amplitude=0.25):
    time = torch.arange(
        int(sample_rate * seconds),
        dtype=torch.float32,
    ) / sample_rate
    return amplitude * torch.sin(2.0 * math.pi * frequency * time)


def _features():
    features = torch.zeros((32, FEATURE_DIMENSION), dtype=torch.float32)
    features[:, feature_index("audio_valid")] = 1.0
    features[:, feature_index("vocal_valid")] = 1.0
    return features


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
    maximum_increment = maximum_control_increment(
        32,
        DEFAULT_INCREMENT_LOGIT_BOUND,
    )
    assert (
        float(torch.max(torch.diff(mix_position)).detach())
        <= maximum_increment + 1e-6
    )
    assert (
        float(torch.max(torch.diff(low_end_position)).detach())
        <= maximum_increment + 1e-6
    )


def test_v3_objective_has_zero_shape_penalties_for_linear_controls():
    source = torch.stack((_tone(220.0), _tone(330.0)))
    target = torch.stack((_tone(550.0), _tone(660.0)))
    control = torch.linspace(0.0, 1.0, 32)
    renderer = DifferentiableTwoBandRenderer(
        sample_rate=8_000,
        lowpass_cutoff_hz=180.0,
        lowpass_kernel_size=127,
    )
    objective = DifferentiableTransitionObjective(
        DifferentiableTransitionObjectiveConfig(),
        energy_frames=32,
    )

    terms = objective(
        renderer(source, target, control, control),
        source,
        target,
    )

    assert float(terms["control_smoothness"]) == pytest.approx(0.0, abs=1e-10)
    assert float(terms["control_curvature"]) == pytest.approx(0.0, abs=1e-10)


def test_v3_increment_bound_stays_below_one_tenth_for_32_points():
    curves = OptimizableControlCurves(control_points=32)
    with torch.no_grad():
        curves.mix_increment_logits.fill_(-100.0)
        curves.mix_increment_logits[10] = 100.0

    mix_position, _ = curves()

    assert maximum_control_increment(32) < 0.1
    assert float(torch.max(torch.diff(mix_position)).detach()) < 0.1


def test_v4_conditioned_terms_are_zero_when_features_are_not_supplied():
    source = torch.stack((_tone(220.0), _tone(330.0)))
    target = torch.stack((_tone(550.0), _tone(660.0)))
    control = torch.linspace(0.0, 1.0, 32)
    renderer = DifferentiableTwoBandRenderer(
        sample_rate=8_000,
        lowpass_cutoff_hz=180.0,
        lowpass_kernel_size=127,
    )

    terms = DifferentiableTransitionObjective(energy_frames=32)(
        renderer(source, target, control, control),
        source,
        target,
    )

    assert float(terms["vocal_overlap"]) == 0.0
    assert float(terms["vocal_boundary"]) == 0.0
    assert float(terms["transient_artifact"]) == 0.0
    assert float(terms["conditioning_valid_fraction"]) == 0.0


def test_v4_vocal_and_transient_terms_reward_handover_in_a_quiet_gap():
    source = torch.stack((_tone(220.0), _tone(330.0)))
    target = torch.stack((_tone(550.0), _tone(660.0)))
    source_features = _features()
    target_features = _features()
    for features in (source_features, target_features):
        features[:, feature_index("vocal_confidence")] = 1.0
    source_features[5:17, feature_index("vocal_activity")] = 1.0
    source_features[5:17, feature_index("vocal_prominence")] = 1.0
    target_features[15:27, feature_index("vocal_activity")] = 1.0
    target_features[15:27, feature_index("vocal_prominence")] = 1.0
    target_features[15:27, feature_index("vocal_phrase_progress")] = 0.8
    source_features[15:18, feature_index("spectral_flux")] = 1.0
    target_features[15:18, feature_index("onset_strength")] = 1.0

    linear = torch.linspace(0.0, 1.0, 32)
    quiet_gap = torch.cat(
        (
            torch.linspace(0.0, 0.08, 14),
            torch.linspace(0.12, 0.88, 4),
            torch.linspace(0.92, 1.0, 14),
        )
    )
    move_on_transient = torch.cat(
        (
            torch.linspace(0.0, 0.12, 15),
            torch.linspace(0.18, 0.82, 3),
            torch.linspace(0.88, 1.0, 14),
        )
    )
    renderer = DifferentiableTwoBandRenderer(
        sample_rate=8_000,
        lowpass_cutoff_hz=180.0,
        lowpass_kernel_size=127,
    )
    objective = DifferentiableTransitionObjective(energy_frames=32)

    linear_terms = objective(
        renderer(source, target, linear, linear),
        source,
        target,
        source_features,
        target_features,
    )
    transient_terms = objective(
        renderer(source, target, move_on_transient, move_on_transient),
        source,
        target,
        source_features,
        target_features,
    )
    gap_terms = objective(
        renderer(source, target, quiet_gap, quiet_gap),
        source,
        target,
        source_features,
        target_features,
    )

    assert float(linear_terms["vocal_overlap"]) > 0.0
    assert float(gap_terms["vocal_overlap"]) < float(linear_terms["vocal_overlap"])
    assert float(transient_terms["transient_artifact"]) > float(
        linear_terms["transient_artifact"]
    )
    assert float(gap_terms["conditioning_valid_fraction"]) == pytest.approx(1.0)


def test_v4_rejects_only_one_feature_tensor():
    source = torch.stack((_tone(220.0), _tone(330.0)))
    target = torch.stack((_tone(550.0), _tone(660.0)))
    control = torch.linspace(0.0, 1.0, 32)
    renderer = DifferentiableTwoBandRenderer(
        sample_rate=8_000,
        lowpass_cutoff_hz=180.0,
        lowpass_kernel_size=127,
    )

    with pytest.raises(ValueError, match="both be set"):
        DifferentiableTransitionObjective(energy_frames=32)(
            renderer(source, target, control, control),
            source,
            target,
            _features(),
            None,
        )
