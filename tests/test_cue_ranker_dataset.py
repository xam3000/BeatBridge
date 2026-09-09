import hashlib
import json
import math

import pytest
import torch

from src.features import VARIABLE_DATASET_FORMAT_VERSION
from src.features.contract import feature_index
from src.features.cue_ranker_dataset import _normalizer_record, export_cue_ranker_dataset
from src.features.cue_ranker_universe import build_cue_ranker_universe, write_cue_ranker_pair_index
from src.ml.cue_ranker_data import CueRankerGroupedDataset
from src.ml.cue_ranker_teacher import TEACHER_MODEL_NAME, TeacherEvaluation, label_cue_ranker_teacher, seal_teacher_release
from src.ml.variable_model import VariableTCNBiLSTMTransitionControl
from src.ml.variable_runner import (
    VARIABLE_TEMPORAL_TRAINING_RUNNER_NAME,
    VARIABLE_TRAINING_RUN_FORMAT_VERSION,
)

from test_cue_ranker_universe import _candidate, _pair_manifest, _record, _sha


def test_dataset_v3_keeps_old_dataset_contracts_and_writes_only_train_validation(tmp_path):
    source, target = _sha("source"), _sha("target")
    pair = tmp_path / "pair.json"; _pair_manifest(pair, [_candidate(source, target, "a", 2), _candidate(source, target, "b", 8)])
    mapping = {source: "train", target: "train"}
    index = write_cue_ranker_pair_index([_record(pair, source, target, "train")], tmp_path / "pair-index.json", split_map=mapping)
    universe = build_cue_ranker_universe(index, tmp_path / "universe", split_map=mapping).output_directory
    run, checkpoint = tmp_path / "run.json", tmp_path / "best.pt"
    contract = {"model_name": TEACHER_MODEL_NAME}
    torch.save({
        "format_version": VARIABLE_TRAINING_RUN_FORMAT_VERSION,
        "runner_name": VARIABLE_TEMPORAL_TRAINING_RUNNER_NAME,
        "model_name": TEACHER_MODEL_NAME,
        "run_id": "synthetic-teacher-run",
        "contract": contract,
        "model_state_dict": VariableTCNBiLSTMTransitionControl().state_dict(),
    }, checkpoint)
    run.write_text(json.dumps({
        "format_version": VARIABLE_TRAINING_RUN_FORMAT_VERSION,
        "runner_name": VARIABLE_TEMPORAL_TRAINING_RUNNER_NAME,
        "run_id": "synthetic-teacher-run",
        "status": "completed",
        "contract": contract,
        "files": {"best_checkpoint": {"path": "best.pt", "sha256": hashlib.sha256(checkpoint.read_bytes()).hexdigest()}},
    }), encoding="utf-8")
    release = seal_teacher_release(run, checkpoint, tmp_path / "release.json", renderer_config={"sample_rate": 11025}, objective_config={}, normalizer_sha256=_sha("normalizer"), backend_provenance={"rubberband_backend_sha256": _sha("backend")})
    labels = label_cue_ranker_teacher(universe, release, tmp_path / "labels", evaluator=lambda row, release: TeacherEvaluation(-float(row["transition_length_bars"]), .9, {"alignment_contract": "local_grid_target_to_source_v1"})).output_directory
    result = export_cue_ranker_dataset(universe, labels, tmp_path / "dataset", train_only_normalizer={
        "fit_scope": "training_tracks_only", "stats_id": "synthetic",
        "spectral_flux_log1p_p99": 1.0, "onset_strength_log1p_p99": 1.0,
        "training_audio_sha256": [source, target],
        "input_universe_manifest_sha256": hashlib.sha256((universe / "manifest.json").read_bytes()).hexdigest(),
    })
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert VARIABLE_DATASET_FORMAT_VERSION == 2
    assert manifest["format_version"] == 3
    assert manifest["test"] == {"state": "sealed_not_materialized"}
    assert set(manifest["counts"]) == {"train", "validation"}
    assert not (result.output_directory / "test").exists()


def test_normalizer_record_rejects_a_different_input_universe():
    source, target = _sha("source"), _sha("target")
    with pytest.raises(ValueError, match="input universe differs"):
        _normalizer_record(
            {
                "fit_scope": "training_tracks_only",
                "stats_id": "synthetic",
                "spectral_flux_log1p_p99": 1.0,
                "onset_strength_log1p_p99": 1.0,
                "training_audio_sha256": [source, target],
                "input_universe_manifest_sha256": _sha("other-universe"),
            },
            universe_manifest_sha256=_sha("current-universe"),
            training_audio_sha256=[source, target],
        )


def test_grouped_loader_context_uses_full_universe_size_not_label_sample_size():
    # The sampled members can be much fewer than the complete candidate group.
    # At inference the ranker sees the latter, so this context field must agree.
    features = torch.zeros(16, 54)
    features[:, feature_index("transition_position")] = (
        torch.arange(16, dtype=torch.float32) + 0.5
    ) / 16
    row = {
        "candidate_id": "sampled-candidate",
        "transition_length_bars": 2,
        "sequence_length": 16,
        "features_a": features,
        "features_b": features.clone(),
        "global_features": torch.zeros(16),
        "length_condition": torch.tensor([0.25]),
        "candidate": {
            "source_track": {},
            "target_track": {},
            "source_cutpoint": {"bar_index": 1, "count_in_bar": 1, "beats_in_bar": 4},
            "target_cutpoint": {"bar_index": 2, "count_in_bar": 1, "beats_in_bar": 4},
            "source_grid": {"grid_source": "verified", "fallback_used": False},
            "target_grid": {"grid_source": "verified", "fallback_used": False},
        },
    }
    dataset = object.__new__(CueRankerGroupedDataset)
    dataset.feature_loader = None
    dataset.split = "train"
    dataset._groups = [{
        "group_id": "group",
        "members": (row,),
        "group": {"universe_size": 600},
    }]

    member = dataset[0]["members"][0]
    assert member["candidate_context"][8].item() == pytest.approx(math.log1p(600))
