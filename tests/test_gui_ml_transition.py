import hashlib
import json
from types import SimpleNamespace

import librosa
import numpy as np
import pytest
import soundfile as sf
import torch

from src.analysis.models import AnalysisResult, BeatGridMetadata
from src.features import FEATURE_DIMENSION, GLOBAL_FEATURE_DIMENSION, SEQUENCE_LENGTH, feature_schema
from src.gui import ml_transition
from src.ml.inference_contract import load_fixed_inference_contract


def _write_manifest(path, payload):
    raw = json.dumps(payload).encode()
    path.write_bytes(raw)
    return {"path": str(path), "sha256": hashlib.sha256(raw).hexdigest()}


def _run_contract(tmp_path, *, dataset_overrides=None, backend="roformer", model="contract-stem-model"):
    dataset = {
        "dataset_id": "training-dataset",
        "format_version": 1,
        "feature_protocol_version": 1,
        "global_pair_extractor_version": 1,
        "sample_rate": 44_100,
        "transition_bars": 4,
        "vocal_backend": "demucs",
        "vocal_model": "htdemucs",
        "feature_schema": feature_schema(),
        "normalization": {
            "stats_id": "train-example",
            "fit_scope": "training_tracks_only",
            "spectral_flux_log1p_p99": 0.3,
            "onset_strength_log1p_p99": 0.25,
        },
    }
    dataset.update(dataset_overrides or {})
    manifest = _write_manifest(tmp_path / "manifest.json", dataset)
    waveform = {"format_version": 2, "vocal_model": model}
    if backend is not None:
        waveform["vocal_backend"] = backend
    stem_manifest = _write_manifest(tmp_path / "stems.json", waveform)
    return {
        "dataset": {
            "dataset_id": "training-dataset",
            "path": str(tmp_path),
            "manifest_sha256": manifest["sha256"],
            "vocal_waveform_cache_manifests": {"train": [stem_manifest]},
        },
        "model": {"name": "vocal_time_shared_mlp_v2", "config": {"hidden_dimensions": [8]}},
        "waveform_cache": {"vocal_model": model},
        "renderer": {
            "sample_rate": 11_025,
            "control_protocol_version": 4,
            "lowpass_cutoff_hz": 180,
            "lowpass_kernel_size": 127,
        },
    }


@pytest.mark.parametrize(
    "source_bpm,target_bpm,expected_target",
    [(150.0, 120.0, 282_240), (120.0, 150.0, 441_000), (120.0, 120.0, 352_800)],
)
def test_gui_feature_and_waveform_contract_at_model_entry(
    tmp_path, monkeypatch, source_bpm, target_bpm, expected_target,
):
    run_contract = _run_contract(tmp_path)
    family = run_contract["model"]["name"]
    paths = (tmp_path / "source.wav", tmp_path / "target.wav")
    for path in paths:
        sf.write(path, np.zeros(100, dtype=np.float32), 48_000)
    calls = []
    windows = []

    def analysis(path):
        calls.append(path)
        return AnalysisResult(
            bpm=source_bpm if path == str(paths[0]) else target_bpm,
            beat_frames=((384_000, 1, 4),),
            grid_metadata=BeatGridMetadata("fallback_from_detected_beats", True, "synthetic", 0.0),
        )

    def load_features(path, *, target_bpm, analysis, sample_rate, vocal_backend, vocal_model, **kwargs):
        assert (vocal_backend, vocal_model) == ("demucs", "htdemucs")
        bpm = analysis(path).bpm

        def model_window(cue, *, role, normalization):
            windows.append((role, cue))
            assert normalization.stats_id == "train-example"
            assert normalization.spectral_flux_log1p_p99 == 0.3
            assert normalization.onset_strength_log1p_p99 == 0.25
            return np.zeros((SEQUENCE_LENGTH, FEATURE_DIMENSION), dtype=np.float32)

        return SimpleNamespace(
            cache_directory=tmp_path,
            manifest={
                "feature_protocol_version": 1,
                "sample_rate": sample_rate,
                "original_bpm": bpm,
                "aligned_bpm": bpm if target_bpm is None else target_bpm,
                "vocal_backend": vocal_backend,
                "vocal_model": vocal_model,
            },
            model_window=model_window,
        )

    def global_features(_a, _b, *, cue_sample_a, cue_sample_b, **kwargs):
        assert (cue_sample_a, cue_sample_b) == (352_800, expected_target)
        return np.zeros(GLOBAL_FEATURE_DIMENSION, dtype=np.float32)

    def bridge(candidate, analysis, *, sample_rate, vocal_backend, vocal_model, **kwargs):
        assert (vocal_backend, vocal_model) == ("roformer", "contract-stem-model")
        assert analysis(paths[0]).bpm == candidate["source_bpm"] == source_bpm
        assert analysis(paths[1]).bpm == candidate["target_bpm"] == target_bpm
        assert candidate["target_cutpoint"]["sample"] == 352_800
        context = np.zeros((2, 20 * sample_rate), dtype=np.float32)
        window = context[:, :512]
        return window, window, window, window, {
            "transition_samples": 512,
            "source_cut_sample": 352_800,
            "target_cut_sample": expected_target,
            "source_audio": context,
            "target_audio": context,
            "tempo_backend": "stub",
        }

    def model(features_a, features_b, global_features):
        assert features_a.shape == features_b.shape == (SEQUENCE_LENGTH, FEATURE_DIMENSION)
        assert global_features.shape == (GLOBAL_FEATURE_DIMENSION,)
        curve = torch.linspace(0, 1, SEQUENCE_LENGTH)
        return SimpleNamespace(
            mix_position=curve, low_end_position=curve, vocal_position=curve,
            vocal_duck_a=torch.zeros_like(curve), vocal_duck_b=torch.zeros_like(curve),
        )

    run = ml_transition._ModelRun(
        model, family, {"contract": run_contract}, tmp_path / "run.json",
        {"run_manifest_sha256": "run", "checkpoint_path": "ckpt", "checkpoint_sha256": "ckpt", "checkpoint_epoch": 1},
    )
    monkeypatch.setattr(ml_transition, "_load_model_run", lambda path: run)
    monkeypatch.setitem(vars(librosa), "get_samplerate", lambda path: sf.info(path).samplerate)
    monkeypatch.setattr("src.features.extract_or_load_track_features", load_features)
    monkeypatch.setattr("src.features.build_global_pair_features", global_features)
    monkeypatch.setattr("src.bridge.extract_aligned_vocal_bridge", bridge)

    result, provenance = ml_transition.render_model_transition(
        *paths, source_seconds=8.05, target_seconds=8.05, source_bpm=None, target_bpm=None,
        transition_bars=4, analysis=analysis, analysis_cache=tmp_path, feature_cache=tmp_path,
        model_run=tmp_path,
    )
    assert result.transition_end_sample - result.transition_start_sample == 512
    assert windows == [("source", 352_800), ("target", expected_target)]
    assert calls == list(map(str, paths))
    assert provenance["source_grid"]["fallback_used"] is True
    assert provenance["preview_renderer"]["lowpass_kernel_size"] == 511


