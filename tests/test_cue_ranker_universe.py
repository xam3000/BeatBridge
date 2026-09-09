import hashlib
import json

import numpy as np
import pytest

from src.features.cue_ranker_universe import (
    _assign_sampling,
    build_cue_ranker_pair_index,
    build_cue_ranker_universe,
    canonical_json_sha256,
    load_cue_ranker_universe_rows,
    write_cue_ranker_pair_index,
)


def _sha(value):
    return hashlib.sha256(value.encode()).hexdigest()


def _candidate(source_sha, target_sha, identifier, bars, *, source_sample=100, target_sample=200):
    grid_a, grid_b = _sha("grid-a-" + identifier), _sha("grid-b-" + identifier)
    grid = lambda value: {"analysis_id": _sha("analysis-" + value), "backend_version": "synthetic", "beat_grid_sha256": value, "confidence": 1.0, "fallback_used": False, "format_version": 1, "grid_source": "synthetic_verified"}
    return {
        "format_version": 2, "candidate_id": identifier,
        "source_track": {"path": "source.wav", "sha256": source_sha},
        "target_track": {"path": "target.wav", "sha256": target_sha},
        "source_cutpoint": {"sample": source_sample, "beat_index": 4, "bar_index": 1, "count_in_bar": 1, "beats_in_bar": 4},
        "target_cutpoint": {"sample": target_sample, "beat_index": 12, "bar_index": 3, "count_in_bar": 1, "beats_in_bar": 4},
        "transition_length_bars": bars, "transition_length_beats": bars * 4,
        "generator": "bar_grid_v2_length_specific", "filter_status": "accepted",
        "source_grid": grid(grid_a), "target_grid": grid(grid_b),
    }


def _pair_manifest(path, candidates):
    config = {"format_version": 2, "candidate_generator": "bar_grid_v2_length_specific", "transition_lengths_bars": [2, 4, 6, 8], "source_boundary_count": None, "target_boundary_count": None, "max_tempo_relative_difference": 0.15, "approximate_grid_policy": "reject"}
    path.write_text(json.dumps({
        "candidate_generation": {"format_version": 2, "approximate_grid_policy": "reject", "candidates": candidates},
        "candidate_request_config": config,
        "candidate_request_config_sha256": canonical_json_sha256(config),
        "candidate_ranking": {"ranker": "feature_baseline_v3", "scores": [
            {"candidate_id": item["candidate_id"], "total_score": index / 10}
            for index, item in enumerate(candidates)
        ]},
    }), encoding="utf-8")


