"""Audit R_P11_01 from historical files and compare meters on synthetic signals."""

import argparse
from importlib.metadata import version
import json
from pathlib import Path
import re

import numpy as np
import soundfile as sf

from src.evaluation.comparison_study import measure_clip
from src.evaluation.p11_stimuli import BASE, frozen_inputs
from src.features.p07_mert import file_sha256
from src.features.p08_windows import read_json


def meter_check():
    import pyloudnorm

    rate = 44100
    time = np.arange(12*rate) / rate
    sine = .1 * np.sin(2*np.pi*1000*time)
    signals = {"1k_0.1_stereo": sine, "100Hz_0.1_stereo": .1*np.sin(2*np.pi*100*time),
               "4k_0.1_stereo": .1*np.sin(2*np.pi*4000*time),
               "gated_1k": sine*np.repeat([.0001, 1., .01, 1.], 3*rate)}
    rows = []
    for name, mono in signals.items():
        stereo = np.stack([mono, mono]).astype("float32")
        ff, peak = measure_clip(stereo)
        ref = float(pyloudnorm.Meter(rate, filter_class="DeMan").integrated_loudness(stereo.T))
        if abs(ff - ref) > .1 or abs(peak - (-20)) > .1:
            raise ValueError(f"Synthetic meter mismatch for {name}: FFmpeg {ff}, reference {ref}, peak {peak}")
        rows.append(dict(name=name, ffmpeg_lufs=ff, reference_lufs=ref, peak_dbtp=peak, difference_lu=ff-ref))
    return dict(reference="pyloudnorm", version=version("pyloudnorm"), filter="DeMan", tolerance_lu=.1,
                peak_tolerance_db=.1, synthetic_only=True, signals=rows)


def review(original):
    pairs, paths = frozen_inputs()
    grids, cues, keys = [], [], []
    sizes = {}
    for pair in pairs:
        pid = pair["pair_id"]
        for role in ("source", "target"):
            sha = pair[role]["sha256"]
            rate = sf.info(paths[sha]).samplerate
            for cache in (original/"cache/analysis/v2"/sha).glob("*/analysis.json"):
                obj = read_json(cache)["result"]
                frames = np.array(obj["beat_frames"])[:, 0]
                median = float(np.median(np.diff(frames)))
                grids.append(dict(pair=pid, role=role, sample_rate=rate, grid_beats=len(frames),
                                  sha256=sha, median_native_samples=median, median_bpm=60*rate/median,
                                  bpm_field=obj["bpm"], all_on_512_hop=bool(np.all(frames % 512 == 0))))
        directory = original/pid/"stimuli"
        if not directory.exists():
            continue
        rows = read_json(directory/"results.json")
        lengths = {}
        for row in rows:
            wav = directory/row["wav"]
            assert file_sha256(wav) == row["wav_sha256"]
            lengths.setdefault(str(wav.stat().st_size), []).append([row["selector"],row["condition"]])
            if row["condition"] == "E":
                g = row["geometry"]
                a, b = (np.diff(g[k]) for k in ("source_beats", "target_beats"))
                assert row["bridge_samples"] == min(a.sum(), b.sum())
                cues.append(dict(pair=pid, selector=row["selector"], backend=g["tempo_backend"],
                                 median_a=float(np.median(a)), median_b=float(np.median(b)),
                                 span_difference_ms=1000*float(a.sum()-b.sum())/44100))
        sizes[pid] = lengths
    for person in ("VP01","VP02","VP03"):
        canonical = original/"blind"/person
        older = original/"sessions"/person
        if not older.exists():
            older = BASE.parent/"p11_archiv_run01_sessions"/person
        assert file_sha256(canonical/"zuordnung.json") == file_sha256(older/"zuordnung.json")
        pages = [read.read_text(encoding="utf-8") for read in
                 (canonical/"player/index.html", older/"player/index.html")]
        sessions = [json.loads(re.search(r"^const session = (.+);$", p, re.MULTILINE)[1]) for p in pages]
        assert 'session_id' in sessions[0] and 'session_id' not in sessions[1]
        keys.append(dict(person=person, key_identical=True, html_different=pages[0] != pages[1]))
    return dict(native_grids=grids, historical_windows=cues, historical_sizes=sizes,
                historical_players=keys, independent_meter=meter_check())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    report = review(BASE/"run01")
    with args.output.open("x", encoding="utf-8") as f:
        json.dump(report, f, indent=2, allow_nan=False)
    print(report["independent_meter"])
