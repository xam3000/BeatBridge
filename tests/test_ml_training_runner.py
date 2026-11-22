import json

import pytest
import torch

from src.features import FEATURE_DIMENSION, GLOBAL_FEATURE_DIMENSION, SEQUENCE_LENGTH
from src.ml import TrainingConfig, train_feature_control_model


def _examples(count, seed):
    generator = torch.Generator().manual_seed(seed)
    result = []
    for index in range(count):
        features_a = torch.rand(
            (SEQUENCE_LENGTH, FEATURE_DIMENSION),
            generator=generator,
        )
        features_b = torch.rand(
            (SEQUENCE_LENGTH, FEATURE_DIMENSION),
            generator=generator,
        )
        features_a[:, -3:] = 0.0
        features_b[:, -3:] = 0.0
        result.append({
            "example_id": f"example-{seed}-{index}",
            "features_a": features_a,
            "features_b": features_b,
            "global_features": torch.zeros(GLOBAL_FEATURE_DIMENSION),
            "source_audio": 0.05 * torch.randn((2, 800), generator=generator),
            "target_audio": 0.05 * torch.randn((2, 800), generator=generator),
            "waveform_cache_hit": True,
        })
    return result


def _config(max_epochs):
    return TrainingConfig(
        seed=17,
        max_epochs=max_epochs,
        batch_size=2,
        learning_rate=1e-3,
        patience=10,
        min_delta=0.0,
        training_sample_rate=8_000,
        lowpass_kernel_size=31,
        device="cpu",
    )


def test_september_tcn_cli_keeps_constant_rate_through_the_optimizer(tmp_path, monkeypatch):
    from src.ml import __main__ as cli, runner

    (tmp_path / "manifest.json").write_text('{"dataset_id":"synthetic"}', encoding="utf-8")
    monkeypatch.setattr(runner, "FeatureControlDataset", lambda path, split, **kw: _examples(1, len(split)))
    output = tmp_path / "tcn"
    monkeypatch.setattr("sys.argv", [
        "src.ml", "train-tcn-bilstm", str(tmp_path), str(output),
        "--constant-learning-rate", "--control-initialization", "equal_power_v1",
        "--max-epochs", "1", "--device", "cpu", "--wandb-mode", "disabled",
    ])
    assert cli.main() == 0
    checkpoint = torch.load(output / "checkpoints/latest.pt", weights_only=True)
    assert checkpoint["lr_scheduler_state_dict"] is None
    assert checkpoint["optimizer_state_dict"]["param_groups"][0]["lr"] == 0.001
    assert checkpoint["history"][0]["phase"] == "equal_power_initialization"
    assert "_equal_power_v1" in checkpoint["model_state_dict"]


def test_training_runner_writes_baseline_history_and_restartable_checkpoints(
    tmp_path,
    monkeypatch,
):
    output = tmp_path / "run"
    first = train_feature_control_model(
        _examples(3, 1),
        _examples(2, 2),
        output,
        config=_config(1),
        progress=lambda message: None,
    )

    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    history = json.loads((output / "history.json").read_text(encoding="utf-8"))
    assert first.status == "completed"
    assert first.last_epoch == 1
    assert manifest["status"] == "completed"
    assert manifest["last_epoch"] == 1
    assert manifest["contract"]["objective"]["version"] == 4
    assert history["epochs"][0]["phase"] == "equal_power_initialization"
    assert len(history["epochs"]) == 2
    assert torch.isfinite(torch.tensor(history["epochs"][1]["validation"]["loss"]))
    assert (output / "checkpoints" / "latest.pt").is_file()
    assert (output / "checkpoints" / "best.pt").is_file()

    real_torch_load = torch.load

    def require_weights_only(*args, **kwargs):
        assert kwargs.get("weights_only") is True
        return real_torch_load(*args, **kwargs)

    monkeypatch.setattr(torch, "load", require_weights_only)
    resumed = train_feature_control_model(
        _examples(3, 1),
        _examples(2, 2),
        output,
        config=_config(2),
        resume=True,
        progress=lambda message: None,
    )
    resumed_history = json.loads((output / "history.json").read_text(encoding="utf-8"))
    assert resumed.status == "completed"
    assert resumed.last_epoch == 2
    assert [entry["epoch"] for entry in resumed_history["epochs"]] == [0, 1, 2]


def test_training_runner_rejects_modified_latest_checkpoint(tmp_path):
    output = tmp_path / "run"
    train_feature_control_model(
        _examples(2, 7),
        _examples(1, 8),
        output,
        config=_config(1),
        progress=lambda message: None,
    )
    latest_path = output / "checkpoints" / "latest.pt"
    latest_path.write_bytes(latest_path.read_bytes() + b"tampered")

    with pytest.raises(ValueError, match="Latest checkpoint SHA-256"):
        train_feature_control_model(
            _examples(2, 7),
            _examples(1, 8),
            output,
            config=_config(2),
            resume=True,
            progress=lambda message: None,
        )


def test_training_runner_refuses_to_overwrite_existing_run(tmp_path):
    output = tmp_path / "run"
    output.mkdir()
    try:
        train_feature_control_model(
            _examples(1, 3),
            _examples(1, 4),
            output,
            config=_config(1),
            progress=lambda message: None,
        )
    except FileExistsError:
        pass
    else:
        raise AssertionError("Existing training output must not be overwritten")


@pytest.mark.skipif(not torch.cuda.is_available(), reason="CUDA is unavailable")
def test_training_runner_uses_cuda_for_auto_device(tmp_path):
    config = TrainingConfig(
        seed=19,
        max_epochs=1,
        batch_size=1,
        learning_rate=1e-3,
        patience=2,
        min_delta=0.0,
        training_sample_rate=8_000,
        lowpass_kernel_size=31,
        device="auto",
    )
    output = tmp_path / "cuda-run"
    result = train_feature_control_model(
        _examples(1, 5),
        _examples(1, 6),
        output,
        config=config,
        progress=lambda message: None,
    )

    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    assert result.status == "completed"
    assert manifest["contract"]["training"]["device"] == "cuda:0"
