import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from src.features.variable_contract import geometry_for_length
import src.ml.variable_waveform_cache as variable_cache
from src.ml.__main__ import build_argument_parser
from src.ml.variable_waveform_cache import (
    VARIABLE_WAVEFORM_ALIGNMENT_CONTRACT,
    VariableWaveformAlignmentReject,
    _match_pair_boundary,
    align_variable_waveform_windows,
    load_or_create_variable_waveform_cache,
    load_variable_waveform_cache_index,
    write_variable_waveform_cache_index,
)


def _sha(label):
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _example(length=2, split="train"):
    geometry = geometry_for_length(length)
    source_sha = _sha(f"source-{length}")
    target_sha = _sha(f"target-{length}")
    return {
        "dataset_format_version": 2,
        "feature_protocol_version": 2,
        "example_id": f"example-{length}",
        "candidate_id": f"candidate-{length}",
        "split": split,
        "transition_length_bars": length,
        "transition_length_beats": geometry.transition_length_beats,
        "sequence_length": geometry.sequence_length,
        "source_bpm": 120.0,
        "target_bpm": 120.0,
        "source_track": {"sha256": source_sha, "path": "source.wav"},
        "target_track": {"sha256": target_sha, "path": "target.wav"},
        "source_grid": {
            "format_version": 1,
            "grid_source": "verified-test-grid",
            "fallback_used": False,
            "beat_grid_sha256": _sha(f"source-grid-{length}"),
        },
        "target_grid": {
            "format_version": 1,
            "grid_source": "verified-test-grid",
            "fallback_used": False,
            "beat_grid_sha256": _sha(f"target-grid-{length}"),
        },
    }


def _stretch_to_expected(mix, vocal, **kwargs):
    expected = int(kwargs["expected_samples"])
    positions = np.linspace(0.0, 1.0, mix.shape[-1])
    target_positions = np.linspace(0.0, 1.0, expected)

    def stretch(value):
        return np.stack(
            [np.interp(target_positions, positions, value[channel]) for channel in range(2)]
        ).astype(np.float32)

    return (
        stretch(mix),
        stretch(vocal),
        {
            "backend": "synthetic_pitch_preserving_test",
            "backend_version": "test-v1",
            "rounding_correction": {"count": 0, "side": "start"},
        },
    )


@pytest.mark.parametrize("length", (2, 4, 6, 8))
def test_alignment_supports_all_lengths_and_four_way_shapes(length):
    geometry = geometry_for_length(length)
    source = np.zeros((2, 1000), dtype=np.float32)
    target = np.zeros((2, 800), dtype=np.float32)
    result = align_variable_waveform_windows(
        source,
        target,
        source.copy(),
        target.copy(),
        source_window=(0, 1000, geometry.transition_length_beats),
        target_window=(0, 800, geometry.transition_length_beats),
        source_bpm=120.0,
        target_bpm=120.0,
        render_sample_rate=1000,
        training_sample_rate=1000,
        time_stretch=None,
        stretch_pair=_stretch_to_expected,
        resampler=lambda value, _source, _target: value,
    )
    assert result.source_audio.shape == (2, 1000)
    assert result.source_audio.shape == result.target_audio.shape
    assert result.source_audio.shape == result.source_vocal_audio.shape
    assert result.source_audio.shape == result.target_vocal_audio.shape
    assert result.provenance["alignment_contract"] == VARIABLE_WAVEFORM_ALIGNMENT_CONTRACT
    assert result.provenance["raw_windows"]["declared_beats"] == geometry.transition_length_beats


def test_target_mix_and_vocal_receive_the_same_stretch_parameters():
    calls = []

    def stretcher(mix, vocal, **kwargs):
        calls.append(kwargs.copy())
        return _stretch_to_expected(mix, vocal, **kwargs)

    result = align_variable_waveform_windows(
        np.ones((2, 1000), dtype=np.float32),
        np.ones((2, 800), dtype=np.float32),
        np.ones((2, 1000), dtype=np.float32),
        np.ones((2, 800), dtype=np.float32),
        source_window=(0, 1000, 8),
        target_window=(0, 800, 8),
        source_bpm=120.0,
        target_bpm=120.0,
        render_sample_rate=1000,
        training_sample_rate=1000,
        time_stretch=None,
        stretch_pair=stretcher,
        resampler=lambda value, _source, _target: value,
    )
    assert len(calls) == 1
    assert calls[0]["tempo_factor"] == pytest.approx(0.8)
    assert result.target_audio.shape == result.target_vocal_audio.shape


def test_boundary_correction_preserves_source_start_and_target_cue_end():
    source = np.arange(10, dtype=np.float32)[None, :].repeat(2, axis=0)
    vocal = (100 + np.arange(10, dtype=np.float32))[None, :].repeat(2, axis=0)
    source_fixed, source_vocal_fixed = _match_pair_boundary(source, vocal, 9, "end", 2)
    target_fixed, target_vocal_fixed = _match_pair_boundary(source, vocal, 9, "start", 2)
    assert source_fixed[:, 0].tolist() == source[:, 0].tolist()
    assert target_fixed[:, -1].tolist() == source[:, -1].tolist()
    assert source_vocal_fixed[:, 0].tolist() == vocal[:, 0].tolist()
    assert target_vocal_fixed[:, -1].tolist() == vocal[:, -1].tolist()


def test_large_backend_residual_is_rejected():
    value = np.zeros((2, 100), dtype=np.float32)
    with pytest.raises(VariableWaveformAlignmentReject, match="rounding_residual_exceeds_tolerance"):
        _match_pair_boundary(value, value.copy(), 103, "start", 2)


