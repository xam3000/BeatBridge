"""Optional Weights & Biases logging for reproducible training runs.

The local ``history.json`` and ``manifest.json`` remain the authoritative run
records.  W&B is an additive telemetry and artifact sink that can be disabled
without importing the optional dependency.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import math
import os
from pathlib import Path
import warnings


WANDB_MODES = ("disabled", "offline", "online")


@dataclass(frozen=True)
class WandbConfig:
    """Settings for optional W&B logging.

    ``disabled`` is the default so unit tests and existing scripts remain
    network-free.  ``offline`` stores W&B data locally for a later sync;
    ``online`` uploads metrics during training.
    """

    mode: str = "disabled"
    project: str = "beatbridge"
    entity: str | None = None
    group: str | None = None
    log_checkpoints: bool = True

    def __post_init__(self):
        if self.mode not in WANDB_MODES:
            raise ValueError(
                f"wandb mode must be one of {WANDB_MODES}, got {self.mode!r}"
            )
        if not self.project:
            raise ValueError("wandb project must not be empty")

    @classmethod
    def from_environment(cls, *, mode: str | None = None):
        """Create settings from ``WANDB_*`` variables without requiring login."""

        return cls(
            mode=(mode or os.environ.get("WANDB_MODE", "disabled")).lower(),
            project=os.environ.get("WANDB_PROJECT", "beatbridge"),
            entity=os.environ.get("WANDB_ENTITY") or None,
            group=os.environ.get("WANDB_GROUP") or None,
            log_checkpoints=os.environ.get("WANDB_LOG_CHECKPOINTS", "1")
            not in {"0", "false", "no"},
        )


class WandbLogger:
    """Small failure-tolerant adapter around the optional W&B SDK."""

    def __init__(self, run, config: WandbConfig, wandb_module=None):
        self._run = run
        self.config = config
        self._wandb = wandb_module

    @classmethod
    def start(
        cls,
        config: WandbConfig | None,
        *,
        run_id: str,
        runner_name: str,
        contract: dict,
        output_directory,
        resume: bool,
    ) -> "WandbLogger":
        config = config or WandbConfig.from_environment()
        if config.mode == "disabled":
            return cls(None, config)

        try:
            import wandb
        except ImportError as error:
            raise RuntimeError(
                "W&B logging was requested, but the optional 'wandb' package "
                "is not installed. Install requirements.txt first."
            ) from error

        output_directory = Path(output_directory)
        wandb_data_directory = output_directory / "wandb" / "data"
        wandb_data_directory.mkdir(parents=True, exist_ok=True)
        # W&B otherwise defaults artifact staging to a user-global AppData
        # directory, which may be read-only on managed Windows environments.
        os.environ["WANDB_DATA_DIR"] = str(wandb_data_directory)
        wandb_run_id = hashlib.sha256(
            f"{run_id}|{output_directory.resolve()}".encode("utf-8")
        ).hexdigest()[:20]
        init_kwargs = {
            "project": config.project,
            "name": f"{runner_name}-{run_id}",
            "id": wandb_run_id,
            "mode": config.mode,
            "job_type": "train",
            "config": _public_contract(contract),
            "dir": str(output_directory / "wandb"),
        }
        if config.entity:
            init_kwargs["entity"] = config.entity
        if config.group:
            init_kwargs["group"] = config.group
        # W&B supports server-side resume for online runs. Offline runs are
        # intentionally independent local records and the SDK ignores this
        # option there.
        if config.mode == "online":
            init_kwargs["resume"] = "allow"
        del resume  # The deterministic local run ID remains the source of truth.
        return cls(wandb.init(**init_kwargs), config, wandb)

    @property
    def enabled(self):
        return self._run is not None

    def log_epoch(self, epoch: int, train_metrics: dict, validation_metrics: dict, *,
                  best_validation_loss: float, stale_epochs: int, improved: bool):
        if not self.enabled:
            return
        payload = {
            "epoch": int(epoch),
            "best/validation_loss": float(best_validation_loss),
            "early_stopping/stale_epochs": int(stale_epochs),
            "early_stopping/improved": int(bool(improved)),
        }
        payload.update(_flatten_metrics("train", train_metrics))
        payload.update(_flatten_metrics("validation", validation_metrics))
        self._call("log metrics", lambda: self._run.log(payload, step=int(epoch)))

    def finish(
        self,
        *,
        status: str,
        last_epoch: int,
        best_epoch: int,
        best_validation_loss: float,
        output_directory,
        error: Exception | None = None,
    ):
        if not self.enabled:
            return
        summary = {
            "status": status,
            "last_epoch": int(last_epoch),
            "best_epoch": int(best_epoch),
            "best_validation_loss": float(best_validation_loss),
        }
        if error is not None:
            summary["error"] = f"{type(error).__name__}: {error}"
        self._call("update summary", lambda: self._run.summary.update(summary))

        if error is None and self.config.log_checkpoints:
            output_directory = Path(output_directory)
            artifact_paths = [
                output_directory / "checkpoints" / "best.pt",
                output_directory / "checkpoints" / "latest.pt",
                output_directory / "history.json",
                output_directory / "manifest.json",
            ]

            def log_artifact():
                artifact = self._wandb.Artifact(
                    name=f"{self._run.name}-results",
                    type="model",
                    metadata={
                        "status": status,
                        "best_epoch": int(best_epoch),
                        "best_validation_loss": float(best_validation_loss),
                    },
                )
                for path in artifact_paths:
                    if path.is_file():
                        artifact.add_file(str(path), name=path.name)
                self._run.log_artifact(artifact, aliases=[status, "latest"])

            self._call("log model artifact", log_artifact)
        self._call("finish run", lambda: self._run.finish())

    def _call(self, operation: str, callback):
        try:
            callback()
        except Exception as error:  # Telemetry must not corrupt local training.
            warnings.warn(
                f"W&B {operation} failed; local training artifacts remain valid: "
                f"{type(error).__name__}: {error}",
                RuntimeWarning,
                stacklevel=2,
            )


def _flatten_metrics(prefix: str, metrics: dict) -> dict[str, float]:
    result = {}
    for name, value in metrics.items():
        scalar = float(value)
        if not math.isfinite(scalar):
            continue
        result[f"{prefix}/{name}"] = scalar
    return result


def _public_contract(contract: dict) -> dict:
    """Remove local filesystem paths before sending config to W&B."""

    def copy(value, *, in_dataset=False):
        if isinstance(value, dict):
            return {
                name: copy(item, in_dataset=in_dataset or name == "dataset")
                for name, item in value.items()
                if not (in_dataset and name == "path")
            }
        if isinstance(value, (list, tuple)):
            return [copy(item, in_dataset=in_dataset) for item in value]
        return value

    return copy(contract)
