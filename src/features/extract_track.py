"""Extract reusable full-track features and cache them by audio/config hash."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import uuid

import librosa
import numpy as np

from src.analysis.models import unpack_analysis_result
from src.analysis.pre_analysis import PreAnalysis, ensure_bar_metadata_with_provenance
from src.features.contract import (
    FEATURE_DIMENSION,
    FEATURE_PROTOCOL_VERSION,
    SEQUENCE_LENGTH,
    feature_index,
    validate_feature_array,
    validate_feature_channels,
)
from src.features.vocal import (
    DEFAULT_DEMUCS_MODEL,
    extract_or_load_vocal_stem,
)
from src.pipeline import DEFAULT_SAMPLE_RATE, RENDER_RESULT_FORMAT_VERSION
from src.tempo import TimeStretch


TRACK_FEATURE_CACHE_FORMAT_VERSION = 1
TRACK_FEATURE_EXTRACTOR_VERSION = 2
DEFAULT_FEATURE_CACHE_ROOT = Path("output") / "feature_cache"
DEFAULT_ANALYSIS_ROOT = Path("output") / "pre_analysis"
TIME_STRETCH_POLICY = "ffmpeg_librubberband_then_cli_r3"
SPECTRAL_DESCRIPTOR_BINS = 128
EPSILON = 1e-10


@dataclass(frozen=True)
class FeatureNormalizationStats:
    """Training-split-only scale values for deferred unbounded channels."""

    spectral_flux_log1p_p99: float
    onset_strength_log1p_p99: float
    stats_id: str

    def __post_init__(self):
        if not self.stats_id:
            raise ValueError("stats_id must not be empty")
        for name in ("spectral_flux_log1p_p99", "onset_strength_log1p_p99"):
            value = float(getattr(self, name))
            if not math.isfinite(value) or value <= 0:
                raise ValueError(f"{name} must be a finite value above 0")


@dataclass(frozen=True)
class TrackFeatureArtifact:
    """One cached full-track analysis plus bridge-window extraction."""

    cache_directory: Path
    manifest: dict
    base_features: np.ndarray
    bin_boundaries: np.ndarray
    spectral_flux_raw: np.ndarray
    onset_strength_raw: np.ndarray
    cache_hit: bool

    @property
    def bin_count(self):
        return int(self.base_features.shape[0])

    def model_window(
        self,
        cue_sample,
        *,
        role,
        normalization: FeatureNormalizationStats,
    ):
        """Return one contract-valid source-postroll or target-preroll window."""
        role = str(role)
        if role not in {"source", "target"}:
            raise ValueError("role must be 'source' or 'target'")
        cue_sample = int(cue_sample)
        boundary_index = int(np.argmin(np.abs(self.bin_boundaries - cue_sample)))
        nearest_boundary = int(self.bin_boundaries[boundary_index])
        neighboring_widths = np.diff(self.bin_boundaries)
        tolerance = max(1, int(np.median(neighboring_widths) // 2))
        if abs(nearest_boundary - cue_sample) > tolerance:
            raise ValueError(
                f"Cue sample {cue_sample} is not close to a cached half-beat boundary"
            )

        start = boundary_index if role == "source" else boundary_index - SEQUENCE_LENGTH
        end = start + SEQUENCE_LENGTH
        if start < 0 or end > self.bin_count:
            raise ValueError(
                f"Track has insufficient cached context for a {role} window at "
                f"sample {cue_sample}"
            )

        features = self.base_features[start:end].copy()
        features[:, feature_index("transition_position")] = (
            np.arange(SEQUENCE_LENGTH, dtype=np.float32) + 0.5
        ) / float(SEQUENCE_LENGTH)
        features[:, feature_index("spectral_flux")] = _normalize_deferred(
            self.spectral_flux_raw[start:end],
            normalization.spectral_flux_log1p_p99,
        )
        features[:, feature_index("onset_strength")] = _normalize_deferred(
            self.onset_strength_raw[start:end],
            normalization.onset_strength_log1p_p99,
        )
        return validate_feature_array(features.astype(np.float32, copy=False))


def extract_or_load_track_features(
    song_path,
    *,
    cache_root=DEFAULT_FEATURE_CACHE_ROOT,
    analysis=None,
    analysis_root=DEFAULT_ANALYSIS_ROOT,
    sample_rate=DEFAULT_SAMPLE_RATE,
    target_bpm=None,
    tempo_adjuster=None,
    vocal_backend="disabled",
    vocal_model=DEFAULT_DEMUCS_MODEL,
    vocal_stem_loader=None,
):
    """Load one immutable cache entry or extract it from the complete track."""
    song_path = Path(song_path)
    if not song_path.is_file():
        raise FileNotFoundError(f"Audio track does not exist: {song_path}")
    sample_rate = int(sample_rate)
    if sample_rate <= 0:
        raise ValueError("sample_rate must be greater than 0")

    source_hash = _file_sha256(song_path)
    vocal_backend = str(vocal_backend)
    if vocal_backend not in {"disabled", "demucs"}:
        raise ValueError("vocal_backend must be 'disabled' or 'demucs'")
    vocal_artifact = None
    if vocal_backend == "demucs":
        vocal_stem_loader = vocal_stem_loader or extract_or_load_vocal_stem
        vocal_artifact = vocal_stem_loader(
            song_path,
            cache_root=cache_root,
            source_sha256=source_hash,
            model_name=vocal_model,
        )
    detected_sample_rate = librosa.get_samplerate(str(song_path))
    if detected_sample_rate is None or int(detected_sample_rate) <= 0:
        raise ValueError(f"Could not determine sample rate: {song_path}")
    source_sample_rate = int(detected_sample_rate)
    analysis = analysis or PreAnalysis(str(Path(analysis_root)) + os.sep)
    original_bpm, beat_frames, grid_metadata = unpack_analysis_result(
        analysis(str(song_path))
    )
    original_bpm = float(original_bpm)
    if not math.isfinite(original_bpm) or original_bpm <= 0:
        raise ValueError("Analysis BPM must be a finite value above 0")
    beat_frames, grid_metadata = ensure_bar_metadata_with_provenance(
        beat_frames,
        bpm=original_bpm,
        existing_metadata=grid_metadata,
    )
    beat_frames = _scale_beat_frames(
        beat_frames,
        sample_rate / float(source_sample_rate),
    )
    aligned_bpm = original_bpm if target_bpm is None else float(target_bpm)
    if not math.isfinite(aligned_bpm) or aligned_bpm <= 0:
        raise ValueError("target_bpm must be a finite value above 0")

    stretch_scale = original_bpm / aligned_bpm
    aligned_beat_frames = _scale_beat_frames(beat_frames, stretch_scale)
    beat_grid_hash = _beat_grid_hash(aligned_beat_frames)
    cache_config = {
        "feature_protocol_version": FEATURE_PROTOCOL_VERSION,
        "extractor_version": TRACK_FEATURE_EXTRACTOR_VERSION,
        "rendering_protocol_version": RENDER_RESULT_FORMAT_VERSION,
        "source_sha256": source_hash,
        "sample_rate": sample_rate,
        "original_bpm": original_bpm,
        "aligned_bpm": aligned_bpm,
        "beat_grid_sha256": beat_grid_hash,
        "beat_grid_metadata": grid_metadata.to_dict(),
        "time_stretch_policy": TIME_STRETCH_POLICY,
        "vocal_backend": vocal_backend,
        "vocal_model": None if vocal_artifact is None else str(vocal_model),
        "vocal_artifact_sha256": (
            None
            if vocal_artifact is None
            else vocal_artifact.manifest["artifact_sha256"]
        ),
    }
    cache_id = hashlib.sha256(
        json.dumps(cache_config, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()[:20]
    cache_directory = (
        Path(cache_root)
        / f"feature_protocol_v{FEATURE_PROTOCOL_VERSION}"
        / source_hash[:16]
        / cache_id
    )
    cached = _load_cached_artifact(cache_directory, cache_config)
    if cached is not None:
        return cached

    audio, _ = librosa.load(
        str(song_path),
        sr=sample_rate,
        mono=True,
        dtype=np.float32,
    )
    audio = np.asarray(audio, dtype=np.float32)
    if audio.size == 0 or not np.isfinite(audio).all():
        raise ValueError(f"Audio must contain finite samples: {song_path}")

    vocal_audio = None
    if vocal_artifact is not None:
        vocal_audio = np.asarray(vocal_artifact.audio, dtype=np.float32)
        if int(vocal_artifact.sample_rate) != sample_rate:
            vocal_audio = librosa.resample(
                vocal_audio,
                orig_sr=int(vocal_artifact.sample_rate),
                target_sr=sample_rate,
            ).astype(np.float32, copy=False)
        vocal_audio = _match_audio_length(vocal_audio, audio.size)

    tempo_backend = "not_needed"
    if not np.isclose(original_bpm, aligned_bpm):
        tempo_adjuster = tempo_adjuster or TimeStretch()
        audio = tempo_adjuster.adjust_tempo_to_bpm(
            audio,
            sample_rate,
            original_bpm,
            aligned_bpm,
        )
        if vocal_audio is not None:
            vocal_audio = tempo_adjuster.adjust_tempo_to_bpm(
                vocal_audio,
                sample_rate,
                original_bpm,
                aligned_bpm,
            )
            vocal_audio = _match_audio_length(vocal_audio, audio.size)
        tempo_backend = (
            getattr(tempo_adjuster, "last_backend", None)
            or type(tempo_adjuster).__name__
        )
    base_features, boundaries, flux_raw, onset_raw = _extract_track_arrays(
        audio,
        sample_rate,
        aligned_beat_frames,
        vocal_audio=vocal_audio,
    )
    validate_feature_channels(base_features, name="base_features")

    cache_directory.mkdir(parents=True, exist_ok=True)
    data_path = cache_directory / "track_features.npz"
    manifest_path = cache_directory / "manifest.json"
    _write_npz_atomic(
        data_path,
        base_features=base_features.astype(np.float32, copy=False),
        bin_boundaries=boundaries.astype(np.int64, copy=False),
        spectral_flux_raw=flux_raw.astype(np.float32, copy=False),
        onset_strength_raw=onset_raw.astype(np.float32, copy=False),
    )
    manifest = {
        "format_version": TRACK_FEATURE_CACHE_FORMAT_VERSION,
        **cache_config,
        "cache_id": cache_id,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_path": str(song_path),
        "source_sample_rate": source_sample_rate,
        "tempo_backend": tempo_backend,
        "audio_sample_count": int(audio.shape[-1]),
        "bin_count": int(base_features.shape[0]),
        "feature_dimension": FEATURE_DIMENSION,
        "dtype": "float32",
        "data_file": data_path.name,
        "deferred_normalization": [
            "spectral_flux",
            "onset_strength",
        ],
        "extractor_components": {
            "timing": "half_beat_grid_v1",
            "energy": "numpy_fft_energy_v1",
            "spectral_rhythm": "numpy_fft_change_v1",
            "harmonic": "fft_chroma_tonnetz_v1",
            "phrase": "not_implemented",
            "vocal": (
                "not_implemented"
                if vocal_artifact is None
                else "demucs_energy_activity_v1"
            ),
        },
        "vocal_artifact": (
            None
            if vocal_artifact is None
            else {
                "cache_directory": str(vocal_artifact.cache_directory),
                "cache_hit": bool(vocal_artifact.cache_hit),
                "artifact_sha256": vocal_artifact.manifest["artifact_sha256"],
                "model_name": vocal_artifact.manifest["model_name"],
                "demucs_version": vocal_artifact.manifest["demucs_version"],
                "weights": vocal_artifact.manifest["weights"],
                "paper": vocal_artifact.manifest["paper"],
            }
        ),
    }
    _write_json_atomic(manifest_path, manifest)
    return TrackFeatureArtifact(
        cache_directory=cache_directory,
        manifest=manifest,
        base_features=base_features,
        bin_boundaries=boundaries,
        spectral_flux_raw=flux_raw,
        onset_strength_raw=onset_raw,
        cache_hit=False,
    )


def normalization_stats_from_training_artifacts(artifacts, *, stats_id):
    """Fit only the two deferred p99 scales from training-track caches."""
    artifacts = tuple(artifacts)
    if not artifacts:
        raise ValueError("At least one training artifact is required")
    flux = np.concatenate([artifact.spectral_flux_raw for artifact in artifacts])
    onset = np.concatenate([artifact.onset_strength_raw for artifact in artifacts])
    return FeatureNormalizationStats(
        spectral_flux_log1p_p99=max(
            float(np.percentile(np.log1p(flux), 99)),
            EPSILON,
        ),
        onset_strength_log1p_p99=max(
            float(np.percentile(np.log1p(onset), 99)),
            EPSILON,
        ),
        stats_id=str(stats_id),
    )


def _extract_track_arrays(audio, sample_rate, beat_frames, *, vocal_audio=None):
    boundaries, beat_phases, bar_phases = _half_beat_grid(beat_frames, audio.size)
    bin_count = boundaries.size - 1
    features = np.zeros((bin_count, FEATURE_DIMENSION), dtype=np.float32)
    rms_db = np.zeros(bin_count, dtype=np.float64)
    flux_raw = np.zeros(bin_count, dtype=np.float64)
    onset_raw = np.zeros(bin_count, dtype=np.float64)
    chroma = np.zeros((bin_count, 12), dtype=np.float64)
    descriptors = np.zeros((bin_count, SPECTRAL_DESCRIPTOR_BINS), dtype=np.float64)
    low_ratios = np.zeros(bin_count, dtype=np.float64)
    vocal_rms_db = np.zeros(bin_count, dtype=np.float64)

    features[:, feature_index("beat_phase_sin")] = np.sin(2 * np.pi * beat_phases)
    features[:, feature_index("beat_phase_cos")] = np.cos(2 * np.pi * beat_phases)
    features[:, feature_index("bar_phase_sin")] = np.sin(2 * np.pi * bar_phases)
    features[:, feature_index("bar_phase_cos")] = np.cos(2 * np.pi * bar_phases)
    features[:, feature_index("audio_valid")] = 1.0
    features[:, feature_index("beat_pulse_confidence")] = 1.0

    for index, (start, end) in enumerate(zip(boundaries[:-1], boundaries[1:], strict=True)):
        segment = np.asarray(audio[int(start) : int(end)], dtype=np.float64)
        if segment.size < 4:
            raise ValueError("Half-beat grid contains an audio bin shorter than 4 samples")
        windowed = segment * np.hanning(segment.size)
        spectrum = np.fft.rfft(windowed)
        power = np.abs(spectrum) ** 2
        frequencies = np.fft.rfftfreq(segment.size, d=1.0 / sample_rate)
        total_power = max(float(np.sum(power)), EPSILON)
        rms = math.sqrt(max(float(np.mean(segment**2)), EPSILON))
        rms_db[index] = 20.0 * math.log10(rms)
        if vocal_audio is not None:
            vocal_segment = np.asarray(
                vocal_audio[int(start) : int(end)],
                dtype=np.float64,
            )
            vocal_rms = math.sqrt(
                max(float(np.mean(vocal_segment**2)), EPSILON)
            )
            vocal_rms_db[index] = 20.0 * math.log10(vocal_rms)

        low = float(np.sum(power[frequencies < 180.0])) / total_power
        mid = float(
            np.sum(power[(frequencies >= 180.0) & (frequencies < 4_000.0)])
        ) / total_power
        high = max(0.0, 1.0 - low - mid)
        low_ratios[index] = low
        features[index, feature_index("low_energy_ratio")] = low
        features[index, feature_index("mid_energy_ratio")] = mid
        features[index, feature_index("high_energy_ratio")] = high

        centroid = float(np.sum(frequencies * power) / total_power)
        bandwidth = math.sqrt(
            max(float(np.sum(((frequencies - centroid) ** 2) * power) / total_power), 0.0)
        )
        cumulative = np.cumsum(power)
        rolloff_index = min(
            int(np.searchsorted(cumulative, 0.85 * cumulative[-1])),
            frequencies.size - 1,
        )
        nyquist = sample_rate / 2.0
        features[index, feature_index("spectral_centroid")] = np.clip(
            centroid / nyquist, 0, 1
        )
        features[index, feature_index("spectral_bandwidth")] = np.clip(
            bandwidth / nyquist, 0, 1
        )
        features[index, feature_index("spectral_rolloff")] = np.clip(
            frequencies[rolloff_index] / nyquist, 0, 1
        )
        flatness = math.exp(float(np.mean(np.log(power + EPSILON)))) / max(
            float(np.mean(power)),
            EPSILON,
        )
        features[index, feature_index("spectral_flatness")] = np.clip(flatness, 0, 1)

        peak_to_rms = float(np.max(np.abs(segment))) / max(rms, EPSILON)
        features[index, feature_index("crest_factor")] = np.clip(
            (peak_to_rms - 1.0) / 19.0,
            0,
            1,
        )

        descriptor_frequency = np.linspace(0.0, nyquist, SPECTRAL_DESCRIPTOR_BINS)
        descriptor = np.interp(descriptor_frequency, frequencies, np.sqrt(power))
        descriptor /= max(float(np.sum(descriptor)), EPSILON)
        descriptors[index] = descriptor

        valid_pitch = frequencies >= 27.5
        if np.any(valid_pitch):
            midi = np.rint(
                69.0 + 12.0 * np.log2(frequencies[valid_pitch] / 440.0)
            ).astype(int)
            pitch_classes = np.mod(midi, 12)
            np.add.at(chroma[index], pitch_classes, power[valid_pitch])
            chroma[index] /= max(float(np.sum(chroma[index])), EPSILON)

        if power.size >= 3:
            local_peaks = np.zeros(power.shape, dtype=bool)
            local_peaks[1:-1] = np.logical_and(
                power[1:-1] > power[:-2],
                power[1:-1] >= power[2:],
            )
            harmonic_ratio = float(np.sum(power[local_peaks])) / total_power
            features[index, feature_index("harmonic_ratio")] = np.clip(
                harmonic_ratio,
                0,
                1,
            )

    if bin_count > 1:
        descriptor_delta = descriptors[1:] - descriptors[:-1]
        flux_raw[1:] = np.linalg.norm(descriptor_delta, axis=1)
        onset_raw[1:] = np.mean(np.maximum(descriptor_delta, 0.0), axis=1)

    features[:, feature_index("rms_dbfs")] = (
        2.0 * np.clip((rms_db + 60.0) / 60.0, 0.0, 1.0) - 1.0
    )
    median_db = float(np.median(rms_db))
    features[:, feature_index("rms_db_relative")] = np.clip(
        (rms_db - median_db) / 24.0,
        -1,
        1,
    )
    features[:, feature_index("loudness_slope")] = np.clip(
        np.diff(rms_db, prepend=rms_db[0]) / 12.0,
        -1,
        1,
    )
    order = np.argsort(np.argsort(rms_db))
    features[:, feature_index("local_energy_percentile")] = (
        order / max(bin_count - 1, 1)
    )
    features[:, feature_index("silence_probability")] = np.clip(
        (-rms_db - 45.0) / 15.0,
        0,
        1,
    )
    features[:, feature_index("kick_prominence")] = np.clip(
        low_ratios * (1.0 - np.exp(-20.0 * onset_raw)),
        0,
        1,
    )
    for pitch_class in range(12):
        features[:, feature_index(f"chroma_{pitch_class:02d}")] = chroma[:, pitch_class]
    tonnetz = librosa.feature.tonnetz(chroma=chroma.T)
    for axis in range(6):
        features[:, feature_index(f"tonnetz_{axis}")] = np.clip(
            tonnetz[axis],
            -1,
            1,
        )
    if vocal_audio is not None:
        _fill_vocal_features(features, rms_db, vocal_rms_db)
    return (
        features,
        boundaries,
        flux_raw.astype(np.float32),
        onset_raw.astype(np.float32),
    )


def _fill_vocal_features(features, mix_rms_db, vocal_rms_db):
    """Convert a Demucs vocal stem into bounded, deterministic vocal scores."""
    relative_db = vocal_rms_db - mix_rms_db
    prominence = np.clip((relative_db + 36.0) / 36.0, 0.0, 1.0)
    absolute_gate = 1.0 / (1.0 + np.exp(-(vocal_rms_db + 45.0) / 4.0))
    relative_gate = 1.0 / (1.0 + np.exp(-(relative_db + 24.0) / 4.0))
    activity = np.clip(absolute_gate * relative_gate, 0.0, 1.0)
    if activity.size > 1:
        padded = np.pad(activity, (1, 1), mode="edge")
        activity = (
            0.25 * padded[:-2] + 0.5 * padded[1:-1] + 0.25 * padded[2:]
        )
    delta = np.diff(activity, prepend=activity[0])
    onset = np.clip(delta / 0.35, 0.0, 1.0)
    offset = np.clip(-delta / 0.35, 0.0, 1.0)
    active = activity >= 0.35
    progress = np.zeros(activity.shape, dtype=np.float64)
    start = 0
    while start < active.size:
        if not active[start]:
            start += 1
            continue
        end = start + 1
        while end < active.size and active[end]:
            end += 1
        run_length = end - start
        progress[start:end] = (
            np.arange(run_length, dtype=np.float64) + 0.5
        ) / run_length
        start = end
    confidence = np.clip(2.0 * np.abs(activity - 0.5), 0.0, 1.0)
    features[:, feature_index("vocal_activity")] = activity
    features[:, feature_index("vocal_prominence")] = prominence
    features[:, feature_index("vocal_onset_probability")] = onset
    features[:, feature_index("vocal_offset_probability")] = offset
    features[:, feature_index("vocal_phrase_progress")] = progress
    features[:, feature_index("vocal_confidence")] = confidence
    features[:, feature_index("vocal_valid")] = 1.0


def _match_audio_length(audio, expected_size):
    audio = np.asarray(audio, dtype=np.float32)
    expected_size = int(expected_size)
    if audio.size >= expected_size:
        return audio[:expected_size]
    return np.pad(audio, (0, expected_size - audio.size)).astype(
        np.float32,
        copy=False,
    )


def _half_beat_grid(beat_frames, audio_sample_count):
    if len(beat_frames) < 2:
        raise ValueError("At least two beat frames are required")
    boundaries = []
    beat_phases = []
    bar_phases = []
    for left, right in zip(beat_frames[:-1], beat_frames[1:], strict=True):
        start, count_in_bar, beats_in_bar = (int(value) for value in left)
        end = int(right[0])
        if start < 0 or end > int(audio_sample_count) or end - start < 4:
            continue
        midpoint = int(round((start + end) / 2.0))
        if midpoint <= start or midpoint >= end:
            continue
        if not boundaries:
            boundaries.append(start)
        elif boundaries[-1] != start:
            raise ValueError("Beat grid contains a gap or overlapping interval")
        boundaries.extend((midpoint, end))
        for beat_phase in (0.25, 0.75):
            beat_phases.append(beat_phase)
            bar_phases.append(
                ((count_in_bar - 1) + beat_phase) / float(beats_in_bar)
            )
    if len(boundaries) < SEQUENCE_LENGTH + 1:
        raise ValueError(
            f"Track needs at least {SEQUENCE_LENGTH} complete half-beat bins"
        )
    return (
        np.asarray(boundaries, dtype=np.int64),
        np.asarray(beat_phases, dtype=np.float64),
        np.asarray(bar_phases, dtype=np.float64),
    )


def _normalize_deferred(values, log1p_p99):
    return np.clip(np.log1p(values) / float(log1p_p99), 0.0, 1.0).astype(
        np.float32
    )


def _scale_beat_frames(beat_frames, scale):
    return [
        (int(round(int(sample) * scale)), int(count), int(beats))
        for sample, count, beats in beat_frames
    ]


def _beat_grid_hash(beat_frames):
    payload = json.dumps(beat_frames, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _file_sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_cached_artifact(cache_directory, expected_config):
    manifest_path = cache_directory / "manifest.json"
    if not manifest_path.is_file():
        return None
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if any(manifest.get(key) != value for key, value in expected_config.items()):
        return None
    data_path = cache_directory / manifest["data_file"]
    if not data_path.is_file():
        return None
    with np.load(data_path, allow_pickle=False) as payload:
        base_features = payload["base_features"].astype(np.float32, copy=False)
        boundaries = payload["bin_boundaries"].astype(np.int64, copy=False)
        flux_raw = payload["spectral_flux_raw"].astype(np.float32, copy=False)
        onset_raw = payload["onset_strength_raw"].astype(np.float32, copy=False)
    validate_feature_channels(base_features, name="base_features")
    bin_count = base_features.shape[0]
    if (
        boundaries.shape != (bin_count + 1,)
        or flux_raw.shape != (bin_count,)
        or onset_raw.shape != (bin_count,)
    ):
        raise ValueError(f"Cached track-feature shapes are inconsistent: {cache_directory}")
    return TrackFeatureArtifact(
        cache_directory=cache_directory,
        manifest=manifest,
        base_features=base_features,
        bin_boundaries=boundaries,
        spectral_flux_raw=flux_raw,
        onset_strength_raw=onset_raw,
        cache_hit=True,
    )


def _write_npz_atomic(path, **arrays):
    temporary_path = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temporary_path.open("wb") as output:
            np.savez_compressed(output, **arrays)
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)


def _write_json_atomic(path, payload):
    temporary_path = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        temporary_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)


def build_argument_parser():
    parser = argparse.ArgumentParser(
        description="Extract or reuse a versioned full-track feature cache."
    )
    parser.add_argument("song")
    parser.add_argument("--cache-root", default=str(DEFAULT_FEATURE_CACHE_ROOT))
    parser.add_argument("--analysis-root", default=str(DEFAULT_ANALYSIS_ROOT))
    parser.add_argument("--sample-rate", type=int, default=DEFAULT_SAMPLE_RATE)
    parser.add_argument("--target-bpm", type=float)
    parser.add_argument(
        "--vocal-backend",
        choices=("disabled", "demucs"),
        default="demucs",
    )
    parser.add_argument("--vocal-model", default=DEFAULT_DEMUCS_MODEL)
    return parser


def main():
    args = build_argument_parser().parse_args()
    artifact = extract_or_load_track_features(
        args.song,
        cache_root=args.cache_root,
        analysis_root=args.analysis_root,
        sample_rate=args.sample_rate,
        target_bpm=args.target_bpm,
        vocal_backend=args.vocal_backend,
        vocal_model=args.vocal_model,
    )
    print(
        json.dumps(
            {
                "cache_hit": artifact.cache_hit,
                "cache_directory": str(artifact.cache_directory),
                "bin_count": artifact.bin_count,
                "feature_dimension": int(artifact.base_features.shape[-1]),
                "tempo_backend": artifact.manifest["tempo_backend"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
