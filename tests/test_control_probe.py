import json

from src.evaluation.control_probe import select_probe_candidates


def _hash(character):
    return character * 64


def _candidate(candidate_id, source_hash, target_hash, bars):
    return {
        "candidate_id": candidate_id,
        "source_track": {"path": f"{source_hash}.wav", "sha256": _hash(source_hash)},
        "target_track": {"path": f"{target_hash}.wav", "sha256": _hash(target_hash)},
        "transition_length_bars": bars,
    }


def _write_pair(root, name, candidates, scores):
    pair = root / "pairs" / name
    pair.mkdir(parents=True)
    (pair / "manifest.json").write_text(
        json.dumps(
            {
                "candidate_generation": {
                    "candidates": candidates,
                }
            }
        ),
        encoding="utf-8",
    )
    variants = [
        {
            "variant_id": f"{candidate_id}::equal_power",
            "candidate_id": candidate_id,
            "renderer": "equal_power",
        }
        for candidate_id, _ in scores
    ]
    (pair / "transition_metrics.json").write_text(
        json.dumps(
            {
                "ranking": {
                    "scores": [
                        {
                            "candidate_id": candidate_id,
                            "renderer": "equal_power",
                            "variant_id": f"{candidate_id}::equal_power",
                            "total_score": score,
                        }
                        for candidate_id, score in scores
                    ]
                },
                "variants": variants,
            }
        ),
        encoding="utf-8",
    )


def test_probe_selection_prefers_four_bar_scores_without_reusing_tracks(tmp_path):
    policy_path = tmp_path / "track_exclusions.json"
    policy_path.write_text('{"format_version": 1, "tracks": []}', encoding="utf-8")
    _write_pair(
        tmp_path,
        "pair-1",
        (
            _candidate("best", "a", "b", 4),
            _candidate("two-bars", "c", "d", 2),
        ),
        (("best", 0.95), ("two-bars", 0.99)),
    )
    _write_pair(
        tmp_path,
        "pair-2",
        (_candidate("reuses-b", "b", "e", 4),),
        (("reuses-b", 0.94),),
    )
    _write_pair(
        tmp_path,
        "pair-3",
        (_candidate("second", "f", "g", 4),),
        (("second", 0.90),),
    )

    selected = select_probe_candidates(
        tmp_path,
        pair_count=2,
        transition_bars=4,
        track_exclusions_path=policy_path,
    )

    assert [item["candidate"]["candidate_id"] for item in selected] == [
        "best",
        "second",
    ]


def test_probe_selection_skips_tracks_from_the_policy(tmp_path):
    policy_path = tmp_path / "track_exclusions.json"
    policy_path.write_text(
        json.dumps(
            {
                "format_version": 1,
                "tracks": [
                    {
                        "path": "a.wav",
                        "sha256": _hash("a"),
                        "reason": "Too fast for this comparison set.",
                        "scopes": ["control_probe"],
                        "excluded_at": "2026-07-29",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    _write_pair(
        tmp_path,
        "pair-1",
        (_candidate("excluded", "a", "b", 4),),
        (("excluded", 0.99),),
    )
    _write_pair(
        tmp_path,
        "pair-2",
        (_candidate("allowed", "c", "d", 4),),
        (("allowed", 0.90),),
    )

    selected = select_probe_candidates(
        tmp_path,
        pair_count=1,
        transition_bars=4,
        track_exclusions_path=policy_path,
    )

    assert selected[0]["candidate"]["candidate_id"] == "allowed"


def test_probe_selection_can_reuse_a_track_but_not_the_same_pair(tmp_path):
    policy_path = tmp_path / "track_exclusions.json"
    policy_path.write_text('{"format_version": 1, "tracks": []}', encoding="utf-8")
    _write_pair(
        tmp_path,
        "pair-1",
        (
            _candidate("best", "a", "b", 4),
            _candidate("same-pair-lower", "a", "b", 4),
        ),
        (("best", 0.99), ("same-pair-lower", 0.98)),
    )
    _write_pair(
        tmp_path,
        "pair-2",
        (_candidate("reuses-a", "a", "c", 4),),
        (("reuses-a", 0.97),),
    )

    selected = select_probe_candidates(
        tmp_path,
        pair_count=2,
        transition_bars=4,
        track_exclusions_path=policy_path,
        max_track_uses=2,
    )

    assert [item["candidate"]["candidate_id"] for item in selected] == [
        "best",
        "reuses-a",
    ]
