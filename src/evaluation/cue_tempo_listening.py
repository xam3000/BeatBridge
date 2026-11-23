"""Make a level-matched three-way comparison on two development pairs."""

import argparse
import csv
import json
from pathlib import Path

import numpy as np
import soundfile as sf

from src.bridge import extract_prepared_bridge, prepare_bridge_pair
from src.evaluation.comparison_study import measure_clip
from src.evaluation.p10_pairs import RATE, development_views, pair_generation
from src.evaluation.p11_alignment import align_target
from src.features.p07_mert import file_sha256
from src.features.p08_pairs import publish_dataset
from src.tempo.cue_alignment import CUE_ALIGNMENT, LEGACY_ALIGNMENT, CueAlignmentError, measure_cue_alignment


def select(pairs, views):
    with (pairs / "candidate_scores.csv").open(encoding="utf-8") as file:
        allowed = {(r["pair"], r["candidate_id"]) for r in csv.DictReader(file)}
    for pair in json.loads((pairs / "pairs.json").read_bytes())["pairs"]:
        a, b = [views[pair[k]] for k in ("source", "target")]
        generation, analysis = pair_generation(a, b)
        for cue in sorted(generation.candidates, key=lambda c: c.candidate_id):
            if (pair["pair"], cue.candidate_id) not in allowed:
                continue
            grids = [np.array(analysis(view["path"]).beat_frames)[:, 0] * RATE /
                     sf.info(view["path"]).samplerate for view in (a,b)]
            s, t = cue.source_cutpoint.beat_index, cue.target_cutpoint.beat_index
            before = abs(np.diff(grids[0][[s, s+16]])[0] -
                         np.diff(grids[1][[t-16, t]])[0] * cue.target_bpm / cue.source_bpm)
            if before <= .020 * RATE or grids[0][s] < 5*RATE:
                continue
            try:
                measurement = measure_cue_alignment(*grids, s, t, 16, RATE)
                measurement.require_valid()
            except CueAlignmentError:
                continue
            yield pair["pair"], cue.to_dict(), analysis, before * 1000 / RATE
            break


def clips(candidate, analysis):
    result = {}
    for method in (LEGACY_ALIGNMENT, CUE_ALIGNMENT):
        pipeline = prepare_bridge_pair(candidate, analysis, tempo_alignment=method)
        a, b, geometry = extract_prepared_bridge(candidate, pipeline, include_context_audio=True)
        s, t = geometry["source_cut_sample"], geometry["target_cut_sample"]
        prefix = geometry["source_audio"][:, s - 5*RATE:s]
        suffix = geometry["target_audio"][:, t:t + 8*RATE]
        if prefix.shape[-1] != 5*RATE or suffix.shape[-1] != 8*RATE:
            raise ValueError("Incomplete development context")

        def crossfade(left, right):
            out, into = pipeline.cutter._build_envelopes(left.shape[-1])
            return np.concatenate((prefix, left * out + right * into, suffix), axis=-1)

        result[method] = crossfade(a, b)
        if method == LEGACY_ALIGNMENT:
            source, target = [candidate[role + "_cutpoint"]["beat_index"] for role in ("source", "target")]
            marks_a = [f[0] for f in pipeline.beat_frames1[source:source+17]]
            marks_b = [f[0] for f in pipeline.adjusted_beat_frames2[target-16:target+1]]
            beatwise, _ = align_target(pipeline.adjusted_song2, marks_a, marks_b, RATE)
            result["beatwise_run02"] = crossfade(pipeline.song1[:, s:marks_a[-1]], beatwise)
    return result


def prepare(destination):
    views = {v["sha256"]: v for v in development_views()}
    pairs = Path("output/review_jp_20261118/p10_ranking/run01/pairs")
    receipt = []
    with publish_dataset(destination) as stage:
        for pair, cue, analysis, before in select(pairs, views):
            batch = clips(cue, analysis)
            length = min(c.shape[-1] for c in batch.values())
            for name, audio in batch.items():
                audio = audio[:, :length]
                lufs, peak = measure_clip(audio)
                gain = -23. - lufs
                if peak + gain >= -1.:
                    raise ValueError("Development clip would exceed the true-peak ceiling")
                path = stage / f"{pair}-{name}.wav"
                sf.write(path, (audio * 10**(gain/20)).T, RATE, subtype="PCM_24")
                pcm, rate = sf.read(path, dtype="float32", always_2d=True)
                level, tp = measure_clip(pcm.T)
                if rate != RATE or abs(level + 23.) > .2 or tp > -1:
                    raise ValueError("Exported development clip outside level tolerance")
                receipt.append(dict(pair=pair, candidate=cue["candidate_id"], method=name,
                                    before_ms=before, samples=length, lufs=level, dbtp=tp,
                                    file=path.name, sha256=file_sha256(path)))
            if len(receipt) == 6:
                break
        if len(receipt) != 6:
            raise ValueError("Fewer than two matching development pairs")
        (stage / "manifest.json").write_text(json.dumps(receipt, indent=2), encoding="utf8")
    print(receipt)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path)
    prepare(parser.parse_args().destination)
