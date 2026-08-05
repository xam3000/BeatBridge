import hashlib
import json

import numpy as np
import pytest
import torch

from src.control import DifferentiableTransitionObjectiveConfig
from src.ml import FeatureControlMLP
from src.evaluation.ml_control_study import (
    _load_best_model,
    _select_indices,
    _validate_bridge,
)


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_load_best_model_verifies_checkpoint_and_restores_contract(tmp_path):
    run = tmp_path / "run"
    checkpoints = run / "checkpoints"
    checkpoints.mkdir(parents=True)
    model = FeatureControlMLP()
    checkpoint_path = checkpoints / "best.pt"
    torch.save(
        {
            "run_id": "run-test",
            "epoch": 3,
            "model_state_dict": model.state_dict(),
        },
        checkpoint_path,
    )
    manifest = {
        "status": "early_stopped",
        "run_id": "run-test",
        "best_epoch": 3,
        "model_parameter_count": model.parameter_count,
        "files": {
            "best_checkpoint": {
                "path": "checkpoints/best.pt",
                "sha256": _sha256(checkpoint_path),
            }
        },
        "contract": {
            "model": {
                "name": "time_shared_mlp_v1",
                "config": model.config.to_dict(),
            },
            "renderer": {
                "sample_rate": 8_000,
                "lowpass_cutoff_hz": 180.0,
                "lowpass_kernel_size": 31,
            },
            "objective": {
                "config": DifferentiableTransitionObjectiveConfig().__dict__,
            },
        },
    }
    (run / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    restored, provenance, objective_config, sample_rate = _load_best_model(run)

    assert restored.parameter_count == model.parameter_count
    assert provenance["checkpoint_epoch"] == 3
    assert sample_rate == 8_000
    assert objective_config.vocal_overlap_weight == 1.0


def test_select_indices_limits_repeated_directed_pairs():
    examples = [
        {
            "example_id": f"example-{index}",
            "candidate_rank": index + 1,
            "source_track": {"sha256": "a"},
            "target_track": {"sha256": "b"},
        }
        for index in range(3)
    ]

    selected = _select_indices(examples, max_examples_per_pair=2, example_limit=None)

    assert selected == (0, 1)


def test_validate_bridge_rejects_nonfinite_or_mismatched_audio():
    valid = np.zeros((2, 100), dtype=np.float32)
    source, target = _validate_bridge(valid, valid.copy())
    assert source.shape == target.shape == (2, 100)

    invalid = valid.copy()
    invalid[0, 0] = np.nan
    with pytest.raises(ValueError):
        _validate_bridge(invalid, valid)
    with pytest.raises(ValueError):
        _validate_bridge(valid, valid[:, :-1])
