import hashlib
import json
import shutil
from types import SimpleNamespace

import numpy as np
import torch

from src.features import FEATURE_DIMENSION, GLOBAL_FEATURE_DIMENSION, SEQUENCE_LENGTH
from src.ml import (
    FeatureControlDataset,
    collate_feature_control_examples,
    load_or_create_bridge_waveforms,
    load_or_create_vocal_bridge_waveforms,
)
import src.ml.data as ml_data


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _candidate():
    return {
        "candidate_id": "candidate-test",
        "source_track": {"path": "source.wav", "sha256": "a" * 64},
        "target_track": {"path": "target.wav", "sha256": "b" * 64},
        "source_cutpoint": {"sample": 1000},
        "target_cutpoint": {"sample": 2000},
        "source_bpm": 160.0,
        "target_bpm": 160.0,
        "transition_length_beats": 16,
        "transition_length_bars": 4,
    }


def _example(pair_manifest_path=None, pair_manifest_sha256=None):
    candidate = _candidate()
    return {
        "example_id": "example-test",
        "candidate_id": candidate["candidate_id"],
        "split": "train",
        "source_track": candidate["source_track"],
        "target_track": candidate["target_track"],
        "source_cutpoint": candidate["source_cutpoint"],
        "target_cutpoint": candidate["target_cutpoint"],
        "pair_manifest_path": None if pair_manifest_path is None else str(pair_manifest_path),
        "pair_manifest_sha256": pair_manifest_sha256,
    }


def _fake_bridge(candidate, analysis, *, sample_rate, include_context_audio):
    assert candidate["candidate_id"] == "candidate-test"
    assert sample_rate == 8_000
    assert not include_context_audio
    source = np.full((2, 800), 0.25, dtype=np.float32)
    target = np.full((2, 800), -0.25, dtype=np.float32)
    return source, target, {
        "sample_rate": sample_rate,
        "transition_samples": 800,
        "tempo_backend": "not_needed",
    }


def test_bridge_waveforms_are_written_once_and_reused(tmp_path):
    calls = []

    def extractor(*args, **kwargs):
        calls.append(1)
        return _fake_bridge(*args, **kwargs)

    first = load_or_create_bridge_waveforms(
        _example(),
        _candidate(),
        cache_root=tmp_path,
        training_sample_rate=4_000,
        render_sample_rate=8_000,
        analysis=object(),
        bridge_extractor=extractor,
        verify_audio_hashes=False,
    )
    second = load_or_create_bridge_waveforms(
        _example(),
        _candidate(),
        cache_root=tmp_path,
        training_sample_rate=4_000,
        render_sample_rate=8_000,
        analysis=object(),
        bridge_extractor=extractor,
        verify_audio_hashes=False,
    )

    assert calls == [1]
    assert not first.cache_hit
    assert second.cache_hit
    assert first.source_audio.shape == first.target_audio.shape == (2, 400)
    np.testing.assert_array_equal(first.source_audio, second.source_audio)
    assert (first.cache_directory / "manifest.json").is_file()
    assert (first.cache_directory / "bridge_waveforms.npz").is_file()


def test_concurrent_cache_publication_reuses_valid_winner(tmp_path, monkeypatch):
    def concurrent_replace(source, destination):
        shutil.copytree(source, destination)
        raise PermissionError("simulated Windows directory publication race")

    monkeypatch.setattr(ml_data.os, "replace", concurrent_replace)
    artifact = load_or_create_bridge_waveforms(
        _example(),
        _candidate(),
        cache_root=tmp_path,
        training_sample_rate=4_000,
        render_sample_rate=8_000,
        analysis=object(),
        bridge_extractor=_fake_bridge,
        verify_audio_hashes=False,
    )

    assert artifact.cache_hit
    assert artifact.cache_directory.is_dir()


