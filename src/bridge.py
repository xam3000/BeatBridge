"""Shared extraction of sample-aligned source and target bridge waveforms."""

from __future__ import annotations

from pathlib import Path

import librosa
import numpy as np

from src.cutting.equal_power_fade_cut import EqualPowerFadeCut
from src.features.vocal import (
    DEFAULT_ROFORMER_MODEL,
    DEFAULT_VOCAL_BACKEND,
    extract_or_load_vocal_stem_with_backend,
)
from src.pipeline import BeatBridgePipeline, DEFAULT_SAMPLE_RATE, PROJECT_ROOT
from src.tempo.time_stretch import TimeStretch
from src.tempo.cue_alignment import CUE_ALIGNMENT, LEGACY_ALIGNMENT


DEFAULT_FEATURE_CACHE_ROOT = Path("output") / "feature_cache"


def extract_aligned_bridge(
    candidate,
    analysis,
    *,
    sample_rate=DEFAULT_SAMPLE_RATE,
    include_context_audio=False,
    tempo_alignment=CUE_ALIGNMENT,
):
    """Return the aligned source-postroll and target-preroll for one candidate."""
    pipeline = prepare_bridge_pair(candidate, analysis, sample_rate=sample_rate, tempo_alignment=tempo_alignment)
    return extract_prepared_bridge(
        candidate, pipeline, include_context_audio=include_context_audio,
    )


def prepare_bridge_pair(candidate, analysis, *, sample_rate=DEFAULT_SAMPLE_RATE, tempo_alignment=CUE_ALIGNMENT):
    """Load both tracks once. Fit the local tempo when the specific cue is known."""
    transition_beats = int(candidate["transition_length_beats"])
    cutter = EqualPowerFadeCut(fade_beats=transition_beats)
    pipeline = BeatBridgePipeline(
        candidate["source_track"]["path"],
        candidate["target_track"]["path"],
        analysis,
        TimeStretch(),
        cutter,
        target_sample_rate=int(sample_rate),
        bpm1=candidate["source_bpm"],
        bpm2=candidate["target_bpm"],
        tempo_alignment=tempo_alignment,
    )
    if tempo_alignment == LEGACY_ALIGNMENT:
        pipeline.adjust_tempo()
    return pipeline


