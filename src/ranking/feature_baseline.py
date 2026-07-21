"""Explainable feature baseline for ranking transition candidates."""

from dataclasses import dataclass
import math
from pathlib import Path

import librosa
import numpy as np

from src.candidates import TransitionCandidate


RANKING_FORMAT_VERSION = 1
RANKER_NAME = "feature_baseline_v3"


@dataclass(frozen=True)
class FeatureRankingConfig:
    """Weights and scaling constants for the high-power ranking baseline."""

    high_power_weight: float = 0.30
    non_overlap_weight: float = 0.30
    harmonic_weight: float = 0.18
    energy_weight: float = 0.10
    timbre_weight: float = 0.05
    tempo_weight: float = 0.07
    energy_tolerance_db: float = 24.0
    tempo_tolerance: float = 0.15
    min_track_dynamic_range_db: float = 3.0
    drop_boundary_contrast_db: float = 6.0

    def __post_init__(self):
        weights = (
            self.high_power_weight,
            self.non_overlap_weight,
            self.harmonic_weight,
            self.energy_weight,
            self.timbre_weight,
            self.tempo_weight,
        )
        if any(weight < 0 for weight in weights):
            raise ValueError("Ranking weights must be greater than or equal to 0")
        if not math.isclose(sum(weights), 1.0, abs_tol=1e-9):
            raise ValueError("Ranking weights must sum to 1.0")
        if self.energy_tolerance_db <= 0:
            raise ValueError("energy_tolerance_db must be greater than 0")
        if self.tempo_tolerance <= 0:
            raise ValueError("tempo_tolerance must be greater than 0")
        if self.min_track_dynamic_range_db < 0:
            raise ValueError("min_track_dynamic_range_db must be greater than or equal to 0")
        if self.drop_boundary_contrast_db <= 0:
            raise ValueError("drop_boundary_contrast_db must be greater than 0")

    def to_dict(self):
        return {
            "high_power_weight": self.high_power_weight,
            "non_overlap_weight": self.non_overlap_weight,
            "harmonic_weight": self.harmonic_weight,
            "energy_weight": self.energy_weight,
            "timbre_weight": self.timbre_weight,
            "tempo_weight": self.tempo_weight,
            "energy_tolerance_db": self.energy_tolerance_db,
            "tempo_tolerance": self.tempo_tolerance,
            "min_track_dynamic_range_db": self.min_track_dynamic_range_db,
            "drop_boundary_contrast_db": self.drop_boundary_contrast_db,
        }


@dataclass(frozen=True)
class _WindowFeatures:
    duration_seconds: float
    rms_db: float
    chroma_profile: np.ndarray
    spectral_centroid: float


@dataclass(frozen=True)
class CandidateScore:
    """One explainable score assigned to an accepted candidate."""

    candidate_id: str
    rank: int
    total_score: float
    component_scores: dict[str, float]
    measurements: dict[str, float]

    def to_dict(self):
        return {
            "candidate_id": self.candidate_id,
            "rank": self.rank,
            "total_score": _rounded(self.total_score),
            "component_scores": {
                name: _rounded(value) for name, value in self.component_scores.items()
            },
            "measurements": {
                name: _rounded(value) for name, value in self.measurements.items()
            },
        }


@dataclass(frozen=True)
class RankingFailure:
    """A candidate that could not be scored without blocking other candidates."""

    candidate_id: str
    error_type: str
    message: str

    def to_dict(self):
        return {
            "candidate_id": self.candidate_id,
            "error_type": self.error_type,
            "message": self.message,
        }


@dataclass(frozen=True)
class CandidateRankingResult:
    """Versioned result of one feature-ranking run."""

    scores: tuple[CandidateScore, ...]
    failures: tuple[RankingFailure, ...]
    config: FeatureRankingConfig
    ranker: str = RANKER_NAME
    format_version: int = RANKING_FORMAT_VERSION

    def to_dict(self):
        return {
            "format_version": self.format_version,
            "ranker": self.ranker,
            "config": self.config.to_dict(),
            "scores": [score.to_dict() for score in self.scores],
            "failures": [failure.to_dict() for failure in self.failures],
        }


