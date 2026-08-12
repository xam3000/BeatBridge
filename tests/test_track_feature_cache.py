import json

import numpy as np
import pytest
import soundfile as sf

from src.analysis.models import AnalysisResult, BeatGridMetadata
from src.features import FEATURE_DIMENSION, SEQUENCE_LENGTH, feature_index
from src.features.extract_track import (
    FeatureNormalizationStats,
    extract_or_load_track_features,
    normalization_stats_from_training_artifacts,
)


class _Analysis:
    def __init__(self, sample_rate, beat_count=25, bpm=120.0):
        self.sample_rate = sample_rate
        self.beat_count = beat_count
        self.bpm = bpm

    def __call__(self, _):
        beat_samples = int(round(self.sample_rate * 60.0 / self.bpm))
        return self.bpm, [
            (index * beat_samples, index % 4 + 1, 4)
            for index in range(self.beat_count)
        ]


class _DetectedAnalysis(_Analysis):
    def __call__(self, path):
        bpm, beats = super().__call__(path)
        return AnalysisResult(
            bpm,
            tuple(beats),
            BeatGridMetadata(
                grid_source="test_detector",
                fallback_used=False,
                backend_version="test_detector=1",
                confidence=0.9,
            ),
        )


def _write_tone(path, *, sample_rate=8_000, seconds=13.0, frequency=220.0):
    time = np.arange(int(sample_rate * seconds), dtype=np.float32) / sample_rate
    audio = 0.2 * np.sin(2 * np.pi * frequency * time)
    sf.write(path, audio, sample_rate, subtype="FLOAT")


def test_full_track_features_are_cached_and_reused(tmp_path):
    song = tmp_path / "song.wav"
    _write_tone(song)
    analysis = _Analysis(8_000)

    first = extract_or_load_track_features(
        song,
        cache_root=tmp_path / "cache",
        analysis=analysis,
        sample_rate=8_000,
    )
    second = extract_or_load_track_features(
        song,
        cache_root=tmp_path / "cache",
        analysis=analysis,
        sample_rate=8_000,
    )

    assert first.cache_hit is False
    assert second.cache_hit is True
    assert first.cache_directory == second.cache_directory
    assert first.base_features.shape[1] == FEATURE_DIMENSION
    assert np.array_equal(first.base_features, second.base_features)
    assert (first.cache_directory / "manifest.json").is_file()
    assert (first.cache_directory / "track_features.npz").is_file()
    assert first.manifest["beat_grid_metadata"]["grid_source"] == "external_unknown"


def test_grid_provenance_changes_feature_cache_identity(tmp_path):
    song = tmp_path / "song.wav"
    _write_tone(song)

    unknown = extract_or_load_track_features(
        song,
        cache_root=tmp_path / "cache",
        analysis=_Analysis(8_000),
        sample_rate=8_000,
    )
    detected = extract_or_load_track_features(
        song,
        cache_root=tmp_path / "cache",
        analysis=_DetectedAnalysis(8_000),
        sample_rate=8_000,
    )

    assert unknown.cache_directory != detected.cache_directory
    assert detected.manifest["beat_grid_metadata"] == {
        "format_version": 1,
        "grid_source": "test_detector",
        "fallback_used": False,
        "backend_version": "test_detector=1",
        "confidence": 0.9,
    }


def test_audio_change_creates_a_different_cache_entry(tmp_path):
    song = tmp_path / "song.wav"
    analysis = _Analysis(8_000)
    _write_tone(song, frequency=220.0)
    first = extract_or_load_track_features(
        song,
        cache_root=tmp_path / "cache",
        analysis=analysis,
        sample_rate=8_000,
    )

    _write_tone(song, frequency=440.0)
    second = extract_or_load_track_features(
        song,
        cache_root=tmp_path / "cache",
        analysis=analysis,
        sample_rate=8_000,
    )

    assert second.cache_hit is False
    assert first.cache_directory != second.cache_directory


