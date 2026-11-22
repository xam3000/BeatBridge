"""Optional Weights & Biases logging for reproducible training runs.

The local ``history.json`` and ``manifest.json`` remain the authoritative run
records.  W&B is an additive telemetry and artifact sink that can be disabled
without importing the optional dependency.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import math
import numbers
import os
from pathlib import Path
import warnings


WANDB_MODES = ("disabled", "offline", "online")
WANDB_SWEEP_ID_ENV = "WANDB_SWEEP_ID"
WANDB_SWEEP_RUN_ID_ENV = "WANDB_RUN_ID"
WANDB_SWEEP_PARAM_PATH_ENV = "WANDB_SWEEP_PARAM_PATH"


def load_sweep_parameters() -> dict:
    """Read the current agent trial's parameters from W&B's generated YAML."""

    config_path = os.environ.get(WANDB_SWEEP_PARAM_PATH_ENV)
    if not config_path:
        raise RuntimeError(
            "This command must be started by a W&B sweep agent; "
            f"{WANDB_SWEEP_PARAM_PATH_ENV} is not set."
        )

    try:
        import yaml
    except ImportError as error:
        raise RuntimeError(
            "W&B sweep configuration parsing requires the 'PyYAML' dependency."
        ) from error

    path = Path(config_path)
    if not path.is_file():
        raise FileNotFoundError(f"W&B sweep parameter file does not exist: {path}")
    with path.open("r", encoding="utf-8") as stream:
        payload = yaml.safe_load(stream) or {}
    if not isinstance(payload, dict):
        raise ValueError("W&B sweep parameter file must contain a YAML mapping")

    payload.pop("wandb_version", None)
    parameters = {}
    for name, entry in payload.items():
        if not isinstance(entry, dict) or "value" not in entry:
            raise ValueError(f"Invalid W&B sweep parameter entry for {name!r}")
        parameters[name] = entry["value"]
    return parameters


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
    name: str | None = None
    tags: tuple[str, ...] = ()
    log_checkpoints: bool = True
    artifact_paths: tuple[str, ...] | None = None

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
            name=os.environ.get("WANDB_NAME") or None,
            tags=tuple(tag for tag in os.environ.get("WANDB_TAGS", "").split(",") if tag),
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
        sweep_run = bool(os.environ.get(WANDB_SWEEP_ID_ENV))
        wandb_run_id = hashlib.sha256(
            f"{run_id}|{output_directory.resolve()}".encode("utf-8")
        ).hexdigest()[:20]
        init_kwargs = {
            "mode": config.mode,
            "job_type": "train",
            "config": _public_contract(contract),
            "dir": str(output_directory / "wandb"),
        }
        if sweep_run:
            # Sweep agents set the run and sweep IDs in the environment. Let
            # wandb.init() consume those values so this training run remains a
            # child of the active sweep instead of creating a detached run.
            init_kwargs["name"] = config.name or (
                f"{runner_name}-{os.environ.get(WANDB_SWEEP_RUN_ID_ENV, run_id)}"
            )
            init_kwargs["resume"] = "allow"
        else:
            init_kwargs.update({
                "project": config.project,
                "name": config.name or f"{runner_name}-{run_id}",
                "id": wandb_run_id,
            })
            if config.entity:
                init_kwargs["entity"] = config.entity
        if config.group:
            init_kwargs["group"] = config.group
        if config.tags:
            init_kwargs["tags"] = list(config.tags)
        # W&B supports server-side resume for online runs. Offline runs are
        # intentionally independent local records and the SDK ignores this
        # option there.
        if config.mode == "online" and not sweep_run:
            init_kwargs["resume"] = "allow"
        del resume  # The deterministic local run ID remains the source of truth.
        logger = cls(wandb.init(**init_kwargs), config, wandb)
        define_metric = getattr(logger._run, "define_metric", None)
        if callable(define_metric):
            logger._call(
                "define learning-rate chart axis",
                lambda: define_metric(
                    "learning_rate", step_metric="epoch", summary="last"
                ),
            )
        return logger

    @property
    def enabled(self):
        return self._run is not None

    def log_epoch(self, epoch: int, train_metrics: dict, validation_metrics: dict, *,
                  best_validation_loss: float | None, stale_epochs: int, improved: bool):
        if not self.enabled:
            return
        payload = {
            "epoch": int(epoch),
            "early_stopping/stale_epochs": int(stale_epochs),
            "early_stopping/improved": int(bool(improved)),
        }
        if best_validation_loss is not None:
            payload.update({"best_validation_loss": float(best_validation_loss),
                            "best/validation_loss": float(best_validation_loss)})
        train_metrics = dict(train_metrics)
        learning_rate = train_metrics.pop("learning_rate", None)
        payload.update(_flatten_metrics("train", train_metrics))
        if learning_rate is not None:
            payload["learning_rate"] = float(learning_rate)
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
        artifact_paths=None,
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
            relative_paths = artifact_paths or self.config.artifact_paths or (
                "checkpoints/best.pt", "checkpoints/latest.pt", "history.json", "manifest.json"
            )
            artifact_paths = [(output_directory / relative).resolve() for relative in relative_paths]

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
    """Flatten nested metric mappings in sorted key order.

    Missing optional metrics (``None``) are omitted.  All other non-scalars,
    including strings and sequences, are rejected instead of being stringified
    or accidentally passed to ``float``.
    """
    if not isinstance(metrics, dict):
        raise TypeError(f"metrics at {prefix!r} must be a dict")
    result = {}

    def visit(path, value):
        if isinstance(value, dict):
            for key in sorted(value, key=lambda item: str(item)):
                if not isinstance(key, str):
                    raise TypeError(f"metric key at {path!r} must be a string")
                visit(f"{path}/{key}", value[key])
            return
        if value is None:
            return
        if isinstance(value, bool):
            scalar = float(value)
        elif isinstance(value, numbers.Real):
            scalar = float(value)
        else:
            # Support scalar tensor/NumPy values without accepting arrays.
            try:
                if getattr(value, "ndim", None) == 0 or getattr(value, "numel", lambda: -1)() == 1:
                    scalar = float(value)
                else:
                    raise TypeError
            except (TypeError, ValueError, RuntimeError, OverflowError) as error:
                raise TypeError(
                    f"metric {path!r} must be a finite scalar, mapping, or None; "
                    f"got {type(value).__name__}"
                ) from error
        if math.isfinite(scalar):
            result[path] = scalar

    for name in sorted(metrics):
        if not isinstance(name, str):
            raise TypeError(f"metric key at {prefix!r} must be a string")
        visit(f"{prefix}/{name}", metrics[name])
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