def rank_candidates(
    candidates,
    *,
    target_sample_rate=44_100,
    config: FeatureRankingConfig | None = None,
) -> CandidateRankingResult:
    """Rank candidates for a high-power to high-power transition.

    The source window ends at its cutpoint; the target high-power window starts
    at its cutpoint. Both approximately span the requested transition length.
    Track audio and repeated window features are cached. A failed candidate is
    recorded and does not prevent the remaining scores.
    """
    candidates = tuple(candidates)
    target_sample_rate = int(target_sample_rate)
    if target_sample_rate <= 0:
        raise ValueError("target_sample_rate must be greater than 0")
    config = FeatureRankingConfig() if config is None else config

    audio_cache: dict[str, np.ndarray] = {}
    feature_cache: dict[tuple[object, ...], _WindowFeatures] = {}
    energy_profile_cache: dict[str, np.ndarray] = {}
    unranked_scores = []
    failures = []
    for candidate in candidates:
        try:
            source_audio = _load_mono(
                candidate.source_track.path,
                target_sample_rate,
                audio_cache,
            )
            target_audio = _load_mono(
                candidate.target_track.path,
                target_sample_rate,
                audio_cache,
            )
            unranked_scores.append(
                _score_candidate(
                    candidate,
                    source_audio,
                    target_audio,
                    target_sample_rate,
                    config,
                    feature_cache,
                    energy_profile_cache,
                )
            )
        except Exception as error:
            failures.append(
                RankingFailure(
                    candidate_id=candidate.candidate_id,
                    error_type=type(error).__name__,
                    message=str(error),
                )
            )

    ordered = sorted(
        unranked_scores,
        key=lambda score: (-score["total_score"], score["candidate_id"]),
    )
    scores = tuple(
        CandidateScore(
            candidate_id=score["candidate_id"],
            rank=rank,
            total_score=score["total_score"],
            component_scores=score["component_scores"],
            measurements=score["measurements"],
        )
        for rank, score in enumerate(ordered, start=1)
    )
    return CandidateRankingResult(scores, tuple(failures), config)


def _load_mono(path, sample_rate, cache):
    cache_key = str(Path(path))
    if cache_key not in cache:
        audio, _ = librosa.load(cache_key, sr=sample_rate, mono=True)
        audio = np.asarray(audio, dtype=np.float32)
        if audio.size == 0:
            raise ValueError(f"Audio track is empty: {cache_key}")
        cache[cache_key] = audio
    return cache[cache_key]


def _score_candidate(
    candidate,
    source_audio,
    target_audio,
    sample_rate,
    config,
    feature_cache,
    energy_profile_cache,
):
    source_key = str(Path(candidate.source_track.path))
    target_key = str(Path(candidate.target_track.path))
    source_window = _window_features(
        source_audio,
        source_key,
        candidate.source_cutpoint.sample,
        candidate.transition_length_beats,
        candidate.source_bpm,
        sample_rate,
        "preceding",
        feature_cache,
    )
    source_transition_window = _window_features(
        source_audio,
        source_key,
        candidate.source_cutpoint.sample,
        candidate.transition_length_beats,
        candidate.source_bpm,
        sample_rate,
        "following",
        feature_cache,
    )
    target_window = _window_features(
        target_audio,
        target_key,
        candidate.target_cutpoint.sample,
        candidate.transition_length_beats,
        candidate.target_bpm,
        sample_rate,
        "following",
        feature_cache,
    )
    target_transition_window = _window_features(
        target_audio,
        target_key,
        candidate.target_cutpoint.sample,
        candidate.transition_length_beats,
        candidate.target_bpm,
        sample_rate,
        "preceding",
        feature_cache,
    )

    source_profile = _track_energy_profile(
        source_key,
        source_audio,
        energy_profile_cache,
    )
    target_profile = _track_energy_profile(
        target_key,
        target_audio,
        energy_profile_cache,
    )
    source_power_percentile = _relative_power_percentile(
        source_window.rms_db,
        source_profile,
        config.min_track_dynamic_range_db,
    )
    target_power_percentile = _relative_power_percentile(
        target_window.rms_db,
        target_profile,
        config.min_track_dynamic_range_db,
    )
    high_power_score = min(source_power_percentile, target_power_percentile)

    source_transition_percentile = _relative_power_percentile(
        source_transition_window.rms_db,
        source_profile,
        config.min_track_dynamic_range_db,
    )
    target_transition_percentile = _relative_power_percentile(
        target_transition_window.rms_db,
        target_profile,
        config.min_track_dynamic_range_db,
    )
    source_drop_fall_db = source_window.rms_db - source_transition_window.rms_db
    target_drop_rise_db = target_window.rms_db - target_transition_window.rms_db
    source_boundary_score = float(
        np.clip(source_drop_fall_db / config.drop_boundary_contrast_db, 0.0, 1.0)
    )
    target_boundary_score = float(
        np.clip(target_drop_rise_db / config.drop_boundary_contrast_db, 0.0, 1.0)
    )
    transition_low_power_score = max(
        0.0,
        1.0 - max(source_transition_percentile, target_transition_percentile),
    )
    non_overlap_score = math.sqrt(
        transition_low_power_score * min(source_boundary_score, target_boundary_score)
    )

    energy_difference_db = abs(source_window.rms_db - target_window.rms_db)
    energy_score = max(0.0, 1.0 - energy_difference_db / config.energy_tolerance_db)

    harmonic_score = _cosine_similarity(
        source_window.chroma_profile,
        target_window.chroma_profile,
        neutral=0.5,
    )
    timbre_score, spectral_distance = _spectral_similarity(
        source_window.spectral_centroid,
        target_window.spectral_centroid,
    )
    tempo_score = max(
        0.0,
        1.0 - candidate.tempo_relative_difference / config.tempo_tolerance,
    )

    component_scores = {
        "high_power": high_power_score,
        "non_overlap": non_overlap_score,
        "harmonic": harmonic_score,
        "energy": energy_score,
        "timbre": timbre_score,
        "tempo": tempo_score,
    }
    total_score = (
        high_power_score * config.high_power_weight
        + non_overlap_score * config.non_overlap_weight
        + harmonic_score * config.harmonic_weight
        + energy_score * config.energy_weight
        + timbre_score * config.timbre_weight
        + tempo_score * config.tempo_weight
    )
    return {
        "candidate_id": candidate.candidate_id,
        "total_score": float(np.clip(total_score, 0.0, 1.0)),
        "component_scores": component_scores,
        "measurements": {
            "source_high_power_window_seconds": source_window.duration_seconds,
            "target_high_power_window_seconds": target_window.duration_seconds,
            "source_rms_db": source_window.rms_db,
            "target_rms_db": target_window.rms_db,
            "source_transition_rms_db": source_transition_window.rms_db,
            "target_transition_rms_db": target_transition_window.rms_db,
            "source_power_percentile": source_power_percentile,
            "target_power_percentile": target_power_percentile,
            "source_transition_power_percentile": source_transition_percentile,
            "target_transition_power_percentile": target_transition_percentile,
            "source_drop_fall_db": source_drop_fall_db,
            "target_drop_rise_db": target_drop_rise_db,
            "energy_difference_db": energy_difference_db,
            "spectral_distance_octaves": spectral_distance,
            "tempo_relative_difference": candidate.tempo_relative_difference,
        },
    }


