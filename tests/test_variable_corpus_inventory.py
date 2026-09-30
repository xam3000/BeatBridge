from src.variable_corpus_inventory import (
    _exclude_frozen_split_recording_conflicts,
    _recording_group_key,
)


def test_recording_group_normalises_version_suffixes():
    base = _recording_group_key(
        "Code Black;Atmozfears", "Accelerate (Official XXlerator Anthem 2014)"
    )
    special = _recording_group_key(
        "Code Black;Atmozfears",
        "Accelerate (Official XXlerator Anthem 2014) - Special Edit",
    )
    assert base == special
    assert _recording_group_key("The Raiders", "A Feeling - Citizen Remix") == (
        "the raiders|a feeling"
    )


def test_preexisting_recording_conflict_keeps_test_and_excludes_train():
    train_sha = "a" * 64
    test_sha = "b" * 64
    rows = [
        {"sha256": train_sha, "recording_group_id": "same", "path": "train.flac"},
        {"sha256": test_sha, "recording_group_id": "same", "path": "test.flac"},
    ]
    retained, excluded = _exclude_frozen_split_recording_conflicts(
        rows, {train_sha: "train", test_sha: "test"}
    )
    assert [row["sha256"] for row in retained] == [test_sha]
    assert excluded[0]["sha256"] == train_sha
    assert excluded[0]["kept_split"] == "test"
