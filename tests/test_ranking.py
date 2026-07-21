import math

import numpy as np
import soundfile as sf

from src.candidates import CutPoint, TrackReference, TransitionCandidate
from src.ranking import rank_candidates


def _candidate(candidate_id, source_path, target_path, target_cutpoint):
    return TransitionCandidate(
        candidate_id=candidate_id,
        source_track=TrackReference(str(source_path), "source-hash"),
        target_track=TrackReference(str(target_path), "target-hash"),
        source_cutpoint=CutPoint(44_100, 4, 1, 1, 4),
        target_cutpoint=CutPoint(target_cutpoint, 4, 1, 1, 4),
        transition_length_bars=1,
        transition_length_beats=2,
        source_bpm=120.0,
        target_bpm=120.0,
        tempo_relative_difference=0.0,
        generator="test",
    )


def test_feature_ranking_prefers_matching_audio_window(tmp_path):
    sample_rate = 44_100
    time = np.arange(sample_rate * 3) / sample_rate
    source_audio = np.concatenate(
        [
            0.25 * np.sin(2 * np.pi * 440.0 * time[:sample_rate]),
            0.02 * np.sin(2 * np.pi * 330.0 * time[: sample_rate * 2]),
        ]
    )
    target_audio = np.concatenate(
        [
            0.02 * np.sin(2 * np.pi * 330.0 * time[:sample_rate]),
            0.25 * np.sin(2 * np.pi * 440.0 * time[:sample_rate]),
            0.05 * np.sin(2 * np.pi * 523.25 * time[:sample_rate]),
        ]
    )
    source_path = tmp_path / "source.wav"
    target_path = tmp_path / "target.wav"
    sf.write(source_path, source_audio, sample_rate)
    sf.write(target_path, target_audio, sample_rate)

    matching = _candidate("matching", source_path, target_path, sample_rate)
    mismatching = _candidate("mismatching", source_path, target_path, sample_rate * 2)
    result = rank_candidates((mismatching, matching), target_sample_rate=sample_rate)

    assert not result.failures
    assert [score.candidate_id for score in result.scores] == ["matching", "mismatching"]
    assert result.scores[0].rank == 1
    assert result.scores[0].total_score > result.scores[1].total_score
    assert result.scores[0].component_scores["high_power"] > result.scores[1].component_scores["high_power"]
    assert result.scores[0].component_scores["non_overlap"] > result.scores[1].component_scores["non_overlap"]
    assert result.to_dict()["ranker"] == "feature_baseline_v3"


def test_feature_ranking_handles_silent_windows_without_nan(tmp_path):
    audio_path = tmp_path / "silence.wav"
    sf.write(audio_path, np.zeros(44_100 * 3, dtype=np.float32), 44_100)
    candidate = _candidate("silence", audio_path, audio_path, 44_100)

    result = rank_candidates((candidate,))

    assert not result.failures
    assert math.isfinite(result.scores[0].total_score)
    assert 0.0 <= result.scores[0].total_score <= 1.0
