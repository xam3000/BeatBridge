"""Additive variable-length time-shared MLP baseline for Dataset Format 2."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import math

import torch
from torch import nn

from src.control import DEFAULT_INCREMENT_LOGIT_BOUND, bounded_monotone_unit_curve
from src.features import FEATURE_DIMENSION, GLOBAL_FEATURE_DIMENSION
from src.features.variable_contract import geometry_for_length


VARIABLE_MLP_MODEL_FORMAT_VERSION = 2
VARIABLE_TIME_SHARED_MLP_MODEL_NAME = "variable_time_shared_mlp_v1"
VARIABLE_LENGTH_CONDITIONING_VERSION = 1
VARIABLE_TCN_BILSTM_MODEL_FORMAT_VERSION = 4
VARIABLE_TCN_BILSTM_MODEL_NAME = "variable_tcn_bilstm_transition_control_v1"


@dataclass(frozen=True)
class VariableTimeSharedMLPConfig:
    """Architecture and constructive-curve contract for the v2 baseline."""

    hidden_dimensions: tuple[int, ...] = (64, 32)
    dropout: float = 0.0
    increment_logit_bound: float = DEFAULT_INCREMENT_LOGIT_BOUND
    maximum_vocal_ducking: float = 0.75
    initial_vocal_duck_logit: float = -4.0

    def __post_init__(self):
        if not self.hidden_dimensions or any(int(value) <= 0 for value in self.hidden_dimensions):
            raise ValueError("hidden_dimensions must contain positive integers")
        if not 0.0 <= float(self.dropout) < 1.0:
            raise ValueError("dropout must be in [0, 1)")
        if not math.isfinite(float(self.increment_logit_bound)) or self.increment_logit_bound <= 0:
            raise ValueError("increment_logit_bound must be finite and positive")
        if not 0.0 <= float(self.maximum_vocal_ducking) < 1.0:
            raise ValueError("maximum_vocal_ducking must be in [0, 1)")
        if not math.isfinite(float(self.initial_vocal_duck_logit)):
            raise ValueError("initial_vocal_duck_logit must be finite")

    def to_dict(self):
        payload = asdict(self)
        payload["hidden_dimensions"] = list(self.hidden_dimensions)
        return payload


@dataclass(frozen=True)
class VariableTimeSharedMLPOutput:
    """Constructively valid controls with exactly the requested ``T`` points."""

    format_version: int
    model_name: str
    transition_length_bars: int
    transition_length_beats: int
    sequence_length: int
    length_condition: torch.Tensor
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
class VariableTCNBiLSTMControlConfig:
    """Dynamic-T temporal controller contract, independent from v1 TCN/LSTM."""

    encoder_channels: tuple[int, int] = (64, 128)
    tcn_kernel_size: int = 3
    tcn_dilation: int = 2
    fusion_dimension: int = 256
    controller_hidden_size: int = 128
    controller_layers: int = 2
    output_dimension: int = 10
    dropout: float = 0.0
    increment_logit_bound: float = DEFAULT_INCREMENT_LOGIT_BOUND
    maximum_vocal_ducking: float = 0.75
    initial_vocal_duck_logit: float = -4.0

    def __post_init__(self):
        if self.encoder_channels != (64, 128):
            raise ValueError("encoder_channels must be exactly (64, 128)")
        integer_fields = {
            "tcn_kernel_size": self.tcn_kernel_size,
            "tcn_dilation": self.tcn_dilation,
            "fusion_dimension": self.fusion_dimension,
            "controller_hidden_size": self.controller_hidden_size,
            "controller_layers": self.controller_layers,
            "output_dimension": self.output_dimension,
        }
        if any(type(value) is not int for value in integer_fields.values()):
            raise ValueError("TCN/BiLSTM architecture fields must be Python ints")
        if self.tcn_kernel_size < 3 or self.tcn_kernel_size % 2 == 0:
            raise ValueError("tcn_kernel_size must be odd and at least 3")
        if self.tcn_dilation <= 0 or self.fusion_dimension != 256:
            raise ValueError("tcn_dilation must be positive and fusion_dimension must be 256")
        if self.controller_hidden_size != 128 or self.controller_layers != 2:
            raise ValueError("controller_hidden_size and controller_layers must be 128 and 2")
        if self.output_dimension != 10:
            raise ValueError("output_dimension must be exactly 10")
        if not 0.0 <= float(self.dropout) < 1.0:
            raise ValueError("dropout must be in [0, 1)")
        if not math.isfinite(float(self.increment_logit_bound)) or self.increment_logit_bound <= 0:
            raise ValueError("increment_logit_bound must be finite and positive")
        if not 0.0 <= float(self.maximum_vocal_ducking) < 1.0:
            raise ValueError("maximum_vocal_ducking must be in [0, 1)")
        if not math.isfinite(float(self.initial_vocal_duck_logit)):
            raise ValueError("initial_vocal_duck_logit must be finite")

    def to_dict(self):
        payload = asdict(self)
        payload["encoder_channels"] = list(self.encoder_channels)
        return payload


@dataclass(frozen=True)
class VariableTCNBiLSTMControlOutput:
    """Dynamic-T temporal controls with explicit vocal-aware semantics."""

    format_version: int
    model_name: str
    transition_length_bars: int
    transition_length_beats: int
    sequence_length: int
    length_condition: torch.Tensor
    controls: torch.Tensor
    controller_logits: torch.Tensor
    mix_position: torch.Tensor
    low_end_position: torch.Tensor
    vocal_position: torch.Tensor
    vocal_duck_a: torch.Tensor
    vocal_duck_b: torch.Tensor
    vocal_gain_a: torch.Tensor
    vocal_gain_b: torch.Tensor
    position_increment_logits: torch.Tensor
    vocal_duck_logits: torch.Tensor


class VariableTimeSharedMLP(nn.Module):
    """Predict time-shared control increments for one homogeneous ``T`` batch.

    The 16 v1 global features are concatenated unchanged.  The normalized
    length condition is a separate input channel and is present in both the
    interval and point heads, so it cannot be silently ignored as metadata.
    """

    def __init__(self, config: VariableTimeSharedMLPConfig | None = None):
        super().__init__()
        self.config = config or VariableTimeSharedMLPConfig()
        input_dimension = 2 * FEATURE_DIMENSION + GLOBAL_FEATURE_DIMENSION + 1
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
        *,
        transition_length_bars,
        length_condition: torch.Tensor | None = None,
    ) -> VariableTimeSharedMLPOutput:
        features_a, features_b, global_features, squeezed = _normalise_variable_inputs(
            features_a,
            features_b,
            global_features,
        )
        geometry = geometry_for_length(
            transition_length_bars,
            sequence_length=int(features_a.shape[1]),
        )
        condition = _normalise_length_condition(
            length_condition,
            geometry.transition_length_bars,
            batch_size=int(features_a.shape[0]),
            device=features_a.device,
            dtype=features_a.dtype,
        )
        interval_condition = condition.unsqueeze(1).expand(-1, geometry.sequence_length - 1, -1)
        midpoint_fused = torch.cat(
            (
                0.5 * (features_a[:, :-1] + features_a[:, 1:]),
                0.5 * (features_b[:, :-1] + features_b[:, 1:]),
                global_features.unsqueeze(1).expand(-1, geometry.sequence_length - 1, -1),
                interval_condition,
            ),
            dim=-1,
        )
        position_logits = self.interval_mlp(midpoint_fused).transpose(1, 2)
        positions = torch.stack(
            tuple(
                _exact_unit_curve(
                    bounded_monotone_unit_curve(
                        position_logits[:, index],
                        self.config.increment_logit_bound,
                    )
                )
                for index in range(3)
            ),
            dim=1,
        )

        point_fused = torch.cat(
            (
                features_a,
                features_b,
                global_features.unsqueeze(1).expand(-1, geometry.sequence_length, -1),
                condition.unsqueeze(1).expand(-1, geometry.sequence_length, -1),
            ),
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
        angle = vocal_position * (math.pi / 2.0)
        vocal_gain_a = torch.cos(angle).clamp(0.0, 1.0) * (1.0 - vocal_duck[:, 0])
        vocal_gain_b = torch.sin(angle).clamp(0.0, 1.0) * (1.0 - vocal_duck[:, 1])
        if squeezed:
            positions = positions.squeeze(0)
            position_logits = position_logits.squeeze(0)
            vocal_duck_logits = vocal_duck_logits.squeeze(0)
            vocal_duck = vocal_duck.squeeze(0)
            vocal_gain_a = vocal_gain_a.squeeze(0)
            vocal_gain_b = vocal_gain_b.squeeze(0)
            condition = condition.squeeze(0)
        return VariableTimeSharedMLPOutput(
            format_version=VARIABLE_MLP_MODEL_FORMAT_VERSION,
            model_name=VARIABLE_TIME_SHARED_MLP_MODEL_NAME,
            transition_length_bars=geometry.transition_length_bars,
            transition_length_beats=geometry.transition_length_beats,
            sequence_length=geometry.sequence_length,
            length_condition=condition,
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


class VariableTCNBiLSTMTransitionControl(nn.Module):
    """Shared TCN + pair fusion + packed BiLSTM for one valid Dataset-2 length.

    Homogeneous Dataset-2 batches need no padding.  ``sequence_lengths`` is
    nevertheless supported for a padded carrier tensor: padded feature values
    are masked before convolution and excluded from the BiLSTM via packing.
    The public output is always cropped to the explicitly requested ``T``.
    """

    def __init__(self, config: VariableTCNBiLSTMControlConfig | None = None):
        super().__init__()
        self.config = config or VariableTCNBiLSTMControlConfig()
        first_channels, last_channels = self.config.encoder_channels
        kernel_size = self.config.tcn_kernel_size
        dilation = self.config.tcn_dilation
        self.shared_tcn_encoder = nn.Sequential(
            nn.Conv1d(FEATURE_DIMENSION, first_channels, kernel_size, padding=(kernel_size - 1) // 2),
            nn.GELU(),
            nn.Conv1d(first_channels, last_channels, kernel_size, padding=(kernel_size - 1) // 2),
            nn.GELU(),
            nn.Conv1d(
                last_channels,
                last_channels,
                kernel_size,
                padding=dilation * (kernel_size - 1) // 2,
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
        # Do not LayerNorm a single scalar: that would erase L/8 entirely.
        self.length_projection = nn.Linear(1, self.config.fusion_dimension)
        self.controller = nn.LSTM(
            input_size=self.config.fusion_dimension,
            hidden_size=self.config.controller_hidden_size,
            num_layers=self.config.controller_layers,
            batch_first=True,
            dropout=float(self.config.dropout) if self.config.controller_layers > 1 else 0.0,
            bidirectional=True,
        )
        self.output_head = nn.Linear(
            2 * self.config.controller_hidden_size,
            self.config.output_dimension,
        )
        nn.init.zeros_(self.output_head.weight)
        nn.init.zeros_(self.output_head.bias)
        # A near-neutral but nonzero starting ducking is retained separately.
        with torch.no_grad():
            self.output_head.bias[3:5].fill_(float(self.config.initial_vocal_duck_logit))

    def forward(
        self,
        features_a: torch.Tensor,
        features_b: torch.Tensor,
        global_features: torch.Tensor,
        *,
        transition_length_bars,
        length_condition: torch.Tensor | None = None,
        sequence_lengths: torch.Tensor | None = None,
    ) -> VariableTCNBiLSTMControlOutput:
        features_a, features_b, global_features, squeezed = _normalise_variable_inputs(
            features_a,
            features_b,
            global_features,
        )
        geometry = geometry_for_length(transition_length_bars)
        valid_lengths = _normalise_sequence_lengths(
            sequence_lengths,
            batch_size=int(features_a.shape[0]),
            padded_time=int(features_a.shape[1]),
            expected_time=geometry.sequence_length,
            device=features_a.device,
        )
        condition = _normalise_length_condition(
            length_condition,
            geometry.transition_length_bars,
            batch_size=int(features_a.shape[0]),
            device=features_a.device,
            dtype=features_a.dtype,
        )
        valid_mask = (
            torch.arange(features_a.shape[1], device=features_a.device).unsqueeze(0)
            < valid_lengths.unsqueeze(1)
        )
        feature_mask = valid_mask.unsqueeze(-1).to(dtype=features_a.dtype)
        encoded_a = self.shared_tcn_encoder((features_a * feature_mask).transpose(1, 2)).transpose(1, 2)
        encoded_b = self.shared_tcn_encoder((features_b * feature_mask).transpose(1, 2)).transpose(1, 2)
        pair_features = torch.cat(
            (encoded_a, encoded_b, encoded_a - encoded_b, encoded_a * encoded_b),
            dim=-1,
        )
        fused = self.fusion(pair_features)
        fused = fused + self.global_projection(global_features).unsqueeze(1)
        fused = fused + self.length_projection(condition).unsqueeze(1)
        packed = nn.utils.rnn.pack_padded_sequence(
            fused,
            valid_lengths.detach().to(device="cpu", dtype=torch.int64),
            batch_first=True,
            enforce_sorted=False,
        )
        packed_sequence, _ = self.controller(packed)
        sequence, _ = nn.utils.rnn.pad_packed_sequence(
            packed_sequence,
            batch_first=True,
            total_length=features_a.shape[1],
        )
        controller_logits = self.output_head(sequence[:, : geometry.sequence_length])
        position_increment_logits = controller_logits[:, :-1, :3].transpose(1, 2)
        positions = _exact_unit_curve(
            bounded_monotone_unit_curve(
                position_increment_logits,
                self.config.increment_logit_bound,
            )
        )
        vocal_duck_logits = controller_logits[:, :, 3:5].transpose(1, 2)
        vocal_position = positions[:, 2]
        duck_window = 4.0 * vocal_position * (1.0 - vocal_position)
        vocal_duck = (
            float(self.config.maximum_vocal_ducking)
            * torch.sigmoid(vocal_duck_logits)
            * duck_window.unsqueeze(1)
        )
        angle = vocal_position * (math.pi / 2.0)
        vocal_gain_a = torch.cos(angle).clamp(0.0, 1.0) * (1.0 - vocal_duck[:, 0])
        vocal_gain_b = torch.sin(angle).clamp(0.0, 1.0) * (1.0 - vocal_duck[:, 1])
        controls = torch.sigmoid(controller_logits).clone()
        controls[..., 0] = 1.0 - positions[:, 0]
        controls[..., 1] = positions[:, 0]
        controls[..., 8] = positions[:, 1]
        controls[..., 9] = 0.5 * (vocal_duck[:, 0] + vocal_duck[:, 1])
        if squeezed:
            controls = controls.squeeze(0)
            controller_logits = controller_logits.squeeze(0)
            positions = positions.squeeze(0)
            position_increment_logits = position_increment_logits.squeeze(0)
            vocal_duck_logits = vocal_duck_logits.squeeze(0)
            vocal_duck = vocal_duck.squeeze(0)
            vocal_gain_a = vocal_gain_a.squeeze(0)
            vocal_gain_b = vocal_gain_b.squeeze(0)
            condition = condition.squeeze(0)
        return VariableTCNBiLSTMControlOutput(
            format_version=VARIABLE_TCN_BILSTM_MODEL_FORMAT_VERSION,
            model_name=VARIABLE_TCN_BILSTM_MODEL_NAME,
            transition_length_bars=geometry.transition_length_bars,
            transition_length_beats=geometry.transition_length_beats,
            sequence_length=geometry.sequence_length,
            length_condition=condition,
            controls=controls,
            controller_logits=controller_logits,
            mix_position=positions[..., 0, :],
            low_end_position=positions[..., 1, :],
            vocal_position=positions[..., 2, :],
            vocal_duck_a=vocal_duck[..., 0, :],
            vocal_duck_b=vocal_duck[..., 1, :],
            vocal_gain_a=vocal_gain_a,
            vocal_gain_b=vocal_gain_b,
            position_increment_logits=position_increment_logits,
            vocal_duck_logits=vocal_duck_logits,
        )

    @property
    def parameter_count(self):
        return sum(parameter.numel() for parameter in self.parameters())


def _control_mlp(input_dimension, config, *, output_dimension, output_bias):
    layers: list[nn.Module] = [nn.LayerNorm(input_dimension)]
    previous = int(input_dimension)
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


def _normalise_variable_inputs(features_a, features_b, global_features):
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
    if features_a.ndim != 3 or features_a.shape[2] != FEATURE_DIMENSION:
        raise ValueError(f"Track features must have shape (B, T, {FEATURE_DIMENSION})")
    if global_features.ndim != 2 or global_features.shape != (
        features_a.shape[0],
        GLOBAL_FEATURE_DIMENSION,
    ):
        raise ValueError(f"global_features must have shape (B, {GLOBAL_FEATURE_DIMENSION})")
    if not (features_a.device == features_b.device == global_features.device):
        raise ValueError("All model inputs must share device")
    if not (features_a.dtype == features_b.dtype == global_features.dtype):
        raise ValueError("All model inputs must share dtype")
    return features_a, features_b, global_features, squeezed


def _normalise_sequence_lengths(value, *, batch_size, padded_time, expected_time, device):
    """Validate homogeneous valid lengths for an optionally padded carrier."""
    if value is None:
        if int(padded_time) != int(expected_time):
            raise ValueError(
                "Padded feature tensors require explicit sequence_lengths"
            )
        return torch.full((batch_size,), int(expected_time), device=device, dtype=torch.int64)
    if not isinstance(value, torch.Tensor):
        raise TypeError("sequence_lengths must be a torch.Tensor")
    lengths = value.to(device=device, dtype=torch.int64)
    if lengths.ndim != 1 or lengths.shape[0] != batch_size:
        raise ValueError(f"sequence_lengths must have shape ({batch_size},)")
    if torch.any(lengths != int(expected_time)):
        raise ValueError(
            "Variable Dataset-2 batches must contain one explicit valid sequence length"
        )
    if int(padded_time) < int(expected_time):
        raise ValueError("Padded feature tensor is shorter than its valid sequence length")
    return lengths


def _normalise_length_condition(value, transition_length_bars, *, batch_size, device, dtype):
    expected = float(geometry_for_length(transition_length_bars).length_condition)
    if value is None:
        raise ValueError("length_condition must be provided explicitly for the variable model")
    if not isinstance(value, torch.Tensor):
        raise TypeError("length_condition must be a torch.Tensor")
    condition = value
    if condition.ndim == 1:
        condition = condition.unsqueeze(0)
    if condition.shape != (batch_size, 1):
        raise ValueError(f"length_condition must have shape ({batch_size}, 1)")
    if not condition.is_floating_point() or condition.device != device or condition.dtype != dtype:
        raise ValueError("length_condition must share floating dtype and device with features")
    if not torch.isfinite(condition).all() or not torch.allclose(
        condition,
        condition.new_full(condition.shape, expected),
        rtol=0.0,
        atol=1e-6,
    ):
        raise ValueError("length_condition does not match transition_length_bars")
    return condition


def _exact_unit_curve(curve):
    """Keep the differentiable interior while making both contract endpoints exact."""
    result = curve.clone()
    result[..., 0] = 0.0
    result[..., -1] = 1.0
    return result
