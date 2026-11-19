"""P01 must keep edition, split and pairing decisions stable across deliveries."""

import hashlib

import pytest

from src.evaluation.audit_exposure import History, population, resolve_groups


def track(name, *, title=None, artist="Fixture", isrc=""):
    return dict(path=f"musik/{name}.flac", sha256=hashlib.sha256(name.encode()).hexdigest(),
                artist=artist, title=title or name, isrc=isrc)


def cleared(rows):
    return {t["sha256"]: dict(decision="unused", source="generated test fixture") for t in rows}


def test_transitive_exposure_and_unresolved_origin():
    rows = [track("original", title="Song"), track("edition", title="Song (Radio Edit)", isrc="DEAAA2600001"),
            track("renamed", isrc="DEAAA2600001"), track("excerpt"), track("unknown"), track("unrelated")]
    history = History(rows)
    history.mark("S001", "test", digest=rows[0]["sha256"])
    reviews = cleared(rows)
    reviews[rows[3]["sha256"]]["alias_sha256"] = rows[2]["sha256"]
    del reviews[rows[4]["sha256"]]
    resolve_groups(rows, history, reviews)
    assert len({r["recording_group_id"] for r in rows[:4]}) == 1
    assert [r["status"] for r in rows] == ["exposed"] * 4 + ["pending", "eligible"]


@pytest.mark.parametrize("groups,expected_pairs", [(19, 0), (20, 10), (21, 10), (22, 11), (24, 12), (26, 12)])
def test_disjoint_pairs_and_deterministic_representative(groups, expected_pairs):
    rows = [track(str(i)) for i in range(groups)]
    rows.append(track("alternate", title="0 (Extended Mix)"))
    resolve_groups(rows, History(rows), cleared(rows))
    result = population(rows)
    assert result == population(list(reversed(rows)))
    assert len(result["eligible_groups"]) == groups
    assert len(result["pairs"]) == expected_pairs
    assert result["missing_groups_for_10"] == max(0, 20 - groups)
    ids = [pair[role]["recording_group_id"] for pair in result["pairs"] for role in ("source", "target")]
    assert len(set(ids)) == len(ids)
    chosen = {g["recording_group_id"]: g["sha256"] for g in result["eligible_groups"]}
    assert chosen[rows[0]["recording_group_id"]] == min(rows[0]["sha256"], rows[-1]["sha256"])


def test_conflicting_historical_path_and_unknown_alias_stop():
    a, b = track("a"), track("b")
    history = History([a])
    with pytest.raises(ValueError, match="SHA mismatch"):
        history.mark("S001", "input", a["path"], b["sha256"])
    reviews = cleared([a])
    reviews[a["sha256"]]["alias_sha256"] = b["sha256"]
    with pytest.raises(ValueError, match="absent file"):
        resolve_groups([a], history, reviews)


def test_prior_exposure_cannot_be_cleared_by_later_submission():
    rows = [track("previously reviewed"), track("new edition", title="previously reviewed")]
    history = History(rows)
    history.previously_exposed.add(rows[0]["sha256"])
    resolve_groups(rows, history, cleared(rows))
    assert [t["status"] for t in rows] == ["exposed", "exposed"]
