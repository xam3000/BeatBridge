from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

from src.mashup import export_mashup


RATE = 8000


def sequence(tmp_path, rates, periods):
    sections, analysis, signals = [], {}, []
    for i, (rate, period) in enumerate(zip(rates, periods, strict=True)):
        path = tmp_path / f"original-{i}.wav"
        step = round(rate * period)
        samples = 80 * step
        signal = .2 * np.sin(np.arange(samples) * ((i + 1) * .013))
        sf.write(path, signal, rate, subtype="FLOAT")
        sections.append(dict(path=path.as_posix(), start_seconds=0, end_seconds=samples / rate))
        analysis[str(path)] = (60 / period, [(j * step, j % 4 + 1, 4) for j in range(80)])
        signals.append(signal.astype("float32"))
    return dict(format_version=1, sections=sections, edges=[]), analysis, signals


@pytest.mark.parametrize("bars", [1, 2, 3, 4])
def test_three_tracks_match_every_expected_pcm_sample(tmp_path, bars):
    plan, analysis, signals = sequence(tmp_path, [RATE]*3, [.125]*3)
    plan["sections"][0]["start_seconds"] = .25
    plan["sections"][-1]["end_seconds"] = 8
    plan["edges"] = [
        dict(source_seconds=4, target_seconds=3, renderer="fade", bars=bars),
        dict(source_seconds=6, target_seconds=3, renderer="simple", bars=1),
    ]
    result = export_mashup(plan, tmp_path / "published", analysis.__getitem__, sample_rate=RATE)
    samples = 4*bars*1000
    ramp = np.linspace(0, 1, samples, dtype="float32")
    expected = np.concatenate((
        signals[0][2000:32000],
        (1-ramp) * signals[0][32000:32000+samples] + ramp * signals[1][24000-samples:24000],
        signals[1][24000:48000],
        signals[2][24000:64000],
    ))
    actual, sr = sf.read(tmp_path / "published" / "mashup.wav", dtype="float32")
    assert sr == RATE and len(expected) == result["samples"]
    assert actual.shape == (len(expected), 2)
    np.testing.assert_allclose(actual[:, 0], expected, atol=1.6e-7)
    np.testing.assert_array_equal(actual[:, 0], actual[:, 1])
    assert result["edges"][0]["bridge_output"] == [30000, 30000 + samples]


def test_middle_track_is_stretched_once_from_original_at_mixed_rates(tmp_path):
    plan, analysis, _ = sequence(tmp_path, [RATE, RATE*2, RATE], [.125, .15, .1])
    plan["edges"] = [
        dict(source_seconds=4, target_seconds=4.8, renderer="fade", bars=2),
        dict(source_seconds=7.2, target_seconds=3.2, renderer="equal_power", bars=3),
    ]
    calls = []

    class Stretch:
        last_backend = "test"

        def adjust_tempo_by_factor(self, audio, rate, factor):
            calls.append((audio.shape[-1], factor))
            indices = np.rint(np.arange(round(audio.shape[-1]/factor))*factor).astype(int)
            return audio[:, indices.clip(max=audio.shape[-1]-1)]

    one = export_mashup(plan, tmp_path / "first", analysis.__getitem__, sample_rate=RATE, tempo_adjuster=Stretch())
    assert calls == pytest.approx([(96000, 1.2), (64000, .8)])
    # Input spans are measured on each track's final playback clock.
    assert one["edges"][0]["source_window"] == [32000, 40000]
    assert one["edges"][1]["source_window"] == [48000, 60000]
    two = export_mashup(plan, tmp_path / "again", analysis.__getitem__, sample_rate=RATE, tempo_adjuster=Stretch())
    assert one["sha256"] == two["sha256"]