def extract_prepared_bridge(candidate, pipeline, *, include_context_audio=False):
    """Apply the existing fade-cut geometry to one cue of the prepared pair."""
    transition_beats = int(candidate["transition_length_beats"])
    for role, track, bpm in (("source", pipeline.song1_name, pipeline.bpm1),
                             ("target", pipeline.song2_name, pipeline.bpm2)):
        declared_bpm = candidate[role + "_bpm"]
        if str(candidate[role + "_track"]["path"]) != track or (
                declared_bpm is not None and float(declared_bpm) != bpm):
            raise ValueError(f"Candidate {role} track or tempo differs from the prepared pair")
        expected_grid = (candidate.get(role + "_grid") or {}).get("beat_grid_sha256")
        metadata = pipeline.grid_metadata1 if role == "source" else pipeline.grid_metadata2
        if (pipeline.tempo_alignment == CUE_ALIGNMENT and expected_grid is not None
                and metadata.beat_grid_sha256 != expected_grid):
            raise ValueError(f"Candidate {role} beat grid differs from the analysis")
    if transition_beats != pipeline.cutter.fade_beats_before:
        raise ValueError("Candidate window differs from the prepared fade length")
    cutter = pipeline.cutter
    sample_rate = pipeline.target_sample_rate
    coordinate_rate = int(candidate.get("cue_sample_rate", DEFAULT_SAMPLE_RATE))
    if coordinate_rate <= 0:
        raise ValueError("Invalid candidate sample rate")
    if pipeline.tempo_alignment == CUE_ALIGNMENT:
        for role, frames in (("source", pipeline.beat_frames1), ("target", pipeline.beat_frames2)):
            cue = candidate[role + "_cutpoint"]
            if "beat_index" in cue:
                index = int(cue["beat_index"])
                expected = round(cue["sample"] * sample_rate / coordinate_rate)
                if not 0 <= index < len(frames) or abs(frames[index][0] - expected) > 1:
                    raise ValueError(f"Candidate {role} cue does not match the observed beat index")
    source_cut, target_cut = pipeline.adjust_at_cue(
        round(candidate["source_cutpoint"]["sample"] * sample_rate / coordinate_rate),
        round(candidate["target_cutpoint"]["sample"] * sample_rate / coordinate_rate),
        transition_beats,
    )
    source_audio, target_audio = pipeline.adjusted_song1, pipeline.adjusted_song2
    source_end = cutter._find_beat_offset_sample(
        pipeline.beat_frames1,
        source_cut,
        transition_beats,
        source_audio.shape[-1],
    )
    target_start = cutter._find_beat_offset_sample(
        pipeline.adjusted_beat_frames2,
        target_cut,
        -transition_beats,
        target_audio.shape[-1],
    )
    transition_samples = source_end - source_cut
    if pipeline.tempo_alignment == LEGACY_ALIGNMENT:
        transition_samples = min(transition_samples, target_cut - target_start)
    if transition_samples <= 0 or target_cut < transition_samples:
        raise ValueError("Candidate has no complete aligned transition window")
    source = np.asarray(
        source_audio[..., source_cut : source_cut + transition_samples],
        dtype=np.float32,
    )
    target = np.asarray(
        target_audio[..., target_cut - transition_samples : target_cut],
        dtype=np.float32,
    )
    geometry = {
        "source_cut_sample": int(source_cut),
        "target_cut_sample": int(target_cut),
        "transition_samples": int(transition_samples),
        "transition_seconds": float(transition_samples / int(sample_rate)),
        "tempo_backend": pipeline.tempo_backend,
        "sample_rate": int(sample_rate),
    }
    if pipeline.cue_alignment:
        geometry["tempo_alignment"] = pipeline.cue_alignment.to_dict()
    if include_context_audio:
        geometry["target_sample_scale"] = pipeline.adjusted_sample_scale2
        geometry["source_grid_end_sample"] = int(source_end)
        geometry["target_grid_start_sample"] = int(target_start)
        geometry["source_audio"] = source_audio
        geometry["target_audio"] = target_audio
    return source, target, geometry