def _record(path, source, target, split):
    config = {"format_version": 2, "candidate_generator": "bar_grid_v2_length_specific", "transition_lengths_bars": [2, 4, 6, 8], "source_boundary_count": None, "target_boundary_count": None, "max_tempo_relative_difference": 0.15, "approximate_grid_policy": "reject"}
    return {"pair_manifest_path": str(path), "pair_manifest_sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "source_audio_sha256": source, "target_audio_sha256": target, "candidate_generator": "bar_grid_v2_length_specific", "candidate_request_config": config, "candidate_request_config_sha256": canonical_json_sha256(config)}


def test_complete_universe_has_stable_group_ids_variable_ragged_sizes_and_no_top_k(tmp_path):
    train_a, train_b, valid_a, valid_b = (_sha(name) for name in ("train-a", "train-b", "valid-a", "valid-b"))
    train_manifest, valid_manifest = tmp_path / "train.json", tmp_path / "valid.json"
    train_candidates = [_candidate(train_a, train_b, f"train-{i}", (2, 4, 6)[i % 3], source_sample=100 + i) for i in range(9)]
    valid_candidates = [_candidate(valid_a, valid_b, f"valid-{i}", 2 if i < 2 else 8, source_sample=400 + i) for i in range(3)]
    _pair_manifest(train_manifest, train_candidates)
    _pair_manifest(valid_manifest, valid_candidates)
    split_map = {train_a: "train", train_b: "train", valid_a: "validation", valid_b: "validation"}
    index = write_cue_ranker_pair_index([_record(valid_manifest, valid_a, valid_b, "validation"), _record(train_manifest, train_a, train_b, "train")], tmp_path / "pair_index.json", split_map=split_map)
    first = build_cue_ranker_universe(index, tmp_path / "universe-1", split_map=split_map, sampling_seed=7)
    second = build_cue_ranker_universe(index, tmp_path / "universe-2", split_map=split_map, sampling_seed=7)
    assert first.candidate_counts == {"train": 9, "validation": 3}
    first_rows, second_rows = load_cue_ranker_universe_rows(first.output_directory, "train"), load_cue_ranker_universe_rows(second.output_directory, "train")
    assert [(row["group_id"], row["candidate_id"], row["p_inclusion"]) for row in first_rows] == [(row["group_id"], row["candidate_id"], row["p_inclusion"]) for row in second_rows]
    assert len(first_rows) == 9  # not feature-baseline top-k
    with np.load(first.output_directory / "index" / "train-ragged-groups.npz", allow_pickle=False) as ragged:
        assert ragged["group_offsets"].tolist() == [0, 9]
    with np.load(first.output_directory / "index" / "validation-ragged-groups.npz", allow_pickle=False) as ragged:
        assert ragged["group_offsets"].tolist() == [0, 3]
    assert {row["sequence_length"] for row in first_rows} == {16, 32, 48}
    assert all(row["p_inclusion"] == 1.0 and row["label_selected"] for row in first_rows)
    assert any(row["hard_negative_anchor"] for row in first_rows)


def test_sealed_pair_index_never_opens_test_manifest_and_test_loader_is_refused(tmp_path):
    train_a, train_b, test_a, test_b = (_sha(name) for name in ("train-a", "train-b", "test-a", "test-b"))
    train_manifest = tmp_path / "train.json"
    _pair_manifest(train_manifest, [_candidate(train_a, train_b, "ok", 4)])
    missing_test_manifest = tmp_path / "must-never-open-test.json"
    mapping = {train_a: "train", train_b: "train", test_a: "test", test_b: "test"}
    index = write_cue_ranker_pair_index([
        _record(train_manifest, train_a, train_b, "train"),
        {"pair_manifest_path": str(missing_test_manifest), "pair_manifest_sha256": _sha("not-a-file"), "source_audio_sha256": test_a, "target_audio_sha256": test_b, "candidate_generator": "bar_grid_v2_length_specific", "candidate_request_config_sha256": _sha("test-request")},
    ], tmp_path / "pair_index.json", split_map=mapping)
    payload = json.loads(index.read_text(encoding="utf-8"))
    assert len(payload["pairs"]) == 1
    result = build_cue_ranker_universe(index, tmp_path / "universe", split_map=mapping)
    assert result.candidate_counts["train"] == 1
    with pytest.raises(ValueError, match="train and validation"):
        load_cue_ranker_universe_rows(result.output_directory, "test")
    assert not missing_test_manifest.exists()


def test_pair_index_requires_full_identity_and_split_map_hash(tmp_path):
    source, target = _sha("source"), _sha("target")
    path = tmp_path / "pair.json"
    first = _candidate(source, target, "collision", 2, source_sample=1)
    second = _candidate(source, target, "collision", 2, source_sample=2)
    _pair_manifest(path, [first, second])
    mapping = {source: "train", target: "train"}
    index = write_cue_ranker_pair_index([_record(path, source, target, "train")], tmp_path / "pair_index.json", split_map=mapping)
    with pytest.raises(ValueError, match="candidate_id_collision"):
        build_cue_ranker_universe(index, tmp_path / "bad-universe", split_map=mapping)
    assert canonical_json_sha256(mapping) != canonical_json_sha256({source: "validation", target: "validation"})


def test_quality_strata_sampling_is_deterministic_and_marks_listwise_hard_negatives():
    def rows():
        return [{"candidate_id": f"candidate-{index:04d}", "candidate_identity_sha256": _sha(f"identity-{index}"), "baseline_status": "scored" if index < 560 else "unscored", "feature_baseline_v3_score": index / 600 if index < 560 else None} for index in range(600)]
    first, second = rows(), rows()
    _assign_sampling(first, group_id=_sha("group"), seed=9)
    _assign_sampling(second, group_id=_sha("group"), seed=9)
    assert [(row["candidate_id"], row["label_selected"], row["p_inclusion"]) for row in first] == [(row["candidate_id"], row["label_selected"], row["p_inclusion"]) for row in second]
    selected = [row for row in first if row["label_selected"]]
    assert 0 < len(selected) < len(first)
    assert all(0.0 < row["p_inclusion"] <= 1.0 for row in selected)
    assert any(row["hard_negative_anchor"] for row in selected)
    assert any(row["sampling_stratum"] == "baseline_unscored" for row in selected)


def test_pair_index_cli_source_manifest_filters_test_before_child_open(tmp_path):
    train_a, train_b, test_a, test_b = (_sha(name) for name in ("train-a", "train-b", "test-a", "test-b"))
    train_pair = tmp_path / "train-pair.json"
    _pair_manifest(train_pair, [_candidate(train_a, train_b, "train", 2)])
    train_record = _record(train_pair, train_a, train_b, "train")
    test_record = {
        **train_record,
        "pair_manifest_path": str(tmp_path / "test-pair-must-not-open.json"),
        "pair_manifest_sha256": _sha("test-pair"),
        "source_audio_sha256": test_a,
        "target_audio_sha256": test_b,
    }
    source_manifest = tmp_path / "batch-manifest.json"
    source_manifest.write_text(json.dumps({
        "format_version": 1,
        "sources": [{
            "source_audio_sha256": train_a,
            "pairs": [
                {**train_record, "status": "completed"},
                {**test_record, "status": "completed"},
            ],
        }],
    }), encoding="utf-8")
    assignments = {train_a: "train", train_b: "train", test_a: "test", test_b: "test"}
    split_payload = {
        "format_version": 1,
        "source_manifest_sha256": hashlib.sha256(source_manifest.read_bytes()).hexdigest(),
        "mapping_sha256": canonical_json_sha256(assignments),
        "track_assignments": [
            {"sha256": key, "split": value} for key, value in sorted(assignments.items())
        ],
    }
    split_path = tmp_path / "split-map.json"
    split_path.write_text(json.dumps(split_payload), encoding="utf-8")
    index_path = tmp_path / "pair-index.json"
    from src.features.__main__ import main
    assert main(["build-cue-ranker-pair-index", str(source_manifest), str(index_path), "--split-map", str(split_path)]) == 0
    payload = json.loads(index_path.read_text(encoding="utf-8"))
    assert len(payload["pairs"]) == 1
    assert payload["source_manifest"]["sha256"] == hashlib.sha256(source_manifest.read_bytes()).hexdigest()
    assert payload["split_map"]["file_sha256"] == hashlib.sha256(split_path.read_bytes()).hexdigest()
    assert not (tmp_path / "test-pair-must-not-open.json").exists()
    result = build_cue_ranker_universe(index_path, tmp_path / "universe", split_map=split_path)
    assert result.candidate_counts == {"train": 1, "validation": 0}


def test_pair_index_rejects_incomplete_producer_provenance_before_any_child_open(tmp_path):
    source, target = _sha("source"), _sha("target")
    missing_pair = tmp_path / "missing-pair.json"
    with pytest.raises(ValueError, match="candidate_request_config_missing"):
        write_cue_ranker_pair_index(
            [{
                "pair_manifest_path": str(missing_pair),
                "pair_manifest_sha256": _sha("pair"),
                "source_audio_sha256": source,
                "target_audio_sha256": target,
                "candidate_generator": "bar_grid_v2_length_specific",
                "candidate_request_config_sha256": _sha("request"),
            }],
            tmp_path / "pair-index.json",
            split_map={source: "train", target: "train"},
        )
    assert not missing_pair.exists()
