import json

import pytest

from src.evaluation.analyze_control_study import analyze_control_study
from src.evaluation.control_study_ratings import RATING_CRITERIA


def _scores(value):
    return {criterion: value for criterion in RATING_CRITERIA}


def _write_study(tmp_path, *, status="completed"):
    pairs = [
        {
            "index": 1,
            "directory": "pair_01",
            "source_track": "source_1.wav",
            "target_track": "target_1.wav",
        },
        {
            "index": 2,
            "directory": "pair_02",
            "source_track": "source_2.wav",
            "target_track": "target_2.wav",
        },
    ]
    ratings = [
        {
            "pair_index": 1,
            "directory": "pair_01",
            "status": "rated",
            "preferred": "B",
            "scores": {"A": _scores(3), "B": _scores(5)},
            "issues": {"A": ["abrupt_gain"], "B": []},
            "notes": "B is cleaner.",
        },
        {
            "pair_index": 2,
            "directory": "pair_02",
            "status": "rated",
            "preferred": "tie",
            "scores": {"A": _scores(4), "B": _scores(4)},
            "issues": {"A": [], "B": []},
            "notes": "",
        },
    ]
    answer_pairs = [
        {
            "index": 1,
            "directory": "pair_01",
            "mapping": {
                "A": "optimized_proxy",
                "B": "baseline_equal_power",
            },
        },
        {
            "index": 2,
            "directory": "pair_02",
            "mapping": {
                "A": "baseline_equal_power",
                "B": "optimized_proxy",
            },
        },
    ]
    (tmp_path / "manifest.json").write_text(
        json.dumps({"blind": True, "pairs": pairs}), encoding="utf-8"
    )
    (tmp_path / "ratings.json").write_text(
        json.dumps(
            {
                "status": status,
                "criteria": list(RATING_CRITERIA),
                "ratings": ratings,
                "study_notes": [],
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "answer_key.json").write_text(
        json.dumps({"pairs": answer_pairs}), encoding="utf-8"
    )


def test_completed_study_is_unblinded_and_summarized(tmp_path):
    _write_study(tmp_path)

    output_path = analyze_control_study(tmp_path)

    result = json.loads(output_path.read_text(encoding="utf-8"))
    assert result["preference_counts"] == {
        "baseline_equal_power": 1,
        "optimized_proxy": 0,
        "tie": 1,
    }
    assert result["criterion_summary"]["baseline_equal_power"]["overall"]["mean"] == 4.5
    assert result["criterion_summary"]["optimized_proxy"]["overall"]["mean"] == 3.5
    assert result["paired_delta_optimized_minus_baseline"]["overall"]["mean"] == -1.0
    assert result["pairs"][0]["preferred_method"] == "baseline_equal_power"
    assert result["pairs"][1]["preferred_method"] == "tie"


def test_incomplete_study_cannot_be_unblinded(tmp_path):
    _write_study(tmp_path, status="in_progress")

    with pytest.raises(ValueError, match="completed"):
        analyze_control_study(tmp_path)