@pytest.mark.parametrize("bars", [1, 2, 3])
def test_fixed_model_rejects_other_baseline_lengths(tmp_path, bars):
    with pytest.raises(ValueError, match="requested transition_bars"):
        load_fixed_inference_contract(_run_contract(tmp_path), transition_bars=bars)


def test_legacy_demucs_waveforms_resolve_from_bound_format_2_manifest(tmp_path):
    run = _run_contract(tmp_path, backend=None, model="htdemucs")
    contract = load_fixed_inference_contract(run, transition_bars=4)
    assert contract.waveform_vocals == contract.feature_vocals
    assert contract.waveform_vocals.backend == "demucs"


@pytest.mark.parametrize(
    "dataset_overrides,requested_bars,field",
    [
        ({"dataset_id": "other"}, 4, "dataset.dataset_id"),
        ({"feature_protocol_version": 2}, 4, "dataset.feature_protocol_version"),
        ({"sample_rate": 22_050}, 4, "dataset.sample_rate"),
        ({"vocal_backend": "unknown"}, 4, "dataset.vocal_backend"),
        ({"normalization": {"fit_scope": "validation"}}, 4, "dataset.normalization.fit_scope"),
        ({}, 2, "requested transition_bars"),
    ],
)
def test_incompatible_dataset_reports_contract_field(tmp_path, dataset_overrides, requested_bars, field):
    run = _run_contract(tmp_path, dataset_overrides=dataset_overrides)
    with pytest.raises(ValueError, match=field):
        load_fixed_inference_contract(run, transition_bars=requested_bars)


def test_bound_waveform_backend_conflict_is_explicit(tmp_path):
    run = _run_contract(tmp_path)
    run["waveform_cache"]["vocal_backend"] = "demucs"
    with pytest.raises(ValueError, match="stems.json.vocal_backend.*demucs.*roformer"):
        load_fixed_inference_contract(run, transition_bars=4)


def test_modified_dataset_manifest_is_rejected_before_using_contract(tmp_path):
    run = _run_contract(tmp_path)
    manifest = tmp_path / "manifest.json"
    manifest.write_bytes(manifest.read_bytes() + b"\n")
    with pytest.raises(ValueError, match="manifest.json SHA-256"):
        load_fixed_inference_contract(run, transition_bars=4)


def test_incompatible_vocal_feature_artifact_is_rejected_before_inference(tmp_path):
    contract = load_fixed_inference_contract(_run_contract(tmp_path), transition_bars=4)
    artifact = SimpleNamespace(manifest={
        "feature_protocol_version": 1,
        "sample_rate": 44_100,
        "original_bpm": 120.0,
        "aligned_bpm": 150.0,
        "vocal_backend": "roformer",
        "vocal_model": "other-model",
    })
    with pytest.raises(ValueError, match="target features.vocal_backend.*demucs.*roformer"):
        contract.validate_track_features(artifact, role="target", original_bpm=120.0, aligned_bpm=150.0)
