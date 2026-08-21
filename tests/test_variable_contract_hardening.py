import json

import pytest

from src.analysis.models import BeatGridMetadata
from src.candidates.models import TrackReference
from src.candidates.variable import (
    VariableCandidateGenerationConfig,
    generate_variable_candidates_from_grids,
)
from src.features.variable_split import load_variable_split_authority
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


def test_variable_candidates_reject_non_four_four_meter():
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
