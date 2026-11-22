import json
import math

import pytest
import torch

from src.features import (
    FEATURE_DIMENSION,
    GLOBAL_FEATURE_DIMENSION,
    SEQUENCE_LENGTH,
    feature_index,
)
from src.ml import VocalTrainingConfig, train_vocal_feature_control_model


def _examples(count, seed):
    generator = torch.Generator().manual_seed(seed)
    examples = []
    for index in range(count):
        features_a = torch.zeros((SEQUENCE_LENGTH, FEATURE_DIMENSION))
        features_b = torch.zeros_like(features_a)
        for features in (features_a, features_b):
            features[:, feature_index("audio_valid")] = 1.0
            features[:, feature_index("vocal_valid")] = 1.0
            features[:, feature_index("vocal_activity")] = 0.8
            features[:, feature_index("vocal_prominence")] = 0.7
            features[:, feature_index("vocal_confidence")] = 1.0
        time = torch.arange(800, dtype=torch.float32) / 8_000.0
        source_vocal = 0.05 * torch.sin(2.0 * math.pi * 330.0 * time).repeat(2, 1)
        target_vocal = 0.05 * torch.sin(2.0 * math.pi * 440.0 * time).repeat(2, 1)
        source = source_vocal + 0.02 * torch.randn((2, 800), generator=generator)
        target = target_vocal + 0.02 * torch.randn((2, 800), generator=generator)
        examples.append({
            "example_id": f"example-{seed}-{index}",
            "features_a": features_a,
            "features_b": features_b,
            "global_features": torch.zeros(GLOBAL_FEATURE_DIMENSION),
            "source_audio": source,
            "target_audio": target,
            "source_vocal_audio": source_vocal,
            "target_vocal_audio": target_vocal,
            "waveform_cache_hit": True,
        })
    return examples


def _config(max_epochs):
    return VocalTrainingConfig(
        seed=23,
        max_epochs=max_epochs,
        batch_size=2,
        learning_rate=1e-3,
        patience=10,
        min_delta=0.0,
        training_sample_rate=8_000,
        lowpass_kernel_size=31,
        device="cpu",
    )


def test_vocal_runner_persists_v2_contract_terms_and_resume(tmp_path, monkeypatch):
    output = tmp_path / "vocal-run"
    first = train_vocal_feature_control_model(
        _examples(3, 1),
        _examples(2, 2),
        output,
        config=_config(1),
        progress=lambda message: None,
    )

    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    history = json.loads((output / "history.json").read_text(encoding="utf-8"))
    contract = manifest["contract"]
    assert first.status == "completed"
    assert first.last_epoch == 1
    assert manifest["format_version"] == 3
    assert manifest["runner_name"] == "self_supervised_vocal_train_validation_v2"
    assert contract["model"]["format_version"] == 2
    assert contract["model"]["name"] == "vocal_time_shared_mlp_v2"
    assert contract["renderer"]["control_protocol_version"] == 4
    assert contract["objective"]["version"] == 5
    assert contract["waveform_cache"]["format_version"] == 2
    assert history["epochs"][0]["phase"] == "equal_power_initialization"
    assert "vocal_audibility" in history["epochs"][1]["validation"]
    assert "vocal_stem_overlap" in history["epochs"][1]["validation"]
    assert (output / "checkpoints" / "latest.pt").is_file()
    assert (output / "checkpoints" / "best.pt").is_file()

    real_torch_load = torch.load

    def require_weights_only(*args, **kwargs):
        assert kwargs.get("weights_only") is True
        return real_torch_load(*args, **kwargs)

    monkeypatch.setattr(torch, "load", require_weights_only)
    resumed = train_vocal_feature_control_model(
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


def test_vocal_runner_requires_stem_waveforms(tmp_path):
    train = _examples(1, 3)
    del train[0]["source_vocal_audio"]

    with pytest.raises(ValueError, match="source_vocal_audio"):
        train_vocal_feature_control_model(
            train,
            _examples(1, 4),
            tmp_path / "run",
            config=_config(1),
            progress=lambda message: None,
        )


def test_vocal_runner_rejects_modified_latest_checkpoint(tmp_path):
    output = tmp_path / "vocal-run"
    train_vocal_feature_control_model(
        _examples(2, 7),
        _examples(1, 8),
        output,
        config=_config(1),
        progress=lambda message: None,
    )
    latest_path = output / "checkpoints" / "latest.pt"
    latest_path.write_bytes(latest_path.read_bytes() + b"tampered")

    with pytest.raises(ValueError, match="Latest vocal checkpoint hash"):
        train_vocal_feature_control_model(
            _examples(2, 7),
            _examples(1, 8),
            output,
            config=_config(2),
            resume=True,
            progress=lambda message: None,
        )


def test_vocal_runner_refuses_to_overwrite_existing_run(tmp_path):
    output = tmp_path / "run"
    output.mkdir()

    with pytest.raises(FileExistsError):
        train_vocal_feature_control_model(
            _examples(1, 5),
            _examples(1, 6),
            output,
            config=_config(1),
            progress=lambda message: None,
        )
