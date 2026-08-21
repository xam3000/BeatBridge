import numpy as np
import pytest
import subprocess

from src.analysis.pre_analysis import (
    MERGE_ALGORITHM_VERSION,
    MERGE_ALGORITHM_VERSION_V2,
    PARTIAL_GRID_SOURCE_V2,
    PartialPreAnalysis,
    PreAnalysis,
    _partial_merge,
    monotone_unique_beat_matches,
)
from src.analysis.models import BeatGridMetadata
from src.candidates import (
    TrackReference,
    VariableCandidateGenerationConfig,
    generate_candidates,
)
from src.candidates.generation import _parse_grid, _window_beats


def _grid(bar_count=20, samples_per_beat=100):
    return [
        (bar * 4 * samples_per_beat + beat * samples_per_beat, beat + 1, 4)
        for bar in range(bar_count)
        for beat in range(4)
    ]


def _times_and_auftakt(frames):
    samples = [frame[0] for frame in frames]
    times = np.asarray(samples, dtype=float) / 100.0
    auftakt = [(float(time), frame[1], frame[2]) for time, frame in zip(times, frames)]
    return samples, times, auftakt


def _verified_metadata():
    return BeatGridMetadata(
        grid_source=PARTIAL_GRID_SOURCE_V2,
        fallback_used=False,
        backend_version="synthetic",
        confidence=1.0,
    )


def test_v2_merge_is_additive_and_exact_full_match_has_new_identity():
    frames = _grid(bar_count=16)
    samples, times, auftakt = _times_and_auftakt(frames)

    matched, diagnostics, missing = _partial_merge(samples, times, auftakt)

    assert matched == frames
    assert diagnostics["matches"]["count"] == len(frames)
    assert diagnostics["match_coverage"] == {
        "librosa_inside_common_range": 1.0,
        "auftakt_inside_common_range": 1.0,
    }
    assert diagnostics["acceptance"]["accepted"] is True
    assert diagnostics["bars"]["longest_contiguous_complete_bar_block"] == 16
    assert missing == {"librosa": [], "auftakt": []}
    assert PreAnalysis.__init__ is not PartialPreAnalysis.__init__
    assert PreAnalysis._find_closest_beat_index is not None
    assert MERGE_ALGORITHM_VERSION != MERGE_ALGORITHM_VERSION_V2


def test_v2_merge_keeps_extra_auftakt_beats_before_and_after_as_diagnostics():
    frames = _grid(bar_count=16)
    samples, times, auftakt = _times_and_auftakt(frames)
    auftakt = [(-1.0, 4, 4), *auftakt, (times[-1] + 1.0, 1, 4)]

    matched, diagnostics, missing = _partial_merge(samples, times, auftakt)

    assert matched == frames
    assert diagnostics["unmatched"]["auftakt"] == {
        "before": 1,
        "inside": 0,
        "after": 1,
    }
    assert [item["region"] for item in missing["auftakt"]] == ["before", "after"]
    assert diagnostics["acceptance"]["accepted"] is True


def test_v2_merge_accepts_five_missing_librosa_matches_when_coverage_remains_sufficient():
    frames = _grid(bar_count=80)
    samples, times, auftakt = _times_and_auftakt(frames)
    missing_indices = {17, 89, 173, 241, 307}
    shortened_auftakt = [
        beat for index, beat in enumerate(auftakt) if index not in missing_indices
    ]

    matched, diagnostics, missing = _partial_merge(
        samples,
        times,
        shortened_auftakt,
    )

    assert len(matched) == len(frames) - len(missing_indices)
    assert len(missing["librosa"]) == 5
    assert diagnostics["match_coverage"]["librosa_inside_common_range"] > 0.98
    assert diagnostics["match_coverage"]["auftakt_inside_common_range"] > 0.98
    assert diagnostics["acceptance"]["accepted"] is True
    assert all(frame is not None and len(frame) == 3 for frame in matched)


def test_monotone_matching_does_not_reuse_an_auftakt_beat():
    matches = monotone_unique_beat_matches(
        [0.0, 1.00, 1.10, 2.0],
        [0.0, 1.05, 2.0],
    )

    assert len(matches) == 3
    assert [(left, right) for left, right, _distance in matches][0] == (0, 0)
    assert [(left, right) for left, right, _distance in matches][-1] == (3, 2)
    assert {left for left, _right, _distance in matches} <= {0, 1, 2, 3}
    assert len({right for _left, right, _distance in matches}) == len(matches)
    assert all(
        left_a < left_b and right_a < right_b
        for (left_a, right_a, _), (left_b, right_b, _) in zip(matches, matches[1:])
    )


