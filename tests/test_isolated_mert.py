from types import SimpleNamespace

import numpy as np
import pytest
import torch

from src.evaluation.mert_window_check import isolated_mean
from src.features.p07_mert import FRAME_STEP, HIDDEN_SIZE, LAYER_COUNT, RECEPTIVE_FIELD, FrozenMert


def test_batched_mert_sees_only_its_window_and_averages_bars_equally():
    encoder = object.__new__(FrozenMert)
    encoder.device = torch.device("cpu")
    encoder.torch = torch
    encoder.processor = lambda clips, **kw: SimpleNamespace(input_values=torch.from_numpy(np.atleast_2d(clips)))

    def full_attention(clips, **kwargs):
        frames = clips.unfold(1, RECEPTIVE_FIELD, FRAME_STEP).mean(-1)
        # Every frame observes the full input of its own example.
        layer = (frames + clips.mean(1, keepdim=True)).unsqueeze(-1).expand(-1, -1, HIDDEN_SIZE)
        return SimpleNamespace(hidden_states=[layer] * LAYER_COUNT)

    encoder.model = full_attention
    edges = np.array([0, 800, 2400, 3200, 4800, 5600, 7200, 8000, 9600, 11200])
    bars = np.asarray([np.linspace(a, b, 9, dtype=int) for a, b in zip(edges[:-1], edges[1:])])
    audio = np.random.default_rng(17).normal(size=edges[-1]).astype(np.float32)
    starts = [4, 0, 5]
    expected = [isolated_mean(encoder, audio, bars[s:s+4]) for s in starts]
    np.testing.assert_allclose(encoder.isolated_means(audio, bars, starts), expected, atol=1e-6)
    audio[4800:] = 100.
    np.testing.assert_allclose(encoder.isolated_means(audio, bars, starts)[1], expected[1], atol=1e-6)
    with pytest.raises(ValueError, match="contiguous"):
        encoder.isolated_means(audio, bars[[0, 1, 3, 4]], [0])
    assert encoder.isolated_means(audio, bars, []).shape == (0, LAYER_COUNT, HIDDEN_SIZE)
    with pytest.raises(ValueError, match="start index"):
        encoder.isolated_means(audio, bars, [-1])
