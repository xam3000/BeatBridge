"""New control semantics over the unchanged, SHA-bound legacy variable networks."""

from dataclasses import dataclass, replace
import math

import torch

from . import variable_model as legacy
from .control_initialization import EQUAL_POWER, LEGACY, bind_control_state, config_dict, neutral_at_zero, validate_initialization


@dataclass(frozen=True)
class VariableTimeSharedMLPConfig(legacy.VariableTimeSharedMLPConfig):
    control_initialization: str = EQUAL_POWER

    def __post_init__(self):
        super().__post_init__()
        validate_initialization(self.control_initialization)

    def to_dict(self):
        return config_dict(self)


@dataclass(frozen=True)
class VariableTCNBiLSTMControlConfig(legacy.VariableTCNBiLSTMControlConfig):
    control_initialization: str = EQUAL_POWER

    def __post_init__(self):
        super().__post_init__()
        validate_initialization(self.control_initialization)

    def to_dict(self):
        return config_dict(self)


def _apply_contract(output, config):
    if getattr(config, "control_initialization", LEGACY) == LEGACY:
        return output
    position = output.vocal_position
    duck = (config.maximum_vocal_ducking * neutral_at_zero(output.vocal_duck_logits - config.initial_vocal_duck_logit)
            * (4 * position * (1 - position)).unsqueeze(-2))
    duck_a, duck_b = duck.unbind(-2)
    angle = position * (math.pi / 2)
    fields = dict(vocal_duck_a=duck_a, vocal_duck_b=duck_b,
                  vocal_gain_a=torch.cos(angle).clamp(0, 1) * (1 - duck_a),
                  vocal_gain_b=torch.sin(angle).clamp(0, 1) * (1 - duck_b))
    if isinstance(output, legacy.VariableTCNBiLSTMControlOutput):
        # The vocal renderer uses the named five controls. Keep the auxiliary
        # ten-channel view consistent with that rendering (no band EQ).
        controls = output.controls.clone()
        mix_angle = output.mix_position * (math.pi / 2)
        controls[..., 0] = torch.cos(mix_angle).clamp(0, 1)
        controls[..., 1] = torch.sin(mix_angle).clamp(0, 1)
        controls[..., 2:8] = 1
        controls[..., 9] = (duck_a + duck_b) / 2
        fields["controls"] = controls
    return replace(output, **fields)


class VariableTimeSharedMLP(legacy.VariableTimeSharedMLP):
    def __init__(self, config=None):
        super().__init__(config or VariableTimeSharedMLPConfig())
        bind_control_state(self)

    def forward(self, features_a, features_b, global_features, **length):
        output = super().forward(features_a, features_b, global_features, **length)
        return _apply_contract(output, self.config)


class VariableTCNBiLSTMTransitionControl(legacy.VariableTCNBiLSTMTransitionControl):
    def __init__(self, config=None):
        super().__init__(config or VariableTCNBiLSTMControlConfig())
        bind_control_state(self)

    def forward(self, features_a, features_b, global_features, **length):
        output = super().forward(features_a, features_b, global_features, **length)
        return _apply_contract(output, self.config)
