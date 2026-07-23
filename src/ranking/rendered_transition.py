"""Explainable baseline metric for already rendered transition audio."""

from dataclasses import dataclass
import math

import librosa
import numpy as np


RENDERED_TRANSITION_METRIC_FORMAT_VERSION = 1
RENDERED_TRANSITION_METRIC_NAME = "rendered_transition_baseline_v1"


@dataclass(frozen=True)
class RenderedTransitionMetricConfig:
    """Weights and scaling constants for the rendered-audio baseline."""

    energy_shape_weight: float = 0.30
    boundary_smoothness_weight: float = 0.30
    harmonic_continuity_weight: float = 0.20
    rhythmic_stability_weight: float = 0.20
    desired_energy_contrast_db: float = 6.0
    boundary_rms_tolerance_db: float = 12.0
    boundary_window_seconds: float = 0.10
    click_context_seconds: float = 0.25
    onset_hop_length: int = 512

    def __post_init__(self):
        weights = (
            self.energy_shape_weight,
            self.boundary_smoothness_weight,
            self.harmonic_continuity_weight,
            self.rhythmic_stability_weight,
        )
        if any(weight < 0 for weight in weights):
            raise ValueError("Rendered-transition metric weights must be non-negative")
        if not math.isclose(sum(weights), 1.0, abs_tol=1e-9):
            raise ValueError("Rendered-transition metric weights must sum to 1.0")
        if self.desired_energy_contrast_db <= 0:
            raise ValueError("desired_energy_contrast_db must be greater than 0")
        if self.boundary_rms_tolerance_db <= 0:
            raise ValueError("boundary_rms_tolerance_db must be greater than 0")
        if self.boundary_window_seconds <= 0:
            raise ValueError("boundary_window_seconds must be greater than 0")
        if self.click_context_seconds <= 0:
            raise ValueError("click_context_seconds must be greater than 0")
        if int(self.onset_hop_length) <= 0:
            raise ValueError("onset_hop_length must be greater than 0")

    def to_dict(self):
        return {
            "energy_shape_weight": self.energy_shape_weight,
            "boundary_smoothness_weight": self.boundary_smoothness_weight,
            "harmonic_continuity_weight": self.harmonic_continuity_weight,
            "rhythmic_stability_weight": self.rhythmic_stability_weight,
            "desired_energy_contrast_db": self.desired_energy_contrast_db,
            "boundary_rms_tolerance_db": self.boundary_rms_tolerance_db,
            "boundary_window_seconds": self.boundary_window_seconds,
            "click_context_seconds": self.click_context_seconds,
            "onset_hop_length": self.onset_hop_length,
        }


@dataclass(frozen=True)
class RenderedTransitionInput:
    """One rendered variant plus the musical boundaries needed for scoring."""

    candidate_id: str
    renderer: str
    audio: np.ndarray
    sample_rate: int
    transition_start_sample: int
    transition_end_sample: int
    transition_length_beats: int
    bpm: float


