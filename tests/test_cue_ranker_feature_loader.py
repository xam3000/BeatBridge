import hashlib
import json

import numpy as np
import pytest
from torch.utils.data import DataLoader

from src.features.contract import feature_index
from src.ml.cue_ranker_data import CueRankerGroupedDataset, collate_cue_ranker_groups
from src.ml.cue_ranker_runner import CueRankerTrainingConfig, train_cue_ranker


def _sha_bytes(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_records(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(path, row_json=np.asarray([json.dumps(row, sort_keys=True, separators=(",", ":")) for row in rows], dtype=str))


def _record(path, root):
    return {"path": str(path.relative_to(root)), "sha256": _sha_bytes(path), "bytes": path.stat().st_size}


def _candidate(source, target, index, bars):
    digest = hashlib.sha256(f"candidate-{index}-{bars}".encode()).hexdigest()
    grid = lambda name: {"format_version": 1, "analysis_id": hashlib.sha256(name.encode()).hexdigest(), "beat_grid_sha256": hashlib.sha256((name + "-grid").encode()).hexdigest(), "backend_version": "synthetic", "grid_source": "synthetic_verified", "confidence": 1.0, "fallback_used": False}
    return {
        "format_version": 2, "candidate_id": f"{index}-{bars}", "generator": "bar_grid_v2_length_specific", "filter_status": "accepted",
        "source_track": {"path": "never-open-source.wav", "sha256": source}, "target_track": {"path": "never-open-target.wav", "sha256": target},
        "source_cutpoint": {"sample": 2000, "bar_index": 3, "count_in_bar": 1, "beats_in_bar": 4},
        "target_cutpoint": {"sample": 8000, "bar_index": 12, "count_in_bar": 1, "beats_in_bar": 4},
        "source_grid": grid(f"source-{index}"), "target_grid": grid(f"target-{index}"),
        "source_bpm": 128.0, "target_bpm": 128.0,
        "transition_length_bars": bars, "transition_length_beats": bars * 4,
        "identity": digest,
    }


def _feature_cache(root, audio_sha, bpm):
    directory = root / "feature_protocol_v2" / audio_sha[:16] / "synthetic"
    directory.mkdir(parents=True)
    base = np.zeros((130, 54), dtype=np.float32)
    base[:, feature_index("audio_valid")] = 1.0
    base[:, feature_index("beat_pulse_confidence")] = 1.0
    boundaries = np.arange(131, dtype=np.int64) * 100
    data = directory / "track_features.npz"
    np.savez_compressed(data, base_features=base, bin_boundaries=boundaries, spectral_flux_raw=np.ones(130, dtype=np.float32), onset_strength_raw=np.ones(130, dtype=np.float32))
    manifest = {"format_version": 1, "source_sha256": audio_sha, "sample_rate": 44100, "aligned_bpm": bpm, "data_file": data.name, "cache_id": "synthetic"}
    manifest_path = directory / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    return _sha_bytes(data), _sha_bytes(manifest_path)


def _synthetic_dataset(root):
    cache = root / "cache"
    universe_root, labels_root, dataset = root / "universe", root / "labels", root / "dataset"
    source_train, target_train = (hashlib.sha256(value.encode()).hexdigest() for value in ("source-train", "target-train"))
    source_valid, target_valid = (hashlib.sha256(value.encode()).hexdigest() for value in ("source-valid", "target-valid"))
    cache_hashes = {
        source_train: _feature_cache(cache, source_train, 128.0), target_train: _feature_cache(cache, target_train, 128.0),
        source_valid: _feature_cache(cache, source_valid, 128.0), target_valid: _feature_cache(cache, target_valid, 128.0),
    }
    normalizer_source = root / "normalizer-source.json"
    normalizer_source.write_text(json.dumps({"fit_scope": "training_tracks_only", "stats_id": "synthetic", "spectral_flux_log1p_p99": 1.0, "onset_strength_log1p_p99": 1.0}), encoding="utf-8")
    normalizer_source_sha = _sha_bytes(normalizer_source)
    split_rows, labels = {}, {}
    for split, source, target in (("train", source_train, target_train), ("validation", source_valid, target_valid)):
        rows = []
        for index, bars in enumerate((2, 4, 6, 8)):
            candidate = _candidate(source, target, split, bars)
            row = {"row_id": index, "split": split, "group_id": f"group-{split}", "candidate_id": candidate["candidate_id"], "candidate_identity_sha256": candidate["identity"], "candidate": candidate, "source_audio_sha256": source, "target_audio_sha256": target, "transition_length_bars": bars, "transition_length_beats": bars * 4, "sequence_length": bars * 8, "length_condition": bars / 8, "label_selected": True, "p_inclusion": 1.0}
            rows.append(row)
        split_rows[split] = rows
        labels[split] = [{"group_id": row["group_id"], "candidate_id": row["candidate_id"], "candidate_identity_sha256": row["candidate_identity_sha256"], "teacher_status": "scored", "teacher_utility": float(i), "teacher_provenance": {"normalizer_sha256": normalizer_source_sha, "source_feature_payload_sha256": cache_hashes[source][0], "source_feature_manifest_sha256": cache_hashes[source][1], "target_feature_payload_sha256": cache_hashes[target][0], "target_feature_manifest_sha256": cache_hashes[target][1]}} for i, row in enumerate(rows)]
    universe_files, label_files = {}, {}
    for split in ("train", "validation"):
        upath, lpath = universe_root / "index" / f"{split}.npz", labels_root / "teacher" / f"{split}.npz"
        _write_records(upath, split_rows[split]); _write_records(lpath, labels[split])
        universe_files[f"{split}_candidates"] = _record(upath, universe_root)
        label_files[f"{split}_teacher_labels"] = _record(lpath, labels_root)
    universe_manifest = {"format_version": 1, "files": universe_files, "test": {"state": "sealed_not_materialized"}}
    universe_path = universe_root / "manifest.json"; universe_path.write_text(json.dumps(universe_manifest), encoding="utf-8")
    labels_manifest = {"universe_manifest_sha256": _sha_bytes(universe_path), "files": label_files, "test": {"state": "sealed_not_materialized"}}
    labels_path = labels_root / "manifest.json"; labels_path.write_text(json.dumps(labels_manifest), encoding="utf-8")
    dataset_files = {}
    for split in ("train", "validation"):
        rows = [dict(row, **label) for row, label in zip(split_rows[split], labels[split], strict=True)]
        cpath = dataset / "index" / f"{split}-candidates.npz"; _write_records(cpath, rows)
        gpath = dataset / "groups" / f"{split}.jsonl"; gpath.parent.mkdir(parents=True, exist_ok=True); gpath.write_text(json.dumps({"group_id": f"group-{split}", "member_row_ids": [0, 1, 2, 3], "universe_size": 99}) + "\n", encoding="utf-8")
        rpath = dataset / "index" / f"{split}-ragged.npz"; np.savez_compressed(rpath, group_ids=np.asarray([f"group-{split}"], dtype=str), group_offsets=np.asarray([0, 4]), member_row_ids=np.asarray([0, 1, 2, 3]))
        dataset_files[f"{split}_candidates"] = _record(cpath, dataset); dataset_files[f"{split}_groups"] = _record(gpath, dataset); dataset_files[f"{split}_ragged_groups"] = _record(rpath, dataset)
    normalizer = {"format_version": 1, "fit_scope": "training_tracks_only", "stats_id": "synthetic", "spectral_flux_log1p_p99": 1.0, "onset_strength_log1p_p99": 1.0, "input_universe_manifest_sha256": _sha_bytes(universe_path), "training_audio_sha256": [source_train, target_train], "source_sha256": normalizer_source_sha}
    npath = dataset / "normalization" / "train_only_stats.json"; npath.parent.mkdir(parents=True); npath.write_text(json.dumps(normalizer), encoding="utf-8"); dataset_files["train_only_normalizer"] = _record(npath, dataset)
    manifest = {"format_version": 3, "universe_manifest_sha256": _sha_bytes(universe_path), "teacher_manifest_sha256": _sha_bytes(labels_path), "normalization": {"fit_scope": "training_tracks_only", "sha256": _sha_bytes(npath)}, "inputs": {"universe_manifest": {"path": str(universe_path), "sha256": _sha_bytes(universe_path)}, "teacher_manifest": {"path": str(labels_path), "sha256": _sha_bytes(labels_path)}, "train_only_normalizer_source": {"path": str(normalizer_source), "sha256": normalizer_source_sha}}, "files": dataset_files, "test": {"state": "sealed_not_materialized"}}
    mpath = dataset / "manifest.json"; dataset.mkdir(exist_ok=True); mpath.write_text(json.dumps(manifest), encoding="utf-8")
    return dataset, cache


def test_format3_feature_loader_trains_all_variable_lengths_and_rejects_tampering(tmp_path):
    dataset_root, cache = _synthetic_dataset(tmp_path)
    train = CueRankerGroupedDataset(dataset_root, "train", feature_cache_root=cache)
    validation = CueRankerGroupedDataset(dataset_root, "validation", feature_cache_root=cache)
    assert [member["features_a"].shape[0] for member in train[0]["members"]] == [16, 32, 48, 64]
    assert train[0]["members"][0]["candidate_context"][8].item() == pytest.approx(np.log1p(99))
    result = train_cue_ranker(DataLoader(train, batch_size=1, collate_fn=collate_cue_ranker_groups), DataLoader(validation, batch_size=1, collate_fn=collate_cue_ranker_groups), tmp_path / "run", dataset_manifest_sha256=_sha_bytes(dataset_root / "manifest.json"), config=CueRankerTrainingConfig(max_epochs=1, device="cpu"))
    assert result.last_epoch == 1
    (cache / "feature_protocol_v2").rglob("track_features.npz").__next__().write_bytes(b"tampered")
    with pytest.raises(ValueError, match="sha_reference_unresolved"):
        CueRankerGroupedDataset(dataset_root, "train", feature_cache_root=cache)[0]


def test_format3_loader_rejects_test_split(tmp_path):
    dataset_root, cache = _synthetic_dataset(tmp_path)
    with pytest.raises(ValueError, match="only train and validation"):
        CueRankerGroupedDataset(dataset_root, "test", feature_cache_root=cache)


def test_format3_loader_proves_train_only_normalizer_scope(tmp_path):
    dataset_root, cache = _synthetic_dataset(tmp_path)
    normalizer_path = dataset_root / "normalization" / "train_only_stats.json"
    normalizer = json.loads(normalizer_path.read_text(encoding="utf-8"))
    normalizer["training_audio_sha256"].append(hashlib.sha256(b"source-valid").hexdigest())
    normalizer_path.write_text(json.dumps(normalizer), encoding="utf-8")
    manifest_path = dataset_root / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["files"]["train_only_normalizer"]["sha256"] = _sha_bytes(normalizer_path)
    manifest["normalization"]["sha256"] = _sha_bytes(normalizer_path)
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="normalizer_leakage_or_scope_mismatch"):
        CueRankerGroupedDataset(dataset_root, "train", feature_cache_root=cache)


@pytest.mark.parametrize("target, message", [
    ("universe/manifest.json", "universe_manifest_sha_mismatch"),
    ("labels/manifest.json", "teacher_manifest_sha_mismatch"),
    ("normalizer-source.json", "normalizer_source_sha_mismatch"),
])
def test_format3_loader_rejects_tampered_input_chain(tmp_path, target, message):
    dataset_root, cache = _synthetic_dataset(tmp_path)
    (tmp_path / target).write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match=message):
        CueRankerGroupedDataset(dataset_root, "train", feature_cache_root=cache)


def test_train_cue_ranker_cli_has_no_testsplit_and_runs_cpu(tmp_path, monkeypatch):
    from src.ml import __main__ as cli

    dataset_root, cache = _synthetic_dataset(tmp_path)
    parser = cli.build_argument_parser()
    cue_parser = next(action.choices["train-cue-ranker"] for action in parser._actions if isinstance(getattr(action, "choices", None), dict) and "train-cue-ranker" in action.choices)
    assert "--test" not in {option for action in cue_parser._actions for option in action.option_strings}
    cli_run = tmp_path / "cli-run"
    monkeypatch.setattr("sys.argv", ["python", "train-cue-ranker", str(dataset_root), str(cli_run), "--feature-cache-root", str(cache), "--max-epochs", "1", "--device", "cpu", "--wandb-mode", "offline"])
    assert cli.main() == 0
    assert all((cli_run / name).is_file() for name in ("best.pt", "latest.pt", "history.json", "manifest.json"))
    assert (cli_run / "wandb").is_dir()
