import json
from pathlib import Path

from src.evaluation.all_models_control_study import (
    _empty_ratings,
    build_listening_page,
    discover_representative_runs,
)


def _write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_player_contains_every_pair_and_has_no_answer_mapping():
    manifest = {
        "dataset_id": "dataset-1",
        "created_at_utc": "2026-09-04T00:00:00+00:00",
        "criteria": ["cleanliness"],
        "pairs": [
            {
                "index": 1,
                "directory": "01__a__to__b",
                "source_track": "musik/a.flac",
                "target_track": "musik/b.flac",
                "transition_length_bars": 4,
                "tempo_adjustment_fraction": 0.001,
                "labels": ["A", "B", "C"],
            }
        ],
    }
    page = build_listening_page(manifest)
    assert "01__a__to__b" in page
    assert "label+'.wav'" in page
    assert "Bewertungen herunterladen" in page
    assert "baseline_equal_power" not in page
    ratings = _empty_ratings(manifest)
    assert ratings["ratings"][0]["scores"]["C"]["artifact_freedom"] is None


def test_discovery_keeps_best_compatible_run_per_family(tmp_path):
    dataset = tmp_path / "dataset"
    dataset_manifest = {"dataset_id": "shared"}
    _write_json(dataset / "manifest.json", dataset_manifest)
    import hashlib

    dataset_sha = hashlib.sha256((dataset / "manifest.json").read_bytes()).hexdigest()
    runs = tmp_path / "runs"

    def add(name, family, loss, *, dataset_id="shared", renderer=None):
        run = runs / name
        checkpoint = run / "checkpoints" / "best.pt"
        checkpoint.parent.mkdir(parents=True)
        checkpoint.write_bytes(b"checkpoint")
        _write_json(
            run / "manifest.json",
            {
                "status": "completed",
                "best_validation_loss": loss,
                "contract": {
                    "model": {"name": family},
                    "dataset": {
                        "dataset_id": dataset_id,
                        "manifest_sha256": dataset_sha,
                    },
                    "renderer": {"name": renderer},
                },
                "files": {"best_checkpoint": {"path": "checkpoints/best.pt"}},
            },
        )

    add("mlp_worse", "time_shared_mlp_v1", 0.4)
    add("mlp_best", "time_shared_mlp_v1", 0.3)
    add("vocal", "vocal_time_shared_mlp_v2", 0.5)
    add(
        "tcn_wrong_renderer",
        "tcn_bilstm_transition_control_v1",
        0.1,
        renderer="other",
    )
    add(
        "tcn",
        "tcn_bilstm_transition_control_v1",
        0.6,
        renderer="differentiable_full_band_transition_v1",
    )
    add("foreign", "time_shared_mlp_v1", 0.01, dataset_id="foreign")

    selected = {path.name for path in discover_representative_runs(runs, dataset)}
    assert selected == {"mlp_best", "vocal", "tcn"}