def test_vocal_bridge_cache_stores_mix_and_stems_once(tmp_path):
    extraction_calls = []

    def vocal_loader(path, *, cache_root, source_sha256, model_name):
        return SimpleNamespace(
            manifest={"artifact_sha256": source_sha256},
            audio=np.zeros(800, dtype=np.float32),
            sample_rate=8_000,
        )

    def vocal_bridge_extractor(
        candidate,
        analysis,
        *,
        sample_rate,
        include_context_audio,
        source_vocal_artifact,
        target_vocal_artifact,
        **kwargs,
    ):
        extraction_calls.append(1)
        assert source_vocal_artifact.manifest["artifact_sha256"] == "a" * 64
        assert target_vocal_artifact.manifest["artifact_sha256"] == "b" * 64
        source = np.full((2, 800), 0.2, dtype=np.float32)
        target = np.full((2, 800), -0.2, dtype=np.float32)
        source_vocal = np.full((2, 800), 0.05, dtype=np.float32)
        target_vocal = np.full((2, 800), -0.05, dtype=np.float32)
        return source, target, source_vocal, target_vocal, {
            "transition_samples": 800,
            "tempo_backend": "not_needed",
            "vocal_tempo_backend": "not_needed",
        }

    kwargs = {
        "cache_root": tmp_path / "waveforms",
        "feature_cache_root": tmp_path / "features",
        "training_sample_rate": 4_000,
        "render_sample_rate": 8_000,
        "analysis": object(),
        "bridge_extractor": vocal_bridge_extractor,
        "vocal_stem_loader": vocal_loader,
        "verify_audio_hashes": False,
    }
    first = load_or_create_vocal_bridge_waveforms(_example(), _candidate(), **kwargs)
    second = load_or_create_vocal_bridge_waveforms(_example(), _candidate(), **kwargs)

    assert extraction_calls == [1]
    assert not first.cache_hit
    assert second.cache_hit
    assert first.source_audio.shape == first.source_vocal_audio.shape == (2, 400)
    np.testing.assert_array_equal(first.target_vocal_audio, second.target_vocal_audio)

    collated = collate_feature_control_examples(({
        "example_id": "example-test",
        "features_a": torch.from_numpy(np.zeros((32, 54), dtype=np.float32)),
        "features_b": torch.from_numpy(np.zeros((32, 54), dtype=np.float32)),
        "global_features": torch.from_numpy(np.zeros(16, dtype=np.float32)),
        "source_audio": torch.from_numpy(first.source_audio),
        "target_audio": torch.from_numpy(first.target_audio),
        "source_vocal_audio": torch.from_numpy(first.source_vocal_audio),
        "target_vocal_audio": torch.from_numpy(first.target_vocal_audio),
        "waveform_cache_hit": False,
    },))
    assert len(collated["source_vocal_audio"]) == 1


def test_feature_control_dataset_joins_npz_metadata_candidate_and_audio_cache(tmp_path):
    candidate = _candidate()
    pair_manifest_path = tmp_path / "pair_manifest.json"
    pair_manifest_path.write_text(
        json.dumps(
            {"candidate_generation": {"candidates": [candidate]}},
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    example = _example(pair_manifest_path, _sha256(pair_manifest_path))
    examples_path = tmp_path / "examples.jsonl"
    examples_path.write_text(json.dumps(example) + "\n", encoding="utf-8")
    train_path = tmp_path / "train.npz"
    np.savez_compressed(
        train_path,
        example_ids=np.asarray([example["example_id"]]),
        features_a=np.zeros((1, SEQUENCE_LENGTH, FEATURE_DIMENSION), dtype=np.float32),
        features_b=np.zeros((1, SEQUENCE_LENGTH, FEATURE_DIMENSION), dtype=np.float32),
        global_features=np.zeros((1, GLOBAL_FEATURE_DIMENSION), dtype=np.float32),
    )
    (tmp_path / "manifest.json").write_text(
        json.dumps(
            {
                "dataset_id": "dataset-test",
                "files": {
                    "train": {"sha256": _sha256(train_path)},
                    "examples": {"sha256": _sha256(examples_path)},
                },
            }
        ),
        encoding="utf-8",
    )
    waveform_root = tmp_path / "waveforms"
    dataset = FeatureControlDataset(
        tmp_path,
        "train",
        waveform_cache_root=waveform_root,
        training_sample_rate=4_000,
        render_sample_rate=8_000,
        build_missing_waveforms=True,
        analysis=object(),
        bridge_extractor=_fake_bridge,
        verify_audio_hashes=False,
    )

    item = dataset[0]

    assert item["example_id"] == "example-test"
    assert item["features_a"].shape == (SEQUENCE_LENGTH, FEATURE_DIMENSION)
    assert item["global_features"].shape == (GLOBAL_FEATURE_DIMENSION,)
    assert item["source_audio"].shape == item["target_audio"].shape == (2, 400)
    assert not item["waveform_cache_hit"]

    cached_dataset = FeatureControlDataset(
        tmp_path,
        "train",
        waveform_cache_root=waveform_root,
        training_sample_rate=4_000,
        render_sample_rate=8_000,
        build_missing_waveforms=False,
        bridge_extractor=lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("cache hit must not extract audio")
        ),
        verify_audio_hashes=False,
    )
    assert cached_dataset[0]["waveform_cache_hit"]