def test_cached_track_yields_contract_valid_source_and_target_windows(tmp_path):
    song = tmp_path / "song.wav"
    _write_tone(song)
    artifact = extract_or_load_track_features(
        song,
        cache_root=tmp_path / "cache",
        analysis=_Analysis(8_000),
        sample_rate=8_000,
    )
    stats = normalization_stats_from_training_artifacts(
        (artifact,),
        stats_id="train-split-test",
    )
    source_cue = int(artifact.bin_boundaries[4])
    target_cue = int(artifact.bin_boundaries[-4])

    source = artifact.model_window(
        source_cue,
        role="source",
        normalization=stats,
    )
    target = artifact.model_window(
        target_cue,
        role="target",
        normalization=stats,
    )

    assert source.shape == (SEQUENCE_LENGTH, FEATURE_DIMENSION)
    assert target.shape == (SEQUENCE_LENGTH, FEATURE_DIMENSION)
    assert source[0, feature_index("transition_position")] == pytest.approx(
        0.5 / SEQUENCE_LENGTH
    )
    assert source[-1, feature_index("transition_position")] == pytest.approx(
        31.5 / SEQUENCE_LENGTH
    )
    assert np.all(source[:, feature_index("vocal_valid")] == 0.0)
    assert np.all(source[:, feature_index("phrase_valid")] == 0.0)


def test_cache_manifest_records_missing_vocal_and_phrase_extractors(tmp_path):
    song = tmp_path / "song.wav"
    _write_tone(song)
    artifact = extract_or_load_track_features(
        song,
        cache_root=tmp_path / "cache",
        analysis=_Analysis(8_000),
        sample_rate=8_000,
    )

    manifest = json.loads(
        (artifact.cache_directory / "manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["extractor_components"]["vocal"] == "not_implemented"
    assert manifest["extractor_components"]["phrase"] == "not_implemented"
    assert manifest["feature_protocol_version"] == 1
    assert manifest["tempo_backend"] == "not_needed"


def test_window_requires_training_normalization_and_sufficient_context(tmp_path):
    song = tmp_path / "song.wav"
    _write_tone(song)
    artifact = extract_or_load_track_features(
        song,
        cache_root=tmp_path / "cache",
        analysis=_Analysis(8_000),
        sample_rate=8_000,
    )
    stats = FeatureNormalizationStats(1.0, 1.0, "fixed")

    with pytest.raises(ValueError, match="insufficient cached context"):
        artifact.model_window(
            int(artifact.bin_boundaries[2]),
            role="target",
            normalization=stats,
        )


def test_tempo_aligned_track_variant_is_cached_by_target_bpm(tmp_path):
    class _TempoAdjuster:
        def __init__(self, *, fail=False):
            self.fail = fail
            self.last_backend = None

        def adjust_tempo_to_bpm(
            self,
            audio,
            sample_rate,
            original_bpm,
            target_bpm,
        ):
            if self.fail:
                raise AssertionError("A cache hit must not run time stretching")
            output_count = int(round(audio.size * original_bpm / target_bpm))
            positions = np.linspace(0, audio.size - 1, output_count)
            self.last_backend = "fake_tempo_backend"
            return np.interp(positions, np.arange(audio.size), audio).astype(np.float32)

    song = tmp_path / "song.wav"
    _write_tone(song)
    analysis = _Analysis(8_000, bpm=120.0)
    first = extract_or_load_track_features(
        song,
        cache_root=tmp_path / "cache",
        analysis=analysis,
        sample_rate=8_000,
        target_bpm=100.0,
        tempo_adjuster=_TempoAdjuster(),
    )
    second = extract_or_load_track_features(
        song,
        cache_root=tmp_path / "cache",
        analysis=analysis,
        sample_rate=8_000,
        target_bpm=100.0,
        tempo_adjuster=_TempoAdjuster(fail=True),
    )

    assert first.cache_hit is False
    assert first.manifest["tempo_backend"] == "fake_tempo_backend"
    assert first.manifest["aligned_bpm"] == pytest.approx(100.0)
    assert second.cache_hit is True
    assert second.cache_directory == first.cache_directory
