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
TRANSITION_CONTROL_MODEL_FORMAT_VERSION = 3
TRANSITION_CONTROL_MODEL_NAME = "tcn_bilstm_transition_control_v1"
TRANSITION_CONTROL_OUTPUT_NAMES = (
    "gain_A",
    "gain_B",
    "eq_low_A",
    "eq_low_B",
    "eq_mid_A",
    "eq_mid_B",
    "eq_high_A",
    "eq_high_B",
    "low_end_ownership",
    "vocal_ducking",
)


def _require_python_int(name: str, value) -> int:
    """Require an actual Python ``int`` for frozen architecture fields."""

    if type(value) is not int:
        raise ValueError(f"{name} must be a Python int")
    return value


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


@dataclass(frozen=True)
class TCNBiLSTMTransitionControlConfig:
    """Architecture contract for the larger transition-control model.

    The two track encoders share weights.  Global pair features are projected
    to the fusion width and added after the four-way pair fusion, preserving
    the explicit ``[A, B, A-B, A*B]`` representation.
    """

    encoder_channels: tuple[int, int] = (64, 128)
    tcn_kernel_size: int = 3
    tcn_dilation: int = 2
    fusion_dimension: int = 256
    controller_hidden_size: int = 128
    controller_layers: int = 2
    output_dimension: int = len(TRANSITION_CONTROL_OUTPUT_NAMES)
    dropout: float = 0.0

    def __post_init__(self):
        if (
            type(self.encoder_channels) is not tuple
            or len(self.encoder_channels) != 2
            or any(type(value) is not int for value in self.encoder_channels)
        ):
            raise ValueError(
                "encoder_channels must be a tuple of two Python ints (64, 128)"
            )
        if tuple(self.encoder_channels) != (64, 128):
            raise ValueError("encoder_channels must be exactly (64, 128)")
        tcn_kernel_size = _require_python_int("tcn_kernel_size", self.tcn_kernel_size)
        tcn_dilation = _require_python_int("tcn_dilation", self.tcn_dilation)
        fusion_dimension = _require_python_int("fusion_dimension", self.fusion_dimension)
        controller_hidden_size = _require_python_int(
            "controller_hidden_size", self.controller_hidden_size
        )
        controller_layers = _require_python_int("controller_layers", self.controller_layers)
        output_dimension = _require_python_int("output_dimension", self.output_dimension)
        if tcn_kernel_size < 3 or tcn_kernel_size % 2 == 0:
            raise ValueError("tcn_kernel_size must be an odd integer >= 3")
        if tcn_dilation <= 0:
            raise ValueError("tcn_dilation must be positive")
        if fusion_dimension != 256:
            raise ValueError("fusion_dimension must be 256")
        if controller_hidden_size != 128:
            raise ValueError("controller_hidden_size must be 128")
        if controller_layers != 2:
            raise ValueError("controller_layers must be 2")
        if output_dimension != len(TRANSITION_CONTROL_OUTPUT_NAMES):
            raise ValueError("output_dimension must match the ten control outputs")
        if not 0.0 <= float(self.dropout) < 1.0:
            raise ValueError("dropout must be in [0, 1)")

    def to_dict(self):
        payload = asdict(self)
        payload["encoder_channels"] = list(self.encoder_channels)
        return payload


@dataclass(frozen=True)
class TCNBiLSTMTransitionControlOutput:
    """Bounded per-halfbeat transition controls.

    ``controls`` has shape ``(B, 32, 10)`` (or ``(32, 10)`` for a single
    example).  The controller logits are retained for diagnostics and future
    constraint transforms; the public controls are sigmoid-bounded to [0, 1].
    """

    format_version: int
    model_name: str
    controls: torch.Tensor
    controller_logits: torch.Tensor

    def __getitem__(self, name: str) -> torch.Tensor:
        try:
            index = TRANSITION_CONTROL_OUTPUT_NAMES.index(name)
        except ValueError as error:
            raise KeyError(name) from error
        return self.controls[..., index]

    @property
    def gain_a(self):
        return self["gain_A"]

    @property
    def gain_b(self):
        return self["gain_B"]

    @property
    def low_end_ownership(self):
        return self["low_end_ownership"]

    @property
    def vocal_ducking(self):
        return self["vocal_ducking"]


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


