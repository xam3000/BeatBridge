import hashlib
import json

import pytest
import torch

from src.features.cue_ranker_universe import build_cue_ranker_universe, write_cue_ranker_pair_index
from src.ml.cue_ranker_teacher import TEACHER_MODEL_NAME, TeacherEvaluation, label_cue_ranker_teacher, load_frozen_teacher, seal_teacher_release, teacher_cache_key, verify_teacher_release
from src.ml.variable_model import VariableTCNBiLSTMTransitionControl
from src.ml.variable_runner import (
    VARIABLE_TEMPORAL_TRAINING_RUNNER_NAME,
    VARIABLE_TRAINING_RUN_FORMAT_VERSION,
)

from test_cue_ranker_universe import _candidate, _pair_manifest, _record, _sha


def _universe(tmp_path):
    a, b = _sha("a"), _sha("b")
    manifest = tmp_path / "pair.json"
    _pair_manifest(manifest, [_candidate(a, b, "good", 2), _candidate(a, b, "guard", 4), _candidate(a, b, "failed", 6)])
    mapping = {a: "train", b: "train"}
    index = write_cue_ranker_pair_index([_record(manifest, a, b, "train")], tmp_path / "pair-index.json", split_map=mapping)
    return build_cue_ranker_universe(index, tmp_path / "universe", split_map=mapping).output_directory


def _release(tmp_path):
    checkpoint = tmp_path / "best.pt"
    contract = {"model_name": TEACHER_MODEL_NAME}
    torch.save(
        {
            "format_version": VARIABLE_TRAINING_RUN_FORMAT_VERSION,
            "runner_name": VARIABLE_TEMPORAL_TRAINING_RUNNER_NAME,
            "model_name": TEACHER_MODEL_NAME,
            "run_id": "synthetic-teacher-run",
            "contract": contract,
            "model_state_dict": VariableTCNBiLSTMTransitionControl().state_dict(),
        },
        checkpoint,
    )
    run = tmp_path / "run.json"
    run.write_text(json.dumps({
        "format_version": VARIABLE_TRAINING_RUN_FORMAT_VERSION,
        "runner_name": VARIABLE_TEMPORAL_TRAINING_RUNNER_NAME,
        "run_id": "synthetic-teacher-run",
        "status": "completed",
        "contract": contract,
        "files": {"best_checkpoint": {"path": "best.pt", "sha256": hashlib.sha256(checkpoint.read_bytes()).hexdigest()}},
    }), encoding="utf-8")
    return seal_teacher_release(run, checkpoint, tmp_path / "teacher_release.json", renderer_config={"sample_rate": 11025}, objective_config={}, normalizer_sha256=_sha("normalizer"), backend_provenance={"rubberband_backend_sha256": _sha("rubberband")})


def test_teacher_release_rejects_checkpoint_not_declared_as_completed_run_best(tmp_path):
    checkpoint = tmp_path / "best.pt"
    torch.save({"model_state_dict": VariableTCNBiLSTMTransitionControl().state_dict()}, checkpoint)
    other = tmp_path / "other.pt"
    torch.save({"model_state_dict": VariableTCNBiLSTMTransitionControl().state_dict()}, other)
    run = tmp_path / "run.json"
    run.write_text(json.dumps({
        "format_version": VARIABLE_TRAINING_RUN_FORMAT_VERSION,
        "runner_name": VARIABLE_TEMPORAL_TRAINING_RUNNER_NAME,
        "run_id": "synthetic-teacher-run",
        "status": "completed",
        "contract": {"model_name": TEACHER_MODEL_NAME},
        "files": {"best_checkpoint": {"path": "other.pt", "sha256": hashlib.sha256(other.read_bytes()).hexdigest()}},
    }), encoding="utf-8")

    with pytest.raises(ValueError, match="teacher_run_best_checkpoint"):
        seal_teacher_release(
            run,
            checkpoint,
            tmp_path / "teacher_release.json",
            renderer_config={"sample_rate": 11025},
            objective_config={},
            normalizer_sha256=_sha("normalizer"),
            backend_provenance={"rubberband_backend_sha256": _sha("rubberband")},
        )


def test_teacher_labels_are_frozen_auditable_and_failure_isolated(tmp_path):
    universe, release = _universe(tmp_path), _release(tmp_path)
    def evaluator(row, _release):
        if row["candidate_id"] == "failed": return TeacherEvaluation(None, None, {"alignment_contract": "local_grid_target_to_source_v1"}, "synthetic_render_failure")
        return TeacherEvaluation(-0.2, 0.4 if row["candidate_id"] == "guard" else 0.8, {"alignment_contract": "local_grid_target_to_source_v1"})
    result = label_cue_ranker_teacher(universe, release, tmp_path / "labels", evaluator=evaluator)
    assert result.counts["train"] == {"selected": 3, "scored": 1, "guard_rejected": 1, "failed": 1}
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert manifest["test"] == {"state": "sealed_not_materialized"}
    assert manifest["teacher_release_sha256"] == hashlib.sha256(release.read_bytes()).hexdigest()
    frozen, _, _ = load_frozen_teacher(release)
    assert frozen.training is False
    release.write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError):
        verify_teacher_release(release)


def test_teacher_cache_key_binds_alignment_payloads_backend_and_contract(tmp_path):
    _, release_path = _universe(tmp_path), _release(tmp_path)
    release, _ = verify_teacher_release(release_path)
    record = {"candidate_identity_sha256": _sha("candidate"), "candidate_request_config_sha256": _sha("request")}
    provenance = {key: _sha(key) for key in ("source_feature_payload_sha256", "target_feature_payload_sha256", "source_feature_manifest_sha256", "target_feature_manifest_sha256", "source_grid_sha256", "target_grid_sha256", "source_audio_sha256", "target_audio_sha256", "source_stem_payload_sha256", "target_stem_payload_sha256", "rubberband_backend_sha256")}
    provenance["local_source_window_samples"] = 1234
    first = teacher_cache_key(record, provenance, release)
    provenance["source_grid_sha256"] = _sha("changed-grid")
    assert teacher_cache_key(record, provenance, release) != first