def test_complete_mismatch_remains_fallback_eligible_only():
    frames = _grid(bar_count=16)
    samples, times, _auftakt = _times_and_auftakt(frames)
    shifted_auftakt = [(float(time + 0.5), 1, 4) for time in times]

    matched, diagnostics, missing = _partial_merge(samples, times, shifted_auftakt)

    assert matched == []
    assert diagnostics["acceptance"]["accepted"] is False
    assert diagnostics["acceptance"]["reasons"]
    assert len(missing["librosa"]) == len(frames)
    assert len(missing["auftakt"]) == len(frames)


def test_disjoint_sequences_report_before_and_after_without_inside_matches():
    frames = _grid(bar_count=8)
    samples, times, _auftakt = _times_and_auftakt(frames)
    disjoint_auftakt = [(float(time + 100.0), 1, 4) for time in times]

    _matched, diagnostics, missing = _partial_merge(samples, times, disjoint_auftakt)

    assert diagnostics["common_time_range_seconds"]["overlap"] is False
    assert diagnostics["unmatched"]["librosa"] == {
        "before": len(frames),
        "inside": 0,
        "after": 0,
    }
    assert diagnostics["unmatched"]["auftakt"] == {
        "before": 0,
        "inside": 0,
        "after": len(frames),
    }
    assert all(item["region"] == "before" for item in missing["librosa"])
    assert all(item["region"] == "after" for item in missing["auftakt"])


def test_partial_grid_with_count_gap_cannot_create_candidate_across_gap():
    frames = _grid(bar_count=40)
    missing_bar = 8
    grid_with_gap = frames[: missing_bar * 4] + frames[(missing_bar + 1) * 4 :]
    strict_grid = _parse_grid(grid_with_gap, strict_contiguity=True)
    boundary_after_gap = next(
        boundary for boundary in strict_grid.boundaries
        if boundary.sample == (missing_bar + 1) * 4 * 100
    )

    assert _window_beats(strict_grid, boundary_after_gap.bar_index, 2) is None

    result = generate_candidates(
        TrackReference("source.wav", "source"),
        120.0,
        grid_with_gap,
        TrackReference("target.wav", "target"),
        120.0,
        _grid(bar_count=40),
        source_grid_metadata=_verified_metadata(),
        target_grid_metadata=_verified_metadata(),
        config=VariableCandidateGenerationConfig(transition_lengths_bars=(2, 4, 6, 8)),
    )

    assert all(
        candidate.source_cutpoint.sample != boundary_after_gap.sample
        for candidate in result.candidates
    )
    assert {candidate.transition_length_bars for candidate in result.candidates} == {
        2,
        4,
        6,
        8,
    }


def test_v2_rejects_nonmonotone_input_without_inventing_metadata():
    with pytest.raises(ValueError, match="strictly increasing"):
        monotone_unique_beat_matches([0.0, 1.0, 0.5], [0.0, 1.0])


def test_partial_preanalysis_roundtrip_uses_new_cache_identity_and_provenance(
    tmp_path,
    monkeypatch,
):
    song = tmp_path / "synthetic.wav"
    song.write_bytes(b"synthetic-audio-placeholder")
    frames = _grid(bar_count=16)
    calls = []
    real_run = subprocess.run

    def fake_run(command, check=True, **kwargs):
        if isinstance(command, (list, tuple)) and len(command) >= 2 and command[-2] == "-r":
            assert check is True
            calls.append(command)
            output_path = command[-1]
            lines = ["synthetic aufTAKT header"] + [
                f"{sample / 100.0},{count_in_bar},{beats_in_bar}"
                for sample, count_in_bar, beats_in_bar in frames
            ]
            with open(output_path, "w", encoding="utf-8") as output:
                output.write("\n".join(lines) + "\n")
            return None
        return real_run(command, check=check, **kwargs)

    monkeypatch.setattr("src.analysis.pre_analysis.subprocess.run", fake_run)
    analysis_root = tmp_path / "analysis"
    analysis = PartialPreAnalysis(analysis_root)

    def load_song():
        analysis.song = np.zeros(100 * 64, dtype=np.float32)
        analysis.sr = 100

    def find_bpm():
        analysis.bpm = 120.0
        analysis.beat_frames = [frame[0] for frame in frames]

    analysis.load_song = load_song
    analysis.find_bpm = find_bpm
    first = analysis(song)

    assert first.grid_metadata.grid_source == PARTIAL_GRID_SOURCE_V2
    assert first.grid_metadata.fallback_used is False
    assert "sha256:" in first.grid_metadata.backend_version
    assert first.grid_metadata.analysis_id == analysis.analysis_id
    cache_path = analysis.cache_directory / "analysis.json"
    assert cache_path.is_file()
    assert analysis.analysis_config["merge"]["algorithm"] == MERGE_ALGORITHM_VERSION_V2

    second_analysis = PartialPreAnalysis(analysis_root)
    second = second_analysis(song)

    assert second == first
    assert second_analysis.previous_analysis_kind == "current"
    assert second_analysis.merge_diagnostics["matches"]["count"] == len(frames)
    assert len(calls) == 1
