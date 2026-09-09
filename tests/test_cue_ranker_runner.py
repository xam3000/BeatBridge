import hashlib
import inspect
import json

import pytest
import torch

from src.ml.cue_ranker_data import CueRankerGroupLoader
from src.ml.cue_ranker_runner import (
    CueRankerTrainingConfig,
    _aggregate_ranking_metrics,
    _evaluation_group,
    _score_group,
    cue_ranker_listwise_loss,
    train_cue_ranker,
)
from src.ml.cue_ranker_model import CueRankerTemporalModel


def _row(index, utility):
    generator = torch.Generator().manual_seed(index)
    return {
        "candidate_id": f"candidate-{index}",
        "features_a": torch.randn(16, 54, generator=generator),
        "features_b": torch.randn(16, 54, generator=generator),
        "global_features": torch.randn(16, generator=generator),
        "length_condition": torch.tensor([0.25]),
        "candidate_context": torch.randn(20, generator=generator),
        "grid_source_ids": torch.zeros(2, dtype=torch.long),
        "teacher_utility": utility,
        "p_inclusion": 1.0,
        "teacher_status": "scored",
    }


def _loaders():
    group = {"group_id": "group-a", "members": [_row(0, 0.0), _row(1, 2.0), _row(2, 0.5)]}
    return CueRankerGroupLoader([group]), CueRankerGroupLoader([group])


def test_training_uses_only_explicit_train_validation_loaders_and_resume_is_sha_checked(tmp_path, monkeypatch):
    assert "test_loader" not in inspect.signature(train_cue_ranker).parameters
    train_loader, validation_loader = _loaders()
    dataset_sha = hashlib.sha256(b"synthetic-dataset").hexdigest()
    output = tmp_path / "run"
    result = train_cue_ranker(
        train_loader,
        validation_loader,
        output,
        dataset_manifest_sha256=dataset_sha,
        config=CueRankerTrainingConfig(max_epochs=1, device="cpu"),
    )
    assert result.last_epoch == 1
    assert (output / "best.pt").is_file()
    assert (output / "latest.pt").is_file()
    assert (output / "manifest.sha256").is_file()
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["contract"]["test_split"]["state"] == "sealed_not_materialized"

    latest = output / "latest.pt"
    original = latest.read_bytes()
    latest.write_bytes(original + b"tamper")
    load_called = False
    original_load = torch.load

    def guarded_load(*args, **kwargs):
        nonlocal load_called
        load_called = True
        assert kwargs.get("weights_only") is True
        return original_load(*args, **kwargs)

    monkeypatch.setattr(torch, "load", guarded_load)
    with pytest.raises(ValueError, match="latest checkpoint SHA-256"):
        train_cue_ranker(
            *_loaders(),
            output,
            dataset_manifest_sha256=dataset_sha,
            config=CueRankerTrainingConfig(max_epochs=2, device="cpu"),
            resume=True,
        )
    assert not load_called


def test_resume_loads_only_weights_only_and_extends_epoch(tmp_path, monkeypatch):
    dataset_sha = hashlib.sha256(b"synthetic-dataset").hexdigest()
    output = tmp_path / "run"
    train_cue_ranker(
        *_loaders(), output, dataset_manifest_sha256=dataset_sha,
        config=CueRankerTrainingConfig(max_epochs=1, device="cpu"),
    )
    original_load = torch.load
    calls = []

    def guarded_load(*args, **kwargs):
        calls.append(kwargs.get("weights_only"))
        return original_load(*args, **kwargs)

    monkeypatch.setattr(torch, "load", guarded_load)
    resumed = train_cue_ranker(
        *_loaders(), output, dataset_manifest_sha256=dataset_sha,
        config=CueRankerTrainingConfig(max_epochs=2, device="cpu"), resume=True,
    )
    assert resumed.last_epoch == 2
    assert calls == [True]


def test_candidate_permutation_only_permutes_scores_with_the_rows():
    torch.manual_seed(9)
    model = CueRankerTemporalModel()
    group = {"group_id": "group-a", "members": [_row(0, 0.0), _row(1, 2.0), _row(2, 0.5)]}
    with torch.no_grad():
        original = _score_group(model, group, torch.device("cpu"))
        permuted = {"group_id": "group-a", "members": [group["members"][2], group["members"][0], group["members"][1]]}
        reordered = _score_group(model, permuted, torch.device("cpu"))
    assert torch.allclose(reordered, original[[2, 0, 1]])


