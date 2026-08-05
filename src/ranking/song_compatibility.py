"""Rank target songs by their general suitability for transitions from one source."""

import argparse
from dataclasses import dataclass
import math
import os
from pathlib import Path

import librosa
import numpy as np

from src.analysis.pre_analysis import PreAnalysis


SONG_COMPATIBILITY_FORMAT_VERSION = 1
SONG_COMPATIBILITY_RANKER = "song_compatibility_v1"


@dataclass(frozen=True)
class SongCompatibilityConfig:
    """Transparent weights for selecting candidate target songs."""

    harmonic_weight: float = 0.35
    tempo_weight: float = 0.25
    timbre_weight: float = 0.15
    energy_weight: float = 0.15
    rhythm_weight: float = 0.10
    tempo_tolerance: float = 0.15
    energy_tolerance_db: float = 24.0

    def __post_init__(self):
        weights = (
            self.harmonic_weight,
            self.tempo_weight,
            self.timbre_weight,
            self.energy_weight,
            self.rhythm_weight,
        )
        if any(weight < 0 for weight in weights):
            raise ValueError("Compatibility weights must be greater than or equal to 0")
        if not math.isclose(sum(weights), 1.0, abs_tol=1e-9):
            raise ValueError("Compatibility weights must sum to 1.0")
        if self.tempo_tolerance <= 0:
            raise ValueError("tempo_tolerance must be greater than 0")
        if self.energy_tolerance_db <= 0:
            raise ValueError("energy_tolerance_db must be greater than 0")

    def to_dict(self):
        return {
            "harmonic_weight": self.harmonic_weight,
            "tempo_weight": self.tempo_weight,
            "timbre_weight": self.timbre_weight,
            "energy_weight": self.energy_weight,
            "rhythm_weight": self.rhythm_weight,
            "tempo_tolerance": self.tempo_tolerance,
            "energy_tolerance_db": self.energy_tolerance_db,
        }


