"""Self-supervised renderer/objective loss for feature-to-control models."""

from __future__ import annotations

from dataclasses import dataclass

import torch

from src.control import DifferentiableTransitionObjective, DifferentiableTwoBandRenderer
from src.control import DifferentiableVocalAwareRenderer, VocalAwareTransitionObjective


@dataclass(frozen=True)
class SelfSupervisedBatchResult:
    """Model output and mean differentiable objective components."""

    controls: object
    terms: dict[str, torch.Tensor]


def self_supervised_batch_loss(
    model,
    batch,
    *,
    renderer: DifferentiableTwoBandRenderer,
    objective: DifferentiableTransitionObjective,
):
    """Render variable-length examples independently and average their terms."""
    features_a = batch["features_a"]
    features_b = batch["features_b"]
    global_features = batch["global_features"]
    controls = model(features_a, features_b, global_features)
    batch_size = int(features_a.shape[0])
    source_audio = tuple(batch["source_audio"])
    target_audio = tuple(batch["target_audio"])
    if len(source_audio) != batch_size or len(target_audio) != batch_size:
        raise ValueError("Audio-list length must match the feature batch size")

    accumulated = {}
    for index in range(batch_size):
        source = source_audio[index].to(
            device=features_a.device,
            dtype=features_a.dtype,
        )
        target = target_audio[index].to(
            device=features_a.device,
            dtype=features_a.dtype,
        )
        rendered = renderer(
            source,
            target,
            controls.mix_position[index],
            controls.low_end_position[index],
        )
        terms = objective(
            rendered,
            source,
            target,
            features_a[index],
            features_b[index],
        )
        for name, value in terms.items():
            accumulated[name] = accumulated.get(name, value.new_zeros(())) + value
    mean_terms = {
        name: value / float(batch_size)
        for name, value in accumulated.items()
    }
    return SelfSupervisedBatchResult(controls=controls, terms=mean_terms)


def full_band_self_supervised_batch_loss(
    model,
    batch,
    *,
    renderer,
    objective,
):
    """Train ten TCN/BiLSTM controls through the full-band renderer."""

    features_a = batch["features_a"]
    features_b = batch["features_b"]
    controls = model(features_a, features_b, batch["global_features"])
    batch_size = int(features_a.shape[0])
    source_audio = tuple(batch["source_audio"])
    target_audio = tuple(batch["target_audio"])
    if len(source_audio) != batch_size or len(target_audio) != batch_size:
        raise ValueError("Audio-list length must match the feature batch size")

    accumulated = {}
    for index in range(batch_size):
        source = source_audio[index].to(
            device=features_a.device,
            dtype=features_a.dtype,
        )
        target = target_audio[index].to(
            device=features_a.device,
            dtype=features_a.dtype,
        )
        rendered = renderer(
            source,
            target,
            controls.gain_a[index],
            controls.gain_b[index],
            controls["eq_low_A"][index],
            controls["eq_low_B"][index],
            controls["eq_mid_A"][index],
            controls["eq_mid_B"][index],
            controls["eq_high_A"][index],
            controls["eq_high_B"][index],
            controls.low_end_ownership[index],
            controls.vocal_ducking[index],
        )
        terms = objective(
            rendered,
            source,
            target,
            features_a[index],
            features_b[index],
        )
        for name, value in terms.items():
            accumulated[name] = accumulated.get(name, value.new_zeros(())) + value
    mean_terms = {
        name: value / float(batch_size)
        for name, value in accumulated.items()
    }
    return SelfSupervisedBatchResult(controls=controls, terms=mean_terms)


def vocal_self_supervised_batch_loss(
    model,
    batch,
    *,
    renderer: DifferentiableVocalAwareRenderer,
    objective: VocalAwareTransitionObjective,
):
    """Render stem-aware examples independently and average objective-v5 terms."""
    features_a = batch["features_a"]
    features_b = batch["features_b"]
    controls = model(features_a, features_b, batch["global_features"])
    batch_size = int(features_a.shape[0])
    names = (
        "source_audio",
        "target_audio",
        "source_vocal_audio",
        "target_vocal_audio",
    )
    audio_lists = {name: tuple(batch[name]) for name in names}
    if any(len(values) != batch_size for values in audio_lists.values()):
        raise ValueError("Audio-list length must match the feature batch size")

    accumulated = {}
    for index in range(batch_size):
        audio = {
            name: values[index].to(device=features_a.device, dtype=features_a.dtype)
            for name, values in audio_lists.items()
        }
        rendered = renderer(
            audio["source_audio"],
            audio["target_audio"],
            audio["source_vocal_audio"],
            audio["target_vocal_audio"],
            controls.mix_position[index],
            controls.low_end_position[index],
            controls.vocal_position[index],
            controls.vocal_duck_a[index],
            controls.vocal_duck_b[index],
        )
        terms = objective(
            rendered,
            audio["source_audio"],
            audio["target_audio"],
            audio["source_vocal_audio"],
            audio["target_vocal_audio"],
            features_a[index],
            features_b[index],
        )
        for name, value in terms.items():
            accumulated[name] = accumulated.get(name, value.new_zeros(())) + value
    mean_terms = {name: value / float(batch_size) for name, value in accumulated.items()}
    return SelfSupervisedBatchResult(controls=controls, terms=mean_terms)