def test_epoch_metrics_compare_frozen_teacher_and_all_required_validation_baselines():
    rows = [
        {"candidate_id": "a", "length": 2, "utility": 3.0, "ranker_score": 0.1, "feature_baseline_v3": 0.2, "bpm": -0.3, "harmony": 0.2},
        {"candidate_id": "b", "length": 2, "utility": 2.0, "ranker_score": 0.9, "feature_baseline_v3": 0.1, "bpm": -0.1, "harmony": 0.9},
        {"candidate_id": "c", "length": 4, "utility": 1.0, "ranker_score": 0.2, "feature_baseline_v3": 0.9, "bpm": -0.2, "harmony": 0.1},
    ]
    metrics = _aggregate_ranking_metrics([rows], top_k=2)["ranking"]
    assert set(metrics) == {"all", "2", "4", "6", "8"}
    assert metrics["all"]["teacher_oracle"]["top_1_agreement"] == 1.0
    assert metrics["all"]["teacher_oracle"]["ndcg"] == 1.0
    assert metrics["all"]["ranker"]["top_1_agreement"] == 0.0
    assert metrics["all"]["random_valid"]["groups"] == 1
    assert metrics["all"]["feature_baseline_v3"]["groups"] == 1
    assert metrics["all"]["bpm_only"]["groups"] == 1
    assert metrics["all"]["harmony_only"]["groups"] == 1
    assert metrics["2"]["groups"] == 1
    assert metrics["4"]["groups"] == 0


def test_guard_rejection_is_always_a_negative_anchor_even_with_finite_utility():
    scores = torch.zeros(2, requires_grad=True)
    loss = cue_ranker_listwise_loss(
        scores,
        torch.tensor([0.0, 100.0]),
        torch.ones(2),
        guard_margin=0.05,
        teacher_status=["scored", "guard_rejected"],
    )
    loss.backward()

    # A below-threshold render guard must not become the preferred target just
    # because the differentiable objective happened to be high.
    assert scores.grad[1] > scores.grad[0]

    rows = _evaluation_group(
        {
            "members": [
                _row(0, 0.0),
                {**_row(1, 100.0), "teacher_status": "guard_rejected"},
            ]
        },
        torch.zeros(2),
        CueRankerTrainingConfig(guard_margin=0.05),
    )
    assert rows[1]["utility"] < rows[0]["utility"]


def test_cue_ranker_wandb_lifecycle_logs_epoch_and_root_artifacts(tmp_path, monkeypatch):
    class FakeLogger:
        def __init__(self):
            self.epochs = []
            self.finish_args = None

        def log_epoch(self, *args, **kwargs):
            self.epochs.append((args, kwargs))

        def finish(self, **kwargs):
            self.finish_args = kwargs

    fake = FakeLogger()
    monkeypatch.setattr("src.ml.cue_ranker_runner.WandbLogger.start", lambda *args, **kwargs: fake)
    output = tmp_path / "run"
    result = train_cue_ranker(
        *_loaders(), output, dataset_manifest_sha256=hashlib.sha256(b"synthetic").hexdigest(),
        config=CueRankerTrainingConfig(max_epochs=1, device="cpu"),
        wandb_config=object(),
    )
    assert result.last_epoch == 1
    assert len(fake.epochs) == 1
    assert fake.finish_args["status"] == "completed"
    assert fake.finish_args["artifact_paths"] == ("best.pt", "latest.pt", "history.json", "manifest.json")


def test_cue_ranker_wandb_finishes_on_controlled_error(tmp_path, monkeypatch):
    class FakeLogger:
        def __init__(self):
            self.finish_args = None

        def finish(self, **kwargs):
            self.finish_args = kwargs

    fake = FakeLogger()
    monkeypatch.setattr("src.ml.cue_ranker_runner.WandbLogger.start", lambda *args, **kwargs: fake)
    output = tmp_path / "existing"
    output.mkdir()
    monkeypatch.setattr("src.ml.cue_ranker_runner._load_resume", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("synthetic resume failure")))
    with pytest.raises(RuntimeError, match="synthetic resume failure"):
        train_cue_ranker(
            *_loaders(), output, dataset_manifest_sha256=hashlib.sha256(b"synthetic").hexdigest(),
            config=CueRankerTrainingConfig(max_epochs=2, device="cpu"), resume=True, wandb_config=object(),
        )
    assert fake.finish_args["status"] == "failed"
    assert isinstance(fake.finish_args["error"], RuntimeError)
