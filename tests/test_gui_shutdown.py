"""Exercise Qt shutdown in its own process, including Python/Qt teardown."""

import os
from pathlib import Path
import subprocess
import sys
import threading

import numpy as np
import pytest
import soundfile as sf


def _close_during_waveform_load(paths):
    from PySide6.QtCore import QTimer
    from src import gui_app
    from src.gui import transition_builder, waveform

    started = threading.Event()
    release = threading.Event()
    completed = threading.Event()
    closed_during_load = []
    original_run = waveform._WaveformTask.run
    original_show = transition_builder.TransitionBuilderWindow.show

    def delayed_run(task):
        started.set()
        if not release.wait(10):
            raise TimeoutError("The test did not release the waveform worker")
        original_run(task)
        completed.set()

    def show(window):
        original_show(window)

        def drop_and_close():
            window.sequence_list.tracksDropped.emit(paths, 0)
            closed_during_load.append(started.wait(5) and not completed.is_set())
            window.close()
            threading.Timer(0.25, release.set).start()

        QTimer.singleShot(0, drop_and_close)

    waveform._WaveformTask.run = delayed_run
    transition_builder.TransitionBuilderWindow.show = show
    sys.argv = [sys.argv[0]]
    assert gui_app.main() == 0
    assert closed_during_load == [True]
    assert completed.is_set()


def test_closing_builder_waits_for_active_qt_workers(tmp_path):
    pytest.importorskip("PySide6")
    files = [tmp_path / name for name in ("a.wav", "b.wav")]
    for file in files:
        sf.write(file, np.zeros(16000, dtype=np.float32), 8000)
    child = subprocess.run(
        [sys.executable, "-B", "-c",
         "import runpy, sys; runpy.run_path(sys.argv[1])['_close_during_waveform_load'](sys.argv[2:])",
         str(Path(__file__).resolve()), *map(str, files)],
        cwd=Path(__file__).resolve().parents[1],
        env={**os.environ, "QT_QPA_PLATFORM": "offscreen"},
        capture_output=True, text=True, errors="replace", timeout=60,
    )
    assert child.returncode == 0, child.stderr
    assert "Error calling Python override" not in child.stderr, child.stderr
    assert "Signal source has been deleted" not in child.stderr, child.stderr
