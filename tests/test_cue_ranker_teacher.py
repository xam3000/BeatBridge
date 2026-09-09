import hashlib
import json
import sys

import numpy as np
import pytest
import torch

from src.features.contract import feature_index
from src.features.cue_ranker_universe import build_cue_ranker_universe, write_cue_ranker_pair_index
from src.ml.cue_ranker_teacher import TEACHER_MODEL_NAME, TeacherEvaluation, TeacherLabelingConfig, label_cue_ranker_teacher, load_frozen_teacher, score_prepared_candidate, seal_teacher_release, teacher_cache_key, verify_teacher_release
from src.ml.cue_ranker_teacher_resolver import (
    _load_cache,
    _normalization_from_release,
    _publish_cache,
    teacher_waveform_cache_key,
)
from src.ml.variable_model import VariableTCNBiLSTMTransitionControl
from src.ml.variable_runner import (
    VARIABLE_TEMPORAL_TRAINING_RUNNER_NAME,
    VARIABLE_TRAINING_RUN_FORMAT_VERSION,
)
from src.ml.__main__ import main as ml_main

from test_cue_ranker_universe import _candidate, _pair_manifest, _record, _sha


def _universe(tmp_path):
    a, b = _sha("a"), _sha("b")
    manifest = tmp_path / "pair.json"
    candidates = [_candidate(a, b, "good", 2), _candidate(a, b, "guard", 4), _candidate(a, b, "failed", 6)]
    for candidate in candidates:
        candidate["source_bpm"] = 120.0
        candidate["target_bpm"] = 120.0
    _pair_manifest(manifest, candidates)
    mapping = {a: "train", b: "train"}
    index = write_cue_ranker_pair_index([_record(manifest, a, b, "train")], tmp_path / "pair-index.json", split_map=mapping)
    return build_cue_ranker_universe(index, tmp_path / "universe", split_map=mapping).output_directory


def _release(tmp_path):
    checkpoint = tmp_path / "best.pt"
    contract = {"model_name": TEACHER_MODEL_NAME, "model": {"config": {}}, "renderer": {"name": "DifferentiableVocalAwareRenderer", "sample_rate": 11025}}
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


def test_teacher_cache_key_separates_release_sha_even_with_identical_contract(tmp_path):
    _, release_path = _universe(tmp_path), _release(tmp_path)
    release, _ = verify_teacher_release(release_path)
    record = {"candidate_identity_sha256": _sha("candidate"), "candidate_request_config_sha256": _sha("request")}
    provenance = {key: _sha(key) for key in ("source_feature_payload_sha256", "target_feature_payload_sha256", "source_feature_manifest_sha256", "target_feature_manifest_sha256", "source_grid_sha256", "target_grid_sha256", "source_audio_sha256", "target_audio_sha256", "source_stem_payload_sha256", "target_stem_payload_sha256", "rubberband_backend_sha256")}
    provenance["local_source_window_samples"] = 1234
    assert teacher_cache_key(record, provenance, release, release_sha256=_sha("release-a")) != teacher_cache_key(record, provenance, release, release_sha256=_sha("release-b"))


def test_teacher_waveform_cache_is_immutable_and_provenance_bound(tmp_path):
    _, release_path = _universe(tmp_path), _release(tmp_path)
    release, release_sha = verify_teacher_release(release_path)
    row = {
        "candidate_identity_sha256": _sha("candidate"),
        "candidate_request_config_sha256": _sha("request"),
    }
    provenance = {key: _sha(key) for key in (
        "source_feature_payload_sha256", "target_feature_payload_sha256",
        "source_feature_manifest_sha256", "target_feature_manifest_sha256",
        "source_grid_sha256", "target_grid_sha256", "source_audio_sha256",
        "target_audio_sha256", "source_stem_payload_sha256",
        "target_stem_payload_sha256", "rubberband_backend_sha256",
    )}
    provenance.update({
        "alignment_contract": "local_grid_target_to_source_v1",
        "teacher_release_sha256": release_sha,
        "normalizer_sha256": release["normalizer_sha256"],
        "local_source_window_samples": 16,
    })
    key = teacher_waveform_cache_key(row, provenance, release, release_sha)
    arrays = {name: np.ones((2, 16), dtype=np.float32) for name in (
        "source_audio", "target_audio", "source_vocal_audio", "target_vocal_audio",
    )}
    root = tmp_path / "waveform-cache"
    _publish_cache(
        root, row, key, provenance, arrays, sample_rate=11025,
        alignment={"alignment_contract": "local_grid_target_to_source_v1"},
    )
    loaded = _load_cache(root, row, key, provenance)
    assert loaded is not None and loaded[2] is True
    changed = dict(provenance, source_grid_sha256=_sha("other-grid"))
    changed_key = teacher_waveform_cache_key(row, changed, release, release_sha)
    assert changed_key != key
    assert _load_cache(root, row, changed_key, changed) is None


