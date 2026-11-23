"""Render one complete, selector-paired P11 panel and measure its playback WAVs."""

import json
import math
from pathlib import Path
import re
import subprocess

import numpy as np
import soundfile as sf
import torch

from src.analysis.pre_analysis import PreAnalysis, PartialPreAnalysis, MERGE_ALGORITHM_VERSION_V2
from src.bridge import prepare_bridge_pair, extract_prepared_bridge
from src.evaluation.comparison import Comparison, Evaluator, raw_result, result_row, save_comparison
from src.evaluation.comparison_native import FAMILIES, MODEL_RUNS, RUNS, pair_of
from src.evaluation.ml_control_study import _file_sha256
from src.evaluation.p11_alignment import align_target
from src.features.extract_track import _beat_grid_hash, _load_cached_artifact
from src.ml.inference_contract import load_fixed_inference_contract
from src.tempo.cue_alignment import CUE_ALIGNMENT, LEGACY_ALIGNMENT


SELECTORS = ("ssl", "rule", "random")
RATE = 44100
TARGET_LUFS = -23.
CEILING_DBTP = -1.


def measure_clip(audio):
    """Read only loudnorm's input measurements. Never use its processed signal."""
    if audio.ndim != 2 or audio.shape[0] != 2 or not np.isfinite(audio).all():
        raise ValueError("Expected a finite stereo clip")
    command = ["ffmpeg", "-hide_banner", "-nostats", "-f", "f32le", "-ar", str(RATE),
               "-ac", "2", "-i", "pipe:0", "-af", "loudnorm=linear=false:print_format=json",
               "-f", "null", "-"]
    proc = subprocess.run(command, input=np.asarray(audio.T, dtype="<f4").tobytes(),
                          capture_output=True, check=True)
    match = re.search(rb'\{\s*"input_i".*?\}', proc.stderr, re.S)
    if match is None:
        raise ValueError("FFmpeg did not report integrated loudness")
    values = json.loads(match.group())
    measured = tuple(float(values[key]) for key in ("input_i", "input_tp"))
    if not all(map(math.isfinite, measured)):
        raise ValueError("Clip has unmeasurable loudness or true peak")
    return measured


def normalize_panel(clips, directory):
    if len(clips) not in (7, 9):
        raise ValueError("Peak correction requires the complete master panel")
    raw = [measure_clip(clip) for clip in clips]
    gains = [TARGET_LUFS - lufs for lufs, peak in raw]
    highest = max(peak + gain for (_, peak), gain in zip(raw, gains))
    attenuation = min(0., CEILING_DBTP - highest)
    target = TARGET_LUFS + attenuation
    for index, (clip, (lufs, peak), gain_db) in enumerate(zip(clips, raw, gains)):
        gain = 10 ** ((gain_db + attenuation) / 20)
        path = directory / f"clip-{index+1:02}.wav"
        sf.write(path, (clip * gain).T, RATE, subtype="PCM_24")
        pcm, sr = sf.read(path, dtype="float32", always_2d=True)
        if sr != RATE or pcm.T.shape != clip.shape:
            raise ValueError(f"PCM export geometry differs: {path}")
        final_lufs, final_peak = measure_clip(pcm.T)
        if abs(final_lufs - target) > 0.2 or final_peak > CEILING_DBTP + 0.01:
            raise ValueError(f"Playback out of tolerance: {path}, {final_lufs} LUFS, {final_peak} dBTP")
        yield path, pcm.T, gain, {
            "raw_lufs": lufs, "raw_dbtp": peak, "clip_gain_db": gain_db,
            "pair_gain_db": attenuation, "pair_target_lufs": target,
            "final_lufs": final_lufs, "final_dbtp": final_peak,
        }