def _window_features(
    audio,
    track_key,
    cutpoint,
    beat_count,
    bpm,
    sample_rate,
    position,
    cache,
):
    cache_key = (track_key, int(cutpoint), int(beat_count), float(bpm), position)
    if cache_key in cache:
        return cache[cache_key]
    window, duration_seconds = _audio_window(
        audio,
        cutpoint,
        beat_count,
        bpm,
        sample_rate,
        position,
    )
    rms_db = _rms_db(window)
    if _is_silent(window):
        chroma_profile = np.zeros(12, dtype=np.float32)
        spectral_centroid = 0.0
    else:
        chroma = librosa.feature.chroma_stft(y=window, sr=sample_rate)
        chroma_profile = np.mean(chroma, axis=1)
        spectral_centroid = float(
            np.mean(librosa.feature.spectral_centroid(y=window, sr=sample_rate))
        )
    features = _WindowFeatures(
        duration_seconds=duration_seconds,
        rms_db=rms_db,
        chroma_profile=chroma_profile,
        spectral_centroid=spectral_centroid,
    )
    cache[cache_key] = features
    return features


def _audio_window(audio, cutpoint, beat_count, bpm, sample_rate, position):
    if bpm <= 0 or beat_count <= 0:
        raise ValueError("Candidate BPM and transition beat count must be greater than 0")
    requested_samples = max(1, int(round(beat_count * 60.0 / bpm * sample_rate)))
    cutpoint = min(max(0, int(cutpoint)), audio.size)
    if position == "preceding":
        start = max(0, cutpoint - requested_samples)
        end = cutpoint
    elif position == "following":
        start = cutpoint
        end = min(audio.size, cutpoint + requested_samples)
    else:
        raise ValueError(f"Unknown window position: {position}")
    if end <= start:
        raise ValueError(f"Candidate cutpoint has no {position} audio window")
    return audio[start:end], (end - start) / float(sample_rate)


def _rms_db(audio):
    rms = float(np.sqrt(np.mean(np.square(audio, dtype=np.float64))))
    return float(20.0 * np.log10(max(rms, 1e-6)))


def _spectral_similarity(source_centroid, target_centroid):
    distance = abs(math.log2((source_centroid + 20.0) / (target_centroid + 20.0)))
    return math.exp(-distance), distance


def _track_energy_profile(track_key, audio, cache):
    if track_key not in cache:
        rms = librosa.feature.rms(
            y=audio,
            frame_length=2_048,
            hop_length=512,
            center=True,
        )[0]
        cache[track_key] = 20.0 * np.log10(np.maximum(rms, 1e-6))
    return cache[track_key]


def _relative_power_percentile(rms_db, track_profile, min_dynamic_range_db):
    dynamic_range = float(
        np.percentile(track_profile, 90) - np.percentile(track_profile, 10)
    )
    if dynamic_range < min_dynamic_range_db:
        return 0.5
    return float(np.mean(track_profile <= rms_db))


def _cosine_similarity(first, second, *, neutral):
    denominator = float(np.linalg.norm(first) * np.linalg.norm(second))
    if denominator <= 1e-12:
        return neutral
    return float(np.clip(np.dot(first, second) / denominator, 0.0, 1.0))


def _is_silent(audio):
    return float(np.max(np.abs(audio))) <= 1e-6


def _rounded(value):
    return round(float(value), 6)
