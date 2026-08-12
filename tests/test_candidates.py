import numpy as np
import pytest
import soundfile as sf

from src.analysis.models import AnalysisResult, BeatGridMetadata
from src.analysis.pre_analysis import ensure_bar_metadata_with_provenance
from src.candidates import CandidateGenerationConfig, TrackReference, generate_candidates
from src.pipeline import generate_transition_candidates


def _four_four_grid(bar_count=10, samples_per_beat=100):
    return [
        (bar * 4 * samples_per_beat + beat * samples_per_beat, beat + 1, 4)
        for bar in range(bar_count)
        for beat in range(4)
    ]


def _track(name):
    return TrackReference(path=f"musik/{name}.wav", sha256=f"hash-{name}")


DETECTED_GRID = BeatGridMetadata(
    grid_source="test_detector",
    fallback_used=False,
    backend_version="test_detector=1",
    confidence=0.9,
)


def _detected_grid_kwargs():
    return {
        "source_grid_metadata": DETECTED_GRID,
        "target_grid_metadata": DETECTED_GRID,
    }


def test_default_search_uses_two_or_four_bars_and_all_usable_target_boundaries():
    result = generate_candidates(
        _track("source"),
        120.0,
        _four_four_grid(bar_count=12),
        _track("target"),
        120.0,
        _four_four_grid(bar_count=12),
        **_detected_grid_kwargs(),
    )

    assert len(result.candidates) == 32
    assert {candidate.transition_length_bars for candidate in result.candidates} == {2, 4}
    assert {candidate.target_cutpoint.bar_index for candidate in result.candidates} == {4, 5, 6, 7}


def test_target_boundary_requires_complete_post_transition_bars():
    result = generate_candidates(
        _track("source"),
        120.0,
        _four_four_grid(bar_count=5),
        _track("target"),
        120.0,
        _four_four_grid(bar_count=5),
        **_detected_grid_kwargs(),
    )

    assert not result.candidates
    assert {rejection.code for rejection in result.rejections} == {
        "insufficient_source_bars",
        "insufficient_target_preroll",
    }


def test_generates_deterministic_candidates_from_last_and_first_usable_boundaries():
    config = CandidateGenerationConfig(
        transition_lengths_bars=(1, 2, 4),
        source_boundary_count=2,
        target_boundary_count=2,
    )

    result = generate_candidates(
        _track("source"),
        120.0,
        _four_four_grid(),
        _track("target"),
        120.0,
        _four_four_grid(),
        **_detected_grid_kwargs(),
        config=config,
    )

    assert len(result.candidates) == 12
    assert not result.rejections
    assert {candidate.transition_length_bars for candidate in result.candidates} == {1, 2, 4}
    assert {candidate.transition_length_beats for candidate in result.candidates} == {4, 8, 16}
    assert {candidate.source_cutpoint.bar_index for candidate in result.candidates} == {4, 5}
    assert {candidate.target_cutpoint.bar_index for candidate in result.candidates} == {4, 5}
    assert all(candidate.source_cutpoint.count_in_bar == 1 for candidate in result.candidates)
    assert all(candidate.filter_status == "accepted" for candidate in result.candidates)
    assert result.candidates[0].candidate_id == "candidate-043845385ad1bc0a"


def test_rejects_grid_without_downbeat_metadata():
    result = generate_candidates(
        _track("source"),
        120.0,
        [0, 100, 200, 300],
        _track("target"),
        120.0,
        _four_four_grid(),
        **_detected_grid_kwargs(),
    )

    assert not result.candidates
    assert result.rejections[0].code == "invalid_source_grid"


def test_strict_policy_rejects_structurally_complete_grid_with_unknown_origin():
    result = generate_candidates(
        _track("source"),
        120.0,
        _four_four_grid(),
        _track("target"),
        120.0,
        _four_four_grid(),
    )

    assert not result.candidates
    assert {item.code for item in result.rejections} == {
        "source_grid_provenance_rejected",
        "target_grid_provenance_rejected",
    }
    assert result.to_dict()["source_grid"]["fallback_used"] is None


def test_candidate_config_rejects_unknown_grid_policy():
    with pytest.raises(ValueError, match="reject.*allow"):
        CandidateGenerationConfig(approximate_grid_policy="sometimes")


