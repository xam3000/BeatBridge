import hashlib
import json

import numpy as np
import pytest

from src.features.contract import feature_index
from src.features.p07_audio import CHANNELS, PRODUCTION_VIEWS, bar_geometry, bar_statistics, production_view
from src.features.p07_extract import cache_entry, fit_scaler, identity, variants_for
from src.features.p07_mert import (
    CORE_SAMPLES, FRAME_STEP, RECEPTIVE_FIELD, bar_frame_slots, chunk_spans, frame_centres_twice,
)
from src.features.p07_population import allocate, validate_groups


def test_irregular_bar_and_eight_half_beats_follow_detected_boundaries():
    samples = np.array([
        31, 97, 191, 259, 335, 409, 481, 547, 629,
        733, 795, 881, 951, 1027, 1109, 1173, 1247,
    ])
    frames = np.column_stack((samples, np.arange(len(samples)) % 4 + 1, np.full(len(samples), 4)))
    starts, bars = bar_geometry(frames, 1180)
    # The trailing downbeat falls beyond the waveform and cannot close a bar.
    # There are 16 in-bounds beats, so the legacy full-track feature minimum fails.
    assert starts.size == len(bars) == 0
    starts, bars = bar_geometry(frames, 1250)
    np.testing.assert_array_equal(starts, [0, 4, 8, 12])
    np.testing.assert_array_equal(bars[0], [31, 64, 97, 144, 191, 225, 259, 297, 335])
    sequence = np.arange(32)[:, None]
    pooled = bar_statistics(sequence, starts * 2)
    np.testing.assert_allclose(pooled[:, 0], [3.5, 11.5, 19.5, 27.5])
    np.testing.assert_allclose(pooled[:, 1], np.std(np.arange(8)))
    frames[5, 1] = 3
    np.testing.assert_array_equal(bar_geometry(frames, 1250)[0], [0, 8, 12])


def test_frame_centres_at_chunk_and_bar_edges_are_counted_exactly_once():
    length = CORE_SAMPLES * 2 + 700
    centres = []
    for start, end, left, right in chunk_spans(length):
        count = 1 + (right - left - RECEPTIVE_FIELD) // FRAME_STEP
        positions = frame_centres_twice(left, count)
        centres.extend(positions[(2 * start <= positions) & (positions < 2 * end)])
    expected = frame_centres_twice(0, 1 + (length - RECEPTIVE_FIELD) // FRAME_STEP)
    np.testing.assert_array_equal(centres, expected)
    indices, valid = bar_frame_slots(np.array([199, 200, 399, 400, 599, 600, 799, 800]),
                                    np.array([[100, 200], [300, 400]]))
    np.testing.assert_array_equal(indices[valid], [0, 0, 1, 1])
    np.testing.assert_array_equal(valid, [False, True, True, False, False, True, True, False])


def test_classical_contract_keeps_all_legacy_coordinates_available():
    assert len(set(CHANNELS)) == 41
    assert feature_index("transition_position") == 0
    assert feature_index("beat_phase_cos") == 2
    assert feature_index("vocal_valid") == 53
    assert "silence_probability" in CHANNELS
    assert "beat_pulse_confidence" not in CHANNELS


def test_production_preserves_pitch_duration_and_direct_onset():
    rate = 24000
    samples = np.arange(rate * 2)
    tone = (0.5 * np.sin(2 * np.pi * 440 * samples / rate)).astype(np.float32)
    tone[:900] = 0
    for variant in variants_for("train")[1:]:
        mix, stem, gain = production_view(tone, tone / 4, PRODUCTION_VIEWS[variant])
        assert mix.shape == stem.shape == tone.shape
        assert gain <= PRODUCTION_VIEWS[variant]["gain_db"]
        assert np.max(np.abs(mix)) <= 0.999
        assert np.flatnonzero(np.abs(mix) > 1e-6)[0] == np.flatnonzero(np.abs(tone) > 1e-6)[0]
        assert np.argmax(np.abs(np.fft.rfft(mix[-rate:]))) == 440
        np.testing.assert_allclose(stem, mix / 4, atol=1e-7)
        assert not np.array_equal(tone, mix)
    assert variants_for("validation") == ("original",)


def test_cache_binds_source_grid_model_processing_and_each_file(tmp_path):
    spec = {"variant": "original", "track": {"sha256": "a", "analysis_sha256": "b"},
            "model": {"revision": "c", "sha256": "d"}, "room": {"wet_gain": 0.05}}
    artifact = tmp_path / "bars.npz"
    artifact.write_bytes(b"payload")
    (tmp_path / "entry.json").write_text(json.dumps({
        "spec": spec, "sha256": {"bars.npz": hashlib.sha256(b"payload").hexdigest()},
    }))
    assert cache_entry(tmp_path, spec) is not None
    for field, value in (("track", {"sha256": "changed"}), ("variant", "warm_room"),
                         ("model", {"revision": "changed"}), ("room", {"wet_gain": 0.1})):
        changed = {**spec, field: value}
        assert identity(changed) != identity(spec)
        assert cache_entry(tmp_path, changed) is None
    artifact.write_bytes(b"corrupt")
    assert cache_entry(tmp_path, spec) is None


def test_p01_groups_exclude_historical_alias_and_cross_split_components():
    groups = dict(a="cross", b="cross", c="historical", d="historical",
                  e="clean_train", f="clean_val", g="p01")
    catalog = [dict(sha256=sha, recording_group_id=group,
                    direct_evidence="S005/test" if sha == "d" else "")
               for sha, group in groups.items()]
    assignments = dict(a="train", b="validation", c="train", e="train", f="validation", g="train")
    tracks = [dict(sha256=sha, path=f"musik/{sha}.flac") for sha in assignments]
    included, excluded = allocate(tracks, catalog, assignments, {"p01"}, set())
    assert [row["sha256"] for row in included] == ["e", "f"]
    assert [row["sha256"] for row in excluded] == ["a", "b", "c", "g"]
    train, val = included
    validate_groups([train, val, {**train, "variant": "warm_room"}])
    with pytest.raises(ValueError, match="Only training"):
        validate_groups([train, {**val, "variant": "warm_room"}])
    with pytest.raises(ValueError, match="Cross-split"):
        validate_groups([train, {**val, "recording_group_id": "clean_train"}])


def test_scaler_uses_only_original_training_bars(tmp_path):
    rows = []
    for index, (split, variant, values) in enumerate((
        ("train", "original", [[1, 2], [3, 2]]),
        ("train", "bright_room", [[700, 500]]),
        ("validation", "original", [[900, 800]]),
    )):
        path = tmp_path / str(index)
        path.mkdir()
        np.savez(path / "bars.npz", classical_raw=np.array(values))
        rows.append(dict(split=split, variant=variant, entry=f"{index}/entry.json", cache_id=str(index)))
    scaler = fit_scaler(rows, tmp_path)
    assert scaler["training_entries"] == ["0"]
    assert scaler["mean"] == [2, 2]
    assert scaler["scale"] == [1, 1]
