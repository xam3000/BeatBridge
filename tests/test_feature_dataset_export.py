import hashlib
import json

import numpy as np
import soundfile as sf

from src.features import FEATURE_DIMENSION, GLOBAL_FEATURE_DIMENSION, SEQUENCE_LENGTH
from src.features.dataset_export import (
    CandidateRecord,
    SplitConfig,
    _apply_bpm_filter,
    assign_track_disjoint_splits,
    export_feature_dataset,
)


class _Analysis:
    def __init__(self, sample_rate=8_000, bpm=120.0, beat_count=25):
        self.sample_rate = sample_rate
        self.bpm = bpm
        self.beat_count = beat_count

    def __call__(self, _):
        beat_samples = int(round(self.sample_rate * 60.0 / self.bpm))
        return self.bpm, [
            (index * beat_samples, index % 4 + 1, 4)
            for index in range(self.beat_count)
        ]


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_tone(path, frequency, *, sample_rate=8_000):
    time = np.arange(13 * sample_rate, dtype=np.float32) / sample_rate
    audio = 0.2 * np.sin(2 * np.pi * frequency * time)
    sf.write(path, audio, sample_rate, subtype="FLOAT")


def _candidate(candidate_id, source, target, bars):
    return {
        "format_version": 1,
        "candidate_id": candidate_id,
        "source_track": {"path": str(source), "sha256": _sha256(source)},
        "target_track": {"path": str(target), "sha256": _sha256(target)},
        "source_cutpoint": {
            "sample": 16_000,
            "beat_index": 4,
            "bar_index": 1,
            "count_in_bar": 1,
            "beats_in_bar": 4,
        },
        "target_cutpoint": {
            "sample": 80_000,
            "beat_index": 20,
            "bar_index": 5,
            "count_in_bar": 1,
            "beats_in_bar": 4,
        },
        "transition_length_bars": bars,
        "transition_length_beats": bars * 4,
        "source_bpm": 120.0,
        "target_bpm": 120.0,
        "tempo_relative_difference": 0.0,
        "generator": "test",
        "filter_status": "accepted",
    }


def test_seeded_split_is_strictly_track_disjoint_and_nonempty():
    tracks = [f"{index:064x}" for index in range(6)]
    pair_weights = {
        (left, right): 1
        for left in tracks
        for right in tracks
        if left != right
    }
    assignment = assign_track_disjoint_splits(
        tracks,
        pair_weights,
        config=SplitConfig(
            train=1 / 3,
            validation=1 / 3,
            test=1 / 3,
            seed=17,
            search_attempts=128,
        ),
    )

    assert set(assignment) == set(tracks)
    assert {assignment[track] for track in tracks} == {"train", "validation", "test"}
    assert all(
        sum(assignment[track] == split for track in tracks) == 2
        for split in ("train", "validation", "test")
    )


def test_dataset_export_selects_four_bar_candidate_and_writes_tensors(tmp_path):
    source = tmp_path / "source.wav"
    target = tmp_path / "target.wav"
    _write_tone(source, 220.0)
    _write_tone(target, 330.0)
    two_bar = _candidate("candidate-two", source, target, 2)
    four_bar = _candidate("candidate-four", source, target, 4)
    batch_manifest = tmp_path / "batch.json"
    batch_manifest.write_text(
        json.dumps(
            {
                "format_version": 1,
                "candidate_generation": {
                    "format_version": 1,
                    "candidates": [two_bar, four_bar],
                    "rejections": [],
                },
                "candidate_ranking": {
                    "format_version": 1,
                    "ranker": "test",
                    "scores": [
                        {
                            "candidate_id": "candidate-two",
                            "rank": 1,
                            "total_score": 0.9,
                        },
                        {
                            "candidate_id": "candidate-four",
                            "rank": 2,
                            "total_score": 0.8,
                        },
                    ],
                    "failures": [],
                },
            }
        ),
        encoding="utf-8",
    )
    output = tmp_path / "dataset"

    result = export_feature_dataset(
        batch_manifest,
        output,
        cache_root=tmp_path / "cache",
        analysis=_Analysis(),
        sample_rate=8_000,
        top_k_per_pair=1,
        split_config=SplitConfig(train=1.0, validation=0.0, test=0.0),
        vocal_backend="disabled",
    )

    assert result.example_count == 1
    assert result.split_counts == {"train": 1, "validation": 0, "test": 0}
    with np.load(output / "train.npz", allow_pickle=False) as payload:
        assert payload["features_a"].shape == (1, SEQUENCE_LENGTH, FEATURE_DIMENSION)
        assert payload["features_b"].shape == (1, SEQUENCE_LENGTH, FEATURE_DIMENSION)
        assert payload["global_features"].shape == (1, GLOBAL_FEATURE_DIMENSION)
        assert payload["features_a"].dtype == np.float32
        assert payload["global_features"].dtype == np.float32
    with np.load(output / "validation.npz", allow_pickle=False) as payload:
        assert payload["features_a"].shape == (0, SEQUENCE_LENGTH, FEATURE_DIMENSION)
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    examples = [
        json.loads(line)
        for line in (output / "examples.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert manifest["format_version"] == 1
    assert manifest["normalization"]["fit_scope"] == "training_tracks_only"
    assert {item["split"] for item in manifest["track_assignments"]} == {"train"}
    assert examples[0]["candidate_id"] == "candidate-four"
    assert examples[0]["transition_length_bars"] == 4
    assert examples[0]["source_grid"] is None
    assert examples[0]["target_grid"] is None


def test_bpm_filter_is_inclusive_and_rejects_either_track_outside_range(tmp_path):
    manifest = tmp_path / "manifest.json"
    manifest.write_text("{}", encoding="utf-8")

    def record(example_id, source_bpm, target_bpm):
        return CandidateRecord(
            example_id=example_id,
            candidate={"source_bpm": source_bpm, "target_bpm": target_bpm},
            candidate_rank=1,
            candidate_score=1.0,
            pair_manifest_path=manifest,
            pair_manifest_sha256="0" * 64,
        )

    allowed, rejected = _apply_bpm_filter(
        (
            record("inclusive", 145.0, 165.0),
            record("source-low", 144.99, 155.0),
            record("target-high", 155.0, 165.01),
        ),
        minimum_bpm=145.0,
        maximum_bpm=165.0,
    )

    assert [item.example_id for item in allowed] == ["inclusive"]
    assert [item["example_id"] for item in rejected] == ["source-low", "target-high"]
    assert rejected[0]["matches"][0]["reason"] == "below_minimum_bpm"
    assert rejected[1]["matches"][0]["reason"] == "above_maximum_bpm"
