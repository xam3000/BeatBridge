import numpy as np

from src.evaluation.heldout_control_study import (
    _load_split_features,
    _select_examples,
)


def _example(example_id, source_hash, target_hash, rank, split="test"):
    return {
        "example_id": example_id,
        "split": split,
        "candidate_rank": rank,
        "source_track": {"sha256": source_hash},
        "target_track": {"sha256": target_hash},
    }


def test_select_examples_is_deterministic_and_caps_content_identical_pairs():
    examples = [
        _example("third", "a", "b", 3),
        _example("validation", "a", "b", 1, split="validation"),
        _example("second", "a", "b", 2),
        _example("other", "b", "a", 1),
        _example("first", "a", "b", 1),
    ]

    selected = _select_examples(
        examples,
        split="test",
        max_examples_per_pair=2,
        example_limit=None,
    )

    assert [item["example_id"] for item in selected] == ["first", "second", "other"]


def test_load_split_features_matches_rows_by_example_id(tmp_path):
    path = tmp_path / "test.npz"
    np.savez_compressed(
        path,
        example_ids=np.asarray(["b", "a"]),
        features_a=np.asarray([[[2.0]], [[1.0]]], dtype=np.float32),
        features_b=np.asarray([[[20.0]], [[10.0]]], dtype=np.float32),
    )

    rows = _load_split_features(path)

    assert float(rows["a"][0][0, 0]) == 1.0
    assert float(rows["a"][1][0, 0]) == 10.0
    assert float(rows["b"][0][0, 0]) == 2.0