def extract_aligned_vocal_bridge(
    candidate,
    analysis,
    *,
    sample_rate=DEFAULT_SAMPLE_RATE,
    include_context_audio=False,
    feature_cache_root=DEFAULT_FEATURE_CACHE_ROOT,
    vocal_backend=DEFAULT_VOCAL_BACKEND,
    vocal_model=DEFAULT_ROFORMER_MODEL,
    source_vocal_artifact=None,
    target_vocal_artifact=None,
    tempo_adjuster=None,
    tempo_alignment=CUE_ALIGNMENT,
):
    """Return sample-aligned mix and RoFormer-vocal bridge waveforms."""
    source, target, geometry = extract_aligned_bridge(
        candidate,
        analysis,
        sample_rate=sample_rate,
        include_context_audio=True,
        tempo_alignment=tempo_alignment,
    )
    source_path = _resolve_track_path(candidate["source_track"]["path"])
    target_path = _resolve_track_path(candidate["target_track"]["path"])
    source_vocal_artifact = source_vocal_artifact or extract_or_load_vocal_stem_with_backend(
        source_path,
        backend=vocal_backend,
        cache_root=feature_cache_root,
        source_sha256=candidate["source_track"]["sha256"],
        model_name=vocal_model,
    )
    target_vocal_artifact = target_vocal_artifact or extract_or_load_vocal_stem_with_backend(
        target_path,
        backend=vocal_backend,
        cache_root=feature_cache_root,
        source_sha256=candidate["target_track"]["sha256"],
        model_name=vocal_model,
    )
    source_vocal = _normalise_vocal_artifact(source_vocal_artifact, sample_rate)
    target_vocal = _normalise_vocal_artifact(target_vocal_artifact, sample_rate)
    source_vocal = np.repeat(source_vocal[np.newaxis, :], 2, axis=0)
    target_vocal = np.repeat(target_vocal[np.newaxis, :], 2, axis=0)
    vocal_tempo_backend = "not_needed"
    scale = geometry["target_sample_scale"]
    if scale != 1.0:
        tempo_adjuster = tempo_adjuster or TimeStretch()
        alignment = geometry.get("tempo_alignment")
        original_bpm = (60 * sample_rate / alignment["target_period"] if alignment
                        else float(candidate["target_bpm"]))
        desired_bpm = (60 * sample_rate / alignment["source_period"] if alignment
                       else float(candidate["source_bpm"]))
        target_vocal = tempo_adjuster.adjust_tempo_to_bpm(
            target_vocal, int(sample_rate), original_bpm, desired_bpm,
        )
        vocal_tempo_backend = tempo_adjuster.last_backend or type(tempo_adjuster).__name__
    source_vocal = _match_length(source_vocal, geometry["source_audio"].shape[-1])
    target_vocal = _match_length(target_vocal, geometry["target_audio"].shape[-1])
    transition_samples = int(geometry["transition_samples"])
    source_cut = int(geometry["source_cut_sample"])
    target_cut = int(geometry["target_cut_sample"])
    source_vocal_bridge = np.asarray(
        source_vocal[..., source_cut : source_cut + transition_samples],
        dtype=np.float32,
    )
    target_vocal_bridge = np.asarray(
        target_vocal[..., target_cut - transition_samples : target_cut],
        dtype=np.float32,
    )
    if not (
        source_vocal_bridge.shape
        == target_vocal_bridge.shape
        == source.shape
        == target.shape
    ):
        raise ValueError("Aligned mix and vocal bridges have different shapes")
    geometry.update({
        "vocal_model": str(vocal_model),
        "vocal_backend": str(vocal_backend),
        "source_vocal_artifact_sha256": source_vocal_artifact.manifest["artifact_sha256"],
        "target_vocal_artifact_sha256": target_vocal_artifact.manifest["artifact_sha256"],
        "vocal_tempo_backend": vocal_tempo_backend,
    })
    if include_context_audio:
        geometry["source_vocal_audio"] = source_vocal
        geometry["target_vocal_audio"] = target_vocal
    else:
        geometry.pop("source_audio", None)
        geometry.pop("target_audio", None)
    return source, target, source_vocal_bridge, target_vocal_bridge, geometry


def _resolve_track_path(path):
    path = Path(path)
    return path if path.is_absolute() else PROJECT_ROOT / path


def _normalise_vocal_artifact(artifact, sample_rate):
    audio = np.asarray(artifact.audio, dtype=np.float32)
    if int(artifact.sample_rate) != int(sample_rate):
        audio = librosa.resample(
            audio,
            orig_sr=int(artifact.sample_rate),
            target_sr=int(sample_rate),
            res_type="soxr_hq",
        ).astype(np.float32, copy=False)
    if audio.ndim != 1 or audio.size == 0 or not np.isfinite(audio).all():
        raise ValueError("Vocal artifact must be finite mono audio")
    return audio


def _match_length(audio, expected_samples):
    audio = np.asarray(audio, dtype=np.float32)
    expected_samples = int(expected_samples)
    if audio.shape[-1] >= expected_samples:
        return audio[..., :expected_samples]
    padding = [(0, 0)] * audio.ndim
    padding[-1] = (0, expected_samples - audio.shape[-1])
    return np.pad(audio, padding).astype(np.float32, copy=False)