class TCNBiLSTMTransitionControl(nn.Module):
    """Shared TCN + fusion + two-layer BiLSTM transition controller.

    This is the planned larger architecture, kept separate from the trained
    v1/v2 MLPs.  It consumes the existing feature contract and returns ten
    bounded controls for each of the 32 half-beat positions.  Monotonicity,
    complementary gains, and renderer-specific semantics remain explicit
    downstream constraints rather than being silently assumed by this raw
    architecture implementation.
    """

    def __init__(self, config: TCNBiLSTMTransitionControlConfig | None = None):
        super().__init__()
        self.config = config or TCNBiLSTMTransitionControlConfig()
        first_channels, last_channels = self.config.encoder_channels
        kernel_size = int(self.config.tcn_kernel_size)
        dilation = int(self.config.tcn_dilation)
        padding = (kernel_size - 1) // 2
        dilated_padding = dilation * (kernel_size - 1) // 2

        # One module instance is deliberately reused for A and B.
        self.shared_tcn_encoder = nn.Sequential(
            nn.Conv1d(FEATURE_DIMENSION, first_channels, kernel_size, padding=padding),
            nn.GELU(),
            nn.Conv1d(first_channels, last_channels, kernel_size, padding=padding),
            nn.GELU(),
            nn.Conv1d(
                last_channels,
                last_channels,
                kernel_size,
                padding=dilated_padding,
                dilation=dilation,
            ),
            nn.GELU(),
        )
        self.fusion = nn.Sequential(
            nn.Linear(4 * last_channels, self.config.fusion_dimension),
            nn.GELU(),
        )
        self.global_projection = nn.Sequential(
            nn.LayerNorm(GLOBAL_FEATURE_DIMENSION),
            nn.Linear(GLOBAL_FEATURE_DIMENSION, self.config.fusion_dimension),
        )
        self.controller = nn.LSTM(
            input_size=self.config.fusion_dimension,
            hidden_size=self.config.controller_hidden_size,
            num_layers=self.config.controller_layers,
            batch_first=True,
            dropout=(
                float(self.config.dropout)
                if self.config.controller_layers > 1
                else 0.0
            ),
            bidirectional=True,
        )
        self.output_head = nn.Linear(
            2 * self.config.controller_hidden_size,
            self.config.output_dimension,
        )

    def forward(
        self,
        features_a: torch.Tensor,
        features_b: torch.Tensor,
        global_features: torch.Tensor,
    ) -> TCNBiLSTMTransitionControlOutput:
        features_a, features_b, global_features, squeezed = _normalise_inputs(
            features_a,
            features_b,
            global_features,
        )
        # Conv1d expects (batch, channels, time); the shared encoder preserves
        # the 32-step time axis.
        encoded_a = self.shared_tcn_encoder(features_a.transpose(1, 2)).transpose(1, 2)
        encoded_b = self.shared_tcn_encoder(features_b.transpose(1, 2)).transpose(1, 2)
        pair_features = torch.cat(
            (
                encoded_a,
                encoded_b,
                encoded_a - encoded_b,
                encoded_a * encoded_b,
            ),
            dim=-1,
        )
        fused = self.fusion(pair_features)
        fused = fused + self.global_projection(global_features).unsqueeze(1)
        sequence, _ = self.controller(fused)
        controller_logits = self.output_head(sequence)
        controls = torch.sigmoid(controller_logits)
        if squeezed:
            controls = controls.squeeze(0)
            controller_logits = controller_logits.squeeze(0)
        return TCNBiLSTMTransitionControlOutput(
            format_version=TRANSITION_CONTROL_MODEL_FORMAT_VERSION,
            model_name=TRANSITION_CONTROL_MODEL_NAME,
            controls=controls,
            controller_logits=controller_logits,
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
