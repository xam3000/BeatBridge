"""Additive variable-length feature-to-control training loss path."""

from __future__ import annotations

from dataclasses import dataclass

import torch

from src.control import DifferentiableVocalAwareRenderer
from src.control.variable_differentiable import VariableVocalAwareTransitionObjective
from src.features.variable_contract import geometry_for_length


@dataclass(frozen=True)
class VariableSelfSupervisedBatchResult:
    """Variable model outputs and per-example/time-normalized mean terms."""

    controls: object
    terms: dict[str, torch.Tensor]


def variable_vocal_self_supervised_batch_loss(
    model,
    batch,
    *,
    renderer: DifferentiableVocalAwareRenderer,
    objective: VariableVocalAwareTransitionObjective,
):
    """Render one homogeneous Dataset-2 batch without padding any audio."""

    required = (
        "features_a",
        "features_b",
        "global_features",
        "length_condition",
        "transition_length_bars",
        "source_audio",
        "target_audio",
        "source_vocal_audio",
        "target_vocal_audio",
    )
    missing = [name for name in required if name not in batch]
    if missing:
        raise ValueError("Variable vocal batch is missing: " + ", ".join(missing))
    features_a = batch["features_a"]
    features_b = batch["features_b"]
    length = int(batch["transition_length_bars"])
    geometry = geometry_for_length(length, sequence_length=int(features_a.shape[1]))
    if int(batch["sequence_length"]) != geometry.sequence_length:
        raise ValueError("Batch sequence_length does not match transition geometry")
    batch_size = int(features_a.shape[0])
    controls = model(
        features_a,
        features_b,
        batch["global_features"],
        transition_length_bars=length,
        length_condition=batch["length_condition"],
    )
    audio_lists = {
        name: tuple(batch[name])
        for name in (
            "source_audio",
            "target_audio",
            "source_vocal_audio",
            "target_vocal_audio",
        )
    }
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
            transition_length_bars=length,
        )
        for name, value in terms.items():
            if not isinstance(value, torch.Tensor) or value.numel() != 1:
                raise ValueError(f"Objective term {name} must be a scalar tensor")
            accumulated[name] = accumulated.get(name, value.new_zeros(())) + value
    if batch_size < 1:
        raise ValueError("Cannot calculate a loss for an empty batch")
    mean_terms = {name: value / float(batch_size) for name, value in accumulated.items()}
    return VariableSelfSupervisedBatchResult(controls=controls, terms=mean_terms)
