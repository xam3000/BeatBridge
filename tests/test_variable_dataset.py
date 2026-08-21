import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from src.features import FEATURE_DIMENSION
from src.features.__main__ import build_argument_parser
from src.features.extract_track import TrackFeatureArtifact
from src.features.variable_dataset_export import (
    _select_variable_candidate_records,
    export_variable_feature_dataset,
)
from src.features.variable_split import canonical_mapping_sha256
from src.ml.variable_data import (
    VariableFeatureControlDataset,
    VariableFeatureDataset,
    VariableFeatureDatasetCollection,
    VariableLengthBatchSampler,
    collate_variable_feature_examples,
)


def _sha(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _candidate(source, target, source_sha, target_sha, bars, variant=0):
    candidate_id = f"candidate-{bars}-{variant}-{source_sha[:8]}-{target_sha[:8]}"
    return {
        "format_version": 2,
        "candidate_id": candidate_id,
        "source_track": {"path": str(source), "sha256": source_sha},
        "target_track": {"path": str(target), "sha256": target_sha},
        "source_cutpoint": {"sample": 20 + variant, "beat_index": 4, "bar_index": 1, "count_in_bar": 1, "beats_in_bar": 4},
        "target_cutpoint": {"sample": 80 + variant, "beat_index": 16, "bar_index": 4, "count_in_bar": 1, "beats_in_bar": 4},
        "transition_length_bars": bars,
        "transition_length_beats": bars * 4,
        "source_bpm": 120.0,
        "target_bpm": 120.0,
        "tempo_relative_difference": 0.0,
        "generator": "synthetic-v2",
        "filter_status": "accepted",
    }


def _write_source_manifest(path, pairs, *, variants=1):
    candidates = []
    scores = []
    rank = 1
    for source, target, source_sha, target_sha in pairs:
        for bars in (2, 4, 6, 8):
            for variant in range(variants):
                candidate = _candidate(source, target, source_sha, target_sha, bars, variant)
                candidates.append(candidate)
                scores.append({"candidate_id": candidate["candidate_id"], "rank": rank, "total_score": 1.0 - rank / 100.0})
                rank += 1
    path.write_text(
        json.dumps(
            {
                "format_version": 2,
                "candidate_generation": {"format_version": 2, "candidates": candidates, "rejections": []},
                "candidate_ranking": {"format_version": 2, "ranker": "synthetic", "scores": scores, "failures": []},
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )


def _fake_loader_factory(expected_hashes):
    artifacts = {}

    def loader(path, *, source_sha256=None, **kwargs):
        key = str(path)
        source_sha256 = expected_hashes[key]
        if key not in artifacts:
            base = np.zeros((120, FEATURE_DIMENSION), dtype=np.float32)
            base[:, 40] = 1.0
            artifacts[key] = TrackFeatureArtifact(
                cache_directory=Path("synthetic-cache") / Path(path).stem,
                manifest={
                    "cache_id": Path(path).stem,
                    "source_sha256": source_sha256,
                    "aligned_bpm": 120.0,
                    "sample_rate": 44_100,
                },
                base_features=base,
                bin_boundaries=np.arange(121, dtype=np.int64),
                spectral_flux_raw=np.ones(120, dtype=np.float32),
                onset_strength_raw=np.ones(120, dtype=np.float32),
                cache_hit=True,
            )
        return artifacts[key]

    return loader


def _mapping(pairs):
    mapping = {}
    for index, (_, _, source_sha, target_sha) in enumerate(pairs):
        split = ("train", "validation", "test")[index]
        mapping[source_sha] = split
        mapping[target_sha] = split
    return mapping


def test_variable_dataset_export_writes_all_lengths_and_reuses_one_split_map(tmp_path):
    pairs = [
        (tmp_path / "train_a.wav", tmp_path / "train_b.wav", _sha("train-a"), _sha("train-b")),
        (tmp_path / "validation_a.wav", tmp_path / "validation_b.wav", _sha("validation-a"), _sha("validation-b")),
        (tmp_path / "test_a.wav", tmp_path / "test_b.wav", _sha("test-a"), _sha("test-b")),
    ]
    source_manifest = tmp_path / "batch.json"
    _write_source_manifest(source_manifest, pairs)
    mapping = _mapping(pairs)
    expected_hashes = {
        str(path): sha
        for pair in pairs
        for path, sha in ((pair[0], pair[2]), (pair[1], pair[3]))
    }
    loader = _fake_loader_factory(expected_hashes)
    result = export_variable_feature_dataset(
        source_manifest,
        tmp_path / "dataset-1",
        transition_lengths_bars=(2, 4, 6, 8),
        top_k_per_pair=1,
        split_authority=mapping,
        track_feature_loader=loader,
        vocal_backend="disabled",
    )
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert result.example_count == 12
    assert manifest["format_version"] == 2
    assert manifest["supported_lengths"] == [2, 4, 6, 8]
    assert manifest["split_authority"]["mapping_sha256"] == canonical_mapping_sha256(mapping)
    assert manifest["normalization"]["fit_scope"] == "training_tracks_only"
    assert len(manifest["track_assignments"]) == 6
    for bars, sequence_length in ((2, 16), (4, 32), (6, 48), (8, 64)):
        for split in ("train", "validation", "test"):
            shard = manifest["shards"][str(bars)][split]
            assert shard["count"] == 1
            assert shard["empty"] is False
            npz = tmp_path / "dataset-1" / manifest["files"][shard["npz_file"]]["path"]
            with np.load(npz, allow_pickle=False) as payload:
                assert payload["features_a"].shape == (1, sequence_length, 54)
                assert payload["features_b"].shape == (1, sequence_length, 54)
                assert payload["global_features"].shape == (1, 16)
                assert payload["length_condition"].shape == (1, 1)
                assert payload["transition_length_bars"].tolist() == [bars]
                assert payload["sequence_length"].tolist() == [sequence_length]
                assert payload["length_condition"][0, 0] == pytest.approx(bars / 8)
            assert hashlib.sha256(npz.read_bytes()).hexdigest() == manifest["files"][shard["npz_file"]]["sha256"]

    dataset = VariableFeatureDataset(tmp_path / "dataset-1", 6, "validation")
    item = dataset[0]
    batch = collate_variable_feature_examples([item])
    assert item["features_a"].shape == (48, 54)
    assert batch["features_a"].shape == (1, 48, 54)
    assert batch["transition_length_bars"] == 6

    result2 = export_variable_feature_dataset(
        source_manifest,
        tmp_path / "dataset-2",
        transition_lengths_bars=(2, 4, 6, 8),
        top_k_per_pair=1,
        split_authority=mapping,
        track_feature_loader=_fake_loader_factory(expected_hashes),
        vocal_backend="disabled",
    )
    manifest2 = json.loads(result2.manifest_path.read_text(encoding="utf-8"))
    assert manifest2["dataset_id"] == manifest["dataset_id"]
    assert manifest2["shards"] == manifest["shards"]
    assert manifest2["files"] == manifest["files"]


def test_variable_dataset_documents_empty_length_shards(tmp_path):
    source = tmp_path / "source.wav"
    target = tmp_path / "target.wav"
    source_sha, target_sha = _sha("source"), _sha("target")
    manifest = tmp_path / "batch.json"
    _write_source_manifest(manifest, [(source, target, source_sha, target_sha)])
    result = export_variable_feature_dataset(
        manifest,
        tmp_path / "dataset-empty",
        transition_lengths_bars=(2, 4, 6, 8),
        split_authority={source_sha: "train", target_sha: "train"},
        split_config=__import__("src.features.dataset_export", fromlist=["SplitConfig"]).SplitConfig(train=1.0, validation=0.0, test=0.0),
        track_feature_loader=_fake_loader_factory({str(source): source_sha, str(target): target_sha}),
        vocal_backend="disabled",
    )
    payload = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    for bars in (2, 4, 6, 8):
        for split in ("validation", "test"):
            shard = payload["shards"][str(bars)][split]
            assert shard["count"] == 0
            assert shard["empty"] is True
            assert shard["empty_reason"]


def test_variable_selection_limits_top_k_per_pair_and_length(tmp_path):
    manifest = tmp_path / "ranked.json"
    source = tmp_path / "source.wav"
    target = tmp_path / "target.wav"
    source_sha, target_sha = _sha("source-topk"), _sha("target-topk")
    _write_source_manifest(
        manifest,
        [(source, target, source_sha, target_sha)],
        variants=2,
    )
    records = _select_variable_candidate_records(
        (manifest,),
        lengths=(2, 4, 6, 8),
        top_k_per_pair=1,
    )
    assert len(records) == 4
    assert {record.transition_length_bars for record in records} == {2, 4, 6, 8}


def test_variable_dataset_cli_accepts_multiple_lengths():
    args = build_argument_parser().parse_args(
        [
            "export-dataset-v2",
            "batch.json",
            "dataset-v2",
            "--transition-bars",
            "2",
            "4",
            "6",
            "8",
        ]
    )
    assert args.command == "export-dataset-v2"
    assert tuple(args.transition_bars) == (2, 4, 6, 8)


def test_variable_collection_and_waveform_batches_remain_length_homogeneous(tmp_path):
    source = tmp_path / "source.wav"
    target = tmp_path / "target.wav"
    source_sha, target_sha = _sha("collection-source"), _sha("collection-target")
    source_manifest = tmp_path / "collection.json"
    _write_source_manifest(
        source_manifest,
        [(source, target, source_sha, target_sha)],
        variants=2,
    )
    result = export_variable_feature_dataset(
        source_manifest,
        tmp_path / "collection-dataset",
        transition_lengths_bars=(2, 4, 6, 8),
        top_k_per_pair=2,
        split_authority={source_sha: "train", target_sha: "train"},
        split_config=__import__("src.features.dataset_export", fromlist=["SplitConfig"]).SplitConfig(
            train=1.0, validation=0.0, test=0.0
        ),
        track_feature_loader=_fake_loader_factory(
            {str(source): source_sha, str(target): target_sha}
        ),
        vocal_backend="disabled",
    )
    dataset = VariableFeatureDatasetCollection(result.output_directory, "train")
    assert set(dataset.indices_by_length()) == {2, 4, 6, 8}
    assert all(len(indices) == 2 for indices in dataset.indices_by_length().values())
    sampler = VariableLengthBatchSampler(dataset, batch_size=2, shuffle=False)
    batches = list(sampler)
    assert len(batches) == 4
    assert all(
        len({dataset[index]["transition_length_bars"] for index in batch}) == 1
        for batch in batches
    )

    def waveform_loader(example, geometry):
        samples = 128 + int(example["candidate_id"].split("-")[2]) * 16
        waveform = np.zeros((2, samples), dtype=np.float32)
        return {"source_audio": waveform, "target_audio": waveform.copy()}

    control_dataset = VariableFeatureControlDataset(
        result.output_directory,
        "train",
        waveform_loader=waveform_loader,
    )
    first_batch = [control_dataset[index] for index in batches[0]]
    collated = collate_variable_feature_examples(first_batch)
    assert collated["features_a"].shape == (2, 16, FEATURE_DIMENSION)
    assert len(collated["source_audio"]) == 2
    assert collated["source_audio_lengths"][0] != collated["source_audio_lengths"][1]
