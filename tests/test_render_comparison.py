import json

import numpy as np
import pytest
import soundfile as sf
import torch

from src.bridge import extract_aligned_bridge, extract_prepared_bridge, prepare_bridge_pair
from src.cutting.equal_power_fade_cut import EqualPowerFadeCut
from src.evaluation.comparison import Comparison, Evaluator, new_output, raw_result
from src.evaluation.controller_baselines import direct, fit
from src.evaluation.comparison_study import measure_clip, normalize_panel, render_panel


@pytest.fixture(scope="module", autouse=True)
def cpu_threads():
    old = torch.get_num_threads()
    torch.set_num_threads(2)
    yield
    torch.set_num_threads(old)


def item_for(config, seed=227, n=2051):
    rng = torch.Generator().manual_seed(seed)
    a, b = torch.randn(2, 2, n, generator=rng) * .16
    return {
        "source_audio": a, "target_audio": b, "source_vocal_audio": a*.4, "target_vocal_audio": b*.6,
        "features_a": torch.rand(config.points, 54, generator=rng),
        "features_b": torch.rand(config.points, 54, generator=rng),
        "split": "validation", "pair": ("A", "B"), "candidate_id": "cue", "example_id": "ex",
        "sample_rate": config.sample_rate, "transition_length_bars": config.bars,
        "geometry": {}, "prefix": np.zeros((2, 5*44100), np.float32),
        "suffix": np.zeros((2, 8*44100), np.float32),
    }


@pytest.mark.parametrize("cfg", [Comparison("R1"), Comparison.study(), Comparison("R2"),
                                 Comparison("R3"), Comparison("R4", 2), Comparison("R4", 8)])
def test_equal_power_matches_reference_and_repeats_bitwise(cfg):
    evaluator = Evaluator(cfg)
    beats = cfg.bars * 4
    n = beats * 257
    item = item_for(cfg, n=n)
    # Exercise the reference cutter through cut(), including its edge samples.
    a = np.pad(item["source_audio"].numpy(), ((0, 0), (257*4, 257)))
    b = np.pad(item["target_audio"].numpy(), ((0, 0), (0, 257*5)))
    grid = [(i*257, i%4+1, 4) for i in range(beats + 5)]
    ref = EqualPowerFadeCut(fade_beats=beats).cut(a, b, 4*257, n, grid, grid)[:, 4*257:4*257+n]
    first = evaluator.render(item, evaluator.equal_power()).audio.detach().numpy()
    second = Evaluator(cfg).render(item, Evaluator(cfg).equal_power()).audio.detach().numpy()
    assert first.tobytes() == second.tobytes()
    np.testing.assert_allclose(first, ref, rtol=0, atol=5e-7)


@pytest.mark.parametrize("cfg", [Comparison("R1"), Comparison("R2"), Comparison("R3"), Comparison("R4", 2)])
def test_fixed_direct_start_and_paired_weighting(cfg):
    evaluator = Evaluator(cfg)
    a, b = item_for(cfg), item_for(cfg, seed=228)
    with pytest.raises(ValueError, match="only be fitted on train"):
        evaluator.optimize([a], [a["pair"]], steps=1, fixed=True)
    a["split"] = b["split"] = "train"
    b["pair"] = ("C", "D")
    a["source_audio"] *= 3
    fixed = evaluator.optimize([a, b], [a["pair"], b["pair"]], steps=2, fixed=True)
    duplicated = evaluator.optimize([a, a, b], [a["pair"], a["pair"], b["pair"]], steps=2, fixed=True)
    for name in fixed:
        torch.testing.assert_close(fixed[name], duplicated[name], atol=2e-6, rtol=1e-5)
    direct = evaluator.optimize([a], [a["pair"]], steps=2, fixed=False)
    _, equal_row = raw_result(evaluator, a, "E", evaluator.equal_power())
    _, direct_row = raw_result(evaluator, a, "D", direct)
    assert equal_row.keys() == direct_row.keys()
    assert direct_row["proxy_raw"]["loss"] < equal_row["proxy_raw"]["loss"]
    assert direct_row["proxy_playback"] is None
    assert any(not torch.equal(fixed[k], direct[k]) for k in fixed)


