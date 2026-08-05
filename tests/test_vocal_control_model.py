import math

import torch

from src.control import (
    DifferentiableVocalAwareRenderer,
    VocalAwareTransitionObjective,
    optimize_vocal_control_curves,
)
from src.features import (
    FEATURE_DIMENSION,
    GLOBAL_FEATURE_DIMENSION,
    SEQUENCE_LENGTH,
    feature_index,
)
from src.ml import (
    VocalFeatureControlMLP,
    collate_feature_control_examples,
    vocal_self_supervised_batch_loss,
)


def _features(vocal_activity):
    result = torch.zeros((SEQUENCE_LENGTH, FEATURE_DIMENSION))
    result[:, feature_index("audio_valid")] = 1.0
    result[:, feature_index("vocal_valid")] = 1.0
    result[:, feature_index("vocal_activity")] = float(vocal_activity)
    result[:, feature_index("vocal_prominence")] = float(vocal_activity)
    result[:, feature_index("vocal_confidence")] = 1.0
    return result


def _audio(samples=4_000):
    time = torch.arange(samples, dtype=torch.float32) / 8_000.0
    vocal = 0.08 * torch.sin(2.0 * math.pi * 330.0 * time)
    vocal = vocal.repeat(2, 1)
    accompaniment = 0.03 * torch.sin(2.0 * math.pi * 110.0 * time).repeat(2, 1)
    return accompaniment + vocal, vocal


def test_vocal_model_starts_with_valid_independent_vocal_controls():
    model = VocalFeatureControlMLP()
    features_a = torch.zeros((2, SEQUENCE_LENGTH, FEATURE_DIMENSION))
    features_b = torch.zeros_like(features_a)
    global_features = torch.zeros((2, GLOBAL_FEATURE_DIMENSION))

    output = model(features_a, features_b, global_features)

    linear = torch.linspace(0.0, 1.0, SEQUENCE_LENGTH).expand(2, -1)
    torch.testing.assert_close(output.mix_position, linear, atol=1e-6, rtol=1e-6)
    torch.testing.assert_close(output.low_end_position, linear, atol=1e-6, rtol=1e-6)
    torch.testing.assert_close(output.vocal_position, linear, atol=1e-6, rtol=1e-6)
    assert torch.all(output.vocal_duck_a >= 0)
    assert torch.all(output.vocal_duck_b >= 0)
    assert torch.all(output.vocal_duck_a < model.config.maximum_vocal_ducking)
    assert torch.all(output.vocal_gain_a >= 0)
    assert torch.all(output.vocal_gain_b >= 0)
    torch.testing.assert_close(output.vocal_gain_a[:, 0], torch.ones(2))
    torch.testing.assert_close(output.vocal_gain_a[:, -1], torch.zeros(2), atol=1e-6, rtol=0)
    torch.testing.assert_close(output.vocal_gain_b[:, 0], torch.zeros(2), atol=1e-6, rtol=0)
    torch.testing.assert_close(output.vocal_gain_b[:, -1], torch.ones(2))


def test_vocal_audibility_penalizes_quiet_active_source_vocals():
    source, source_vocal = _audio()
    target = torch.zeros_like(source)
    target_vocal = torch.zeros_like(source_vocal)
    renderer = DifferentiableVocalAwareRenderer(
        sample_rate=8_000,
        lowpass_kernel_size=127,
    )
    objective = VocalAwareTransitionObjective(energy_frames=SEQUENCE_LENGTH)
    position = torch.linspace(0.0, 1.0, SEQUENCE_LENGTH)
    no_duck = torch.zeros(SEQUENCE_LENGTH)
    strong_duck = 0.8 * torch.sin(math.pi * position)

    clear = renderer(
        source,
        target,
        source_vocal,
        target_vocal,
        position,
        position,
        position,
        no_duck,
        no_duck,
    )
    quiet = renderer(
        source,
        target,
        source_vocal,
        target_vocal,
        position,
        position,
        position,
        strong_duck,
        no_duck,
    )
    features_a = _features(1.0)
    features_b = _features(0.0)
    clear_terms = objective(
        clear,
        source,
        target,
        source_vocal,
        target_vocal,
        features_a,
        features_b,
    )
    quiet_terms = objective(
        quiet,
        source,
        target,
        source_vocal,
        target_vocal,
        features_a,
        features_b,
    )

    assert quiet_terms["vocal_audibility"] > clear_terms["vocal_audibility"]


