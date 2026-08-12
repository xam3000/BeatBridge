import json
from pathlib import Path

import pytest

from src.multi_batch_render import (
    _deduplicate_tracks_by_sha256,
    _expand_song_paths,
    _filter_tracks_by_bpm,
    main,
)


class _Analysis:
    def __init__(self, bpms):
        self.bpms = bpms

    def __call__(self, path):
        value = self.bpms[str(path)]
        if isinstance(value, Exception):
            raise value
        return value, []


def test_directory_input_expands_supported_audio_recursively(tmp_path):
    nested = tmp_path / "nested"
    nested.mkdir()
    first = tmp_path / "first.flac"
    second = nested / "second.wav"
    ignored = nested / "notes.txt"
    for path in (first, second, ignored):
        path.write_bytes(b"")

    expanded = _expand_song_paths((tmp_path,))

    assert expanded == tuple(str(path) for path in sorted((first, second)))


def test_multi_batch_bpm_filter_is_inclusive_and_records_failures():
    paths = ("low.flac", "minimum.flac", "maximum.flac", "high.flac", "broken.flac")
    analysis = _Analysis(
        {
            "low.flac": 144.9,
            "minimum.flac": 145.0,
            "maximum.flac": 165.0,
            "high.flac": 165.1,
            "broken.flac": RuntimeError("analysis failed"),
        }
    )

    included, excluded, failures = _filter_tracks_by_bpm(
        paths,
        analysis,
        minimum_bpm=145.0,
        maximum_bpm=165.0,
    )

    assert included == ("minimum.flac", "maximum.flac")
    assert [item["reason"] for item in excluded] == [
        "below_minimum_bpm",
        "above_maximum_bpm",
    ]
    assert failures == [
        {
            "path": "broken.flac",
            "error_type": "RuntimeError",
            "message": "analysis failed",
        }
    ]


def test_identical_audio_files_are_deduplicated_by_content(tmp_path):
    first = tmp_path / "first.flac"
    duplicate = tmp_path / "duplicate.flac"
    different = tmp_path / "different.flac"
    first.write_bytes(b"same audio")
    duplicate.write_bytes(b"same audio")
    different.write_bytes(b"different audio")

    unique, duplicates = _deduplicate_tracks_by_sha256((first, duplicate, different))

    assert unique == (first, different)
    assert len(duplicates) == 1
    assert duplicates[0]["path"] == str(duplicate)
    assert duplicates[0]["same_audio_as"] == str(first)


def _stub_multi_batch(monkeypatch, manifest_path, payload):
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setattr(
        "src.multi_batch_render.generate_multi_song_batch",
        lambda *args, **kwargs: manifest_path,
    )


@pytest.mark.parametrize("stage", ("pair", "source"))
def test_multi_batch_cli_returns_nonzero_for_recorded_failures(
    tmp_path,
    monkeypatch,
    capsys,
    stage,
):
    manifest_path = tmp_path / "manifest.json"
    _stub_multi_batch(
        monkeypatch,
        manifest_path,
        {"failures": [{"stage": stage}], "bpm_filter": {"analysis_failures": []}},
    )

    exit_code = main(
        ["source.wav", "target.wav", "--output-dir", str(tmp_path / "output")]
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert str(manifest_path) in captured.out
    assert "1 recorded failure" in captured.err


def test_multi_batch_cli_returns_nonzero_for_bpm_analysis_failures(
    tmp_path,
    monkeypatch,
):
    manifest_path = tmp_path / "manifest.json"
    _stub_multi_batch(
        monkeypatch,
        manifest_path,
        {"failures": [], "bpm_filter": {"analysis_failures": [{"path": "bad.wav"}]}},
    )

    assert main(
        ["source.wav", "target.wav", "--output-dir", str(tmp_path / "output")]
    ) == 1


def test_multi_batch_cli_propagates_nested_render_and_metric_failures(
    tmp_path,
    monkeypatch,
):
    manifest_path = tmp_path / "manifest.json"
    _stub_multi_batch(
        monkeypatch,
        manifest_path,
        {
            "failures": [],
            "bpm_filter": {"analysis_failures": []},
            "sources": [
                {
                    "pairs": [
                        {
                            "status": "completed",
                            "render_failure_count": 1,
                            "transition_metric_failure_count": 2,
                        }
                    ]
                }
            ],
        },
    )

    assert main(
        ["source.wav", "target.wav", "--output-dir", str(tmp_path / "output")]
    ) == 1


def test_multi_batch_cli_returns_zero_without_recorded_failures(
    tmp_path,
    monkeypatch,
):
    manifest_path = tmp_path / "manifest.json"
    _stub_multi_batch(
        monkeypatch,
        manifest_path,
        {"failures": [], "bpm_filter": {"analysis_failures": []}},
    )

    assert main(
        ["source.wav", "target.wav", "--output-dir", str(tmp_path / "output")]
    ) == 0
