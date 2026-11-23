"""Render the four baseline lengths at the established P04 development cue."""

import argparse
import json
from pathlib import Path

import numpy as np
import soundfile as sf

from src.analysis.models import unpack_analysis_result
from src.analysis.pre_analysis import PreAnalysis, MERGE_ALGORITHM_VERSION_V2
from src.batch_render import render_candidate_batch
from src.candidates import BaselineCandidateGenerationConfig, TrackReference, generate_candidates
from src.evaluation.comparison import new_output, write_json
from src.pipeline import BeatBridgePipeline, DEFAULT_SAMPLE_RATE, _file_sha256
from src.tempo.cue_alignment import LEGACY_ALIGNMENT


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    fixture = Path("docs/masterarbeit/review_jp_20261118/p04/dev_panel.json")
    panel = json.loads(fixture.read_text(encoding="utf-8"))
    manifest = Path(panel["pair_manifest"])
    if panel["split"] != "development" or _file_sha256(manifest) != panel["pair_manifest_sha256"]:
        raise ValueError("P04 development manifest differs")
    records = json.loads(manifest.read_text(encoding="utf-8"))["candidate_generation"]["candidates"]
    cue = next(c for c in records if c["candidate_id"] == panel["selectors"]["rule"])
    analysis = PreAnalysis("output/pre_analysis_variable_v2_strict_20260820_retry01",
                           merge_algorithm=MERGE_ALGORITHM_VERSION_V2)
    rate = DEFAULT_SAMPLE_RATE
    tracks, grids, metadata, bpms, indices = [], [], [], [], []
    for role in ("source", "target"):
        track = TrackReference(**cue[role + "_track"])
        if _file_sha256(track.path) != track.sha256:
            raise ValueError(f"{role} file differs")
        bpm, frames, meta = unpack_analysis_result(analysis(track.path))
        grid = BeatBridgePipeline._scale_beat_frames(frames, rate / sf.info(track.path).samplerate)
        pos = cue[role + "_cutpoint"]["sample"]
        index = next(i for i, f in enumerate(grid) if f[0] == pos and f[1] == 1)
        tracks.append(track)
        bpms.append(bpm)
        grids.append(grid)
        metadata.append(meta)
        indices.append(index)
    s, t = (grid[i][0] for grid, i in zip(grids, indices))
    generated = generate_candidates(
        tracks[0], bpms[0], grids[0], tracks[1], bpms[1], grids[1],
        config=BaselineCandidateGenerationConfig(),
        source_grid_metadata=metadata[0], target_grid_metadata=metadata[1],
        source_cutpoint_range_samples=(s, s + 1), target_cutpoint_range_samples=(t, t + 1),
    )
    if [c.transition_length_bars for c in generated.candidates] != [1, 2, 3, 4]:
        raise ValueError(f"Incomplete development candidate set: {generated.rejections}")
    with new_output(args.output) as out:
        batch = render_candidate_batch(generated, out, renderers=("equal_power",), analysis=analysis,
                                       tempo_alignment=LEGACY_ALIGNMENT,
                                       top_k=None, preview_seconds_before=2, preview_seconds_after=10)
        if batch.failures or len(batch.rendered_variants) != 4:
            raise ValueError(f"Incomplete render set: {batch.failures}")
        verified = []
        for variant in sorted(batch.rendered_variants, key=lambda v: v.transition_length_bars):
            n = variant.transition_length_beats
            end_a = grids[0][indices[0] + n][0]
            start_b = grids[1][indices[1] - n][0]
            scale = bpms[1] / bpms[0]
            overlap = min(end_a - s, round(t * scale) - round(start_b * scale))
            wav = out / variant.output_file
            audio, sr = sf.read(wav, always_2d=True)
            if (n != 4 * variant.transition_length_bars or sr != rate or
                    audio.shape != (12 * rate, 2) or not np.isfinite(audio).all() or
                    variant.transition_start_sample != 2 * rate or
                    variant.transition_end_sample != 2 * rate + overlap):
                raise ValueError(f"Grid or PCM mismatch: {variant.output_file}")
            verified.append(dict(bars=n // 4, beats=n, source_window=[s, end_a],
                                 target_window_original=[start_b, t], overlap_samples=overlap,
                                 clip_frames=len(audio), wav=variant.output_file, sha256=_file_sha256(wav)))
        write_json(out / "verified.json", dict(split="D2 train", fixture=str(fixture),
                   original_cue=cue["candidate_id"], tracks=[x.to_dict() for x in tracks],
                   bpms=bpms, sample_rate=rate, renderer="equal_power", lengths=verified))
    print("Verified four stereo WAVs against source and target downbeats.")


if __name__ == "__main__":
    main()