@pytest.mark.parametrize("profile", ["R1", "R2", "R3", "R4"])
@pytest.mark.parametrize("device", ["cpu", pytest.param("cuda", marks=pytest.mark.skipif(
    not torch.cuda.is_available(), reason="CUDA unavailable"))])
def test_p06_batched_adam_matches_individual_paired_objective(profile, device, monkeypatch):
    monkeypatch.setattr(torch.backends.cudnn, "allow_tf32", False)
    cfg = Comparison(profile)
    ev = Evaluator(cfg)
    items = [item_for(cfg, seed=i) for i in range(5)]
    for i, item in enumerate(items):
        item.update(split="train", pair=("a", str(i // 2)))
    native_items = [{k: v.to(device) if torch.is_tensor(v) else v for k, v in item.items()} for item in items]
    fixed = fit(ev, items, 3, 4, device)
    with torch.device(device):
        expected = ev.optimize(native_items, [item["pair"] for item in native_items], steps=3, fixed=True)
    for key in fixed:
        torch.testing.assert_close(fixed[key], expected[key].cpu(), atol=3e-6, rtol=1e-5)
    for controls, item, native in zip(direct(ev, items, 3, 4, device), items, native_items):
        with torch.device(device):
            expected = ev.optimize([native], [native["pair"]], steps=3, fixed=False)
        for key in controls:
            torch.testing.assert_close(controls[key], expected[key].cpu(), atol=3e-6, rtol=1e-5)
        if device != "cpu":
            cpu = ev.optimize([item], [item["pair"]], steps=3, fixed=False)
            torch.testing.assert_close(ev.terms(item, ev.render(item, controls))["loss"],
                                       ev.terms(item, ev.render(item, cpu))["loss"], atol=1e-6, rtol=1e-5)


def test_pair_loudness_peak_reduction_and_wav_verification(tmp_path):
    t = np.arange(88200) / 44100
    tone = np.tile((.03*np.sin(2*np.pi*997*t)).astype(np.float32), (2, 1))
    impulsive = tone.copy()
    impulsive[:, 44100] = 1.4
    clips = [impulsive] + [tone * k for k in range(1, 7)]
    outputs = list(normalize_panel(clips, tmp_path))
    assert len({entry[3]["pair_gain_db"] for entry in outputs}) == 1
    assert outputs[0][3]["pair_gain_db"] < -1
    for path, pcm, gain, stats in outputs:
        assert sf.info(path).subtype == "PCM_24"
        assert measure_clip(pcm) == (stats["final_lufs"], stats["final_dbtp"])
        assert abs(stats["final_lufs"] - stats["pair_target_lufs"]) <= .2
        assert stats["final_dbtp"] <= -.99
    with pytest.raises(ValueError, match="unmeasurable"):
        measure_clip(np.zeros_like(tone))


def test_study_rows_measure_quantized_bridge_and_keep_duplicate_cues(tmp_path):
    cfg = Comparison.study()
    evaluator = Evaluator(cfg)
    item = item_for(cfg, n=44100)
    # Energy clipping must decrease after gain, while control terms are unchanged.
    item["source_audio"] *= 8
    item["target_audio"] *= 7
    item["prefix"][:] = .05
    rows = render_panel(tmp_path, evaluator, {"cue": item}, dict.fromkeys(("ssl", "rule", "random"), "cue"), 1)
    assert len(rows) == 7 and all(row.keys() == rows[0].keys() for row in rows)
    assert len({row["wav_sha256"] for row in rows if row["condition"] == "E"}) == 1
    assert len({row["wav_sha256"] for row in rows if row["condition"] == "D"}) == 1
    row = rows[0]
    assert row["proxy_raw"]["clipping"] > row["proxy_playback"]["clipping"]
    assert row["proxy_raw"]["control_smoothness"] == row["proxy_playback"]["control_smoothness"]
    pcm, _ = sf.read(tmp_path / row["wav"], dtype="float32")
    stats = row["loudness"]
    gain = 10 ** ((stats["clip_gain_db"] + stats["pair_gain_db"]) / 20)
    rendered = evaluator.render(item, evaluator.equal_power())
    actual = evaluator.terms(item, rendered, gain, torch.from_numpy(pcm[5*44100:6*44100].T))
    assert row["proxy_playback"]["loss"] == float(actual["loss"])
    assert rows[-1]["proxy_raw"] is None and rows[-1]["proxy_playback"] is None
    assert rows[-1]["condition"] == "anchor"
    anchor, _ = sf.read(tmp_path / rows[-1]["wav"], dtype="float32")
    anchor_db = rows[-1]["loudness"]
    gain = 10 ** ((anchor_db["clip_gain_db"] + anchor_db["pair_gain_db"]) / 20)
    np.testing.assert_allclose(anchor[5*44100:6*44100].T, item["source_audio"].numpy()*gain, atol=2e-7)
    json.dumps(rows, allow_nan=False)


def test_comparison_rejects_foreign_inputs(tmp_path):
    cfg = Comparison.study()
    evaluator = Evaluator(cfg)
    item = item_for(cfg)
    item["sample_rate"] = 11025
    with pytest.raises(ValueError, match="Input rate"):
        evaluator.render(item, evaluator.equal_power())
    item["prefix"] = item["prefix"][:, :-1]
    with pytest.raises(ValueError, match="context"):
        render_panel(tmp_path, evaluator, {"cue": item}, dict.fromkeys(("ssl", "rule", "random"), "cue"), 1)


def test_prepared_pair_preserves_legacy_cut_coordinates_and_shorter_window(tmp_path):
    cfg = Comparison.study()
    item = item_for(cfg, n=20001)
    tracks = {}
    grids = {}
    for role, spacing in (("source", 256), ("target", 291)):
        path = tmp_path / f"{role}.wav"
        sf.write(path, item[role + "_audio"].numpy().T, cfg.sample_rate, subtype="FLOAT")
        tracks[role] = {"path": str(path)}
        grids[str(path)] = [(i * spacing, i % 4 + 1, 4) for i in range(64)]

    def analysis(path):
        return 120., grids[path]

    candidate = {
        "source_track": tracks["source"], "target_track": tracks["target"],
        "source_bpm": "120", "target_bpm": None, "transition_length_beats": 16,
        "source_cutpoint": {"sample": 8 * 256}, "target_cutpoint": {"sample": 36 * 291},
    }
    pipeline = prepare_bridge_pair(candidate, analysis)
    for offset in (0, 4):
        cue = dict(candidate, source_cutpoint={"sample": (8 + offset) * 256})
        a, b, geom = extract_prepared_bridge(cue, pipeline, include_context_audio=True)
        legacy_a, legacy_b, _ = extract_aligned_bridge(cue, analysis)
        np.testing.assert_array_equal(a, legacy_a)
        np.testing.assert_array_equal(b, legacy_b)
        assert a.shape == b.shape == (2, 16 * 256)
        s, t = geom["source_cut_sample"], geom["target_cut_sample"]
        reference = pipeline.cutter.cut(geom["source_audio"], geom["target_audio"], s, t,
                                        pipeline.beat_frames1, pipeline.adjusted_beat_frames2)
        item.update(source_audio=torch.from_numpy(a), target_audio=torch.from_numpy(b))
        evaluator = Evaluator(cfg)
        audio = evaluator.render(item, evaluator.equal_power()).audio.numpy()
        entire = np.concatenate((geom["source_audio"][:, :s], audio, geom["target_audio"][:, t:]), axis=-1)
        np.testing.assert_allclose(entire, reference, rtol=0, atol=5e-7)
    with pytest.raises(ValueError, match="tempo"):
        extract_prepared_bridge(dict(candidate, target_bpm=160), pipeline)


def test_configuration_and_incomplete_outputs(tmp_path):
    with pytest.raises(ValueError, match="Sample rate or FIR"):
        Comparison("study")
    with pytest.raises(ValueError, match="length"):
        Comparison("R1", bars=2)
    path = tmp_path / "new"
    with pytest.raises(ValueError), new_output(path) as stage:
        (stage / "partial").touch()
        raise ValueError("invalid input")
    assert not path.exists()
    with new_output(path) as stage:
        (stage / "ok").touch()
    with pytest.raises(FileExistsError), new_output(path):
        pass
