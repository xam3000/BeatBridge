"""Versioned mapping from controller outputs to physical controls."""

from dataclasses import asdict, fields
import json
from pathlib import Path

import torch

from src.control.differentiable import _equal_power_pair, _interpolate_control


LEGACY = "legacy"
EQUAL_POWER = "equal_power_v1"


def validate_initialization(name):
    if name not in (LEGACY, EQUAL_POWER):
        raise ValueError(f"Unsupported control_initialization: {name!r}")


def bind_control_state(model):
    """Make strict state_dict loading reject a silent change of physical mapping."""
    if getattr(model.config, "control_initialization", LEGACY) == EQUAL_POWER:
        model.register_buffer("_equal_power_v1", torch.empty(0, dtype=torch.uint8))


def config_dict(config):
    raw = asdict(config)
    if raw["control_initialization"] == LEGACY:
        # Preserve historical run IDs and exact contract equality on resume.
        del raw["control_initialization"]
    return {k: list(v) if isinstance(v, tuple) else v for k, v in raw.items()}


def read_model_config(kind, raw):
    values = dict(raw)
    values.setdefault("control_initialization", LEGACY)
    missing = {f.name for f in fields(kind)} - values.keys()
    if missing:
        raise ValueError(f"Incomplete {kind.__name__} in manifest: missing {sorted(missing)}")
    for name in ("hidden_dimensions", "encoder_channels"):
        if name in values:
            values[name] = tuple(values[name])
    return kind(**values)


def run_initialization(directory, resume, requested=None, source_manifest=None):
    path = Path(directory) / "manifest.json" if resume else source_manifest
    if path is not None:
        config = json.loads(Path(path).read_text(encoding="utf-8"))["contract"]["model"]["config"]
        bound = config.get("control_initialization", LEGACY)
        if requested is not None and requested != bound:
            raise ValueError("Requested control_initialization differs from the checkpoint contract")
        return bound
    return requested or EQUAL_POWER


def neutral_at_zero(logits):
    """Bounded attenuation. At the cusp use the inward (right) derivative."""
    magnitude = torch.where(logits >= 0, logits, -logits)
    return torch.tanh(magnitude)


def full_band_arguments(controls, names, samples):
    """Legacy gain knots, or sample-interpolated positions as in the P04 reference."""
    if "mix_position" not in controls:
        return tuple(controls[name] for name in names)

    def interpolate(name):
        return _interpolate_control(controls[name][None], samples)[0]

    gains = _equal_power_pair(interpolate("mix_position"))
    return (*gains, *(interpolate(k) for k in names[2:8]),
            interpolate("low_end_position"), interpolate("vocal_ducking"))
