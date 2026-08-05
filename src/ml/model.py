"""Small time-shared feature-to-control MLP baseline."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import math

import torch
from torch import nn

from src.control import (
    DEFAULT_INCREMENT_LOGIT_BOUND,
    bounded_monotone_unit_curve,
)
from src.features import FEATURE_DIMENSION, GLOBAL_FEATURE_DIMENSION, SEQUENCE_LENGTH


FEATURE_CONTROL_MODEL_FORMAT_VERSION = 1
FEATURE_CONTROL_MODEL_NAME = "time_shared_mlp_v1"
VOCAL_FEATURE_CONTROL_MODEL_FORMAT_VERSION = 2
VOCAL_FEATURE_CONTROL_MODEL_NAME = "vocal_time_shared_mlp_v2"


@dataclass(frozen=True)
class FeatureControlMLPConfig:
    """Architecture contract for the first intentionally small baseline."""

    hidden_dimensions: tuple[int, ...] = (64, 32)
    dropout: float = 0.0
    increment_logit_bound: float = DEFAULT_INCREMENT_LOGIT_BOUND

    def __post_init__(self):
        if not self.hidden_dimensions or any(int(value) <= 0 for value in self.hidden_dimensions):
            raise ValueError("hidden_dimensions must contain positive integers")
        if not 0.0 <= float(self.dropout) < 1.0:
            raise ValueError("dropout must be in [0, 1)")
        if float(self.increment_logit_bound) <= 0:
            raise ValueError("increment_logit_bound must be greater than 0")

    def to_dict(self):
        payload = asdict(self)
        payload["hidden_dimensions"] = list(self.hidden_dimensions)
        return payload


@dataclass(frozen=True)
class FeatureControlOutput:
    """Predicted logits and constructively valid mixing curves."""

    format_version: int
    model_name: str
    mix_position: torch.Tensor
    low_end_position: torch.Tensor
    mix_increment_logits: torch.Tensor
    low_end_increment_logits: torch.Tensor


@dataclass(frozen=True)
class VocalFeatureControlMLPConfig(FeatureControlMLPConfig):
    """Small additive baseline with independent vocal handover and ducking."""

    maximum_vocal_ducking: float = 0.75
    initial_vocal_duck_logit: float = -4.0

    def __post_init__(self):
        super().__post_init__()
        if not 0.0 <= float(self.maximum_vocal_ducking) < 1.0:
            raise ValueError("maximum_vocal_ducking must be in [0, 1)")
        if not math.isfinite(float(self.initial_vocal_duck_logit)):
            raise ValueError("initial_vocal_duck_logit must be finite")


@dataclass(frozen=True)
class VocalFeatureControlOutput:
    """Three ownership curves plus separate source/target vocal ducking."""

    format_version: int
    model_name: str
    mix_position: torch.Tensor
    low_end_position: torch.Tensor
    vocal_position: torch.Tensor
    vocal_duck_a: torch.Tensor
    vocal_duck_b: torch.Tensor
    vocal_gain_a: torch.Tensor
    vocal_gain_b: torch.Tensor
    position_increment_logits: torch.Tensor
    vocal_duck_logits: torch.Tensor


class FeatureControlMLP(nn.Module):
    """Predict each half-beat handover increment with one shared MLP."""

    def __init__(self, config: FeatureControlMLPConfig | None = None):
        super().__init__()
        self.config = config or FeatureControlMLPConfig()
        input_dimension = 2 * FEATURE_DIMENSION + GLOBAL_FEATURE_DIMENSION
        layers: list[nn.Module] = [nn.LayerNorm(input_dimension)]
        previous = input_dimension
        for hidden in self.config.hidden_dimensions:
            layers.extend((nn.Linear(previous, int(hidden)), nn.GELU()))
            if self.config.dropout:
                layers.append(nn.Dropout(float(self.config.dropout)))
            previous = int(hidden)
        output = nn.Linear(previous, 2)
        nn.init.zeros_(output.weight)
        nn.init.zeros_(output.bias)
        layers.append(output)
        self.interval_mlp = nn.Sequential(*layers)

    def forward(
        self,
        features_a: torch.Tensor,
        features_b: torch.Tensor,
        global_features: torch.Tensor,
    ) -> FeatureControlOutput:
        features_a, features_b, global_features, squeezed = _normalise_inputs(
            features_a,
            features_b,
            global_features,
        )
        midpoint_a = 0.5 * (features_a[:, :-1] + features_a[:, 1:])
        midpoint_b = 0.5 * (features_b[:, :-1] + features_b[:, 1:])
        global_steps = global_features.unsqueeze(1).expand(-1, SEQUENCE_LENGTH - 1, -1)
        fused = torch.cat((midpoint_a, midpoint_b, global_steps), dim=-1)
        logits = self.interval_mlp(fused).transpose(1, 2)
        curves = bounded_monotone_unit_curve(
            logits,
            self.config.increment_logit_bound,
        )
        if squeezed:
            logits = logits.squeeze(0)
            curves = curves.squeeze(0)
        return FeatureControlOutput(
            format_version=FEATURE_CONTROL_MODEL_FORMAT_VERSION,
            model_name=FEATURE_CONTROL_MODEL_NAME,
            mix_position=curves[..., 0, :],
            low_end_position=curves[..., 1, :],
            mix_increment_logits=logits[..., 0, :],
            low_end_increment_logits=logits[..., 1, :],
        )

    @property
    def parameter_count(self):
        return sum(parameter.numel() for parameter in self.parameters())


class VocalFeatureControlMLP(nn.Module):
    """Predict mix, low-end, and vocal controls from the same feature contract."""

    def __init__(self, config: VocalFeatureControlMLPConfig | None = None):
        super().__init__()
        self.config = config or VocalFeatureControlMLPConfig()
        input_dimension = 2 * FEATURE_DIMENSION + GLOBAL_FEATURE_DIMENSION
        self.interval_mlp = _control_mlp(
            input_dimension,
            self.config,
            output_dimension=3,
            output_bias=0.0,
        )
        self.point_vocal_duck_mlp = _control_mlp(
            input_dimension,
            self.config,
            output_dimension=2,
            output_bias=float(self.config.initial_vocal_duck_logit),
        )

    def forward(
        self,
        features_a: torch.Tensor,
        features_b: torch.Tensor,
        global_features: torch.Tensor,
    ) -> VocalFeatureControlOutput:
        features_a, features_b, global_features, squeezed = _normalise_inputs(
            features_a,
            features_b,
            global_features,
        )
        global_steps = global_features.unsqueeze(1).expand(-1, SEQUENCE_LENGTH - 1, -1)
        midpoint_fused = torch.cat(
            (
                0.5 * (features_a[:, :-1] + features_a[:, 1:]),
                0.5 * (features_b[:, :-1] + features_b[:, 1:]),
                global_steps,
            ),
            dim=-1,
        )
        position_logits = self.interval_mlp(midpoint_fused).transpose(1, 2)
        positions = bounded_monotone_unit_curve(
            position_logits,
            self.config.increment_logit_bound,
        )

        global_points = global_features.unsqueeze(1).expand(-1, SEQUENCE_LENGTH, -1)
        point_fused = torch.cat(
            (features_a, features_b, global_points),
            dim=-1,
        )
        vocal_duck_logits = self.point_vocal_duck_mlp(point_fused).transpose(1, 2)
        vocal_position = positions[:, 2]
        duck_window = 4.0 * vocal_position * (1.0 - vocal_position)
        vocal_duck = (
            float(self.config.maximum_vocal_ducking)
            * torch.sigmoid(vocal_duck_logits)
            * duck_window.unsqueeze(1)
        )
        vocal_base_a = torch.cos(vocal_position * (math.pi / 2.0)).clamp(0.0, 1.0)
        vocal_base_b = torch.sin(vocal_position * (math.pi / 2.0)).clamp(0.0, 1.0)
        vocal_gain_a = vocal_base_a * (1.0 - vocal_duck[:, 0])
        vocal_gain_b = vocal_base_b * (1.0 - vocal_duck[:, 1])
        if squeezed:
            positions = positions.squeeze(0)
            position_logits = position_logits.squeeze(0)
            vocal_duck_logits = vocal_duck_logits.squeeze(0)
            vocal_duck = vocal_duck.squeeze(0)
            vocal_gain_a = vocal_gain_a.squeeze(0)
            vocal_gain_b = vocal_gain_b.squeeze(0)
        return VocalFeatureControlOutput(
            format_version=VOCAL_FEATURE_CONTROL_MODEL_FORMAT_VERSION,
            model_name=VOCAL_FEATURE_CONTROL_MODEL_NAME,
            mix_position=positions[..., 0, :],
            low_end_position=positions[..., 1, :],
            vocal_position=positions[..., 2, :],
            vocal_duck_a=vocal_duck[..., 0, :],
            vocal_duck_b=vocal_duck[..., 1, :],
            vocal_gain_a=vocal_gain_a,
            vocal_gain_b=vocal_gain_b,
            position_increment_logits=position_logits,
            vocal_duck_logits=vocal_duck_logits,
        )

    @property
    def parameter_count(self):
        return sum(parameter.numel() for parameter in self.parameters())


def _control_mlp(input_dimension, config, *, output_dimension, output_bias):
    layers: list[nn.Module] = [nn.LayerNorm(input_dimension)]
    previous = input_dimension
    for hidden in config.hidden_dimensions:
        layers.extend((nn.Linear(previous, int(hidden)), nn.GELU()))
        if config.dropout:
            layers.append(nn.Dropout(float(config.dropout)))
        previous = int(hidden)
    output = nn.Linear(previous, int(output_dimension))
    nn.init.zeros_(output.weight)
    nn.init.constant_(output.bias, float(output_bias))
    layers.append(output)
    return nn.Sequential(*layers)


def _normalise_inputs(features_a, features_b, global_features):
    for name, value in (
        ("features_a", features_a),
        ("features_b", features_b),
        ("global_features", global_features),
    ):
        if not isinstance(value, torch.Tensor):
            raise TypeError(f"{name} must be a torch.Tensor")
        if not value.is_floating_point():
            raise TypeError(f"{name} must use a floating-point dtype")
        if not torch.isfinite(value).all():
            raise ValueError(f"{name} must contain only finite values")
    squeezed = features_a.ndim == 2
    if squeezed:
        features_a = features_a.unsqueeze(0)
        features_b = features_b.unsqueeze(0)
        global_features = global_features.unsqueeze(0)
    if features_a.shape != features_b.shape:
        raise ValueError("features_a and features_b must have identical shapes")
    if features_a.ndim != 3 or features_a.shape[1:] != (
        SEQUENCE_LENGTH,
        FEATURE_DIMENSION,
    ):
        raise ValueError(
            f"Track features must have shape (B, {SEQUENCE_LENGTH}, {FEATURE_DIMENSION})"
        )
    if global_features.ndim != 2 or global_features.shape != (
        features_a.shape[0],
        GLOBAL_FEATURE_DIMENSION,
    ):
        raise ValueError(
            f"global_features must have shape (B, {GLOBAL_FEATURE_DIMENSION})"
        )
    if not (
        features_a.device == features_b.device == global_features.device
        and features_a.dtype == features_b.dtype == global_features.dtype
    ):
        raise ValueError("All model inputs must share device and dtype")
    return features_a, features_b, global_features, squeezed
