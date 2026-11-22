import numpy as np
import pytest

from src.analysis.models import BeatGridMetadata
from src.batch_render import DEFAULT_RENDERERS
from src.candidates import BaselineCandidateGenerationConfig, TrackReference, generate_candidates
from src.candidates.variable import validate_baseline_cue
from src.pipeline import build_cutter


def test_each_length_uses_its_own_complete_windows():
    # Six bars and a final downbeat fit three bars on either side, but never four.
    grid = [(100 * i, i % 4 + 1, 4) for i in range(25)]
    meta = BeatGridMetadata("detected", False, "test", 1.0)
    result = generate_candidates(
        TrackReference("a", "a"*64), 120, grid, TrackReference("b", "b"*64), 120, grid,
        config=BaselineCandidateGenerationConfig(), source_grid_metadata=meta, target_grid_metadata=meta,
        source_cutpoint_range_samples=(1200, 1201), target_cutpoint_range_samples=(1200, 1201),
    )
    assert [(c.transition_length_bars, c.transition_length_beats) for c in result.candidates] == [
        (1, 4), (2, 8), (3, 12)]
    assert any(r.transition_length_bars == 4 and r.code == "insufficient_source_bars"
               for r in result.rejections)
    with pytest.raises(ValueError, match="4 complete bars"):
        validate_baseline_cue(grid, 1200, 4, 2500, "source")
    # Beat labels alone do not reveal a gap in the annotated times.
    gap = [(s + (500 if i > 12 else 0), count, meter) for i, (s, count, meter) in enumerate(grid)]
    with pytest.raises(ValueError, match="contiguous 4/4"):
        validate_baseline_cue(gap, 1200, 1, 3000, "source")
    grid[13] = (1300, 3, 4)
    with pytest.raises(ValueError, match="contiguous 4/4"):
        validate_baseline_cue(grid, 1200, 1, 2500, "target")


@pytest.mark.parametrize("bars", [1, 2, 3, 4])
def test_legacy_linear_alias_is_sample_identical(bars):
    assert "tempo_fade" not in DEFAULT_RENDERERS
    grid = [(i*100, i % 4 + 1, 4) for i in range(41)]
    audio = np.linspace(-1, 1, 4100, dtype=np.float32)
    def cut(name):
        return build_cutter(name, 4*bars).cut(audio, audio[::-1], 2000, 2000, grid, grid)
    np.testing.assert_array_equal(cut("fade"), cut("tempo_fade"))


def test_gui_fixed_model_locks_length(monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    from src.gui import transition_builder as gui

    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(gui, "discover_control_models", lambda path: [("Fixed", "fixture-run")])
    window = gui.TransitionBuilderWindow()
    try:
        length = window.length_combo
        assert [length.itemData(i) for i in range(length.count())] == [1, 2, 3, 4]
        length.setCurrentIndex(length.findData(3))
        window.model_combo.setCurrentIndex(1)
        assert length.currentData() == 4 and not length.isEnabled()
        window.model_combo.setCurrentIndex(0)
        assert length.isEnabled()
    finally:
        window.close()
        app.processEvents()
