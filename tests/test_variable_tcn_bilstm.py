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
    load_variable_checkpoint_for_initialization,
    collate_variable_feature_examples,
    load_variable_checkpoint_for_resume,
    train_variable_temporal_control_model,
    variable_checkpoint_payload,
    variable_vocal_self_supervised_batch_loss,
    write_variable_run_manifest,
)
from src.ml.variable_runner import _validated_cache_exclusions


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


def test_variable_cache_exclusions_must_match_report_and_only_validation(monkeypatch, tmp_path):
    import hashlib
    import json
    from types import SimpleNamespace

    import src.ml.variable_data as variable_data

    lengths = (2, 4, 6, 8)
    all_examples = {
        (split, length): {
            "example_id": f"{split}-{length}",
            "split": split,
            "transition_length_bars": length,
        }
        for split in ("train", "validation")
        for length in lengths
    }

    def fake_dataset(_directory, length, split):
        return SimpleNamespace(examples=(all_examples[(split, length)],))

    monkeypatch.setattr(variable_data, "VariableFeatureDataset", fake_dataset)
    indexed = {
        example["example_id"]: {
            "split": example["split"],
            "transition_length_bars": example["transition_length_bars"],
        }
        for (split, length), example in all_examples.items()
        if (split, length) != ("validation", 8)
    }
    index_sha = "a" * 64
    report = {
        "dataset_manifest_sha256": "b" * 64,
        "splits": ["train", "validation"],
        "lengths": list(lengths),
        "cache_index": {"file_sha256": index_sha, "entry_count": len(indexed)},
        "counts": {},
        "rejections": [{
            "split": "validation",
            "length": 8,
            "example_id": "validation-8",
            "reason": "feature_grid_provenance_mismatch",
        }],
    }
    for split in ("train", "validation"):
        report["counts"][split] = {}
        for length in lengths:
            rejected = split == "validation" and length == 8
            report["counts"][split][str(length)] = {
                "requested": 1,
                "cache_hits": 0 if rejected else 1,
                "cache_misses": 0,
                "rejected": 1 if rejected else 0,
            }
    report_path = tmp_path / "materialization_report.json"
    report_path.write_text(json.dumps(report), encoding="utf-8")

    result = _validated_cache_exclusions(
        tmp_path,
        tmp_path,
        "b" * 64,
        {"entries": indexed, "file_sha256": index_sha},
        lengths,
    )
    assert [row["example_id"] for row in result["rejections"]] == ["validation-8"]
    assert result["report_sha256"] == hashlib.sha256(report_path.read_bytes()).hexdigest()

    report["rejections"][0]["split"] = "train"
    report_path.write_text(json.dumps(report), encoding="utf-8")
    with pytest.raises(ValueError, match="Validation cache rejections"):
        _validated_cache_exclusions(
            tmp_path,
            tmp_path,
            "b" * 64,
            {"entries": indexed, "file_sha256": index_sha},
            lengths,
        )


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
    initialized, provenance = load_variable_checkpoint_for_initialization(
        output / "manifest.json",
        output / manifest["files"]["best_checkpoint"]["path"],
    )
    assert initialized["epoch"] == 1
    assert provenance["optimizer_state_loaded"] is False
    fine_tune_output = tmp_path / "temporal-fine-tune"
    train_variable_temporal_control_model(
        (_batch(2, 1), _batch(4, 1)),
        (_batch(2, 1), _batch(4, 1)),
        fine_tune_output,
        config=VariableTemporalTrainingConfig(max_epochs=1, training_sample_rate=8_000, lowpass_kernel_size=31, device="cpu"),
        dataset_manifest_sha256=digest,
        supported_lengths=(2, 4),
        initialize_from_manifest=output / "manifest.json",
        initialize_from_checkpoint=output / manifest["files"]["best_checkpoint"]["path"],
        progress=lambda message: None,
    )
    fine_tune_manifest = __import__("json").loads((fine_tune_output / "manifest.json").read_text(encoding="utf-8"))
    assert fine_tune_manifest["contract"]["initialization"]["mode"] == "model_weights_only_optimizer_reset_v1"
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


def test_all_lengths_smoke_resumes_and_preserves_cache_bindings(tmp_path):
    digest = hashlib.sha256(b"all-length-smoke-dataset").hexdigest()
    index_sha = hashlib.sha256(b"all-length-smoke-index").hexdigest()
    root_sha = hashlib.sha256(b"all-length-smoke-root").hexdigest()
    batches = tuple(_batch(length, 1) for length in (2, 4, 6, 8))
    output = tmp_path / "all-length-smoke"
    common = {
        "dataset_manifest_sha256": digest,
        "supported_lengths": (2, 4, 6, 8),
        "waveform_cache_index_sha256": index_sha,
        "waveform_cache_root_manifest_sha256": root_sha,
        "progress": lambda _message: None,
    }
    train_variable_temporal_control_model(
        batches,
        batches,
        output,
        config=VariableTemporalTrainingConfig(max_epochs=1, training_sample_rate=8_000, lowpass_kernel_size=31, device="cpu"),
        **common,
    )
    resumed = train_variable_temporal_control_model(
        batches,
        batches,
        output,
        config=VariableTemporalTrainingConfig(max_epochs=2, training_sample_rate=8_000, lowpass_kernel_size=31, device="cpu"),
        resume=True,
        **common,
    )
    assert [row["epoch"] for row in resumed["history"]] == [0, 1, 2]
    assert resumed["history"][0]["phase"] == "equal_power_initialization"
    manifest = __import__("json").loads((output / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["contract"]["supported_lengths"] == [2, 4, 6, 8]
    assert manifest["contract"]["waveform_cache_index_sha256"] == index_sha
    assert manifest["contract"]["waveform_cache_root_manifest_sha256"] == root_sha


def test_variable_e0_measured_before_first_update_and_resumable(tmp_path):
    import json

    output = tmp_path / "interrupted"
    train, validation = (_batch(2, 1),), (_batch(2, 1),)
    config = VariableTemporalTrainingConfig(max_epochs=1, training_sample_rate=8000, lowpass_kernel_size=31, device="cpu")
    settings = dict(config=config, supported_lengths=(2,), dataset_manifest_sha256="a" * 64)

    def interrupt(message):
        if message.startswith("epoch=0 "):
            raise InterruptedError("stop after E0")

    with pytest.raises(InterruptedError, match="stop after E0"):
        train_variable_temporal_control_model(train, validation, output, progress=interrupt, **settings)
    meta = json.loads((output / "manifest.json").read_text())
    assert meta["last_epoch"] == 0 and meta["files"]["best_checkpoint"] is None
    state = torch.load(output / meta["files"]["latest_checkpoint"]["path"], weights_only=True)
    assert state["epoch"] == 0 and state["optimizer_state_dict"]["state"] == {}
    model = VariableTCNBiLSTMTransitionControl().eval()
    model.load_state_dict(state["model_state_dict"])
    zero = state["history"][0]
    for split, batches in (("train", train), ("validation", validation)):
        with torch.no_grad():
            expected = variable_vocal_self_supervised_batch_loss(
                model, batches[0], renderer=DifferentiableVocalAwareRenderer(sample_rate=8000, lowpass_kernel_size=31),
                objective=VariableVocalAwareTransitionObjective(),
            ).terms
        assert zero[split]["by_length"]["2"] == {k: float(v) for k, v in expected.items()}
    resumed = train_variable_temporal_control_model(train, validation, output, resume=True, **settings)
    assert [row["epoch"] for row in resumed["history"]] == [0, 1]
    assert resumed["history"][0] == zero and resumed["best_epoch"] == 1