def study_item(candidate, pipeline, artifacts, normalization, split, alignment_dir=None):
    source, target, geometry = extract_prepared_bridge(candidate, pipeline, include_context_audio=True)
    s, t = geometry["source_cut_sample"], geometry["target_cut_sample"]
    prefix = geometry.pop("source_audio")[:, max(0, s - 5*RATE):s]
    suffix = geometry.pop("target_audio")[:, t:t + 8*RATE]
    if prefix.shape != (2, 5*RATE) or suffix.shape != (2, 8*RATE):
        raise ValueError(f"Incomplete 5/8-second context for {candidate['candidate_id']}")
    windows = []
    for role, cue, frames, artifact in zip(
        ("source", "target"), (s, t), (pipeline.beat_frames1, pipeline.adjusted_beat_frames2), artifacts,
    ):
        index = candidate[role + "_cutpoint"]["beat_index"]
        declared = candidate[role + "_cutpoint"]["sample"]
        scale = 1.0 if role == "source" else geometry["target_sample_scale"]
        start = index if role == "source" else index - 16
        window = frames[start:start + 17]
        if (abs(round(declared * scale) - cue) > 1 or not 0 <= index < len(frames)
                or frames[index][0] != cue or start < 0 or len(window) != 17
                or any(tuple(frame[1:3]) != (i % 4 + 1, 4) for i, frame in enumerate(window))):
            raise ValueError(f"{role} cue or complete 4/4 window differs from the declared grid")
        geometry[role + "_beats"] = [frame[0] for frame in window]
        # Historical P04 control features live on the global-BPM cache grid.
        # Look up the same native downbeat in that grid, even when the audio
        # uses a cue-specific stretch. The feature and waveform scales differ.
        feature_cue = cue
        if role == "target" and pipeline.tempo_alignment == CUE_ALIGNMENT:
            feature_cue = round(declared * pipeline.bpm2 / pipeline.bpm1)
        windows.append(torch.from_numpy(artifact.model_window(feature_cue, role=role, normalization=normalization)))
    if (geometry["source_grid_end_sample"] != geometry["source_beats"][-1] or
            geometry["target_grid_start_sample"] != geometry["target_beats"][0]):
        raise ValueError("A track ends before its declared bridge boundary")
    if alignment_dir is not None:
        source = pipeline.adjusted_song1[:, s:geometry["source_grid_end_sample"]]
        target, receipt = align_target(pipeline.adjusted_song2, geometry["source_beats"],
                                       geometry["target_beats"], RATE)
        if source.shape != target.shape:
            raise ValueError("Full source span and locally aligned target differ")
        path = alignment_dir / (candidate["candidate_id"] + "-aligned.wav")
        sf.write(path, target.T, RATE, subtype="FLOAT")
        geometry.update(local_alignment=dict(**receipt, file=path.name, sha256=_file_sha256(path)),
                        transition_samples=target.shape[1], transition_seconds=target.shape[1] / RATE)
    return {
        "source_audio": torch.from_numpy(source), "target_audio": torch.from_numpy(target),
        "features_a": windows[0], "features_b": windows[1], "split": split,
        "sample_rate": RATE, "transition_length_bars": candidate["transition_length_bars"],
        "example_id": candidate["candidate_id"], "candidate_id": candidate["candidate_id"],
        "pair": pair_of(candidate), "geometry": geometry, "prefix": prefix, "suffix": suffix,
    }


def render_panel(stage, evaluator, items, selections, steps, *, rotate_anchors=False):
    if evaluator.config != Comparison.study():
        raise ValueError("P11 requires the study render contract")
    if set(selections) != set(SELECTORS) or set(selections.values()) != set(items):
        raise ValueError("Expected one cue per selector and precisely their shared pool of selected cues")
    if len({item["pair"] for item in items.values()}) != 1:
        raise ValueError("A study panel must contain one directed track pair")
    for key, item in items.items():
        if (item["candidate_id"] != key or item["prefix"].shape != (2, 5 * RATE)
                or item["suffix"].shape != (2, 8 * RATE)):
            raise ValueError("Cue identity or context differs from the study protocol")
    cached = {}
    clips, pending = [], []
    anchors = SELECTORS if rotate_anchors else ("rule",)
    conditions = [(s, c) for s in SELECTORS for c in ("E", "D")] + [(s, "anchor") for s in anchors]
    for selector, condition in conditions:
        cue = selections[selector]
        item = items[cue]
        key = cue, condition
        if key not in cached:
            if condition == "anchor":
                audio = item["source_audio"]
                row = result_row(evaluator, item, condition, audio, {}, None)
                rendered = None
            else:
                controls = (evaluator.equal_power() if condition == "E" else
                            evaluator.optimize([item], [item["pair"]], steps=steps, fixed=False))
                rendered, row = raw_result(evaluator, item, condition, controls)
                audio = rendered.audio
            clip = np.concatenate((item["prefix"], audio.numpy(), item["suffix"]), axis=-1)
            cached[key] = clip, rendered, row
        clip, rendered, row = cached[key]
        clips.append(clip)
        pending.append((item, rendered, {**row, "selector": selector}))
    rows = []
    if rotate_anchors or all("local_alignment" in item.get("geometry", {}) for item in items.values()):
        shortest = min(clip.shape[-1] for clip in clips)
        clips = [clip[:, :shortest] for clip in clips]
    for (item, rendered, row), (path, pcm, gain, stats) in zip(pending, normalize_panel(clips, stage), strict=True):
        if rendered is not None:
            start = item["prefix"].shape[-1]
            bridge = torch.from_numpy(pcm[:, start:start+row["bridge_samples"]])
            terms = evaluator.terms(item, rendered, gain=gain, playback_audio=bridge)
            row["proxy_playback"] = {k: float(v) for k, v in terms.items()}
        rows.append({**row, "wav": path.name, "wav_sha256": _file_sha256(path), "loudness": stats,
                     "suffix_frames": pcm.shape[1] - 5*RATE - row["bridge_samples"]})
    return rows


