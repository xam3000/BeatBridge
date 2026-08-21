import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
import soundfile as sf

from src.analysis.models import AnalysisResult, BeatGridMetadata
from src.candidates import CandidateGenerationConfig, VariableCandidateGenerationConfig
from src.candidates.generation import generate_candidates
from src.multi_batch_render import (
    _candidate_generation_config,
    _deduplicate_tracks_by_sha256,
    _expand_song_paths,
    _filter_tracks_by_bpm,
    _normalise_transition_lengths,
    build_argument_parser,
    generate_multi_song_batch,
    main,
)
from src.pipeline import generate_transition_candidates


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


class SyntheticAnalysis:
    def __call__(self, song_path):
        info = sf.info(song_path)
        beat_step = info.samplerate // 2
        beats = tuple(
            (sample, index % 4 + 1, 4)
            for index, sample in enumerate(range(0, info.frames, beat_step))
        )
        return AnalysisResult(
            120.0,
            beats,
            BeatGridMetadata(
                grid_source="synthetic_detector",
                fallback_used=False,
                backend_version="synthetic_detector=1",
                confidence=1.0,
            ),
        )


def _write_synthetic_track(path, *, seconds=40, value=0.0):
    sf.write(path, np.full(44_100 * seconds, value, dtype=np.float32), 44_100)


def test_multi_batch_cli_parses_variable_lengths_and_preserves_default():
    parser = build_argument_parser()

    default_args = parser.parse_args(["source.wav", "target.wav", "--output-dir", "out"])
    assert tuple(default_args.transition_bars) == (2, 4)

    variable_args = parser.parse_args(
        [
            "source.wav",
            "target.wav",
            "--output-dir",
            "out",
            "--transition-bars",
            "2",
            "4",
            "6",
            "8",
        ]
    )
    assert tuple(variable_args.transition_bars) == (2, 4, 6, 8)


def test_multi_batch_uses_v2_config_only_when_variable_lengths_are_requested():
    assert isinstance(_candidate_generation_config((2, 4), approximate_grid_policy="reject"), CandidateGenerationConfig)
    assert not hasattr(
        _candidate_generation_config((2, 4), approximate_grid_policy="reject"),
        "format_version",
    )
    variable_config = _candidate_generation_config(
        (2, 4, 6, 8), approximate_grid_policy="reject"
    )
    assert isinstance(variable_config, VariableCandidateGenerationConfig)
    assert variable_config.transition_lengths_bars == (2, 4, 6, 8)


def test_multi_batch_passes_variable_lengths_to_every_pair_and_root_manifest(
    tmp_path, monkeypatch
):
    source = tmp_path / "source.wav"
    target = tmp_path / "target.wav"
    _write_synthetic_track(source)
    _write_synthetic_track(target, value=0.1)
    analysis = SyntheticAnalysis()
    captured_configs = []

    class Score:
        def __init__(self, target_path):
            self.target_path = str(target_path)
            self.rank = 1
            self.total_score = 1.0

    class Ranking:
        def __init__(self, target_path):
            self.scores = (Score(target_path),)

        def to_dict(self):
            return {"scores": [{"target_path": self.scores[0].target_path}]}

    monkeypatch.setattr("src.multi_batch_render.PreAnalysis", lambda *_args: analysis)
    monkeypatch.setattr(
        "src.multi_batch_render.rank_song_targets",
        lambda source_path, target_paths, **_kwargs: Ranking(target_paths[0]),
    )

    def fake_generate_and_render_batch(song1, song2, output_directory, *, candidate_config, **_kwargs):
        captured_configs.append(candidate_config)
        generation = generate_transition_candidates(
            song1,
            song2,
            analysis=analysis,
            config=candidate_config,
        )
        output_directory = Path(output_directory)
        output_directory.mkdir(parents=True, exist_ok=True)
        manifest_path = output_directory / "manifest.json"
        manifest_path.write_text(
            json.dumps({"candidate_generation": generation.to_dict()}, indent=2)
            + "\n",
            encoding="utf-8",
        )
        return SimpleNamespace(
            manifest_path=manifest_path,
            candidate_generation=generation,
            candidate_ranking=SimpleNamespace(scores=()),
            rendered_variants=(),
            failures=(),
            rendered_transition_ranking=SimpleNamespace(failures=()),
        )

    monkeypatch.setattr(
        "src.multi_batch_render.generate_and_render_batch",
        fake_generate_and_render_batch,
    )

    output_directory = tmp_path / "multi-batch"
    manifest_path = generate_multi_song_batch(
        [str(source), str(target)],
        output_directory,
        top_targets=1,
        top_transitions=1,
        renderers=("simple",),
        analysis_location=tmp_path / "analysis",
        transition_lengths_bars=(2, 4, 6, 8),
    )

    assert len(captured_configs) == 2
    assert all(
        isinstance(config, VariableCandidateGenerationConfig)
        and config.transition_lengths_bars == (2, 4, 6, 8)
        for config in captured_configs
    )
    root_manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    assert root_manifest["transition_lengths_bars"] == [2, 4, 6, 8]
    pair_manifests = list((output_directory / "pairs").glob("*/manifest.json"))
    assert len(pair_manifests) == 2
    for pair_manifest in pair_manifests:
        payload = json.loads(pair_manifest.read_text(encoding="utf-8"))
        lengths = {
            candidate["transition_length_bars"]
            for candidate in payload["candidate_generation"]["candidates"]
        }
        assert {2, 4, 6, 8}.issubset(lengths)


def test_multi_batch_shorter_lengths_survive_missing_eight_bar_context():
    result = generate_candidates(
        _track("source"),
        120.0,
        _grid(bar_count=14),
        _track("target"),
        120.0,
        _grid(bar_count=14),
        source_grid_metadata=_detected_grid_metadata(),
        target_grid_metadata=_detected_grid_metadata(),
        config=VariableCandidateGenerationConfig(
            transition_lengths_bars=_normalise_transition_lengths((2, 4, 6, 8))
        ),
    )

    assert {candidate.transition_length_bars for candidate in result.candidates} == {2, 4, 6}
    assert any(
        rejection.transition_length_bars == 8 for rejection in result.rejections
    )


def _track(name):
    from src.candidates import TrackReference

    return TrackReference(f"{name}.wav", name * 64)


def _grid(*, bar_count):
    return tuple(
        (bar * 4 * 22_050 + beat * 22_050, beat % 4 + 1, 4)
        for bar in range(bar_count)
        for beat in range(4)
    )


def _detected_grid_metadata():
    return BeatGridMetadata(
        grid_source="synthetic_detector",
        fallback_used=False,
        backend_version="synthetic_detector=1",
        confidence=1.0,
    )
