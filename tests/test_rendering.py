from pathlib import Path
import subprocess
import sys

import numpy as np
import pytest
import soundfile as sf

from src.cutting.equal_power_fade_cut import EqualPowerFadeCut
from src.cutting.fade_cut import FadeCut
from src.cutting.simple_cut import SimpleCut
from src.pipeline import (
    BeatBridgePipeline,
    RENDER_RESULT_FORMAT_VERSION,
    main,
    render_transition,
)
from src.candidates import CutPoint, TrackReference, TransitionCandidate
from src.tempo.simple_tempo_adjust import SimpleTempoAdjust
from src.tempo.time_stretch import TimeStretch
from src.variable_rendering import render_variable_transition


class StubAnalysis:
    def __init__(self, bpms):
        self.bpms = {str(Path(path)): float(bpm) for path, bpm in bpms.items()}

    def __call__(self, song_path):
        song_path = str(Path(song_path))
        bpm = self.bpms[song_path]
        info = sf.info(song_path)
        beat_step = int(round(info.samplerate * 60.0 / bpm))
        beats = [
            (sample, index % 4 + 1, 4)
            for index, sample in enumerate(range(0, info.frames, beat_step))
        ]
        return bpm, beats


@pytest.fixture
def synthetic_tracks(tmp_path):
    inputs = tmp_path / "originals"
    inputs.mkdir()
    song1 = inputs / "song1.wav"
    song2 = inputs / "song2.wav"
    duration_seconds = 4
    sr1 = 44_100
    sr2 = 48_000
    time1 = np.arange(sr1 * duration_seconds, dtype=np.float32) / sr1
    time2 = np.arange(sr2 * duration_seconds, dtype=np.float32) / sr2
    stereo = np.column_stack(
        [
            0.1 * np.sin(2 * np.pi * 220 * time1),
            0.1 * np.sin(2 * np.pi * 330 * time1),
        ]
    )
    mono = 0.1 * np.sin(2 * np.pi * 440 * time2)
    sf.write(song1, stereo, sr1)
    sf.write(song2, mono, sr2)

    return {
        "song1": song1,
        "song2": song2,
        "analysis": StubAnalysis({song1: 120.0, song2: 100.0}),
        "cutpoint1": int(2.0 * 44_100),
        "cutpoint2": int(2.4 * 44_100),
    }


@pytest.mark.parametrize("source", ["song1", "song2"])
@pytest.mark.parametrize("alias", ["direct", "relative", "hardlink", "symlink"])
def test_cli_rejects_original_output_before_rendering(synthetic_tracks, tmp_path, monkeypatch, source, alias):
    tracks = [synthetic_tracks[name] for name in ("song1", "song2")]
    before = [path.read_bytes() for path in tracks]
    original = synthetic_tracks[source]
    monkeypatch.chdir(tmp_path)
    output = original
    if alias == "relative":
        output = original.relative_to(tmp_path)
    elif alias == "hardlink":
        output = tmp_path / "link.wav"
        output.hardlink_to(original)
    elif alias == "symlink":
        output = tmp_path / "link.wav"
        try:
            output.symlink_to(original)
        except OSError as error:
            if getattr(error, "winerror", None) != 1314:
                raise
            # Windows without link privilege still supports directory junctions.
            junction = tmp_path / "linked-directory"
            subprocess.run(["cmd", "/c", "mklink", "/J", str(junction), str(original.parent)], check=True)
            output = junction / original.name
    monkeypatch.setattr(sys, "argv", ["pipeline", *map(str, tracks), "0", "0", "simple", "-o", str(output)])
    monkeypatch.setattr("src.pipeline.render_transition", lambda *a, **kw: pytest.fail("render started"))
    with pytest.raises(ValueError, match="overwrite an input"):
        main()
    assert [path.read_bytes() for path in tracks] == before


def test_pipeline_writer_protects_inputs_and_saves_a_separate_preview(synthetic_tracks, tmp_path):
    source, target = (synthetic_tracks[key] for key in ("song1", "song2"))
    pipeline = BeatBridgePipeline(source, target, synthetic_tracks["analysis"], TimeStretch(), SimpleCut())
    output = tmp_path / "preview.wav"
    output.hardlink_to(target)
    before = target.read_bytes()
    with pytest.raises(ValueError, match="overwrite an input"):
        pipeline.save_song(output, pipeline.song1)
    assert target.read_bytes() == before
    output.unlink()
    pipeline.save_song(output, pipeline.song1[:, :1024])
    assert sf.info(output).frames == 1024