def test_rejects_pair_above_tempo_tolerance():
    result = generate_candidates(
        _track("source"),
        100.0,
        _four_four_grid(),
        _track("target"),
        130.0,
        _four_four_grid(),
        **_detected_grid_kwargs(),
    )

    assert not result.candidates
    assert result.rejections[0].code == "tempo_difference_exceeds_limit"


def test_candidate_result_is_serialisable_for_a_future_manifest():
    result = generate_candidates(
        _track("source"),
        120.0,
        _four_four_grid(),
        _track("target"),
        120.0,
        _four_four_grid(),
        **_detected_grid_kwargs(),
    )

    payload = result.to_dict()

    assert payload["format_version"] == 1
    assert payload["candidates"][0]["source_track"]["sha256"] == "hash-source"
    assert payload["candidates"][0]["source_cutpoint"]["sample"] > 0
    assert payload["candidates"][0]["source_grid"]["grid_source"] == "test_detector"
    assert payload["candidates"][0]["source_grid"]["confidence"] == 0.9


def test_pipeline_api_scales_candidate_cutpoints_to_the_renderer_grid(tmp_path):
    song1 = tmp_path / "song1.wav"
    song2 = tmp_path / "song2.wav"
    sf.write(song1, np.zeros(44_100 * 20, dtype=np.float32), 44_100)
    sf.write(song2, np.zeros(48_000 * 20, dtype=np.float32), 48_000)

    class StubAnalysis:
        def __call__(self, song_path):
            info = sf.info(song_path)
            beat_step = info.samplerate // 2  # 120 BPM
            beats = [
                (sample, index % 4 + 1, 4)
                for index, sample in enumerate(range(0, info.frames, beat_step))
            ]
            return AnalysisResult(120.0, tuple(beats), DETECTED_GRID)

    result = generate_transition_candidates(
        song1,
        song2,
        analysis=StubAnalysis(),
        config=CandidateGenerationConfig(
            transition_lengths_bars=(4,),
            source_boundary_count=1,
            target_boundary_count=1,
        ),
    )

    assert len(result.candidates) == 1
    assert result.candidates[0].target_cutpoint.sample == 352_800


def test_pipeline_rejects_fallback_grid_by_default_and_allows_explicit_opt_in(tmp_path):
    song1 = tmp_path / "song1.wav"
    song2 = tmp_path / "song2.wav"
    sf.write(song1, np.zeros(44_100 * 20, dtype=np.float32), 44_100)
    sf.write(song2, np.zeros(44_100 * 20, dtype=np.float32), 44_100)

    class BareBeatAnalysis:
        def __call__(self, song_path):
            return 120.0, list(range(0, sf.info(song_path).frames, 22_050))

    rejected = generate_transition_candidates(
        song1,
        song2,
        analysis=BareBeatAnalysis(),
        config=CandidateGenerationConfig(
            transition_lengths_bars=(1,),
            source_boundary_count=1,
            target_boundary_count=1,
        ),
    )

    assert not rejected.candidates
    assert {item.code for item in rejected.rejections} == {
        "source_grid_provenance_rejected",
        "target_grid_provenance_rejected",
    }
    assert rejected.source_grid.fallback_used is True

    allowed = generate_transition_candidates(
        song1,
        song2,
        analysis=BareBeatAnalysis(),
        config=CandidateGenerationConfig(
            transition_lengths_bars=(1,),
            source_boundary_count=1,
            target_boundary_count=1,
            approximate_grid_policy="allow",
        ),
    )

    assert len(allowed.candidates) == 1
    assert allowed.candidates[0].source_cutpoint.count_in_bar == 1
    assert allowed.candidates[0].source_grid.grid_source == "fallback_from_detected_beats"
    assert allowed.to_dict()["approximate_grid_policy"] == "allow"


def test_fallback_builds_a_beat_grid_from_bpm_when_no_beats_are_detected():
    grid, metadata = ensure_bar_metadata_with_provenance(
        [], bpm=120.0, sample_count=1_000, sample_rate=100
    )

    assert grid[:5] == [(0, 1, 4), (50, 2, 4), (100, 3, 4), (150, 4, 4), (200, 1, 4)]
    assert metadata.to_dict()["grid_source"] == "fallback_from_bpm"
    assert metadata.fallback_used is True
    assert metadata.confidence == 0.0
