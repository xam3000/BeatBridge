import hashlib
import json
import os
from pathlib import Path
import subprocess

import numpy as np
import pytest
import soundfile as sf

from src.analysis.models import BeatGridMetadata
from src.analysis.pre_analysis import (
    ANALYSIS_CACHE_FILENAME,
    ANALYSIS_CACHE_FORMAT_VERSION,
    ANALYSIS_CACHE_NAMESPACE,
    FALLBACK_ANALYSIS_CACHE_FILENAME,
    RECOVERED_ANALYSIS_CACHE_FILENAME,
    PartialPreAnalysis,
    PreAnalysis,
    _analysis_id,
)


def test_legacy_cache_is_marked_unknown_without_mutating_legacy_artifact(tmp_path):
    song = tmp_path / "legacy.wav"
    sf.write(song, np.zeros(8_000, dtype=np.float32), 8_000)
    cache_root = tmp_path / "analysis"
    cache_directory = cache_root / song.stem
    cache_directory.mkdir(parents=True)
    digest = hashlib.sha256(song.read_bytes()).hexdigest()
    beat_lines = "\n".join(
        f"{index * 1000},{index % 4 + 1},4" for index in range(8)
    )
    (cache_directory / "00_pre_analysis.txt").write_text(
        f"{digest}\n120.0\n{beat_lines}\n",
        encoding="utf-8",
    )

    result = PreAnalysis(str(cache_root) + os.sep)(song)

    assert result.grid_metadata.grid_source == "legacy_cache_unknown"
    assert result.grid_metadata.fallback_used is None
    assert result.grid_metadata.analysis_id is None
    assert set(path.name for path in cache_directory.iterdir()) == {"00_pre_analysis.txt"}


