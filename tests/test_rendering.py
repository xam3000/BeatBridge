from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

from src.cutting.equal_power_fade_cut import EqualPowerFadeCut
from src.cutting.simple_cut import SimpleCut
from src.pipeline import (
    BeatBridgePipeline,
    RENDER_RESULT_FORMAT_VERSION,
    render_transition,
)
from src.tempo.time_stretch import TimeStretch


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
    song1 = tmp_path / "song1.wav"
    song2 = tmp_path / "song2.wav"
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
    )

    assert result.format_version == RENDER_RESULT_FORMAT_VERSION
    assert result.renderer == renderer
    assert result.sample_rate == 44_100
    assert result.audio.ndim == 2
    assert result.audio.shape[0] == 2
    assert result.audio.shape[-1] > 0
    assert np.isfinite(result.audio).all()


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


def test_time_stretch_uses_explicit_target_bpm():
    audio = np.zeros((2, 10_000), dtype=np.float32)
    adjusted = TimeStretch().adjust_tempo_to_bpm(
        audio,
        sample_rate=44_100,
        original_bpm=100.0,
        target_bpm=125.0,
    )

    assert adjusted.shape == (2, 8_000)


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
