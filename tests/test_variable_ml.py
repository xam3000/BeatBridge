import hashlib

import pytest
import torch

from src.control import DifferentiableVocalAwareRenderer, VariableVocalAwareTransitionObjective
from src.features import FEATURE_DIMENSION, GLOBAL_FEATURE_DIMENSION, feature_index
from src.features.variable_contract import geometry_for_length
from src.ml import (
    VariableTimeSharedMLP,
    VariableFeatureControlDataset,
    build_variable_training_contract,
    collate_variable_feature_examples,
    load_variable_checkpoint_for_resume,
    variable_checkpoint_payload,
    variable_vocal_self_supervised_batch_loss,
    write_variable_run_manifest,
)


def _features(sequence_length):
    value = torch.zeros((sequence_length, FEATURE_DIMENSION), dtype=torch.float32)
    for name in ("audio_valid", "vocal_valid", "vocal_activity", "vocal_prominence", "vocal_confidence"):
        value[:, feature_index(name)] = 1.0
    return value


def _batch(length, *, samples=(320, 384)):
    geometry = geometry_for_length(length)
    examples = []
    for index, sample_count in enumerate(samples):
        source = 0.03 * torch.randn((2, sample_count))
        target = 0.03 * torch.randn((2, sample_count))
        source_vocal = 0.01 * torch.randn((2, sample_count))
        target_vocal = 0.01 * torch.randn((2, sample_count))
        examples.append(
            {
                "example_id": f"synthetic-{length}-{index}",
                "transition_length_bars": length,
                "sequence_length": geometry.sequence_length,
                "features_a": _features(geometry.sequence_length),
                "features_b": _features(geometry.sequence_length),
                "global_features": torch.zeros(GLOBAL_FEATURE_DIMENSION),
                "length_condition": torch.tensor([length / 8.0]),
                "source_audio": source,
                "target_audio": target,
                "source_vocal_audio": source_vocal,
                "target_vocal_audio": target_vocal,
            }
        )
    return collate_variable_feature_examples(examples)


@pytest.mark.parametrize("length,sequence_length", [(2, 16), (4, 32), (6, 48), (8, 64)])
def test_variable_mlp_outputs_exact_dynamic_control_geometry(length, sequence_length):
    batch = _batch(length, samples=(320, 384))
    model = VariableTimeSharedMLP()
    output = model(
        batch["features_a"],
        batch["features_b"],
        batch["global_features"],
        transition_length_bars=batch["transition_length_bars"],
        length_condition=batch["length_condition"],
    )
    for curve in (output.mix_position, output.low_end_position, output.vocal_position):
        assert curve.shape == (2, sequence_length)
        assert torch.equal(curve[:, 0], torch.zeros(2))
        assert torch.equal(curve[:, -1], torch.ones(2))
        assert torch.all(torch.diff(curve, dim=-1) > 0)
    assert output.position_increment_logits.shape == (2, 3, sequence_length - 1)
    assert output.transition_length_beats == length * 4


def test_variable_loss_forward_backward_and_audio_lengths_are_unpadded():
    torch.manual_seed(22)
    batch = _batch(6, samples=(320, 384))
    model = VariableTimeSharedMLP()
    renderer = DifferentiableVocalAwareRenderer(
        sample_rate=8_000,
        lowpass_kernel_size=31,
    )
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)
    optimizer.zero_grad()
    result = variable_vocal_self_supervised_batch_loss(
        model,
        batch,
        renderer=renderer,
        objective=VariableVocalAwareTransitionObjective(),
    )
    result.terms["loss"].backward()
    optimizer.step()
    assert torch.isfinite(result.terms["loss"])
    assert result.controls.sequence_length == 48
    assert any(parameter.grad is not None for parameter in model.parameters())


def test_variable_model_rejects_wrong_length_condition_and_preserves_old_imports():
    batch = _batch(2, samples=(320, 320))
    model = VariableTimeSharedMLP()
    with pytest.raises(ValueError, match="length_condition"):
        model(
            batch["features_a"],
            batch["features_b"],
            batch["global_features"],
            transition_length_bars=2,
            length_condition=torch.full_like(batch["length_condition"], 0.75),
        )
    from src.ml.model import FeatureControlMLP, VocalFeatureControlMLP

    assert FeatureControlMLP.__name__ == "FeatureControlMLP"
    assert VocalFeatureControlMLP.__name__ == "VocalFeatureControlMLP"


def test_variable_checkpoint_contract_contains_dataset_lengths_and_conditioning(tmp_path):
    model = VariableTimeSharedMLP()
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)
    contract = build_variable_training_contract(
        dataset_manifest_sha256=hashlib.sha256(b"synthetic-dataset").hexdigest(),
    )
    checkpoint = variable_checkpoint_payload(
        run_id="synthetic-run",
        epoch=0,
        model=model,
        optimizer=optimizer,
        contract=contract,
    )
    checkpoint_path = tmp_path / "latest.pt"
    torch.save(checkpoint, checkpoint_path)
    manifest_path = tmp_path / "manifest.json"
    manifest = write_variable_run_manifest(
        manifest_path,
        run_id="synthetic-run",
        contract=contract,
        status="running",
        checkpoint_path=checkpoint_path,
    )
    assert manifest["contract"]["dataset_format_version"] == 2
    assert manifest["contract"]["supported_lengths"] == [2, 4, 6, 8]
    assert manifest["contract"]["length_conditioning"]["field"] == "length_condition"
    restored = load_variable_checkpoint_for_resume(
        manifest_path,
        checkpoint_path,
        expected_contract=contract,
    )
    assert restored["contract"] == contract