def test_pipeline_normalises_sample_rate_channels_and_beat_grid(synthetic_tracks):
    pipeline = BeatBridgePipeline(
        synthetic_tracks["song1"],
        synthetic_tracks["song2"],
        synthetic_tracks["analysis"],
        TimeStretch(),
        SimpleCut(),
    )

    assert pipeline.sr1 == 44_100
    assert pipeline.sr2 == 44_100
    assert pipeline.song1.shape[0] == 2
    assert pipeline.song2.shape[0] == 2
    assert pipeline.beat_frames2[1][0] == 26_460


@pytest.mark.parametrize(
    "renderer",
    ["simple", "fade", "equal_power", "tempo_fade"],
)
def test_rendering_baseline_returns_finite_stereo(synthetic_tracks, renderer):
    result = render_transition(
        synthetic_tracks["song1"],
        synthetic_tracks["song2"],
        synthetic_tracks["cutpoint1"],
        synthetic_tracks["cutpoint2"],
        renderer=renderer,
        fade_beats=2,
        analysis=synthetic_tracks["analysis"],
        tempo_adjuster=SimpleTempoAdjust(),
    )

    assert result.format_version == RENDER_RESULT_FORMAT_VERSION
    assert result.source_grid.grid_source == "external_unknown"
    assert result.target_grid.grid_source == "external_unknown"
    assert result.renderer == renderer
    assert result.sample_rate == 44_100
    assert result.audio.ndim == 2
    assert result.audio.shape[0] == 2
    assert result.audio.shape[-1] > 0
    assert np.isfinite(result.audio).all()
    assert 0 <= result.transition_start_sample < result.audio.shape[-1]
    assert result.transition_start_sample <= result.transition_end_sample <= result.audio.shape[-1]
    if renderer == "simple":
        assert result.transition_end_sample == result.transition_start_sample
    else:
        assert result.transition_end_sample > result.transition_start_sample


@pytest.mark.parametrize(
    "renderer",
    ["simple", "fade", "equal_power", "tempo_fade"],
)
def test_every_renderer_aligns_target_tempo(synthetic_tracks, renderer):
    class RecordingTempoAdjust(SimpleTempoAdjust):
        def __init__(self):
            self.calls = []

        def adjust_tempo_to_bpm(self, audio, sample_rate, original_bpm, target_bpm, **kwargs):
            self.calls.append((original_bpm, target_bpm))
            return super().adjust_tempo_to_bpm(
                audio,
                sample_rate,
                original_bpm,
                target_bpm,
                **kwargs,
            )

    tempo_adjuster = RecordingTempoAdjust()
    render_transition(
        synthetic_tracks["song1"],
        synthetic_tracks["song2"],
        synthetic_tracks["cutpoint1"],
        synthetic_tracks["cutpoint2"],
        renderer=renderer,
        fade_beats=2,
        analysis=synthetic_tracks["analysis"],
        tempo_adjuster=tempo_adjuster,
    )

    assert tempo_adjuster.calls == [(100.0, 120.0)]


def test_equal_power_envelopes_keep_constant_squared_gain():
    cutter = EqualPowerFadeCut(fade_beats=2)
    fade_out, fade_in = cutter._build_envelopes(101)

    np.testing.assert_allclose(
        fade_out**2 + fade_in**2,
        np.ones(101, dtype=np.float32),
        atol=1e-6,
    )
    assert float(fade_out[0]) == pytest.approx(1.0)
    assert float(fade_in[-1]) == pytest.approx(1.0)


def test_bridge_fade_keeps_high_power_sections_outside_the_overlap():
    song1 = np.concatenate(
        [np.ones(400, dtype=np.float32), np.full(600, 0.1, dtype=np.float32)]
    )
    song2 = np.concatenate(
        [np.full(400, 0.2, dtype=np.float32), np.full(600, 2.0, dtype=np.float32)]
    )
    beats = [(sample, index % 4 + 1, 4) for index, sample in enumerate(range(0, 1_000, 100))]

    result = FadeCut(fade_beats=2).cut(song1, song2, 400, 400, beats, beats)

    assert result.shape == (1_200,)
    assert result[399] == pytest.approx(1.0)
    assert float(np.max(result[400:600])) <= 0.200001
    assert result[600] == pytest.approx(2.0)


