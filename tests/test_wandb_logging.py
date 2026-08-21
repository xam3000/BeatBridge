import json

from src.ml import WandbConfig, WandbLogger
from src.ml.wandb_logging import _public_contract


class _FakeArtifact:
    def __init__(self, name, type, metadata):
        self.name = name
        self.type = type
        self.metadata = metadata
        self.files = []

    def add_file(self, path, name=None):
        self.files.append((path, name))


class _FakeRun:
    name = "fake-run"

    def __init__(self):
        self.logged = []
        self.summary = {}
        self.artifacts = []
        self.finished = False

    def log(self, payload, step):
        self.logged.append((payload, step))

    def log_artifact(self, artifact, aliases):
        self.artifacts.append((artifact, aliases))

    def finish(self):
        self.finished = True


class _FakeWandb:
    Artifact = _FakeArtifact

    def __init__(self):
        self.run = _FakeRun()
        self.init_kwargs = None

    def init(self, **kwargs):
        self.init_kwargs = kwargs
        return self.run


def test_disabled_wandb_is_a_noop_without_sdk(tmp_path):
    logger = WandbLogger.start(
        WandbConfig(mode="disabled"),
        run_id="run-id",
        runner_name="runner",
        contract={},
        output_directory=tmp_path,
        resume=False,
    )

    logger.log_epoch(
        0,
        {"loss": 1.0},
        {"loss": 0.5},
        best_validation_loss=0.5,
        stale_epochs=0,
        improved=False,
    )
    logger.finish(
        status="completed",
        last_epoch=0,
        best_epoch=0,
        best_validation_loss=0.5,
        output_directory=tmp_path,
    )
    assert not logger.enabled


def test_online_logger_tracks_metrics_and_run_artifact(tmp_path, monkeypatch):
    fake_wandb = _FakeWandb()
    monkeypatch.setitem(__import__("sys").modules, "wandb", fake_wandb)
    output = tmp_path / "run"
    (output / "checkpoints").mkdir(parents=True)
    (output / "checkpoints" / "best.pt").write_bytes(b"best")
    (output / "checkpoints" / "latest.pt").write_bytes(b"latest")
    (output / "history.json").write_text("{}", encoding="utf-8")
    (output / "manifest.json").write_text("{}", encoding="utf-8")

    logger = WandbLogger.start(
        WandbConfig(mode="offline", project="beatbridge-test"),
        run_id="run-id",
        runner_name="runner",
        contract={
            "dataset": {
                "path": "C:/private/data",
                "id": "dataset-1",
                "cache_manifests": [{"path": "C:/private/cache/manifest.json"}],
            }
        },
        output_directory=output,
        resume=False,
    )
    logger.log_epoch(
        2,
        {"loss": 1.0, "objective_term": 0.25},
        {"loss": 0.5},
        best_validation_loss=0.5,
        stale_epochs=0,
        improved=True,
    )
    logger.finish(
        status="completed",
        last_epoch=2,
        best_epoch=2,
        best_validation_loss=0.5,
        output_directory=output,
    )

    assert fake_wandb.init_kwargs["mode"] == "offline"
    assert fake_wandb.init_kwargs["id"] != "run-id"
    assert fake_wandb.init_kwargs["config"]["dataset"]["id"] == "dataset-1"
    assert "path" not in fake_wandb.init_kwargs["config"]["dataset"]
    assert "path" not in fake_wandb.init_kwargs["config"]["dataset"]["cache_manifests"][0]
    assert fake_wandb.run.logged[0][0]["train/loss"] == 1.0
    assert fake_wandb.run.logged[0][0]["validation/loss"] == 0.5
    assert fake_wandb.run.logged[0][1] == 2
    assert len(fake_wandb.run.artifacts) == 1
    assert fake_wandb.run.finished


def test_public_contract_is_json_serializable_and_redacts_dataset_path():
    contract = _public_contract({"dataset": {"path": "private", "split_counts": {"train": 2}}})
    assert "path" not in contract["dataset"]
    json.dumps(contract)
