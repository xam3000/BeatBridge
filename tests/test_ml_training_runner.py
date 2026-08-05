import json

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
    )


def test_training_runner_writes_baseline_history_and_restartable_checkpoints(tmp_path):
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