def test_unreliable_grid_provenance_is_rejected(tmp_path):
    example = _example()
    example["source_grid"]["fallback_used"] = True
    with pytest.raises(VariableWaveformAlignmentReject, match="unreliable_grid_provenance"):
        load_or_create_variable_waveform_cache(
            example,
            dataset_id="dataset",
            dataset_manifest_sha256=_sha("dataset-manifest"),
            cache_root=tmp_path,
            build_missing=False,
        )


def test_cache_hit_corruption_provenance_and_atomic_publication(tmp_path):
    example = _example()
    arrays = {
        "source": np.zeros((2, 1000), dtype=np.float32),
        "target": np.ones((2, 1000), dtype=np.float32),
    }

    def audio_loader(_example, role, _geometry):
        return arrays[role]

    def vocal_loader(_example, role, _geometry):
        return arrays[role] * 0.5

    kwargs = {
        "dataset_id": "dataset",
        "dataset_manifest_sha256": _sha("dataset-manifest"),
        "cache_root": tmp_path,
        "audio_loader": audio_loader,
        "vocal_loader": vocal_loader,
    }
    first = load_or_create_variable_waveform_cache(example, **kwargs)
    assert first.cache_hit is False
    assert first.cache_directory.name
    assert first.manifest["waveforms"]["sample_rate"] == 11025
    assert not list(tmp_path.rglob("*.tmp"))
    second = load_or_create_variable_waveform_cache(example, **kwargs)
    assert second.cache_hit is True
    assert second.source_audio.shape == second.target_vocal_audio.shape

    (first.cache_directory / "waveforms.npz").write_bytes(b"corrupt")
    with pytest.raises(ValueError, match="cache entry is invalid"):
        load_or_create_variable_waveform_cache(example, **kwargs)

    with pytest.raises(ValueError, match="cache root provenance differs"):
        load_or_create_variable_waveform_cache(
            example,
            **{**kwargs, "dataset_id": "another-dataset"},
        )


def test_atomic_cache_publication_retries_transient_permission_error(tmp_path, monkeypatch):
    example = _example()
    arrays = {
        "source": np.zeros((2, 1000), dtype=np.float32),
        "target": np.ones((2, 1000), dtype=np.float32),
    }
    original_replace = variable_cache.os.replace
    calls = 0

    def fail_once_for_directory(source, destination):
        nonlocal calls
        if Path(source).is_dir():
            calls += 1
            if calls == 1:
                raise PermissionError("transient Windows scanner lock")
        return original_replace(source, destination)

    monkeypatch.setattr(variable_cache.os, "replace", fail_once_for_directory)
    artifact = load_or_create_variable_waveform_cache(
        example,
        dataset_id="dataset",
        dataset_manifest_sha256=_sha("dataset-manifest"),
        cache_root=tmp_path,
        audio_loader=lambda _example, role, _geometry: arrays[role],
        vocal_loader=lambda _example, role, _geometry: arrays[role] * 0.5,
    )

    assert calls == 2
    assert (artifact.cache_directory / "manifest.json").is_file()
    assert (artifact.cache_directory / "waveforms.npz").is_file()
    assert not list(tmp_path.rglob("*.tmp"))


def test_cache_index_binds_root_entry_and_payload_hashes(tmp_path):
    example = _example()
    arrays = {"source": np.zeros((2, 1000), dtype=np.float32), "target": np.ones((2, 1000), dtype=np.float32)}
    dataset_manifest = tmp_path / "dataset-manifest.json"
    dataset_manifest.write_text("{}\n", encoding="utf-8")
    dataset_sha = hashlib.sha256(dataset_manifest.read_bytes()).hexdigest()
    artifact = load_or_create_variable_waveform_cache(
        example,
        dataset_id="dataset",
        dataset_manifest_sha256=dataset_sha,
        cache_root=tmp_path / "cache",
        audio_loader=lambda _example, role, _geometry: arrays[role],
        vocal_loader=lambda _example, role, _geometry: arrays[role] * 0.5,
    )
    index = write_variable_waveform_cache_index(
        tmp_path / "cache",
        dataset_manifest_path=dataset_manifest,
        artifacts=(("train", 2, example, artifact),),
        splits=("train",),
        transition_lengths=(2,),
    )
    loaded = load_variable_waveform_cache_index(
        tmp_path / "cache",
        dataset_manifest_sha256=dataset_sha,
        required_splits=("train",),
        required_lengths=(2,),
    )
    assert loaded["payload"]["payload_sha256"] == index["payload_sha256"]
    assert loaded["entries"][example["example_id"]]["waveforms_sha256"]

    (artifact.cache_directory / "waveforms.npz").write_bytes(b"tampered")
    with pytest.raises(ValueError, match="payload hash differs"):
        load_variable_waveform_cache_index(
            tmp_path / "cache",
            dataset_manifest_sha256=dataset_sha,
            required_splits=("train",),
            required_lengths=(2,),
        )


def test_cache_is_separate_from_legacy_roots_and_cli_parses():
    parser = build_argument_parser()
    cache_args = parser.parse_args(
        ["cache-variable-waveforms", "dataset", "--transition-bars", "2", "4", "6", "8"]
    )
    train_args = parser.parse_args(
        ["train-variable-tcn-bilstm", "dataset", "run", "--device", "cuda:0", "--wandb-mode", "disabled"]
    )
    assert cache_args.command == "cache-variable-waveforms"
    assert cache_args.transition_bars == [2, 4, 6, 8]
    assert train_args.command == "train-variable-tcn-bilstm"
    assert train_args.device == "cuda:0"
