import pytest
import torch

from src.evaluation.check_control_initialization import probe
from src.evaluation.comparison import Comparison, Evaluator
from src.ml import (FeatureControlMLP, TCNBiLSTMTransitionControl, VariableTCNBiLSTMTransitionControl,
                    VariableTimeSharedMLP, VocalFeatureControlMLP)
from src.ml.control_initialization import EQUAL_POWER, LEGACY, neutral_at_zero, read_model_config


@pytest.fixture(scope="module", autouse=True)
def threads():
    previous = torch.get_num_threads()
    torch.set_num_threads(2)
    yield
    torch.set_num_threads(previous)


@pytest.mark.parametrize(("profile", "kind", "bars"), [
    ("R1", FeatureControlMLP, 4), ("R2", VocalFeatureControlMLP, 4), ("R3", TCNBiLSTMTransitionControl, 4),
    *(( "R4", kind, bars) for kind in (VariableTimeSharedMLP, VariableTCNBiLSTMTransitionControl)
      for bars in (2, 4, 6, 8)),
])
def test_fresh_audio_gradients_and_head_updates(profile, kind, bars):
    torch.manual_seed(197)
    cfg = Comparison(profile, bars=bars)
    source, target = torch.randn(2, 2, 4099) * .22
    item = dict(source_audio=source, target_audio=target, source_vocal_audio=source*.45, target_vocal_audio=target*.65,
                features_a=torch.rand(cfg.points, 54), features_b=torch.rand(cfg.points, 54),
                global_features=torch.randn(16), sample_rate=cfg.sample_rate, transition_length_bars=bars,
                sequence_length=cfg.points, length_condition=torch.tensor([bars/8]), example_id="synthetic", split="train")
    evaluator = Evaluator(cfg)
    model = kind()
    report = probe(evaluator, model, item)
    assert report["control_initialization"] == EQUAL_POWER
    # Check each bounded auxiliary head leaves its neutral boundary through audio loss.
    updated = evaluator.learned(model, item)
    if cfg.vocal:
        for name in ("vocal_duck_a", "vocal_duck_b"):
            assert torch.any(updated[name] > 0)
            assert updated[name][0] == updated[name][-1] == 0
    if profile == "R3":
        for name in ("eq_low_A", "eq_low_B", "eq_mid_A", "eq_mid_B", "eq_high_A", "eq_high_B"):
            assert torch.any(updated[name] < 1)
        assert torch.any(updated["vocal_ducking"] > 0)
    for value in updated.values():
        assert torch.isfinite(value).all()
        assert torch.all((value >= -1e-6) & (value <= 1 + 1e-6))


def test_neutral_boundary_has_inward_derivative_and_can_recover_from_either_side():
    logits = torch.tensor([-0.1, 0., 0.1], requires_grad=True)
    attenuation = neutral_at_zero(logits)
    attenuation.sum().backward()
    assert attenuation[1] == 0
    assert logits.grad[0] < 0 and logits.grad[1] == 1 and logits.grad[2] > 0
    torch.testing.assert_close(attenuation[0], attenuation[2])


@pytest.mark.parametrize("kind", [FeatureControlMLP, VocalFeatureControlMLP, TCNBiLSTMTransitionControl,
                                  VariableTimeSharedMLP, VariableTCNBiLSTMTransitionControl])
def test_model_config_distinguishes_missing_legacy_and_explicit_new_contract(kind):
    cfg = kind().config
    raw = cfg.to_dict()
    assert raw["control_initialization"] == EQUAL_POWER
    assert read_model_config(type(cfg), raw) == cfg
    del raw["control_initialization"]
    old = read_model_config(type(cfg), raw)
    assert old.control_initialization == LEGACY and old.to_dict() == raw
    original = kind(old)
    fresh = kind(cfg)
    with pytest.raises(RuntimeError, match="_equal_power_v1"):
        fresh.load_state_dict(original.state_dict())
    with pytest.raises(RuntimeError, match="_equal_power_v1"):
        original.load_state_dict(fresh.state_dict())
    with pytest.raises(ValueError, match="control_initialization"):
        read_model_config(type(cfg), dict(raw, control_initialization="unrecognized"))
