import json

from src.dataset import filter_excluded_tracks, load_track_exclusions


def test_track_policy_filters_only_the_requested_scope(tmp_path):
    policy_path = tmp_path / "track_exclusions.json"
    policy_path.write_text(
        json.dumps(
            {
                "format_version": 1,
                "tracks": [
                    {
                        "path": "music/fast.wav",
                        "sha256": "a" * 64,
                        "reason": "Tempo outlier.",
                        "scopes": ["multi_batch"],
                        "excluded_at": "2026-07-29",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    exclusions = load_track_exclusions(policy_path)

    allowed, rejected = filter_excluded_tracks(
        ("music/fast.wav", "music/allowed.wav"),
        scope="multi_batch",
        exclusions=exclusions,
    )
    training_allowed, training_rejected = filter_excluded_tracks(
        ("music/fast.wav",),
        scope="training",
        exclusions=exclusions,
    )

    assert allowed == ("music/allowed.wav",)
    assert rejected[0]["path"] == "music/fast.wav"
    assert training_allowed == ("music/fast.wav",)
    assert not training_rejected
