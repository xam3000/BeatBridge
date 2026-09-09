from src.evaluation.nontrivial_model_examples import _cue_ranker_demo_rows


def test_cue_ranker_demo_uses_latest_validation_and_keeps_group_counts():
    ranking = {
        str(length): {
            "groups": 1,
            "ranker": {"top_1_agreement": 1.0, "ndcg": 0.9},
            "feature_baseline_v3": {"top_1_agreement": 0.0},
        }
        for length in (2, 4, 6, 8)
    }
    rows = _cue_ranker_demo_rows(
        {"status": "completed"},
        {"epochs": [{"validation": {"ranking": ranking}}]},
    )
    assert [row["length"] for row in rows] == [2, 4, 6, 8]
    assert all(row["groups"] == 1 for row in rows)
    assert all(row["ranker_top1"] == 1.0 for row in rows)
    assert all(row["baseline_top1"] == 0.0 for row in rows)
