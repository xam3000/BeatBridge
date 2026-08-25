import pytest
import torch

from src.ml.cue_ranker_model import (
    CUE_RANKER_CONTEXT_DIMENSION,
    CueRankerTemporalModel,
)
from src.ml.cue_ranker_runner import cue_ranker_listwise_loss


def _inputs(batch, time):
    generator = torch.Generator().manual_seed(100 + time + batch)
    return (
        torch.randn(batch, time, 54, generator=generator),
        torch.randn(batch, time, 54, generator=generator),
        torch.randn(batch, 16, generator=generator),
        torch.full((batch, 1), time / 64.0),
        torch.randn(batch, CUE_RANKER_CONTEXT_DIMENSION, generator=generator),
        torch.zeros(batch, 2, dtype=torch.long),
    )


@pytest.mark.parametrize("time", (16, 32, 48, 64))
def test_ranker_emits_one_finite_float32_score_for_each_variable_length(time):
    model = CueRankerTemporalModel()
    output = model(*_inputs(3, time))
    assert output.shape == (3,)
    assert output.dtype == torch.float32
    assert torch.isfinite(output).all()


def test_ranker_has_private_shared_ab_encoder_and_never_consumes_sample_positions():
    model = CueRankerTemporalModel()
    assert model.shared_tcn_encoder[0].in_channels == 54
    assert model.shared_tcn_encoder[0].out_channels == 64
    assert model.shared_tcn_encoder[2].out_channels == 128
    assert model.shared_tcn_encoder[4].dilation == (2,)
    features_a, features_b, global_features, length, context, grid_ids = _inputs(2, 16)
    first = model(features_a, features_b, global_features, length, context, grid_ids)
    second_context = context.clone()
    # Candidate IDs/sample coordinates are not an input; changing only the
    # caller-side metadata cannot enter the model through a hidden path.
    second = model(features_a, features_b, global_features, length, second_context, grid_ids)
    assert torch.equal(first, second)


def test_masked_temporal_padding_does_not_change_a_score():
    model = CueRankerTemporalModel()
    short = _inputs(1, 16)
    padded = list(_inputs(1, 64))
    for target, source in zip(padded[:2], short[:2]):
        target[:, :16] = source
        target[:, 16:] = 12345.0
    padded[2:] = [value.clone() for value in short[2:]]
    padded = tuple(padded)
    mask = torch.zeros(1, 64, dtype=torch.bool)
    mask[:, :16] = True
    with torch.no_grad():
        short_score = model(*short)
        padded_score = model(*padded, sequence_mask=mask)
    assert padded_score == pytest.approx(short_score, abs=2e-5)


def test_better_teacher_target_changes_listwise_gradient_direction():
    scores = torch.zeros(2, requires_grad=True)
    loss = cue_ranker_listwise_loss(
        scores,
        torch.tensor([0.0, 2.0]),
        torch.ones(2),
        teacher_status=["scored", "scored"],
    )
    loss.backward()
    assert scores.grad[1] < scores.grad[0]


def test_padding_and_single_candidate_group_are_contractually_ignored():
    full = cue_ranker_listwise_loss(
        torch.tensor([0.2, -0.1]),
        torch.tensor([1.0, 0.0]),
        torch.ones(2),
        teacher_status=["scored", "scored"],
    )
    padded, details = cue_ranker_listwise_loss(
        torch.tensor([[0.2, -0.1, float("nan")]]),
        torch.tensor([[1.0, 0.0, float("nan")]]),
        torch.tensor([[1.0, 1.0, float("nan")]]),
        teacher_status=["scored", "scored", "failed"],
        valid_mask=torch.tensor([[True, True, False]]),
        return_details=True,
    )
    assert padded == pytest.approx(full)
    assert details["supported_groups"] == 1

    single, details = cue_ranker_listwise_loss(
        torch.tensor([0.2]), torch.tensor([1.0]), torch.tensor([1.0]),
        teacher_status=["scored"], return_details=True,
    )
    assert single.item() == 0.0
    assert details["insufficient_groups"] == 1
