"""Explainable feature baseline for ranking transition candidates."""

from dataclasses import dataclass
import math
from pathlib import Path

import librosa
import numpy as np

from src.candidates import TransitionCandidate


RANKING_FORMAT_VERSION = 1
RANKER_NAME = "feature_baseline_v1"


@dataclass(frozen=True)
class FeatureRankingConfig:
    """Weights and scaling constants for the first ranking baseline."""

    harmonic_weight: float = 0.35
    energy_weight: float = 0.30
    timbre_weight: float = 0.20
    tempo_weight: float = 0.15
    energy_tolerance_db: float = 24.0
    tempo_tolerance: float = 0.15

    def __post_init__(self):
        weights = (
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

    def to_dict(self):
        return {
            "harmonic_weight": self.harmonic_weight,
            "energy_weight": self.energy_weight,
            "timbre_weight": self.timbre_weight,
            "tempo_weight": self.tempo_weight,
            "energy_tolerance_db": self.energy_tolerance_db,
            "tempo_tolerance": self.tempo_tolerance,
        }


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
    """Rank candidates by harmony, energy, timbre, and tempo compatibility.

    Audio windows end at each candidate cutpoint and approximately span the
    requested transition length. Track audio is loaded once per unique path.
    A failed candidate is recorded and does not prevent the remaining scores.
    """
    candidates = tuple(candidates)
    target_sample_rate = int(target_sample_rate)
    if target_sample_rate <= 0:
        raise ValueError("target_sample_rate must be greater than 0")
    config = FeatureRankingConfig() if config is None else config

    audio_cache: dict[str, np.ndarray] = {}
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


def _score_candidate(candidate, source_audio, target_audio, sample_rate, config):
    source_window, source_seconds = _transition_window(
        source_audio,
        candidate.source_cutpoint.sample,
        candidate.transition_length_beats,
        candidate.source_bpm,
        sample_rate,
    )
    target_window, target_seconds = _transition_window(
        target_audio,
        candidate.target_cutpoint.sample,
        candidate.transition_length_beats,
        candidate.target_bpm,
        sample_rate,
    )

    source_rms_db = _rms_db(source_window)
    target_rms_db = _rms_db(target_window)
    energy_difference_db = abs(source_rms_db - target_rms_db)
    energy_score = max(0.0, 1.0 - energy_difference_db / config.energy_tolerance_db)

    harmonic_score = _chroma_similarity(source_window, target_window, sample_rate)
    timbre_score, spectral_distance = _spectral_similarity(
        source_window,
        target_window,
        sample_rate,
    )
    tempo_score = max(
        0.0,
        1.0 - candidate.tempo_relative_difference / config.tempo_tolerance,
    )

    component_scores = {
        "harmonic": harmonic_score,
        "energy": energy_score,
        "timbre": timbre_score,
        "tempo": tempo_score,
    }
    total_score = (
        harmonic_score * config.harmonic_weight
        + energy_score * config.energy_weight
        + timbre_score * config.timbre_weight
        + tempo_score * config.tempo_weight
    )
    return {
        "candidate_id": candidate.candidate_id,
        "total_score": float(np.clip(total_score, 0.0, 1.0)),
        "component_scores": component_scores,
        "measurements": {
            "source_window_seconds": source_seconds,
            "target_window_seconds": target_seconds,
            "source_rms_db": source_rms_db,
            "target_rms_db": target_rms_db,
            "energy_difference_db": energy_difference_db,
            "spectral_distance_octaves": spectral_distance,
            "tempo_relative_difference": candidate.tempo_relative_difference,
        },
    }


def _transition_window(audio, cutpoint, beat_count, bpm, sample_rate):
    if bpm <= 0 or beat_count <= 0:
        raise ValueError("Candidate BPM and transition beat count must be greater than 0")
    requested_samples = max(1, int(round(beat_count * 60.0 / bpm * sample_rate)))
    end = min(max(0, int(cutpoint)), audio.size)
    start = max(0, end - requested_samples)
    if end <= start:
        raise ValueError("Candidate cutpoint has no preceding audio window")
    return audio[start:end], (end - start) / float(sample_rate)


def _rms_db(audio):
    rms = float(np.sqrt(np.mean(np.square(audio, dtype=np.float64))))
    return float(20.0 * np.log10(max(rms, 1e-6)))


def _chroma_similarity(source, target, sample_rate):
    if _is_silent(source) or _is_silent(target):
        return 0.5
    source_chroma = librosa.feature.chroma_stft(y=source, sr=sample_rate)
    target_chroma = librosa.feature.chroma_stft(y=target, sr=sample_rate)
    source_profile = np.mean(source_chroma, axis=1)
    target_profile = np.mean(target_chroma, axis=1)
    return _cosine_similarity(source_profile, target_profile, neutral=0.5)


def _spectral_similarity(source, target, sample_rate):
    source_centroid = float(np.mean(librosa.feature.spectral_centroid(y=source, sr=sample_rate)))
    target_centroid = float(np.mean(librosa.feature.spectral_centroid(y=target, sr=sample_rate)))
    distance = abs(math.log2((source_centroid + 20.0) / (target_centroid + 20.0)))
    return math.exp(-distance), distance


def _cosine_similarity(first, second, *, neutral):
    denominator = float(np.linalg.norm(first) * np.linalg.norm(second))
    if denominator <= 1e-12:
        return neutral
    return float(np.clip(np.dot(first, second) / denominator, 0.0, 1.0))


def _is_silent(audio):
    return float(np.max(np.abs(audio))) <= 1e-6


def _rounded(value):
    return round(float(value), 6)
