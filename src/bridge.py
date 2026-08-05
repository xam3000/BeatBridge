"""Shared extraction of sample-aligned source and target bridge waveforms."""

from __future__ import annotations

from pathlib import Path

import librosa
import numpy as np

from src.cutting.equal_power_fade_cut import EqualPowerFadeCut
from src.features.vocal import DEFAULT_DEMUCS_MODEL, extract_or_load_vocal_stem
from src.pipeline import BeatBridgePipeline, DEFAULT_SAMPLE_RATE, PROJECT_ROOT
from src.tempo.time_stretch import TimeStretch


DEFAULT_FEATURE_CACHE_ROOT = Path("output") / "feature_cache"


def extract_aligned_bridge(
    candidate,
    analysis,
    *,
    sample_rate=DEFAULT_SAMPLE_RATE,
    include_context_audio=False,
):
    """Return the aligned source-postroll and target-preroll for one candidate."""
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
    )
    source_audio, target_audio = pipeline.adjust_tempo()
    source_cut = int(
        round(
            int(candidate["source_cutpoint"]["sample"])
            * int(sample_rate)
            / DEFAULT_SAMPLE_RATE
        )
    )
    target_cut = int(
        round(
            int(candidate["target_cutpoint"]["sample"])
            * int(sample_rate)
            / DEFAULT_SAMPLE_RATE
            * pipeline.adjusted_sample_scale2
        )
    )
    source_cut, target_cut = cutter.resolve_cut_samples(
        source_audio,
        target_audio,
        source_cut,
        target_cut,
        pipeline.beat_frames1,
        pipeline.adjusted_beat_frames2,
    )
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
    transition_samples = min(source_end - source_cut, target_cut - target_start)
    if transition_samples <= 0:
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
    if include_context_audio:
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
    vocal_model=DEFAULT_DEMUCS_MODEL,
    source_vocal_artifact=None,
    target_vocal_artifact=None,
    tempo_adjuster=None,
):
    """Return sample-aligned mix and Demucs-vocal bridge waveforms."""
    source, target, geometry = extract_aligned_bridge(
        candidate,
        analysis,
        sample_rate=sample_rate,
        include_context_audio=True,
    )
    source_path = _resolve_track_path(candidate["source_track"]["path"])
    target_path = _resolve_track_path(candidate["target_track"]["path"])
    source_vocal_artifact = source_vocal_artifact or extract_or_load_vocal_stem(
        source_path,
        cache_root=feature_cache_root,
        source_sha256=candidate["source_track"]["sha256"],
        model_name=vocal_model,
    )
    target_vocal_artifact = target_vocal_artifact or extract_or_load_vocal_stem(
        target_path,
        cache_root=feature_cache_root,
        source_sha256=candidate["target_track"]["sha256"],
        model_name=vocal_model,
    )
    source_vocal = _normalise_vocal_artifact(source_vocal_artifact, sample_rate)
    target_vocal = _normalise_vocal_artifact(target_vocal_artifact, sample_rate)
    source_vocal = np.repeat(source_vocal[np.newaxis, :], 2, axis=0)
    target_vocal = np.repeat(target_vocal[np.newaxis, :], 2, axis=0)
    vocal_tempo_backend = "not_needed"
    if not np.isclose(candidate["source_bpm"], candidate["target_bpm"]):
        tempo_adjuster = tempo_adjuster or TimeStretch()
        target_vocal = tempo_adjuster.adjust_tempo_to_bpm(
            target_vocal,
            int(sample_rate),
            candidate["target_bpm"],
            candidate["source_bpm"],
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
