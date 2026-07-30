from pathlib import Path
import subprocess

import numpy as np
import pytest
import soundfile as sf

from src.tempo.time_stretch import TimeStretch, TimeStretchBackendError


def _copy_backend_input_to_output(command):
    if "-i" in command:
        input_path = Path(command[command.index("-i") + 1])
    else:
        input_path = Path(command[-2])
    output_path = Path(command[-1])
    audio, sample_rate = sf.read(
        str(input_path),
        dtype="float32",
        always_2d=True,
    )
    sf.write(
        str(output_path),
        audio,
        sample_rate,
        format="WAV",
        subtype="FLOAT",
    )


def test_ffmpeg_librubberband_is_preferred_and_uses_float_stereo(monkeypatch):
    calls = []
    input_subtypes = []

    def fake_run(command, **kwargs):
        calls.append(command)
        input_path = Path(command[command.index("-i") + 1])
        input_subtypes.append(sf.info(str(input_path)).subtype)
        _copy_backend_input_to_output(command)
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    audio = np.zeros((2, 10_000), dtype=np.float32)
    stretch = TimeStretch(
        ffmpeg_executable="ffmpeg-test",
        rubberband_executable="rubberband-test",
    )

    adjusted = stretch.adjust_tempo_to_bpm(
        audio,
        sample_rate=44_100,
        original_bpm=100.0,
        target_bpm=125.0,
    )

    assert adjusted.shape == (2, 8_000)
    assert adjusted.dtype == np.float32
    assert stretch.last_backend == "ffmpeg_librubberband"
    assert len(calls) == 1
    assert calls[0][0] == "ffmpeg-test"
    assert "rubberband=tempo=1.25:pitch=1:channels=together" in calls[0]
    assert "pcm_f32le" in calls[0]
    assert input_subtypes == ["FLOAT"]


def test_standalone_rubberband_r3_is_used_after_ffmpeg_failure(monkeypatch):
    calls = []

    def fake_run(command, **kwargs):
        calls.append(command)
        if command[0] == "ffmpeg-test":
            return subprocess.CompletedProcess(
                command,
                1,
                stdout="",
                stderr="No such filter: rubberband",
            )
        _copy_backend_input_to_output(command)
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    audio = np.zeros(10_000, dtype=np.float32)
    stretch = TimeStretch(
        ffmpeg_executable="ffmpeg-test",
        rubberband_executable="rubberband-test",
    )

    adjusted = stretch.adjust_tempo_by_factor(
        audio,
        sample_rate=44_100,
        tempo_factor=1.25,
    )

    assert adjusted.shape == (8_000,)
    assert stretch.last_backend == "rubberband_cli_r3"
    assert [call[0] for call in calls] == ["ffmpeg-test", "rubberband-test"]
    assert calls[1][1:3] == ["-3", "-t"]
    assert float(calls[1][3]) == pytest.approx(0.8)


def test_missing_rubberband_backends_fail_with_both_step_names(monkeypatch):
    def missing_backend(command, **kwargs):
        raise FileNotFoundError(command[0])

    monkeypatch.setattr(subprocess, "run", missing_backend)
    stretch = TimeStretch(
        ffmpeg_executable="missing-ffmpeg",
        rubberband_executable="missing-rubberband",
    )

    with pytest.raises(TimeStretchBackendError) as error:
        stretch.adjust_tempo_by_factor(
            np.zeros(1_000, dtype=np.float32),
            sample_rate=44_100,
            tempo_factor=1.1,
        )

    message = str(error.value)
    assert "[Time stretch]" in message
    assert "FFmpeg/librubberband" in message
    assert "Rubber Band CLI" in message
    assert stretch.last_backend is None


def test_identity_tempo_skips_external_backends(monkeypatch):
    def unexpected_run(*args, **kwargs):
        raise AssertionError("identity tempo must not start an external backend")

    monkeypatch.setattr(subprocess, "run", unexpected_run)
    audio = np.arange(16, dtype=np.float32)
    stretch = TimeStretch()

    adjusted = stretch.adjust_tempo_by_factor(
        audio,
        sample_rate=44_100,
        tempo_factor=1.0,
    )

    assert np.array_equal(adjusted, audio)
    assert adjusted is not audio
    assert stretch.last_backend == "not_needed"
