import hashlib
import json
import os
from pathlib import Path

import numpy as np
import soundfile as sf

from src.analysis.pre_analysis import (
    ANALYSIS_CACHE_FILENAME,
    ANALYSIS_CACHE_FORMAT_VERSION,
    ANALYSIS_CACHE_NAMESPACE,
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


def _stub_fallback_analysis(analysis, *, sample_rate=8_000):
    def load_song():
        analysis.song = np.zeros(sample_rate * 5, dtype=np.float32)
        analysis.sr = sample_rate

    def find_bpm():
        analysis.bpm = 120.0
        analysis.beat_frames = list(range(0, sample_rate * 5, sample_rate // 2))

    analysis.load_song = load_song
    analysis.find_bpm = find_bpm
    analysis.auftakt_analysis_comparison = lambda: None


def test_current_cache_is_hash_scoped_complete_and_atomic(tmp_path, monkeypatch):
    song = tmp_path / "song.wav"
    sf.write(song, np.zeros(8_000, dtype=np.float32), 8_000)
    analysis = PreAnalysis(tmp_path / "analysis")
    _stub_fallback_analysis(analysis)
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
    assert payload["result"]["grid_metadata"]["fallback_used"] is True
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
    _stub_fallback_analysis(analysis)

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
    _stub_fallback_analysis(analysis)

    result = analysis(song)

    assert result.grid_metadata.analysis_id == analysis.analysis_id
    assert result.grid_metadata.fallback_used is True
    assert (analysis.cache_directory / ANALYSIS_CACHE_FILENAME).is_file()


def test_analysis_contract_change_creates_a_new_cache_identity(tmp_path):
    song = tmp_path / "song.wav"
    sf.write(song, np.zeros(8_000, dtype=np.float32), 8_000)
    cache_root = tmp_path / "analysis"
    first = PreAnalysis(cache_root)
    _stub_fallback_analysis(first)
    first(song)

    changed = PreAnalysis(cache_root)
    changed.analysis_config = {
        **changed.analysis_config,
        "analysis_algorithm": "beatbridge_pre_analysis_test_changed",
    }
    changed.analysis_id = _analysis_id(changed.analysis_config)
    _stub_fallback_analysis(changed)
    changed(song)

    assert first.cache_directory != changed.cache_directory
    assert (first.cache_directory / ANALYSIS_CACHE_FILENAME).is_file()
    assert (changed.cache_directory / ANALYSIS_CACHE_FILENAME).is_file()


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