def _stub_librosa_analysis(analysis, *, sample_rate=8_000):
    def load_song():
        analysis.song = np.zeros(sample_rate * 20, dtype=np.float32)
        analysis.sr = sample_rate

    def find_bpm():
        analysis.bpm = 120.0
        analysis.beat_frames = list(range(0, sample_rate * 20, sample_rate // 2))

    analysis.load_song = load_song
    analysis.find_bpm = find_bpm


def _stub_verified_analysis(analysis):
    _stub_librosa_analysis(analysis)

    def merge():
        analysis.beat_frames = [
            (sample, index % 4 + 1, 4)
            for index, sample in enumerate(analysis.beat_frames)
        ]
        analysis.grid_metadata = BeatGridMetadata(
            grid_source="auftakt_matched_to_librosa",
            fallback_used=False,
            backend_version="synthetic",
            confidence=1.0,
        )

    analysis.auftakt_analysis_comparison = merge


def test_current_cache_is_hash_scoped_complete_and_atomic(tmp_path, monkeypatch):
    song = tmp_path / "song.wav"
    sf.write(song, np.zeros(8_000, dtype=np.float32), 8_000)
    analysis = PreAnalysis(tmp_path / "analysis")
    _stub_verified_analysis(analysis)
    replacements = []
    real_replace = os.replace

    def record_replace(source, target):
        replacements.append((Path(source), Path(target)))
        return real_replace(source, target)

    monkeypatch.setattr("src.analysis.pre_analysis.os.replace", record_replace)

    result = analysis(song)

    digest = hashlib.sha256(song.read_bytes()).hexdigest()
    cache_path = (
        tmp_path
        / "analysis"
        / ANALYSIS_CACHE_NAMESPACE
        / digest
        / analysis.analysis_id
        / ANALYSIS_CACHE_FILENAME
    )
    payload = json.loads(cache_path.read_text(encoding="utf-8"))
    assert replacements and replacements[-1][1] == cache_path
    assert not list(cache_path.parent.glob(".*.tmp"))
    assert payload["format_version"] == ANALYSIS_CACHE_FORMAT_VERSION
    assert payload["source_audio"]["sha256"] == digest
    assert payload["analysis_config"]["analysis_algorithm"] == "beatbridge_pre_analysis_v2"
    assert payload["analysis_config"]["beat_backend"]["library_version"]
    assert "binary_sha256" in payload["analysis_config"]["bar_backend"]
    assert payload["result"]["grid_metadata"]["fallback_used"] is False
    assert result.grid_metadata.analysis_id == analysis.analysis_id
    assert result.grid_metadata.beat_grid_sha256


def test_same_stem_with_different_audio_uses_distinct_cache_directories(tmp_path):
    first = tmp_path / "one" / "same.wav"
    second = tmp_path / "two" / "same.wav"
    first.parent.mkdir()
    second.parent.mkdir()
    sf.write(first, np.zeros(8_000, dtype=np.float32), 8_000)
    sf.write(second, np.ones(8_000, dtype=np.float32) * 0.1, 8_000)
    analysis = PreAnalysis(tmp_path / "analysis")
    _stub_verified_analysis(analysis)

    analysis(first)
    first_directory = analysis.cache_directory
    analysis(second)
    second_directory = analysis.cache_directory

    assert first_directory != second_directory
    assert first_directory.parent.name == hashlib.sha256(first.read_bytes()).hexdigest()
    assert second_directory.parent.name == hashlib.sha256(second.read_bytes()).hexdigest()
    assert (first_directory / ANALYSIS_CACHE_FILENAME).is_file()
    assert (second_directory / ANALYSIS_CACHE_FILENAME).is_file()


def test_stale_legacy_cache_does_not_taint_fresh_v2_provenance(tmp_path):
    song = tmp_path / "song.wav"
    sf.write(song, np.zeros(8_000, dtype=np.float32), 8_000)
    legacy_directory = tmp_path / "analysis" / song.stem
    legacy_directory.mkdir(parents=True)
    (legacy_directory / "00_pre_analysis.txt").write_text(
        "wrong-audio-hash\n120.0\n0,1,4\n",
        encoding="utf-8",
    )
    analysis = PreAnalysis(tmp_path / "analysis")
    _stub_verified_analysis(analysis)

    result = analysis(song)

    assert result.grid_metadata.analysis_id == analysis.analysis_id
    assert result.grid_metadata.fallback_used is False
    assert (analysis.cache_directory / ANALYSIS_CACHE_FILENAME).is_file()


def test_analysis_contract_change_creates_a_new_cache_identity(tmp_path):
    song = tmp_path / "song.wav"
    sf.write(song, np.zeros(8_000, dtype=np.float32), 8_000)
    cache_root = tmp_path / "analysis"
    first = PreAnalysis(cache_root)
    _stub_verified_analysis(first)
    first(song)

    changed = PreAnalysis(cache_root)
    changed.analysis_config = {
        **changed.analysis_config,
        "analysis_algorithm": "beatbridge_pre_analysis_test_changed",
    }
    changed.analysis_id = _analysis_id(changed.analysis_config)
    _stub_verified_analysis(changed)
    changed(song)

    assert first.cache_directory != changed.cache_directory
    assert (first.cache_directory / ANALYSIS_CACHE_FILENAME).is_file()
    assert (changed.cache_directory / ANALYSIS_CACHE_FILENAME).is_file()


@pytest.mark.parametrize("analysis_class", [PreAnalysis, PartialPreAnalysis])
@pytest.mark.parametrize("historical_fallback", [False, True])
def test_auftakt_failure_then_detection_retries_and_preserves_history(
    tmp_path, monkeypatch, analysis_class, historical_fallback,
):
    song = tmp_path / "retry.wav"
    song.write_bytes(b"synthetic audio identity")
    cache_root = tmp_path / "analysis"
    analysis = analysis_class(cache_root)
    _stub_librosa_analysis(analysis)
    monkeypatch.setattr("src.analysis.pre_analysis.tmp_folder", tmp_path / "work")
    calls = []
    if historical_fallback:
        _stub_verified_analysis(analysis)
        analysis(song)
        historical_path = analysis.cache_directory / ANALYSIS_CACHE_FILENAME
        payload = json.loads(historical_path.read_bytes())
        payload["result"]["grid_metadata"].update(
            fallback_used=True, grid_source="fallback_from_detected_beats",
        )
        historical_bytes = json.dumps(payload).encode()
        historical_path.write_bytes(historical_bytes)
        analysis = analysis_class(cache_root)
        _stub_librosa_analysis(analysis)
        assert analysis.load_cached_analysis(song).grid_metadata.fallback_used is True

    def run_auftakt(command, *, check):
        assert check
        calls.append(command)
        if len(calls) == 1:
            raise subprocess.CalledProcessError(1, command)
        lines = ["aufTAKT header"] + [
            f"{index / 2},{(index + 1) % 4 + 1},4" for index in range(40)
        ]
        Path(command[-1]).write_text("\n".join(lines), encoding="utf-8")

    monkeypatch.setattr("src.analysis.pre_analysis.subprocess.run", run_auftakt)
    fallback = analysis(song)
    assert fallback.grid_metadata.fallback_used is True
    assert fallback.beat_frames[0][1] == 1
    assert analysis.merge_diagnostics["error_type"] == "CalledProcessError"
    if not historical_fallback:
        assert not (analysis.cache_directory / ANALYSIS_CACHE_FILENAME).exists()
        assert analysis.load_cached_analysis(song) == fallback
    fallback_path = analysis.cache_directory / FALLBACK_ANALYSIS_CACHE_FILENAME
    assert fallback_path.is_file()
    fallback_bytes = fallback_path.read_bytes()
    analysis.find_bpm = lambda: pytest.fail("Retry should reuse the cached librosa positions")

    detected = analysis(song)
    assert detected.grid_metadata.is_verified_detection
    assert detected.beat_frames[0][1] == 2
    assert detected.grid_metadata.beat_grid_sha256 != fallback.grid_metadata.beat_grid_sha256
    assert detected.grid_metadata.analysis_id == fallback.grid_metadata.analysis_id
    assert analysis_class(cache_root).load_cached_analysis(song) == detected
    assert analysis_class(cache_root)(song) == detected
    assert len(calls) == 2
    assert fallback_path.read_bytes() == fallback_bytes
    if historical_fallback:
        assert historical_path.read_bytes() == historical_bytes
        assert (analysis.cache_directory / RECOVERED_ANALYSIS_CACHE_FILENAME).is_file()


def test_documented_auftakt_hash_matches_tracked_binary():
    project_root = Path(__file__).resolve().parents[1]
    executable = project_root / "aufTAKTCl.exe"
    provenance = json.loads(
        (project_root / "config" / "auftakt_binary_provenance.json").read_text(
            encoding="utf-8"
        )
    )

    assert provenance["sha256"] == hashlib.sha256(executable.read_bytes()).hexdigest()
    assert provenance["size_bytes"] == executable.stat().st_size
    assert provenance["embedded_file_version"] is None
    assert provenance["redistribution_status"] == (
        "unverified_do_not_assume_distribution_rights"
    )