def test_production_resolver_uses_training_normalizer_contract(tmp_path):
    normalizer = tmp_path / "normalizer.json"
    normalizer.write_text(json.dumps({
        "fit_scope": "training_tracks_only", "stats_id": "training-v1",
        "spectral_flux_log1p_p99": 3.5, "onset_strength_log1p_p99": 2.5,
    }), encoding="utf-8")
    release = {"normalizer": {
        "path": str(normalizer),
        "sha256": hashlib.sha256(normalizer.read_bytes()).hexdigest(),
    }}
    stats = _normalization_from_release(release)
    assert stats.stats_id == "training-v1"
    assert stats.spectral_flux_log1p_p99 == 3.5
    assert stats.onset_strength_log1p_p99 == 2.5


def test_teacher_resume_uses_verified_candidate_cache_without_re_evaluation(tmp_path):
    universe, release = _universe(tmp_path), _release(tmp_path)
    calls = []

    def evaluator(row, _release):
        calls.append(row["candidate_id"])
        return TeacherEvaluation(-0.2, 0.8, {"alignment_contract": "local_grid_target_to_source_v1"})

    first = label_cue_ranker_teacher(universe, release, tmp_path / "labels", evaluator=evaluator)
    assert first.cache_misses == 3 and first.cache_hits == 0 and len(calls) == 3
    second = label_cue_ranker_teacher(universe, release, tmp_path / "labels", evaluator=evaluator, resume=True)
    assert second.cache_hits == 3 and second.cache_misses == 0 and len(calls) == 3


def test_teacher_resume_rejects_a_tampered_candidate_cache_before_final_shards(tmp_path):
    universe, release = _universe(tmp_path), _release(tmp_path)

    def evaluator(_row, _release):
        return TeacherEvaluation(-0.2, 0.8, {"alignment_contract": "local_grid_target_to_source_v1"})

    output = tmp_path / "labels"
    label_cue_ranker_teacher(universe, release, output, evaluator=evaluator)
    cache_path = next((output / "candidate_cache").rglob("label.json"))
    cached = json.loads(cache_path.read_text(encoding="utf-8"))
    cached["label"]["teacher_utility"] = 999.0
    cache_path.write_text(json.dumps(cached), encoding="utf-8")

    with pytest.raises(ValueError, match="teacher_label_cache_sha256_mismatch"):
        label_cue_ranker_teacher(universe, release, output, evaluator=evaluator, resume=True)


def test_teacher_partial_failure_budget_resumes_from_candidate_cache(tmp_path):
    universe, release = _universe(tmp_path), _release(tmp_path)
    calls = []

    def evaluator(row, _release):
        calls.append(row["candidate_id"])
        if row["candidate_id"] == "failed":
            return TeacherEvaluation(None, None, {"alignment_contract": "local_grid_target_to_source_v1"}, "synthetic_failure")
        return TeacherEvaluation(-0.2, 0.8, {"alignment_contract": "local_grid_target_to_source_v1"})

    with pytest.raises(RuntimeError, match="teacher_failure_budget_exceeded"):
        label_cue_ranker_teacher(
            universe, release, tmp_path / "labels", evaluator=evaluator,
            config=TeacherLabelingConfig(max_technical_failures=0),
        )
    assert calls == ["failed"]
    result = label_cue_ranker_teacher(
        universe, release, tmp_path / "labels", evaluator=evaluator, resume=True,
    )
    assert calls == ["failed", "good", "guard"]
    assert result.cache_hits == 1 and result.cache_misses == 2
    assert result.counts["train"] == {"selected": 3, "scored": 2, "guard_rejected": 0, "failed": 1}


def test_teacher_candidate_budget_is_resumable(tmp_path):
    universe, release = _universe(tmp_path), _release(tmp_path)
    calls = []

    def evaluator(row, _release):
        calls.append(row["candidate_id"])
        return TeacherEvaluation(-0.2, 0.8, {"alignment_contract": "local_grid_target_to_source_v1"})

    with pytest.raises(RuntimeError, match="teacher_candidate_budget_exceeded"):
        label_cue_ranker_teacher(
            universe, release, tmp_path / "labels", evaluator=evaluator,
            config=TeacherLabelingConfig(max_candidates=1),
        )
    assert calls == ["failed"]
    with pytest.raises(RuntimeError, match="teacher_candidate_budget_exceeded"):
        label_cue_ranker_teacher(
            universe, release, tmp_path / "labels", evaluator=evaluator, resume=True,
            config=TeacherLabelingConfig(max_candidates=1),
        )
    assert calls == ["failed", "good"]
    result = label_cue_ranker_teacher(universe, release, tmp_path / "labels", evaluator=evaluator, resume=True)
    assert calls == ["failed", "good", "guard"]
    assert result.cache_hits == 2 and result.cache_misses == 1