def final_ssl_provenance(manifest, ssl_cue, *, rotated=False):
    from src.ranking.continuation import METHOD, SELECTION
    method, selection = METHOD, SELECTION
    if rotated:
        from src.ranking.continuation import ISOLATED_METHOD, ISOLATED_SELECTION
        method, selection = ISOLATED_METHOD, ISOLATED_SELECTION
        decision = json.loads(selection.read_bytes())
        if decision.get("status") != "selected" or decision.get("ranking_method") != method:
            raise ValueError("The isolated-window study head has not been selected")
    ranking = manifest.get("cue_ranking", {})
    provenance = ranking.get("provenance", {})
    runtime = provenance.get("encoder_runtime", {})
    scores = ranking.get("scores", [])
    if (manifest.get("ranking_method") != method or ranking.get("ranker") != method
            or provenance.get("selection_sha256") != _file_sha256(selection)
            or not runtime.get("device", "").startswith("cuda:") or not runtime.get("gpu")
            or runtime.get("autocast") != "bfloat16" or not scores
            or scores[0]["rank"] != 1 or scores[0]["candidate_id"] != ssl_cue):
        raise ValueError("Final SSL cue requires the selected CUDA/bfloat16 MERT ranking")
    return provenance


def study(stage, args):
    panel = json.loads(args.panel.read_text(encoding="utf-8"))
    if panel["format_version"] != 1 or panel["split"] not in {"development", "final"}:
        raise ValueError("Invalid P11 panel contract")
    if panel["split"] == "final" and args.steps != 80:
        raise ValueError("Final panels require the protocol's 80 updates")
    if panel["split"] == "final" and panel.get("revision") == CUE_ALIGNMENT:
        from src.evaluation.p11_session import PROTOCOL
        if panel.get("study_protocol_sha256") != _file_sha256(PROTOCOL):
            raise ValueError("The revised study panel requires the current v2 protocol")
    selections = panel["selectors"]
    if set(selections) != set(SELECTORS):
        raise ValueError("Missing or unexpected P11 selector")
    manifest_path = Path(panel["pair_manifest"])
    if _file_sha256(manifest_path) != panel["pair_manifest_sha256"]:
        raise ValueError("Pair manifest hash differs")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    ssl_contract = ({"ssl_provenance": final_ssl_provenance(manifest, selections["ssl"],
                                                            rotated=panel.get("revision") == "cue_grid_regression_v3")}
                    if panel["split"] == "final" else {})
    candidates = manifest["candidate_generation"]["candidates"]
    selected = {c["candidate_id"]: c for c in candidates if c["candidate_id"] in selections.values()}
    if set(selected) != set(selections.values()):
        raise ValueError("Selected cue missing from the pair manifest")
    first = selected[selections["rule"]]
    if any(pair_of(c) != pair_of(first) or c["transition_length_bars"] != 4 or
           c["transition_length_beats"] != 16 or c["filter_status"] != "accepted" for c in selected.values()):
        raise ValueError("Invalid pair, cue status, or bridge length")
    if abs(first["target_bpm"] - first["source_bpm"]) / first["source_bpm"] > 0.15:
        raise ValueError("Relative tempo deviation exceeds 15%")
    run = RUNS / MODEL_RUNS[FAMILIES["R1"]] / "manifest.json"
    contract = json.loads(run.read_text(encoding="utf-8"))["contract"]
    inputs = load_fixed_inference_contract(contract, transition_bars=4)
    for role in ("source", "target"):
        track = first[role + "_track"]
        if _file_sha256(track["path"]) != track["sha256"]:
            raise ValueError(f"{role} audio hash differs")
    analysis = (PartialPreAnalysis(args.analysis_root) if args.merge_algorithm == MERGE_ALGORITHM_VERSION_V2
                else PreAnalysis(args.analysis_root, merge_algorithm=args.merge_algorithm))
    alignment = CUE_ALIGNMENT if panel.get("revision") == CUE_ALIGNMENT else LEGACY_ALIGNMENT
    pipeline = prepare_bridge_pair(first, analysis, sample_rate=RATE, tempo_alignment=alignment)
    feature_target_grid = (pipeline._scale_beat_frames(pipeline.beat_frames2, pipeline.bpm2 / pipeline.bpm1)
                           if alignment == CUE_ALIGNMENT else pipeline.adjusted_beat_frames2)
    artifacts, provenance = [], {}
    for role, grid, frames in zip(("source", "target"), (pipeline.grid_metadata1, pipeline.grid_metadata2),
                                  (pipeline.beat_frames1, feature_target_grid)):
        if not grid.is_verified_detection:
            raise ValueError(f"{role} grid lacks verified detection")
        directory = Path(panel[role + "_feature_directory"])
        artifact = _load_cached_artifact(directory, {
            "source_sha256": first[role + "_track"]["sha256"], "beat_grid_sha256": _beat_grid_hash(frames),
        })
        if artifact is None:
            raise ValueError(f"{role} feature cache missing or incompatible with the rendered grid")
        inputs.validate_track_features(artifact, role=role, original_bpm=first[role + "_bpm"],
                                       aligned_bpm=first["source_bpm"])
        artifacts.append(artifact)
        provenance[role] = {"grid": grid.to_dict(), "feature_directory": str(directory),
                            "manifest_sha256": _file_sha256(directory / "manifest.json"),
                            "data_sha256": _file_sha256(directory / artifact.manifest["data_file"])}
    evaluator = Evaluator(Comparison.study(), contract["objective"]["config"])
    alignment_dir = stage if panel.get("revision") == "local_grid_equal_duration_v2" else None
    items = {key: study_item(c, pipeline, artifacts, inputs.normalization, panel["split"], alignment_dir)
             for key, c in selected.items()}
    rows = render_panel(stage, evaluator, items, selections, args.steps,
                        rotate_anchors=panel.get("revision") == "cue_grid_regression_v3")
    version = subprocess.check_output(["ffmpeg", "-version"], text=True).splitlines()[0]
    backends = {item["geometry"]["tempo_backend"] for item in items.values()}
    versions = {name: None for name in backends}
    if "rubberband_cli_r3" in backends:
        versions["rubberband_cli_r3"] = subprocess.check_output(
            ["rubberband", "--version"], stderr=subprocess.STDOUT, text=True
        ).strip()
    if "ffmpeg_librubberband" in backends:
        versions["ffmpeg_librubberband"] = version
    backend = next(iter(backends)) if len(backends) == 1 else "per_cue"
    save_comparison(stage, {
        **evaluator.protocol(), **ssl_contract, "panel": panel, "panel_sha256": _file_sha256(args.panel),
        "r1_manifest_sha256": _file_sha256(run), "normalizer": inputs.normalization.stats_id,
        "features": provenance, "updates": args.steps, "ffmpeg": version,
        "tempo_backend": backend, "tempo_backend_version": versions.get(backend),
        **({"tempo_backend_versions": versions} if alignment == CUE_ALIGNMENT else {}),
        "meter": "FFmpeg loudnorm input_i/input_tp, dynamic measurement at 192 kHz",
        "measurement_window": "entire stereo clip including both contexts", "target_lufs": TARGET_LUFS,
        "pair_peak_ceiling_dbtp": CEILING_DBTP, "limiter": False, "output_subtype": "PCM_24",
    }, rows)