def test_render_transition_returns_a_short_preview_by_default(synthetic_tracks):
    result = render_transition(
        synthetic_tracks["song1"],
        synthetic_tracks["song2"],
        synthetic_tracks["cutpoint1"],
        synthetic_tracks["cutpoint2"],
        renderer="fade",
        fade_beats=2,
        analysis=synthetic_tracks["analysis"],
        tempo_adjuster=SimpleTempoAdjust(),
        preview_seconds_before=0.5,
        preview_seconds_after=0.75,
    )

    assert result.audio.shape[-1] <= int(1.25 * result.sample_rate)


def test_downbeat_snapping_fails_clearly_without_bar_metadata():
    audio = np.zeros((2, 1_000), dtype=np.float32)

    with pytest.raises(ValueError, match="Downbeat snapping requires"):
        SimpleCut().cut(
            audio,
            audio,
            400,
            400,
            [0, 100, 200, 300, 400],
            [0, 100, 200, 300, 400],
        )


@pytest.fixture
def variable_candidate_inputs(tmp_path):
    sample_rate = 44_100
    duration_seconds = 40
    time = np.arange(sample_rate * duration_seconds, dtype=np.float32) / sample_rate
    source = np.column_stack(
        [0.1 * np.sin(2 * np.pi * 220 * time), 0.1 * np.sin(2 * np.pi * 330 * time)]
    )
    target = np.column_stack(
        [0.1 * np.sin(2 * np.pi * 440 * time), 0.1 * np.sin(2 * np.pi * 550 * time)]
    )
    source_path = tmp_path / "variable_source.wav"
    target_path = tmp_path / "variable_target.wav"
    sf.write(source_path, source, sample_rate)
    sf.write(target_path, target, sample_rate)

    class Analysis:
        def __call__(self, song_path):
            info = sf.info(song_path)
            beat_step = int(round(info.samplerate * 60.0 / 120.0))
            beats = [
                (sample, index % 4 + 1, 4)
                for index, sample in enumerate(range(0, info.frames, beat_step))
            ]
            return 120.0, beats

    analysis = Analysis()
    cut_sample = 8 * 4 * (sample_rate // 2)
    target_cut_sample = 12 * 4 * (sample_rate // 2)
    return source_path, target_path, analysis, cut_sample, target_cut_sample


@pytest.mark.parametrize("renderer", ["fade", "equal_power"])
@pytest.mark.parametrize("length_bars", [2, 6, 8])
def test_variable_fade_renderers_are_exactly_taktgenau(
    variable_candidate_inputs,
    renderer,
    length_bars,
    monkeypatch,
):
    source_path, target_path, analysis, cut_sample, target_cut_sample = variable_candidate_inputs
    def load_with_soundfile(path, sr=None, mono=False):
        audio, sample_rate = sf.read(path, always_2d=False)
        if audio.ndim == 2:
            audio = audio.T
        return audio, sample_rate

    monkeypatch.setattr("src.pipeline.librosa.load", load_with_soundfile)
    candidate = TransitionCandidate(
        candidate_id=f"variable-{renderer}-{length_bars}",
        source_track=TrackReference(str(source_path), f"source-{length_bars}"),
        target_track=TrackReference(str(target_path), f"target-{length_bars}"),
        source_cutpoint=CutPoint(cut_sample, 32, 8, 1, 4),
        target_cutpoint=CutPoint(target_cut_sample, 48, 12, 1, 4),
        transition_length_bars=length_bars,
        transition_length_beats=length_bars * 4,
        source_bpm=120.0,
        target_bpm=120.0,
        tempo_relative_difference=0.0,
        generator="bar_grid_v2_length_specific",
        format_version=2,
    )

    result = render_variable_transition(
        candidate,
        renderer=renderer,
        analysis=analysis,
        tempo_adjuster=SimpleTempoAdjust(),
        preview_seconds_before=0.0,
        preview_seconds_after=20.0,
    )

    expected_samples = length_bars * 4 * (sample_rate := 44_100) // 2
    assert result.format_version == 6
    assert result.transition_length_bars == length_bars
    assert result.transition_length_beats == length_bars * 4
    assert result.transition_end_sample - result.transition_start_sample == expected_samples
    assert result.audio.shape == (2, 20 * sample_rate)
    assert np.isfinite(result.audio).all()