def test_checkpoint_hash_manipulation_is_rejected_before_frozen_load(tmp_path):
    _, release = _universe(tmp_path), _release(tmp_path)
    checkpoint = tmp_path / "best.pt"
    checkpoint.write_bytes(checkpoint.read_bytes() + b"tampered")
    with pytest.raises(ValueError, match="sha256_mismatch"):
        load_frozen_teacher(release)


def test_bad_alignment_is_technical_failure_before_model_or_audio_work(tmp_path):
    _, release_path = _universe(tmp_path), _release(tmp_path)
    model, release, _ = load_frozen_teacher(release_path)
    record = {
        "candidate_id": "bad-alignment", "candidate_identity_sha256": _sha("candidate"),
        "candidate_request_config_sha256": _sha("request"), "transition_length_bars": 2,
        "transition_length_beats": 8, "sequence_length": 16,
        "candidate": {"source_bpm": 120.0},
    }
    result = score_prepared_candidate(model, record, {"provenance": {"alignment_contract": "wrong", "normalizer_sha256": release["normalizer_sha256"]}}, release, guard_scorer=lambda *_: 1.0)
    assert result.utility is None
    assert "teacher_alignment_contract_mismatch" in result.error_code


def _prepared_synthetic(release, row):
    steps = int(row["sequence_length"])
    features = np.zeros((steps, 54), dtype=np.float32)
    features[:, feature_index("transition_position")] = (np.arange(steps, dtype=np.float32) + .5) / steps
    for name in ("audio_valid", "vocal_valid", "vocal_activity", "vocal_prominence", "vocal_confidence"):
        features[:, feature_index(name)] = 1.0
    wave = np.full((2, 256), 0.01, dtype=np.float32)
    provenance = {key: _sha(key) for key in ("source_feature_payload_sha256", "target_feature_payload_sha256", "source_feature_manifest_sha256", "target_feature_manifest_sha256", "source_grid_sha256", "target_grid_sha256", "source_audio_sha256", "target_audio_sha256", "source_stem_payload_sha256", "target_stem_payload_sha256", "rubberband_backend_sha256")}
    provenance.update({"alignment_contract": "local_grid_target_to_source_v1", "normalizer_sha256": release["normalizer_sha256"], "local_source_window_samples": 1024})
    return {"features_a": features, "features_b": features.copy(), "global_features": np.zeros(16, dtype=np.float32), "length_condition": np.asarray([float(row["transition_length_bars"]) / 8], dtype=np.float32), "source_audio": wave, "target_audio": wave.copy(), "source_vocal_audio": wave * .2, "target_vocal_audio": wave * .2, "provenance": provenance}


def test_synthetic_candidate_runs_fixed_teacher_and_production_guard(tmp_path):
    universe, release_path = _universe(tmp_path), _release(tmp_path)
    release, _ = verify_teacher_release(release_path)

    class Resolver:
        def resolve(self, row):
            return _prepared_synthetic(release, row)

    result = label_cue_ranker_teacher(
        universe, release_path, tmp_path / "production-labels",
        resolver=Resolver(), config=TeacherLabelingConfig(guard_threshold=0.0),
    )
    label_path = result.output_directory / "teacher" / "train-labels-00000.npz"
    with np.load(label_path, allow_pickle=False) as payload:
        labels = [json.loads(item) for item in payload["row_json"].tolist()]
    assert len(labels) == 3
    assert all(label["teacher_status"] == "scored" for label in labels)
    assert all(label["label_status"] == "success" and np.isfinite(label["teacher_utility"]) for label in labels)


def test_seal_cli_requires_and_binds_explicit_run_normalizer_and_backend(tmp_path, monkeypatch):
    _universe(tmp_path)
    _release(tmp_path)
    run_directory = tmp_path / "run-directory"
    run_directory.mkdir()
    run = json.loads((tmp_path / "run.json").read_text(encoding="utf-8"))
    run["files"]["best_checkpoint"]["path"] = "../best.pt"
    (run_directory / "manifest.json").write_text(json.dumps(run), encoding="utf-8")
    normalizer = tmp_path / "normalizer.json"
    normalizer.write_text(json.dumps({"fit_scope": "training_tracks_only", "stats_id": "synthetic", "spectral_flux_log1p_p99": 1.0, "onset_strength_log1p_p99": 1.0}), encoding="utf-8")
    backend = tmp_path / "backend.json"
    backend.write_text(json.dumps({"rubberband_backend_sha256": _sha("backend")}), encoding="utf-8")
    output = tmp_path / "cli-release.json"
    monkeypatch.setattr(sys, "argv", ["python", "seal-cue-ranker-teacher", str(run_directory), str(output), "--normalizer", str(normalizer), "--backend-provenance", str(backend)])
    assert ml_main() == 0
    sealed, _ = verify_teacher_release(output)
    assert sealed["normalizer"]["sha256"] == hashlib.sha256(normalizer.read_bytes()).hexdigest()