@dataclass(frozen=True)
class RenderedTransitionScore:
    candidate_id: str
    renderer: str
    rank: int
    total_score: float
    component_scores: dict[str, float]
    measurements: dict[str, float]

    @property
    def variant_id(self):
        return f"{self.candidate_id}::{self.renderer}"

    def to_dict(self):
        return {
            "variant_id": self.variant_id,
            "candidate_id": self.candidate_id,
            "renderer": self.renderer,
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
class RenderedTransitionMetricFailure:
    candidate_id: str
    renderer: str
    error_type: str
    message: str

    def to_dict(self):
        return {
            "variant_id": f"{self.candidate_id}::{self.renderer}",
            "candidate_id": self.candidate_id,
            "renderer": self.renderer,
            "error_type": self.error_type,
            "message": self.message,
        }


@dataclass(frozen=True)
class RenderedTransitionRankingResult:
    scores: tuple[RenderedTransitionScore, ...]
    failures: tuple[RenderedTransitionMetricFailure, ...]
    config: RenderedTransitionMetricConfig
    metric: str = RENDERED_TRANSITION_METRIC_NAME
    format_version: int = RENDERED_TRANSITION_METRIC_FORMAT_VERSION

    def to_dict(self):
        return {
            "format_version": self.format_version,
            "metric": self.metric,
            "config": self.config.to_dict(),
            "scores": [score.to_dict() for score in self.scores],
            "failures": [failure.to_dict() for failure in self.failures],
        }


def rank_rendered_transitions(
    rendered_transitions,
    *,
    config: RenderedTransitionMetricConfig | None = None,
) -> RenderedTransitionRankingResult:
    """Score and rank rendered variants without aborting on one bad variant."""
    config = RenderedTransitionMetricConfig() if config is None else config
    unranked = []
    failures = []
    for rendered in tuple(rendered_transitions):
        try:
            unranked.append(_score_rendered_transition(rendered, config))
        except Exception as error:
            failures.append(
                RenderedTransitionMetricFailure(
                    candidate_id=rendered.candidate_id,
                    renderer=rendered.renderer,
                    error_type=type(error).__name__,
                    message=str(error),
                )
            )

    ordered = sorted(
        unranked,
        key=lambda score: (
            -score["total_score"],
            score["candidate_id"],
            score["renderer"],
        ),
    )
    scores = tuple(
        RenderedTransitionScore(
            candidate_id=score["candidate_id"],
            renderer=score["renderer"],
            rank=rank,
            total_score=score["total_score"],
            component_scores=score["component_scores"],
            measurements=score["measurements"],
        )
        for rank, score in enumerate(ordered, start=1)
    )
    return RenderedTransitionRankingResult(scores, tuple(failures), config)


def _score_rendered_transition(rendered, config):
    sample_rate = int(rendered.sample_rate)
    bpm = float(rendered.bpm)
    transition_beats = int(rendered.transition_length_beats)
    if sample_rate <= 0:
        raise ValueError("sample_rate must be greater than 0")
    if bpm <= 0 or transition_beats <= 0:
        raise ValueError("bpm and transition_length_beats must be greater than 0")

    audio = _to_mono(rendered.audio)
    if audio.size == 0:
        raise ValueError("Rendered transition audio is empty")

    start = int(rendered.transition_start_sample)
    end = int(rendered.transition_end_sample)
    if start < 0 or start >= audio.size:
        raise ValueError("transition_start_sample is outside the rendered audio")
    if end < start or end > audio.size:
        raise ValueError("transition_end_sample is outside the rendered audio")

    expected_samples = max(
        1,
        int(round(transition_beats * 60.0 / bpm * sample_rate)),
    )
    has_bridge = end > start
    analysis_end = end if has_bridge else min(audio.size, start + expected_samples)
    if analysis_end <= start:
        raise ValueError("Rendered transition has no audio after its start")

    pre = audio[max(0, start - expected_samples) : start]
    transition = audio[start:analysis_end]
    post = audio[analysis_end : min(audio.size, analysis_end + expected_samples)]
    if pre.size == 0 or post.size == 0:
        raise ValueError("Rendered preview needs audio before and after the transition")

    pre_rms_db = _rms_db(pre)
    transition_rms_db = _rms_db(transition)
    post_rms_db = _rms_db(post)
    energy_fall_db = pre_rms_db - transition_rms_db
    energy_rise_db = post_rms_db - transition_rms_db
    fall_score = float(
        np.clip(energy_fall_db / config.desired_energy_contrast_db, 0.0, 1.0)
    )
    rise_score = float(
        np.clip(energy_rise_db / config.desired_energy_contrast_db, 0.0, 1.0)
    )
    energy_shape_score = math.sqrt(fall_score * rise_score)

    boundaries = (start, end) if has_bridge else (start,)
    boundary_scores = [
        _boundary_smoothness(audio, boundary, sample_rate, config)
        for boundary in boundaries
    ]
    boundary_smoothness_score = float(np.mean([item["score"] for item in boundary_scores]))

    pre_chroma = _chroma_profile(pre, sample_rate)
    post_chroma = _chroma_profile(post, sample_rate)
    if has_bridge:
        split = max(1, transition.size // 2)
        transition_start_chroma = _chroma_profile(transition[:split], sample_rate)
        transition_end_chroma = _chroma_profile(transition[split:], sample_rate)
        harmonic_continuity_score = float(
            np.mean(
                [
                    _cosine_similarity(pre_chroma, transition_start_chroma),
                    _cosine_similarity(transition_end_chroma, post_chroma),
                ]
            )
        )
    else:
        harmonic_continuity_score = _cosine_similarity(pre_chroma, post_chroma)

    local_start = max(0, start - expected_samples)
    local_end = min(audio.size, analysis_end + expected_samples)
    rhythmic_stability_score, beat_autocorrelation = _rhythmic_stability(
        audio[local_start:local_end],
        sample_rate,
        bpm,
        config.onset_hop_length,
    )

    component_scores = {
        "energy_shape": energy_shape_score,
        "boundary_smoothness": boundary_smoothness_score,
        "harmonic_continuity": harmonic_continuity_score,
        "rhythmic_stability": rhythmic_stability_score,
    }
    total_score = (
        energy_shape_score * config.energy_shape_weight
        + boundary_smoothness_score * config.boundary_smoothness_weight
        + harmonic_continuity_score * config.harmonic_continuity_weight
        + rhythmic_stability_score * config.rhythmic_stability_weight
    )
    return {
        "candidate_id": rendered.candidate_id,
        "renderer": rendered.renderer,
        "total_score": float(np.clip(total_score, 0.0, 1.0)),
        "component_scores": component_scores,
        "measurements": {
            "transition_start_seconds": start / float(sample_rate),
            "transition_end_seconds": end / float(sample_rate),
            "actual_transition_seconds": (end - start) / float(sample_rate),
            "expected_transition_seconds": expected_samples / float(sample_rate),
            "pre_window_seconds": pre.size / float(sample_rate),
            "transition_window_seconds": transition.size / float(sample_rate),
            "post_window_seconds": post.size / float(sample_rate),
            "pre_rms_db": pre_rms_db,
            "transition_rms_db": transition_rms_db,
            "post_rms_db": post_rms_db,
            "energy_fall_db": energy_fall_db,
            "energy_rise_db": energy_rise_db,
            "boundary_count": float(len(boundary_scores)),
            "mean_boundary_rms_difference_db": float(
                np.mean([item["rms_difference_db"] for item in boundary_scores])
            ),
            "mean_boundary_click_ratio": float(
                np.mean([item["click_ratio"] for item in boundary_scores])
            ),
            "beat_autocorrelation": beat_autocorrelation,
        },
    }


def _to_mono(audio):
    audio = np.asarray(audio, dtype=np.float32)
    if audio.ndim == 1:
        return audio
    if audio.ndim == 2:
        return np.mean(audio, axis=0, dtype=np.float32)
    raise ValueError("Rendered audio must have shape (samples,) or (channels, samples)")


def _boundary_smoothness(audio, boundary, sample_rate, config):
    window_samples = max(1, int(round(config.boundary_window_seconds * sample_rate)))
    left = audio[max(0, boundary - window_samples) : boundary]
    right = audio[boundary : min(audio.size, boundary + window_samples)]
    if left.size == 0 or right.size == 0:
        raise ValueError("Transition boundary needs audio on both sides")

    rms_difference_db = abs(_rms_db(left) - _rms_db(right))
    rms_score = math.exp(-rms_difference_db / config.boundary_rms_tolerance_db)

    context_samples = max(2, int(round(config.click_context_seconds * sample_rate)))
    context = audio[
        max(0, boundary - context_samples) : min(audio.size, boundary + context_samples)
    ]
    differences = np.abs(np.diff(context.astype(np.float64, copy=False)))
    typical_difference = float(np.percentile(differences, 99)) if differences.size else 0.0
    boundary_jump = abs(float(right[0]) - float(left[-1]))
    if typical_difference <= 1e-9:
        click_ratio = 0.0 if boundary_jump <= 1e-9 else 10.0
    else:
        click_ratio = boundary_jump / typical_difference
    click_score = math.exp(-max(0.0, click_ratio - 1.0))
    return {
        "score": math.sqrt(rms_score * click_score),
        "rms_difference_db": rms_difference_db,
        "click_ratio": click_ratio,
    }


def _rhythmic_stability(audio, sample_rate, bpm, hop_length):
    if _is_silent(audio):
        return 0.5, 0.0
    onset_envelope = librosa.onset.onset_strength(
        y=audio,
        sr=sample_rate,
        hop_length=hop_length,
    )
    onset_envelope = np.asarray(onset_envelope, dtype=np.float64)
    onset_envelope -= np.mean(onset_envelope)
    if onset_envelope.size < 3 or float(np.linalg.norm(onset_envelope)) <= 1e-9:
        return 0.5, 0.0

    beat_lag = max(1, int(round(60.0 * sample_rate / (bpm * hop_length))))
    if beat_lag >= onset_envelope.size:
        return 0.5, 0.0
    numerator = float(np.dot(onset_envelope[:-beat_lag], onset_envelope[beat_lag:]))
    denominator = float(
        np.linalg.norm(onset_envelope[:-beat_lag])
        * np.linalg.norm(onset_envelope[beat_lag:])
    )
    correlation = 0.0 if denominator <= 1e-12 else numerator / denominator
    correlation = float(np.clip(correlation, -1.0, 1.0))
    return float(np.clip((correlation + 1.0) / 2.0, 0.0, 1.0)), correlation


def _chroma_profile(audio, sample_rate):
    if audio.size == 0 or _is_silent(audio):
        return np.zeros(12, dtype=np.float32)
    chroma = librosa.feature.chroma_stft(y=audio, sr=sample_rate)
    return np.mean(chroma, axis=1)


def _cosine_similarity(first, second):
    denominator = float(np.linalg.norm(first) * np.linalg.norm(second))
    if denominator <= 1e-12:
        return 0.5
    return float(np.clip(np.dot(first, second) / denominator, 0.0, 1.0))


def _rms_db(audio):
    rms = float(np.sqrt(np.mean(np.square(audio, dtype=np.float64))))
    return float(20.0 * np.log10(max(rms, 1e-6)))


def _is_silent(audio):
    return float(np.max(np.abs(audio))) <= 1e-6


def _rounded(value):
    return round(float(value), 6)
