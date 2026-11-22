"""Shared native-time bar geometry, classical descriptors and production views."""

import numpy as np
from scipy import signal

from src.features.contract import feature_index
from src.features.extract_track import _extract_track_arrays, _half_beat_grid
from src.features.p07_mert import SAMPLE_RATE


CHANNELS = (
    "rms_dbfs", "rms_db_relative", "loudness_slope", "low_energy_ratio",
    "mid_energy_ratio", "high_energy_ratio", "local_energy_percentile", "crest_factor",
    "silence_probability", "spectral_centroid", "spectral_bandwidth", "spectral_rolloff",
    "spectral_flatness", "spectral_flux", "onset_strength", "kick_prominence",
    "chroma_00", "chroma_01", "chroma_02", "chroma_03", "chroma_04", "chroma_05",
    "chroma_06", "chroma_07", "chroma_08", "chroma_09", "chroma_10", "chroma_11",
    "tonnetz_0", "tonnetz_1", "tonnetz_2", "tonnetz_3", "tonnetz_4", "tonnetz_5",
    "harmonic_ratio", "vocal_activity", "vocal_prominence", "vocal_onset_probability",
    "vocal_offset_probability", "vocal_phrase_progress", "vocal_confidence",
)
CHANNEL_INDICES = [feature_index(name) for name in CHANNELS]
CLASSICAL_COLUMNS = tuple(f"{stat}:{name}" for stat in ("mean", "std") for name in CHANNELS)

PRODUCTION_VIEWS = {
    "original": None,
    "warm_room": {
        "peak_eq": [(220, 0.8, 2.0), (4200, 0.9, -2.5)],
        "gain_db": -3.0, "wet_gain": 0.065, "room_seed": 20261119,
    },
    "bright_room": {
        "peak_eq": [(260, 0.8, -2.2), (3600, 0.9, 2.5)],
        "gain_db": -5.0, "wet_gain": 0.09, "room_seed": 20261120,
    },
}
ROOM = dict(taps=48, first_ms=12, last_ms=150, decay_ms=40, alignment="causal_same_length")


def bar_geometry(frames, sample_count):
    """Return original beat indices and nine boundaries per complete 4/4 bar."""
    frames = np.asarray(frames, dtype=np.int64)
    if len(frames) < 5:
        return np.empty(0, dtype=np.int64), np.empty((0, 9), dtype=np.int64)
    intervals = np.diff(frames[:, 0])
    if np.any(intervals <= 0):
        raise ValueError("Beat positions must be strictly increasing")
    in_bounds = np.flatnonzero((frames[:, 0] >= 0) & (frames[:, 0] <= sample_count))
    usable_frames = frames[in_bounds]
    if len(usable_frames) < 17:
        return np.empty(0, dtype=np.int64), np.empty((0, 9), dtype=np.int64)
    positions = usable_frames[:, 0]
    starts = np.flatnonzero(usable_frames[:-4, 1] == 1)
    windows = usable_frames[starts[:, None] + np.arange(5)]
    durations = np.diff(windows[:, :, 0], axis=1)
    good = np.all(windows[:, :, 1] == [1, 2, 3, 4, 1], axis=1)
    good &= np.all(windows[:, :4, 2] == 4, axis=1)
    good &= np.all((durations >= 4) & (durations <= 1.5 * np.median(intervals)), axis=1)
    starts = starts[good]
    beat_samples = positions[starts[:, None] + np.arange(5)]
    bars = np.empty((starts.size, 9), dtype=np.int64)
    bars[:, ::2] = beat_samples
    bars[:, 1::2] = np.rint((beat_samples[:, :-1] + beat_samples[:, 1:]) / 2)
    return in_bounds[starts], bars


def bar_statistics(features, bins):
    values = features[bins[:, None] + np.arange(8)]
    return np.concatenate((values.mean(axis=1), values.std(axis=1, ddof=0)), axis=1)


def classical_bars(audio, vocal, frames, bars):
    features, boundaries, flux, onset = _extract_track_arrays(
        audio, SAMPLE_RATE, frames, vocal_audio=vocal
    )
    features[:, feature_index("spectral_flux")] = flux
    features[:, feature_index("onset_strength")] = onset
    bins = np.searchsorted(boundaries, bars[:, 0])
    if not np.array_equal(boundaries[bins[:, None] + np.arange(9)], bars):
        raise ValueError("Classical half-beats do not align with the shared bar grid")
    return bar_statistics(features[:, CHANNEL_INDICES], bins)


def _peak_eq(frequency, q, db):
    amp = 10 ** (db / 40)
    omega = 2 * np.pi * frequency / SAMPLE_RATE
    alpha = np.sin(omega) / (2 * q)
    middle = -2 * np.cos(omega)
    return [1 + alpha * amp, middle, 1 - alpha * amp,
            1 + alpha / amp, middle, 1 - alpha / amp]


def production_view(audio, vocal, spec):
    """Apply the same LTI EQ and room to mix and vocal, then a shared gain."""
    if spec is None:
        return audio, vocal, 0.0
    sos = np.array([_peak_eq(*band) for band in spec["peak_eq"]])
    sos /= sos[:, 3, None]
    rng = np.random.default_rng(spec["room_seed"])
    delays = np.rint(np.linspace(ROOM["first_ms"], ROOM["last_ms"], ROOM["taps"]) * SAMPLE_RATE / 1000)
    delays = delays.astype(int)
    taps = rng.choice([-1, 1], ROOM["taps"]) * np.exp(-delays / (SAMPLE_RATE * ROOM["decay_ms"] / 1000))
    impulse = np.zeros(delays[-1] + 1, dtype=np.float32)
    impulse[delays] = spec["wet_gain"] * taps / np.linalg.norm(taps)
    impulse[0] = 1.0

    def transform(samples):
        equalized = signal.sosfilt(sos, samples).astype(np.float32)
        return signal.oaconvolve(equalized, impulse, mode="full")[:len(samples)]

    mix, stem = transform(audio), transform(vocal)
    peak = float(np.max(np.abs(mix)))
    gain = min(10 ** (spec["gain_db"] / 20), 0.999 / max(peak, 1e-10))
    return mix * gain, stem * gain, float(20 * np.log10(gain))
