import hashlib

import pytest
import torch

from src.control import DifferentiableVocalAwareRenderer, VariableVocalAwareTransitionObjective
from src.features import FEATURE_DIMENSION, GLOBAL_FEATURE_DIMENSION, feature_index
from src.features.variable_contract import geometry_for_length
from src.ml import (
    VariableTCNBiLSTMTransitionControl,
    VariableTemporalTrainingConfig,
    build_variable_training_contract,
    collate_variable_feature_examples,
    load_variable_checkpoint_for_resume,
    train_variable_temporal_control_model,
    variable_checkpoint_payload,
    variable_vocal_self_supervised_batch_loss,
    write_variable_run_manifest,
)


def _features(length):
    geometry = geometry_for_length(length)
    features = torch.zeros((geometry.sequence_length, FEATURE_DIMENSION))
    for name in ("audio_valid", "vocal_valid", "vocal_activity", "vocal_prominence", "vocal_confidence"):
        features[:, feature_index(name)] = 1.0
    return features


def _batch(length, count=2):
    geometry = geometry_for_length(length)
    examples = []
    for index in range(count):
        samples = 192 + 16 * index
        examples.append({
            "example_id": f"{length}-{index}",
            "transition_length_bars": length,
            "sequence_length": geometry.sequence_length,
            "features_a": _features(length),
            "features_b": _features(length),
            "global_features": torch.zeros(GLOBAL_FEATURE_DIMENSION),
            "length_condition": torch.tensor([length / 8.0]),
            "source_audio": 0.02 * torch.randn((2, samples)),
            "target_audio": 0.02 * torch.randn((2, samples)),
            "source_vocal_audio": 0.01 * torch.randn((2, samples)),
            "target_vocal_audio": 0.01 * torch.randn((2, samples)),
        })
    return collate_variable_feature_examples(examples)


@pytest.mark.parametrize("length,steps", ((2, 16), (4, 32), (6, 48), (8, 64)))
def test_variable_tcn_bilstm_shapes_endpoints_and_single_inputs(length, steps):
    batch = _batch(length)
    model = VariableTCNBiLSTMTransitionControl()
    output = model(
        batch["features_a"], batch["features_b"], batch["global_features"],
        transition_length_bars=length, length_condition=batch["length_condition"],
    )
    assert output.controls.shape == (2, steps, 10)
    assert output.position_increment_logits.shape == (2, 3, steps - 1)
    for curve in (output.mix_position, output.low_end_position, output.vocal_position):
        assert torch.equal(curve[:, 0], torch.zeros(2))
        assert torch.equal(curve[:, -1], torch.ones(2))
        assert torch.all(torch.diff(curve, dim=-1) > 0)
    assert torch.equal(output.vocal_duck_a[:, 0], torch.zeros(2))
    assert torch.equal(output.vocal_duck_b[:, -1], torch.zeros(2))
    single = model(
        batch["features_a"][0], batch["features_b"][0], batch["global_features"][0],
        transition_length_bars=length, length_condition=batch["length_condition"][0],
    )
    assert single.controls.shape == (steps, 10)


def test_variable_tcn_bilstm_padded_carrier_is_invariant_and_backpropagates():
    torch.manual_seed(31)
    batch = _batch(2)
    model = VariableTCNBiLSTMTransitionControl().eval()
    direct = model(
        batch["features_a"], batch["features_b"], batch["global_features"],
        transition_length_bars=2, length_condition=batch["length_condition"],
    )
    padded_a = torch.cat((batch["features_a"], torch.randn((2, 24, FEATURE_DIMENSION))), dim=1)
    padded_b = torch.cat((batch["features_b"], torch.randn((2, 24, FEATURE_DIMENSION))), dim=1)
    padded = model(
        padded_a, padded_b, batch["global_features"],
        transition_length_bars=2, length_condition=batch["length_condition"],
        sequence_lengths=torch.tensor([16, 16]),
    )
    torch.testing.assert_close(padded.mix_position, direct.mix_position, atol=1e-6, rtol=1e-6)
    model.train()
    output = model(
        batch["features_a"], batch["features_b"], batch["global_features"],
        transition_length_bars=2, length_condition=batch["length_condition"],
    )
    output.controls.square().mean().backward()
    assert any(parameter.grad is not None for parameter in model.parameters())


def test_variable_tcn_bilstm_supports_vocal_renderer_and_objective_v5():
    batch = _batch(4)
    model = VariableTCNBiLSTMTransitionControl()
    result = variable_vocal_self_supervised_batch_loss(
        model,
        batch,
        renderer=DifferentiableVocalAwareRenderer(sample_rate=8_000, lowpass_kernel_size=31),
        objective=VariableVocalAwareTransitionObjective(),
    )
    result.terms["loss"].backward()
    assert torch.isfinite(result.terms["loss"])
    assert result.controls.vocal_position.shape[-1] == 32


def test_temporal_runner_records_length_metrics_and_rejects_resume_length_mismatch(tmp_path):
    digest = hashlib.sha256(b"variable-temporal-synthetic").hexdigest()
    output = tmp_path / "temporal-run"
    result = train_variable_temporal_control_model(
        (_batch(2, 1), _batch(4, 1)),
        (_batch(2, 1), _batch(4, 1)),
        output,
        config=VariableTemporalTrainingConfig(max_epochs=1, training_sample_rate=8_000, lowpass_kernel_size=31, device="cpu"),
        dataset_manifest_sha256=digest,
        supported_lengths=(2, 4),
        progress=lambda message: None,
    )
    assert set(result["history"][0]["train"]["by_length"]) == {"2", "4"}
    manifest = __import__("json").loads((output / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["files"]["latest_checkpoint"]["sha256"]
    wrong_contract = build_variable_training_contract(
        dataset_manifest_sha256=digest,
        supported_lengths=(2, 4, 6),
        model_name="variable_tcn_bilstm_transition_control_v1",
        model_format_version=4,
        objective_name="objective_v5_time_normalized_variable_tcn_bilstm_v1",
    )
    wrong_contract.update({
        "runner_name": manifest["contract"]["runner_name"],
        "model": manifest["contract"]["model"],
        "training": manifest["contract"]["training"],
        "renderer": manifest["contract"]["renderer"],
        "length_scheduler": {**manifest["contract"]["length_scheduler"], "length_order": [2, 4, 6]},
    })
    with pytest.raises(ValueError, match="contract differs"):
        load_variable_checkpoint_for_resume(
            output / "manifest.json", output / "checkpoints" / "latest.pt",
            expected_contract=wrong_contract,
            expected_runner_name="self_supervised_train_validation_variable_tcn_bilstm_v1",
        )