@dataclass(frozen=True)
class SongCompatibilityScore:
    source_path: str
    target_path: str
    rank: int
    total_score: float
    component_scores: dict[str, float]
    measurements: dict[str, float]

    def to_dict(self):
        return {
            "source_path": self.source_path,
            "target_path": self.target_path,
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
class SongCompatibilityFailure:
    target_path: str
    error_type: str
    message: str

    def to_dict(self):
        return {
            "target_path": self.target_path,
            "error_type": self.error_type,
            "message": self.message,
        }


@dataclass(frozen=True)
class SongCompatibilityResult:
    source_path: str
    scores: tuple[SongCompatibilityScore, ...]
    failures: tuple[SongCompatibilityFailure, ...]
    config: SongCompatibilityConfig
    ranker: str = SONG_COMPATIBILITY_RANKER
    format_version: int = SONG_COMPATIBILITY_FORMAT_VERSION

    def to_dict(self):
        return {
            "format_version": self.format_version,
            "ranker": self.ranker,
            "source_path": self.source_path,
            "config": self.config.to_dict(),
            "scores": [score.to_dict() for score in self.scores],
            "failures": [failure.to_dict() for failure in self.failures],
        }


@dataclass(frozen=True)
class _TrackFeatures:
    bpm: float
    chroma_profile: np.ndarray
    rms_db: float
    spectral_centroid: float
    rhythm_profile: np.ndarray


def rank_song_targets(
    source_song,
    target_songs,
    *,
    analysis=None,
    analysis_location=None,
    target_sample_rate=44_100,
    config: SongCompatibilityConfig | None = None,
    feature_cache=None,
) -> SongCompatibilityResult:
    """Rank complete target songs before generating individual cutpoint pairs.

    The result is a pre-selection signal: the highest-ranked songs should be
    passed to candidate generation and its finer cutpoint ranking next.
    """
    source_path = str(Path(source_song))
    target_paths = tuple(str(Path(path)) for path in target_songs)
    if not target_paths:
        raise ValueError("At least one target song must be provided")
    if len(set(target_paths)) != len(target_paths):
        raise ValueError("Target songs must not contain duplicates")
    if source_path in target_paths:
        raise ValueError("Source song must not also be a target song")
    if int(target_sample_rate) <= 0:
        raise ValueError("target_sample_rate must be greater than 0")
    config = SongCompatibilityConfig() if config is None else config
    if analysis is None:
        cache_path = Path("output") / "pre_analysis" if analysis_location is None else Path(analysis_location)
        analysis = PreAnalysis(str(cache_path) + os.sep)

    feature_cache = {} if feature_cache is None else feature_cache
    source_features = _track_features(source_path, analysis, target_sample_rate, feature_cache)
    unranked_scores = []
    failures = []
    for target_path in target_paths:
        try:
            target_features = _track_features(target_path, analysis, target_sample_rate, feature_cache)
            unranked_scores.append(
                _score_pair(source_path, source_features, target_path, target_features, config)
            )
        except Exception as error:
            failures.append(
                SongCompatibilityFailure(
                    target_path=target_path,
                    error_type=type(error).__name__,
                    message=str(error),
                )
            )

    ordered = sorted(
        unranked_scores,
        key=lambda score: (-score["total_score"], score["target_path"]),
    )
    scores = tuple(
        SongCompatibilityScore(
            source_path=source_path,
            target_path=score["target_path"],
            rank=rank,
            total_score=score["total_score"],
            component_scores=score["component_scores"],
            measurements=score["measurements"],
        )
        for rank, score in enumerate(ordered, start=1)
    )
    return SongCompatibilityResult(source_path, scores, tuple(failures), config)


def _track_features(path, analysis, sample_rate, cache):
    cache_key = (path, int(sample_rate))
    if cache_key in cache:
        return cache[cache_key]
    bpm, _ = analysis(path)
    bpm = float(bpm)
    if bpm <= 0:
        raise ValueError("Song BPM must be greater than 0")
    audio, _ = librosa.load(path, sr=sample_rate, mono=True)
    audio = np.asarray(audio, dtype=np.float32)
    if audio.size == 0:
        raise ValueError("Song audio is empty")
    if _is_silent(audio):
        features = _TrackFeatures(
            bpm=bpm,
            chroma_profile=np.zeros(12, dtype=np.float32),
            rms_db=-120.0,
            spectral_centroid=0.0,
            rhythm_profile=np.zeros(32, dtype=np.float32),
        )
    else:
        chroma_profile = np.mean(librosa.feature.chroma_stft(y=audio, sr=sample_rate), axis=1)
        onset_strength = librosa.onset.onset_strength(y=audio, sr=sample_rate)
        features = _TrackFeatures(
            bpm=bpm,
            chroma_profile=chroma_profile,
            rms_db=_rms_db(audio),
            spectral_centroid=float(
                np.mean(librosa.feature.spectral_centroid(y=audio, sr=sample_rate))
            ),
            rhythm_profile=_resample_profile(onset_strength, length=32),
        )
    cache[cache_key] = features
    return features


def _score_pair(source_path, source, target_path, target, config):
    tempo_relative_difference = abs(source.bpm - target.bpm) / max(source.bpm, target.bpm)
    harmonic_score = _cosine_similarity(source.chroma_profile, target.chroma_profile, neutral=0.5)
    rhythm_score = _cosine_similarity(source.rhythm_profile, target.rhythm_profile, neutral=0.5)
    timbre_score, spectral_distance = _spectral_similarity(
        source.spectral_centroid,
        target.spectral_centroid,
    )
    energy_difference_db = abs(source.rms_db - target.rms_db)
    energy_score = max(0.0, 1.0 - energy_difference_db / config.energy_tolerance_db)
    tempo_score = max(0.0, 1.0 - tempo_relative_difference / config.tempo_tolerance)
    component_scores = {
        "harmonic": harmonic_score,
        "tempo": tempo_score,
        "timbre": timbre_score,
        "energy": energy_score,
        "rhythm": rhythm_score,
    }
    total_score = sum(
        component_scores[name] * weight
        for name, weight in (
            ("harmonic", config.harmonic_weight),
            ("tempo", config.tempo_weight),
            ("timbre", config.timbre_weight),
            ("energy", config.energy_weight),
            ("rhythm", config.rhythm_weight),
        )
    )
    return {
        "target_path": target_path,
        "total_score": float(np.clip(total_score, 0.0, 1.0)),
        "component_scores": component_scores,
        "measurements": {
            "source_bpm": source.bpm,
            "target_bpm": target.bpm,
            "tempo_relative_difference": tempo_relative_difference,
            "source_rms_db": source.rms_db,
            "target_rms_db": target.rms_db,
            "energy_difference_db": energy_difference_db,
            "spectral_distance_octaves": spectral_distance,
        },
    }


def _resample_profile(values, *, length):
    values = np.asarray(values, dtype=np.float32)
    if values.size == 0 or float(np.max(values)) <= 1e-12:
        return np.zeros(length, dtype=np.float32)
    positions = np.linspace(0, values.size - 1, num=length)
    profile = np.interp(positions, np.arange(values.size), values).astype(np.float32)
    norm = float(np.linalg.norm(profile))
    return profile if norm <= 1e-12 else profile / norm


def _cosine_similarity(first, second, *, neutral):
    denominator = float(np.linalg.norm(first) * np.linalg.norm(second))
    if denominator <= 1e-12:
        return neutral
    return float(np.clip(np.dot(first, second) / denominator, 0.0, 1.0))


def _spectral_similarity(source_centroid, target_centroid):
    distance = abs(math.log2((source_centroid + 20.0) / (target_centroid + 20.0)))
    return math.exp(-distance), distance


def _rms_db(audio):
    rms = float(np.sqrt(np.mean(np.square(audio, dtype=np.float64))))
    return float(20.0 * np.log10(max(rms, 1e-6)))


def _is_silent(audio):
    return float(np.max(np.abs(audio))) <= 1e-6


def _rounded(value):
    return round(float(value), 6)


def build_argument_parser():
    parser = argparse.ArgumentParser(
        description="Rank target songs by their general transition compatibility with one source song.",
    )
    parser.add_argument("source_song")
    parser.add_argument("target_songs", nargs="+")
    parser.add_argument("--analysis-location")
    parser.add_argument("--target-sample-rate", type=int, default=44_100)
    return parser


def main():
    args = build_argument_parser().parse_args()
    result = rank_song_targets(
        args.source_song,
        args.target_songs,
        analysis_location=args.analysis_location,
        target_sample_rate=args.target_sample_rate,
    )
    for score in result.scores:
        print(f"{score.rank}. {score.target_path} (score={score.total_score:.3f})")
    if result.failures:
        for failure in result.failures:
            print(f"Failed: {failure.target_path}: {failure.error_type}: {failure.message}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
