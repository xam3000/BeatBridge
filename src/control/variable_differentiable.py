"""Dynamic-T Objective-v5 adapter for the additive Dataset-2 ML path."""

from __future__ import annotations

import torch
from torch import nn

from src.features.variable_contract import geometry_for_length

from .differentiable import (
    VOCAL_OBJECTIVE_VERSION,
    VocalAwareRenderResult,
    VocalAwareTransitionObjective,
    VocalAwareTransitionObjectiveConfig,
)


VARIABLE_OBJECTIVE_FORMAT_VERSION = 2
VARIABLE_OBJECTIVE_NAME = "objective_v5_time_normalized_variable_v1"


class VariableVocalAwareTransitionObjective(nn.Module):
    """Apply Objective-v5 with the actual sequence length of each example.

    The underlying objective already reduces energy, control and audio terms
    with means over their current time axis.  Constructing it with ``T`` for
    every call keeps those means comparable across 16/32/48/64 points instead
    of letting longer transitions contribute more merely because they have
    more control bins.
    """

    def __init__(self, config: VocalAwareTransitionObjectiveConfig | None = None):
        super().__init__()
        self.config = config or VocalAwareTransitionObjectiveConfig()

    def forward(
        self,
        render_result: VocalAwareRenderResult,
        source_audio: torch.Tensor,
        target_audio: torch.Tensor,
        source_vocal_audio: torch.Tensor,
        target_vocal_audio: torch.Tensor,
        features_a: torch.Tensor,
        features_b: torch.Tensor,
        *,
        transition_length_bars,
    ) -> dict[str, torch.Tensor]:
        geometry = geometry_for_length(transition_length_bars)
        objective = VocalAwareTransitionObjective(
            config=self.config,
            energy_frames=geometry.sequence_length,
        )
        terms = objective(
            render_result,
            source_audio,
            target_audio,
            source_vocal_audio,
            target_vocal_audio,
            features_a,
            features_b,
        )
        return {
            **terms,
            "objective_format_version": render_result.audio.new_tensor(
                float(VARIABLE_OBJECTIVE_FORMAT_VERSION)
            ),
            "objective_version": render_result.audio.new_tensor(
                float(VOCAL_OBJECTIVE_VERSION)
            ),
            "sequence_length": render_result.audio.new_tensor(
                float(geometry.sequence_length)
            ),
        }
