import numpy as np

from src.evaluation.vocal_objective_study import (
    _select_vocal_examples,
    _vocal_statistics,
)
from src.features import FEATURE_DIMENSION, SEQUENCE_LENGTH, feature_index


def _features(strength):
    features = np.zeros((SEQUENCE_LENGTH, FEATURE_DIMENSION), dtype=np.float32)
    features[:, feature_index("vocal_activity")] = strength
    features[:, feature_index("vocal_prominence")] = strength
    features[:, feature_index("vocal_valid")] = 1.0
    return features


def _example(example_id, source, target, rank=1, split="train"):
    return {
        "example_id": example_id,
        "split": split,
        "candidate_rank": rank,
        "source_track": {"path": source, "sha256": source},
        "target_track": {"path": target, "sha256": target},
    }


def test_vocal_statistics_measure_the_exact_source_and_target_windows():
    statistics = _vocal_statistics(_features(0.8), _features(0.5))

    assert np.isclose(statistics["source_mean_strength"], 0.64)
    assert np.isclose(statistics["target_mean_strength"], 0.25)
    assert statistics["simultaneously_active_bins_above_0_2"] == SEQUENCE_LENGTH


def test_selection_requires_both_sides_and_excludes_struggling_and_duplicate_pairs():
    examples = [
        _example("best", "source-a", "target-a"),
        _example("same-pair", "source-a", "target-a", rank=2),
        _example("target-silent", "source-b", "target-b"),
        _example("excluded", "14 - STRUGGLING.flac", "target-c"),
        _example("other", "source-d", "target-d"),
    ]
    rows = {
        "best": (_features(0.9), _features(0.9)),
        "same-pair": (_features(0.8), _features(0.8)),
        "target-silent": (_features(0.9), _features(0.0)),
        "excluded": (_features(0.9), _features(0.9)),
        "other": (_features(0.7), _features(0.7)),
    }

    selected = _select_vocal_examples(
        examples,
        rows,
        splits=("train",),
        pair_count=2,
        minimum_mean_vocal_strength=0.15,
        max_track_uses=2,
    )

    assert [item["example"]["example_id"] for item in selected] == ["best", "other"]
