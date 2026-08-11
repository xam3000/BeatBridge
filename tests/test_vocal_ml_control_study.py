import hashlib
import json

import pytest
import torch

from src.control import VocalAwareTransitionObjectiveConfig
from src.evaluation.vocal_ml_control_study import (
    _load_best_vocal_model,
    _select_vocal_examples,
)
from src.ml import (
    VOCAL_TRAINING_RUN_FORMAT_VERSION,
    VOCAL_TRAINING_RUNNER_NAME,
    VocalFeatureControlMLP,
)


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_load_best_vocal_model_verifies_checkpoint_and_restores_contract(tmp_path):
    run = tmp_path / "run"
    checkpoints = run / "checkpoints"
    checkpoints.mkdir(parents=True)
    model = VocalFeatureControlMLP()
    checkpoint_path = checkpoints / "best.pt"
    torch.save(
        {
            "run_id": "vocal-run-test",
            "epoch": 4,
            "model_state_dict": model.state_dict(),
        },
        checkpoint_path,
    )
    manifest = {
        "format_version": VOCAL_TRAINING_RUN_FORMAT_VERSION,
        "runner_name": VOCAL_TRAINING_RUNNER_NAME,
        "status": "early_stopped",
        "run_id": "vocal-run-test",
        "best_epoch": 4,
        "model_parameter_count": model.parameter_count,
        "files": {
            "best_checkpoint": {
                "path": "checkpoints/best.pt",
                "sha256": _sha256(checkpoint_path),
            }
        },
        "contract": {
            "dataset": {"dataset_id": "dataset-test", "manifest_sha256": "abc"},
            "model": {
                "name": "vocal_time_shared_mlp_v2",
                "format_version": 2,
                "config": model.config.to_dict(),
            },
            "renderer": {
                "sample_rate": 8_000,
                "lowpass_cutoff_hz": 180.0,
                "lowpass_kernel_size": 31,
            },
            "objective": {
                "config": VocalAwareTransitionObjectiveConfig().__dict__,
            },
        },
    }
    (run / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    restored, config, provenance, objective_config, sample_rate = (
        _load_best_vocal_model(run)
    )

    assert restored.parameter_count == model.parameter_count
    assert config.maximum_vocal_ducking == 0.75
    assert provenance["checkpoint_epoch"] == 4
    assert provenance["dataset"]["dataset_id"] == "dataset-test"
    assert sample_rate == 8_000
    assert objective_config.vocal_audibility_weight == 0.5


def _item(example_id, source, target, tempo, vocal_score, rank=1):
    return {
        "example": {
            "example_id": example_id,
            "candidate_rank": rank,
            "source_track": {"path": source, "sha256": source},
            "target_track": {"path": target, "sha256": target},
        },
        "tempo_adjustment_fraction": tempo,
        "vocal_statistics": {"selection_score": vocal_score},
    }


def test_selection_prefers_tempo_safe_vocal_examples_and_distinct_pairs():
    items = [
        _item("best-a", "source-a", "target-a", 0.0, 0.8),
        _item("same-pair", "source-a", "target-a", 0.0, 1.0),
        _item("best-b", "source-b", "target-b", 0.001, 0.7),
        _item("too-much-stretch", "source-c", "target-c", 0.02, 1.2),
        _item("excluded", "14 - STRUGGLING.flac", "target-d", 0.0, 2.0),
    ]

    selected = _select_vocal_examples(
        items,
        pair_count=2,
        max_track_uses=2,
        maximum_tempo_adjustment_fraction=0.005,
    )

    assert [item["example"]["example_id"] for item in selected] == [
        "same-pair",
        "best-b",
    ]

    with pytest.raises(ValueError, match="Only 2"):
        _select_vocal_examples(
            items,
            pair_count=3,
            max_track_uses=2,
            maximum_tempo_adjustment_fraction=0.005,
        )
