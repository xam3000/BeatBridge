import json

import pytest

from src.analysis.models import BeatGridMetadata
from src.candidates.models import TrackReference
from src.candidates.variable import (
    VariableCandidateGenerationConfig,
    generate_variable_candidates_from_grids,
)
from src.features.dataset_export import SplitConfig
from src.features.variable_split import (
    bind_variable_split_authority,
    build_variable_split_authority,
    extend_variable_split_authority,
    load_variable_split_authority,
)
from src.ml.variable_data import VariableFeatureDatasetCollection
from src.ml.variable_runner import build_variable_training_contract
from src.variable_rendering import render_variable_transition


def _metadata():
    return BeatGridMetadata(
        grid_source="detected",
        fallback_used=False,
        backend_version="hardening-test",
        confidence=1.0,
    )


def _grid(beats_per_bar):
    return [
        (index * 100, (index % beats_per_bar) + 1, beats_per_bar)
        for index in range(96)
    ]


def _mixed_grid(bar_meters):
    frames = []
    for beats_per_bar in bar_meters:
        for count_in_bar in range(1, beats_per_bar + 1):
            frames.append((len(frames) * 100, count_in_bar, beats_per_bar))
    return frames


def test_variable_inputs_reject_fractional_lengths_before_integer_casting(tmp_path):
    with pytest.raises(ValueError, match="integer"):
        VariableCandidateGenerationConfig(transition_lengths_bars=(2.5,))
    with pytest.raises(ValueError, match="integer"):
        VariableFeatureDatasetCollection(
            tmp_path / "missing-dataset",
            "train",
            transition_length_bars=(2.5,),
        )
    with pytest.raises(ValueError, match="integer"):
        build_variable_training_contract(
            dataset_manifest_sha256="a" * 64,
            supported_lengths=(2.5,),
        )


def test_variable_candidates_reject_when_only_non_four_four_windows_exist():
    result = generate_variable_candidates_from_grids(
        TrackReference("source.wav", "a" * 64),
        120.0,
        _grid(3),
        TrackReference("target.wav", "b" * 64),
        120.0,
        _grid(3),
        source_grid_metadata=_metadata(),
        target_grid_metadata=_metadata(),
        config=VariableCandidateGenerationConfig(
            transition_lengths_bars=(2,),
            source_boundary_count=1,
            target_boundary_count=1,
        ),
    )
    assert not result.candidates
    assert [item.code for item in result.rejections] == ["unsupported_meter"]


def test_variable_candidates_keep_local_four_four_windows_in_mixed_meter_tracks():
    grid = _mixed_grid([4] * 20 + [3] * 3 + [4] * 20)
    result = generate_variable_candidates_from_grids(
        TrackReference("source.wav", "a" * 64),
        120.0,
        grid,
        TrackReference("target.wav", "b" * 64),
        120.0,
        grid,
        source_grid_metadata=_metadata(),
        target_grid_metadata=_metadata(),
        config=VariableCandidateGenerationConfig(
            transition_lengths_bars=(2, 4, 6, 8),
            source_boundary_count=1,
            target_boundary_count=1,
        ),
    )

    assert {item.transition_length_bars for item in result.candidates} == {
        2,
        4,
        6,
        8,
    }
    assert all(item.source_cutpoint.beats_in_bar == 4 for item in result.candidates)
    assert all(item.target_cutpoint.beats_in_bar == 4 for item in result.candidates)
    assert all(
        item.transition_length_beats == item.transition_length_bars * 4
        for item in result.candidates
    )
    assert not any(item.code == "unsupported_meter" for item in result.rejections)


def test_variable_candidates_do_not_reject_meter_when_any_requested_length_works():
    grid = _mixed_grid([4] * 12 + [3] * 20)
    result = generate_variable_candidates_from_grids(
        TrackReference("source.wav", "a" * 64),
        120.0,
        grid,
        TrackReference("target.wav", "b" * 64),
        120.0,
        grid,
        source_grid_metadata=_metadata(),
        target_grid_metadata=_metadata(),
        config=VariableCandidateGenerationConfig(
            transition_lengths_bars=(2, 8),
            source_boundary_count=1,
            target_boundary_count=1,
        ),
    )

    assert {item.transition_length_bars for item in result.candidates} == {2}
    assert not any(item.code == "unsupported_meter" for item in result.rejections)


def test_variable_split_loader_rejects_tampered_mapping_hash(tmp_path):
    mapping = {"a" * 64: "train", "b" * 64: "validation"}
    path = tmp_path / "split-authority.json"
    path.write_text(
        json.dumps(
            {
                "format_version": 1,
                "source": "hardening-test",
                "mapping_sha256": "0" * 64,
                "track_assignments": [
                    {"sha256": key, "split": value}
                    for key, value in mapping.items()
                ],
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="mapping hash differs"):
        load_variable_split_authority(path, mapping)


def test_split_extension_preserves_base_and_keeps_recording_groups_together():
    base_track = "a" * 64
    alternate_a = "b" * 64
    alternate_b = "c" * 64
    authority = extend_variable_split_authority(
        {base_track: "test"},
        {
            base_track: "recording-existing",
            alternate_a: "recording-new",
            alternate_b: "recording-new",
        },
        split_config=SplitConfig(seed=17),
    )
    assert authority.assignments[base_track] == "test"
    assert authority.assignments[alternate_a] == authority.assignments[alternate_b]
    assert authority.recording_groups[alternate_a] == "recording-new"
    assert authority.policy["base_mapping_sha256"]
    assert authority.policy["recording_group_mapping_sha256"]


def test_split_extension_rejects_group_crossing_frozen_splits():
    with pytest.raises(ValueError, match="spans frozen splits"):
        extend_variable_split_authority(
            {"a" * 64: "train", "b" * 64: "validation"},
            {"a" * 64: "same-recording", "b" * 64: "same-recording"},
        )


def test_generated_and_bound_split_authorities_keep_mapping_stable():
    hashes = ("a" * 64, "b" * 64, "c" * 64)
    generated = build_variable_split_authority(
        hashes,
        {(track, track): 1 for track in hashes},
        source_manifest_sha256="d" * 64,
    )
    bound = bind_variable_split_authority(
        generated,
        source_manifest_sha256="e" * 64,
        parent_authority_sha256="f" * 64,
    )
    assert bound.assignments == generated.assignments
    assert bound.mapping_sha256 == generated.mapping_sha256
    assert bound.source_manifest_sha256 == "e" * 64
    assert bound.policy["parent_authority_sha256"] == "f" * 64


def test_variable_renderer_rejects_inconsistent_candidate_geometry():
    candidate = type(
        "Candidate",
        (),
        {
            "format_version": 2,
            "transition_length_bars": 2,
            "transition_length_beats": 7,
        },
    )()
    with pytest.raises(ValueError, match="does not match"):
        render_variable_transition(candidate)


def test_training_contract_binds_waveform_cache_index_and_root_manifest():
    contract = build_variable_training_contract(
        dataset_manifest_sha256="a" * 64,
        waveform_cache_index_sha256="b" * 64,
        waveform_cache_root_manifest_sha256="c" * 64,
    )
    assert contract["waveform_cache_index_sha256"] == "b" * 64
    assert contract["waveform_cache_root_manifest_sha256"] == "c" * 64
    assert contract["waveform_cache_index_format_version"] == 1
    with pytest.raises(ValueError, match="[Bb]oth waveform cache SHA bindings"):
        build_variable_training_contract(
            dataset_manifest_sha256="a" * 64,
            waveform_cache_index_sha256="b" * 64,
        )