def test_vocal_ducking_reduces_stem_overlap_when_both_vocals_are_active():
    source, source_vocal = _audio()
    target, target_vocal = _audio()
    renderer = DifferentiableVocalAwareRenderer(
        sample_rate=8_000,
        lowpass_kernel_size=127,
    )
    objective = VocalAwareTransitionObjective(energy_frames=SEQUENCE_LENGTH)
    position = torch.linspace(0.0, 1.0, SEQUENCE_LENGTH)
    no_duck = torch.zeros(SEQUENCE_LENGTH)
    duck = 0.8 * torch.sin(math.pi * position)
    features = _features(1.0)

    overlap = renderer(
        source,
        target,
        source_vocal,
        target_vocal,
        position,
        position,
        position,
        no_duck,
        no_duck,
    )
    reduced = renderer(
        source,
        target,
        source_vocal,
        target_vocal,
        position,
        position,
        position,
        duck,
        no_duck,
    )
    overlap_terms = objective(
        overlap,
        source,
        target,
        source_vocal,
        target_vocal,
        features,
        features,
    )
    reduced_terms = objective(
        reduced,
        source,
        target,
        source_vocal,
        target_vocal,
        features,
        features,
    )

    assert reduced_terms["vocal_stem_overlap"] < overlap_terms["vocal_stem_overlap"]


def test_vocal_self_supervised_loss_supports_gradients_and_variable_lengths():
    examples = []
    for index, samples in enumerate((3_000, 4_000)):
        source, source_vocal = _audio(samples)
        target, target_vocal = _audio(samples)
        examples.append({
            "example_id": f"example-{index}",
            "features_a": _features(1.0),
            "features_b": _features(1.0),
            "global_features": torch.zeros(GLOBAL_FEATURE_DIMENSION),
            "source_audio": source,
            "target_audio": target,
            "source_vocal_audio": source_vocal,
            "target_vocal_audio": target_vocal,
            "waveform_cache_hit": True,
        })
    batch = collate_feature_control_examples(examples)
    model = VocalFeatureControlMLP()
    renderer = DifferentiableVocalAwareRenderer(
        sample_rate=8_000,
        lowpass_kernel_size=127,
    )
    objective = VocalAwareTransitionObjective(energy_frames=SEQUENCE_LENGTH)

    result = vocal_self_supervised_batch_loss(
        model,
        batch,
        renderer=renderer,
        objective=objective,
    )
    result.terms["loss"].backward()

    assert torch.isfinite(result.terms["loss"])
    assert result.controls.vocal_gain_a.shape == (2, SEQUENCE_LENGTH)
    gradients = [parameter.grad for parameter in model.parameters()]
    assert any(gradient is not None and torch.count_nonzero(gradient) for gradient in gradients)
    assert all(gradient is None or torch.isfinite(gradient).all() for gradient in gradients)


def test_direct_vocal_control_optimization_reduces_v5_loss_and_keeps_endpoints():
    source, source_vocal = _audio()
    target, target_vocal = _audio()
    renderer = DifferentiableVocalAwareRenderer(
        sample_rate=8_000,
        lowpass_kernel_size=127,
    )
    objective = VocalAwareTransitionObjective(energy_frames=SEQUENCE_LENGTH)

    result = optimize_vocal_control_curves(
        source,
        target,
        source_vocal,
        target_vocal,
        renderer=renderer,
        objective=objective,
        control_points=SEQUENCE_LENGTH,
        steps=10,
        learning_rate=0.05,
        features_a=_features(1.0),
        features_b=_features(1.0),
    )

    assert result.final_loss < result.initial_loss
    assert float(result.vocal_position[0]) == 0.0
    assert float(result.vocal_position[-1]) == 1.0
    assert float(result.vocal_duck_a[0]) == 0.0
    assert float(result.vocal_duck_a[-1]) == 0.0
    assert torch.isfinite(result.audio).all()