def test_rubberband_preserves_pitch_and_places_target_bars_in_bridge_and_solo(tmp_path):
    output_rate = 24_000
    native_rate = 2 * output_rate
    plan, analysis, _ = sequence(tmp_path, [output_rate, native_rate], [.125, .15])
    plan["edges"] = [dict(source_seconds=4, target_seconds=4.8, renderer="fade", bars=2)]
    # Each four-beat bar in B carries its own pitch, making a misplaced or
    # unstretched passage detectable directly in the published PCM.
    bar_samples = 4 * round(.15 * native_rate)
    t = np.arange(bar_samples) / native_rate
    target = np.concatenate([.2 * np.sin(2 * np.pi * (240 + 40 * bar) * t) for bar in range(20)])
    sf.write(plan["sections"][1]["path"], target, native_rate, subtype="FLOAT")

    destination = tmp_path / "stretched"
    manifest = export_mashup(plan, destination, analysis.__getitem__, sample_rate=output_rate)
    audio, rate = sf.read(destination / "mashup.wav")
    assert rate == output_rate and audio.shape == (11 * rate, 2)
    assert manifest["tracks"][1]["tempo_factor"] == pytest.approx(1.2)
    assert manifest["tracks"][1]["backend"] in {"ffmpeg_librubberband", "rubberband_cli_r3"}
    assert manifest["edges"][0]["bridge_output"] == [4 * rate, 5 * rate]
    # B bars 6 and 7 fill the fade, then bars 8–19 occupy six seconds.
    for seconds, bar in [(4.75, 7), (5.25, 8), (7.25, 12), (10.75, 19)]:
        middle = round(seconds * rate)
        window = audio[middle - rate // 10:middle + rate // 10, 0]
        assert np.sqrt(np.mean(window ** 2)) > .04
        spectrum = np.abs(np.fft.rfft(window * np.hanning(len(window))))
        frequencies = np.fft.rfftfreq(len(window), d=1/rate)
        # Rubber Band can spread a pure tone over adjacent FFT bins.
        # Bar codes are 40 Hz apart, so the 30 Hz passbands remain disjoint.
        expected_band = np.abs(frequencies - (240 + 40 * bar)) <= 15
        assert np.sum(spectrum[expected_band] ** 2) > .65 * np.sum(spectrum ** 2)


@pytest.mark.parametrize("track", [0, 1, 2])
def test_bpm_only_grid_is_rejected_for_each_track(tmp_path, track):
    plan, analysis, _ = sequence(tmp_path, [RATE] * 3, [.125] * 3)
    plan["edges"] = [dict(source_seconds=6, target_seconds=3, renderer="simple", bars=1)] * 2
    path = str(Path(plan["sections"][track]["path"]))
    bpm, _ = analysis[path]
    analysis[path] = bpm, []
    with pytest.raises(ValueError, match="BPM-only grid"):
        export_mashup(plan, tmp_path / "mix", analysis.__getitem__, sample_rate=RATE)
    assert sorted(p.name for p in tmp_path.iterdir()) == [f"original-{i}.wav" for i in range(3)]


def test_one_peak_gain_preserves_the_difference_between_solo_levels(tmp_path):
    plan, analysis, signals = sequence(tmp_path, [RATE, RATE], [.125, .125])
    for section, signal, level in zip(plan["sections"], signals, [1., .5], strict=True):
        sf.write(section["path"], np.full_like(signal, level), RATE, subtype="FLOAT")
    plan["edges"] = [dict(source_seconds=4, target_seconds=3, bars=2, renderer="equal_power")]
    destination = tmp_path / "gain"
    result = export_mashup(plan, destination, analysis.__getitem__, sample_rate=RATE)
    audio, _ = sf.read(destination / "mashup.wav")
    # For these two constant signals the equal-power overlap peaks at sqrt(1² + .5²).
    assert result["peak_before_gain"] == pytest.approx(np.hypot(1., .5))
    assert result["gain"] == pytest.approx((1 - 2**-23) / result["peak_before_gain"])
    np.testing.assert_allclose(audio[[RATE, 6 * RATE], 0], result["gain"] * np.array([1., .5]), atol=2**-23)


def test_invalid_section_keeps_both_originals_and_publishes_nothing(tmp_path):
    plan, analysis, _ = sequence(tmp_path, [RATE, RATE], [.125]*2)
    plan["sections"][1]["start_seconds"] = 3.5
    plan["edges"] = [dict(source_seconds=4, target_seconds=4, bars=3, renderer="equal_power")]
    out = tmp_path / "export"
    with pytest.raises(ValueError, match="zu kurz"):
        export_mashup(plan, out, analysis.__getitem__, sample_rate=RATE)
    assert sorted(p.name for p in tmp_path.iterdir()) == ["original-0.wav", "original-1.wav"]
    original = Path(plan["sections"][0]["path"])
    content = original.read_bytes()
    with pytest.raises(FileExistsError):
        export_mashup(plan, original, analysis.__getitem__)
    assert original.read_bytes() == content


def test_gui_reorders_cues_ranges_settings_and_sections_by_track_identity(monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    from src.gui import transition_builder as gui

    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(gui, "discover_control_models", lambda path: [])
    window = gui.TransitionBuilderWindow()
    try:
        window.tracks = {k: gui.TrackItem(Path(k)) for k in "ABCD"}
        window._refresh_tracks()
        window._replace_sequence(list("ABCD"), select_edge=1)
        window._set_cue("source", 14)
        window._set_cue("target", 31)
        window.source_wave.set_selection_range(12, 19)
        window.length_combo.setCurrentIndex(window.length_combo.findData(3))
        window._sections["B"] = (3, 72)
        window._apply_dragged_sequence_order(list("DBCA"))
        assert window._edge_cues[1] == (14, 31, True, True)
        assert window._edge_ranges[1] == ((12, 19), None)
        assert window._edge_settings[1][0] == 3
        assert window._sections["B"] == (3, 72)
        assert window.source_wave.selection_range_seconds is None
        assert not window._source_cue_set
        window.edge_combo.setCurrentIndex(1)
        assert window._source_cue_set and window.source_cue.value() == 14
        assert window.source_wave.selection_range_seconds == (12, 19)
        # An edge that moves to a different index still carries its own state.
        window._replace_sequence(list("BCA"), select_edge=0)
        assert window._edge_cues[0] == (14, 31, True, True)
        with pytest.raises(ValueError, match="Übergang 2"):
            window._export_plan()
    finally:
        window.close()
        app.processEvents()


def test_gui_exports_current_snapshot_through_worker(tmp_path, monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    from src.analysis import pre_analysis
    from src.gui import transition_builder as gui

    plan, analysis, _ = sequence(tmp_path, [RATE]*3, [.125]*3)
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(gui, "discover_control_models", lambda path: [])
    monkeypatch.setattr(gui.QFileDialog, "getExistingDirectory", lambda *unused: str(tmp_path))
    monkeypatch.setattr(pre_analysis, "PreAnalysis", lambda unused: analysis.__getitem__)
    window = gui.TransitionBuilderWindow()
    try:
        paths = [str(Path(s["path"])) for s in plan["sections"]]
        window.tracks = {p: gui.TrackItem(Path(p)) for p in paths}
        window._refresh_tracks()
        window._replace_sequence(paths, select_edge=0)
        for i, bars in enumerate((1, 3)):
            window.edge_combo.setCurrentIndex(i)
            window.length_combo.setCurrentIndex(window.length_combo.findData(bars))
            window._set_cue("source", 6)
            window._set_cue("target", 3)
        window._sections[paths[-1]] = (0, 7)
        class ImmediatePool:
            def start(self, task):
                task.run()

        window._pool = ImmediatePool()
        window.export_button.click()
        app.processEvents()
        exports = list(tmp_path.glob("BeatBridge-*/mashup.wav"))
        assert len(exports) == 1, window.status_label.text()
        assert window.export_button.isEnabled()
        assert str(exports[0]) in window.status_label.text()
        assert sf.info(exports[0]).frames == round((6 + .5 + 3 + 1.5 + 4) * 44100)
    finally:
        window.close()
        app.processEvents()
