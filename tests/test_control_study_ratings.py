import json

import pytest

from src.evaluation.control_study_ratings import (
    RATING_CRITERIA,
    add_control_study_note,
    create_control_study_ratings,
    migrate_unrated_study_to_current_criteria,
    rate_control_study_pair,
    ratings_summary,
)


def _study(tmp_path):
    (tmp_path / "manifest.json").write_text(
        json.dumps(
            {
                "blind": True,
                "pairs": [
                    {"index": 1, "directory": "pair_01"},
                    {"index": 2, "directory": "pair_02"},
                ],
            }
        ),
        encoding="utf-8",
    )
    create_control_study_ratings(tmp_path)
    return tmp_path


def _scores(value):
    return {criterion: value for criterion in RATING_CRITERIA}


def test_blind_ratings_are_persisted_and_summarized(tmp_path):
    study = _study(tmp_path)

    rate_control_study_pair(
        study,
        1,
        preferred="B",
        scores_a=_scores(3),
        scores_b=_scores(4),
        issues_a=("abrupt_gain",),
        notes="B fades more cleanly.",
    )

    payload = json.loads((study / "ratings.json").read_text(encoding="utf-8"))
    assert payload["status"] == "in_progress"
    assert payload["ratings"][0]["preferred"] == "B"
    assert payload["ratings"][0]["issues"]["A"] == ["abrupt_gain"]
    assert ratings_summary(study)["preference_counts"]["B"] == 1


def test_blind_ratings_require_complete_one_to_five_scores(tmp_path):
    study = _study(tmp_path)
    invalid_scores = _scores(3)
    invalid_scores["energy_shape"] = 6

    with pytest.raises(ValueError, match="between 1 and 5"):
        rate_control_study_pair(
            study,
            1,
            preferred="A",
            scores_a=invalid_scores,
            scores_b=_scores(4),
        )


def test_study_wide_note_is_appended_without_changing_pair_ratings(tmp_path):
    study = _study(tmp_path)

    add_control_study_note(study, "A score of 5 means no issue was noticed.")

    payload = json.loads((study / "ratings.json").read_text(encoding="utf-8"))
    assert payload["study_notes"][0]["note"].startswith("A score of 5")
    assert all(entry["status"] == "unrated" for entry in payload["ratings"])


def test_unrated_legacy_study_can_remove_rhythm_with_provenance(tmp_path):
    study = _study(tmp_path)
    payload = json.loads((study / "ratings.json").read_text(encoding="utf-8"))
    payload["format_version"] = 2
    payload["criteria"].insert(3, "rhythmic_stability")
    for entry in payload["ratings"]:
        for label in ("A", "B"):
            entry["scores"][label]["rhythmic_stability"] = None
    (study / "ratings.json").write_text(json.dumps(payload), encoding="utf-8")

    migrate_unrated_study_to_current_criteria(
        study,
        "The evaluated model cannot affect rhythm.",
    )

    migrated = json.loads((study / "ratings.json").read_text(encoding="utf-8"))
    assert migrated["format_version"] == 3
    assert "rhythmic_stability" not in migrated["criteria"]
    assert migrated["criteria_history"][0]["removed"] == ["rhythmic_stability"]
