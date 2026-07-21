import json

import pytest

from src.evaluation.ratings import load_ratings, rating_summary, save_rating


@pytest.fixture
def batch_directory(tmp_path):
    manifest = {
        "format_version": 1,
        "rendered_variants": [
            {
                "candidate_id": "candidate-1",
                "renderer": "equal_power",
                "output_file": "rendered/candidate-1.wav",
            }
        ],
    }
    (tmp_path / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return tmp_path


def test_rating_is_persisted_and_updates_same_variant(batch_directory):
    save_rating(
        batch_directory,
        "candidate-1",
        "equal_power",
        2,
        issues=("phrasing", "vocals"),
        notes="Vocals collide.",
    )
    save_rating(batch_directory, "candidate-1", "equal_power", 4)

    payload = load_ratings(batch_directory)
    assert payload["format_version"] == 1
    assert len(payload["ratings"]) == 1
    assert payload["ratings"][0]["overall"] == 4
    assert rating_summary(batch_directory)[0]["renderer"] == "equal_power"


def test_rating_rejects_unknown_variant_and_invalid_score(batch_directory):
    with pytest.raises(ValueError, match="No rendered variant"):
        save_rating(batch_directory, "missing", "fade", 3)
    with pytest.raises(ValueError, match="1 to 5"):
        save_rating(batch_directory, "candidate-1", "equal_power", 6)
