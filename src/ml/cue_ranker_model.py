"""The additive ``learned_cue_ranker_v1`` scalar scoring model."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import math

import torch
from torch import nn

from src.features import FEATURE_DIMENSION, GLOBAL_FEATURE_DIMENSION


CUE_RANKER_MODEL_FORMAT_VERSION = 1
CUE_RANKER_MODEL_NAME = "learned_cue_ranker_v1"
CUE_RANKER_CONTEXT_VERSION = "candidate_context_v1"
CUE_RANKER_CONTEXT_DIMENSION = 20
CUE_RANKER_GRID_SOURCE_VOCAB_SIZE = 32
CUE_RANKER_GRID_EMBEDDING_DIMENSION = 8


@dataclass(frozen=True)
class CueRankerTemporalConfig:
    """Frozen v1 architecture configuration from the implementation plan."""

    encoder_channels: tuple[int, int] = (64, 128)
    tcn_kernel_size: int = 3
    tcn_dilation: int = 2
    pair_projection_dimension: int = 192
    context_dimension: int = CUE_RANKER_CONTEXT_DIMENSION
    context_hidden_dimension: int = 64
    grid_vocab_size: int = CUE_RANKER_GRID_SOURCE_VOCAB_SIZE
    grid_embedding_dimension: int = CUE_RANKER_GRID_EMBEDDING_DIMENSION
    dropout: float = 0.0

    def __post_init__(self):
        if self.encoder_channels != (64, 128):
            raise ValueError("Cue-Ranker encoder_channels must be exactly (64, 128)")
        if self.tcn_kernel_size < 3 or self.tcn_kernel_size % 2 == 0:
            raise ValueError("tcn_kernel_size must be odd and at least 3")
        if self.tcn_dilation < 1:
            raise ValueError("tcn_dilation must be positive")
        for name in (
            "pair_projection_dimension",
            "context_dimension",
            "context_hidden_dimension",
            "grid_vocab_size",
            "grid_embedding_dimension",
        ):
            if type(getattr(self, name)) is not int or getattr(self, name) <= 0:
                raise ValueError(f"{name} must be a positive integer")
        if not 0.0 <= float(self.dropout) < 1.0:
            raise ValueError("dropout must be in [0, 1)")

    def to_dict(self):
        payload = asdict(self)
        payload["encoder_channels"] = list(self.encoder_channels)
        return payload


class CueRankerTemporalModel(nn.Module):
    """Score one finite scalar per candidate without using candidate IDs/positions.

    ``features_a`` and ``features_b`` may contain any one supported temporal
    length.  A batch must be homogeneous in ``T``; the grouped loader handles
    mixed lengths by splitting and reassembling a candidate group.
    """

    def __init__(self, config: CueRankerTemporalConfig | None = None):
        super().__init__()
        self.config = config or CueRankerTemporalConfig()
        first_channels, last_channels = self.config.encoder_channels
        kernel = self.config.tcn_kernel_size
        dilation = self.config.tcn_dilation
        self.shared_tcn_encoder = nn.Sequential(
            nn.Conv1d(FEATURE_DIMENSION, first_channels, kernel, padding=(kernel - 1) // 2),
            nn.GELU(),
            nn.Conv1d(first_channels, last_channels, kernel, padding=(kernel - 1) // 2),
            nn.GELU(),
            nn.Conv1d(
                last_channels,
                last_channels,
                kernel,
                dilation=dilation,
                padding=dilation * (kernel - 1) // 2,
            ),
            nn.GELU(),
        )
        self.pair_projection = nn.Sequential(
            nn.Linear(4 * last_channels, self.config.pair_projection_dimension),
            nn.GELU(),
        )
        self.global_projection = nn.Sequential(
            nn.LayerNorm(GLOBAL_FEATURE_DIMENSION),
            nn.Linear(GLOBAL_FEATURE_DIMENSION, self.config.pair_projection_dimension),
        )
        # A scalar is intentionally projected without LayerNorm: L/8 must
        # retain its meaning and cannot be normalized away.
        self.length_projection = nn.Linear(1, self.config.pair_projection_dimension)
        self.attention = nn.Linear(self.config.pair_projection_dimension, 1)
        self.pool_projection = nn.Sequential(
            nn.Linear(2 * self.config.pair_projection_dimension, self.config.pair_projection_dimension),
            nn.GELU(),
        )
        self.grid_source_embedding = nn.Embedding(
            self.config.grid_vocab_size, self.config.grid_embedding_dimension
        )
        context_input = self.config.context_dimension + 2 * self.config.grid_embedding_dimension
        self.context_mlp = nn.Sequential(
            nn.LayerNorm(context_input),
            nn.Linear(context_input, self.config.context_hidden_dimension),
            nn.GELU(),
        )
        self.score_head = nn.Sequential(
            nn.Linear(self.config.pair_projection_dimension + self.config.context_hidden_dimension, 256),
            nn.GELU(),
            nn.Linear(256, 64),
            nn.GELU(),
            nn.Linear(64, 1),
        )

    def forward(
        self,
        features_a: torch.Tensor,
        features_b: torch.Tensor,
        global_features: torch.Tensor,
        length_condition: torch.Tensor,
        candidate_context: torch.Tensor | None = None,
        grid_source_ids: torch.Tensor | None = None,
        sequence_mask: torch.Tensor | None = None,
    ) -> torch.Tensor:
        features_a, features_b, global_features, length_condition, squeezed = _normalise_inputs(
            features_a, features_b, global_features, length_condition
        )
        batch, time, _ = features_a.shape
        if candidate_context is None:
            candidate_context = features_a.new_zeros((batch, self.config.context_dimension))
        candidate_context = _normalise_context(candidate_context, batch, self.config.context_dimension, features_a)
        if grid_source_ids is None:
            grid_source_ids = torch.zeros((batch, 2), device=features_a.device, dtype=torch.long)
        grid_source_ids = _normalise_grid_ids(grid_source_ids, batch, self.config.grid_vocab_size, features_a.device)
        valid = _normalise_sequence_mask(sequence_mask, batch, time, features_a.device)
        mask = valid.unsqueeze(-1).to(dtype=features_a.dtype)
        encoded_a = self.shared_tcn_encoder((features_a * mask).transpose(1, 2)).transpose(1, 2)
        encoded_b = self.shared_tcn_encoder((features_b * mask).transpose(1, 2)).transpose(1, 2)
        pair = torch.cat((encoded_a, encoded_b, encoded_a - encoded_b, encoded_a * encoded_b), dim=-1)
        temporal = self.pair_projection(pair)
        temporal = temporal + self.global_projection(global_features).unsqueeze(1)
        temporal = temporal + self.length_projection(length_condition).unsqueeze(1)
        attention_logits = self.attention(temporal).squeeze(-1)
        attention_logits = attention_logits.masked_fill(~valid, torch.finfo(temporal.dtype).min)
        attention_weights = torch.softmax(attention_logits, dim=1).unsqueeze(-1)
        attention_mean = torch.sum(temporal * attention_weights, dim=1)
        masked_temporal = temporal.masked_fill(~valid.unsqueeze(-1), torch.finfo(temporal.dtype).min)
        masked_max = masked_temporal.max(dim=1).values
        candidate_representation = self.pool_projection(torch.cat((attention_mean, masked_max), dim=-1))
        grid = self.grid_source_embedding(grid_source_ids).reshape(batch, -1)
        context = self.context_mlp(torch.cat((candidate_context, grid), dim=-1))
        scores = self.score_head(torch.cat((candidate_representation, context), dim=-1)).squeeze(-1)
        if not torch.isfinite(scores).all():
            raise FloatingPointError("Cue-Ranker produced a non-finite score")
        return scores.squeeze(0) if squeezed else scores

    @property
    def parameter_count(self):
        return sum(parameter.numel() for parameter in self.parameters())


# Short aliases keep the additive public API convenient without creating a
# second model class or a second state-dict schema.
CueRankerModel = CueRankerTemporalModel
LearnedCueRankerV1 = CueRankerTemporalModel
CueRankerModelConfig = CueRankerTemporalConfig


def _normalise_inputs(features_a, features_b, global_features, length_condition):
    tensors = [torch.as_tensor(value) for value in (features_a, features_b, global_features, length_condition)]
    features_a, features_b, global_features, length_condition = tensors
    squeezed = features_a.ndim == 2
    if squeezed:
        features_a, features_b, global_features, length_condition = (
            features_a.unsqueeze(0), features_b.unsqueeze(0), global_features.unsqueeze(0), length_condition.reshape(1, 1)
        )
    if features_a.ndim != 3 or features_a.shape[-1] != FEATURE_DIMENSION:
        raise ValueError(f"features_a must have shape (B, T, {FEATURE_DIMENSION})")
    if features_b.shape != features_a.shape:
        raise ValueError("features_b must have the same shape as features_a")
    if global_features.shape != (features_a.shape[0], GLOBAL_FEATURE_DIMENSION):
        raise ValueError(f"global_features must have shape (B, {GLOBAL_FEATURE_DIMENSION})")
    if length_condition.shape != (features_a.shape[0], 1):
        raise ValueError("length_condition must have shape (B, 1)")
    for name, value in (("features_a", features_a), ("features_b", features_b), ("global_features", global_features), ("length_condition", length_condition)):
        if not value.is_floating_point():
            raise TypeError(f"{name} must use a floating-point dtype")
        if not torch.isfinite(value).all():
            raise ValueError(f"{name} must contain finite values")
    dtype = torch.float32
    features_a, features_b, global_features, length_condition = (value.to(dtype=dtype) for value in (features_a, features_b, global_features, length_condition))
    return features_a, features_b, global_features, length_condition, squeezed


def _normalise_context(value, batch, dimension, reference):
    value = torch.as_tensor(value, device=reference.device)
    if value.ndim == 1:
        value = value.unsqueeze(0)
    if value.shape != (batch, dimension):
        raise ValueError(f"candidate_context must have shape (B, {dimension})")
    value = value.to(device=reference.device, dtype=reference.dtype)
    if not torch.isfinite(value).all():
        raise ValueError("candidate_context must contain finite values")
    return value


def _normalise_grid_ids(value, batch, vocab_size, device):
    value = torch.as_tensor(value, device=device)
    if value.ndim == 1:
        value = value.unsqueeze(0)
    if value.shape != (batch, 2):
        raise ValueError("grid_source_ids must have shape (B, 2)")
    if value.dtype.is_floating_point:
        if not torch.isfinite(value).all() or not torch.equal(value, value.round()):
            raise ValueError("grid_source_ids must contain integer values")
    value = value.to(dtype=torch.long)
    if torch.any(value < 0) or torch.any(value >= vocab_size):
        raise ValueError("grid_source_ids contain an out-of-range category")
    return value


def _normalise_sequence_mask(value, batch, time, device):
    if value is None:
        return torch.ones((batch, time), dtype=torch.bool, device=device)
    value = torch.as_tensor(value, device=device)
    if value.shape != (batch, time):
        raise ValueError("sequence_mask must have shape (B, T)")
    value = value.to(dtype=torch.bool)
    if not value.any(dim=1).all():
        raise ValueError("sequence_mask must retain at least one timestep per candidate")
    return value
