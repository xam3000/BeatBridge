import math

import numpy as np
import pytest
import torch
from torch.nn import functional as F

from src.cutting.fade_cut import FadeCut
from src.features.p08_pairs import foreign_pools, location, sample_row, sample_split, tempo_close
from src.features.p08_windows import Track, VARIANTS, contiguous_starts, same_track_pool, section_types
from src.ml.p08_contrastive import PairWindows, batch_order, debiased_loss, in_batch_mask, productions


def fixture_track(sha, group, split="validation", bpm=150.):
    starts = np.arange(120) * 8
    bars = starts[:, None] + np.arange(9)
    features = np.zeros((120, 4))
    features[64:, :2] = 1.
    return Track(sha, group, split, bpm, starts // 2, bars, np.arange(4, 113),
                 np.arange(4, 117), features,
                 {t: "intro_like" if t < 64 else "drop_like" for t in range(120)})


def test_full_span_cannot_cross_either_kind_of_gap():
    track = fixture_track("a", "g")
    bars, beats = track.bars[:38].copy(), track.beats[:38].copy()
    beats[12:] += 4
    bars[25:] += 1
    starts = contiguous_starts(beats, bars, 12)
    assert list(starts) == [0, 12, 13, 25, 26]
    assert not len(contiguous_starts(beats[:11], bars[:11], 12))


def test_positive_excludes_fade_bars_and_reads_from_T_in_renderer():
    # Beat lengths deliberately differ. The target is trimmed at its leading edge.
    a, b = np.arange(200, dtype=np.float32), np.arange(300, dtype=np.float32) + 500
    beats = np.arange(81)
    ga, gb = ([(int(step * i), int(i % 4 + 1), 4) for i in beats] for step in (2, 3))
    s, t = ga[20][0], gb[48][0]
    fade = FadeCut(fade_beats=16)
    out = fade.cut(a, b, s, t, ga, gb)
    n = 32
    assert fade.effective_transition_samples == n
    np.testing.assert_array_equal(out[s-32:s], a[ga[4][0]:s])
    np.testing.assert_array_equal(out[s+n:s+n+48], b[t:gb[64][0]])
    fo, fi = fade._build_envelopes(n)
    np.testing.assert_array_equal(out[s:s+n], a[s:s+n] * fo + b[t-n:t] * fi)


def test_same_track_requires_both_gap_and_two_different_features():
    track = fixture_track("a", "g")
    # Positive span rows [24,36); 52 leaves 16 complete rows, 53 leaves 17.
    track.structure[52:54, :2] = 1.
    track.structure[54, 1] = 5.
    pool = same_track_pool(track, 28, 4, 4)
    assert 52 not in pool and 53 in pool and 54 not in pool
    track.structure[:] = 0
    assert not len(same_track_pool(track, 28, 4, 4))


def test_tempo_limits_and_recording_group_rejection():
    assert tempo_close(190, 200) and tempo_close(200, 190)
    assert not tempo_close(189.99, 200)
    q = fixture_track("a", "same", bpm=190)
    foreign, near = foreign_pools(q, [
        q, fixture_track("alias", "same"), fixture_track("other", "h", bpm=200),
        fixture_track("fast", "i", bpm=201), fixture_track("leak", "j", "train", bpm=190),
    ])
    assert set(foreign) == {"h", "i"} and set(near) == {"h"}


def test_freeze_is_order_independent_and_budget_is_shared_across_aliases():
    tracks = [fixture_track(str(i), str(i)) for i in range(8)]
    tracks.append(fixture_track("alias", "0"))
    tables = sample_split(tracks, 4, 4)
    assert tables == sample_split(list(reversed(tracks)), 4, 4)
    rows, _, budget = tables
    assert budget["0"]["drawn"] == 64 and budget["0"]["eligible"] == 2 * len(tracks[0].cues)
    for row in rows:
        assert len(set(row["candidates"])) == 9
        assert set(row["candidates"]) == {row["positive"], *sum(row["negatives"].values(), [])}
        assert row["intro_drop_control"]["section"] != row["positive_section"]
    assert len({row["candidates"].index(row["positive"]) for row in rows}) == 9


def test_missing_pools_exclude_query_without_replacement():
    track = fixture_track("a", "g")
    track.structure[:] = 0
    row, reasons = sample_row(track, 10, ({}, {}), 4, 4)
    assert row is None and set(reasons) == {"insufficient_foreign_groups", "insufficient_tempo_groups",
                                             "insufficient_distant_structural_windows"}


def test_intro_is_anchored_to_file_time_and_drop_needs_kick():
    # At 120 BPM a nominal 4/4 bar is 48k samples at 24 kHz.
    feats = np.array([[0, 0, 0, 0], [0, 0, 2, 0], [4, 0, -2, 0], [4, 0, 5, 0]])
    labels = section_types(np.arange(4), feats, np.array([0, 32, 40, 48]) * 48000, 120)
    assert list(labels.values()) == ["intro_like", "other", "other", "drop_like"]


def test_in_batch_mask_excludes_aliases_and_duplicate_windows():
    def row(group, key, negatives=()):
        return dict(group=group, positive=location(key, 4),
                    negatives={"tempo": [location(s, 4) for s in negatives]})
    rows = [row("g", "a", ["b"]), row("g", "alias"), row("h", "b"), row("i", "c"), row("i", "c")]
    mask = in_batch_mask(rows)
    assert mask[0].tolist() == [False, False, False, True, False]
    assert not mask.diagonal().any()
    assert not mask[3, 4] and not mask[4, 3]


def test_no_lost_partial_batch_and_balanced_productions():
    rows = list(range(65))
    batches = list(batch_order(rows, 20260926, 0))
    assert [len(b) for b in batches] == [32, 32, 1]
    assert sorted(sum(batches, [])) == rows
    assert batches != list(batch_order(rows, 20260926, 1))
    assert set(productions("q", 20260926, e) for e in range(9)) == {
        (a, b) for a in VARIANTS for b in VARIANTS
    }


@pytest.mark.parametrize("prior", [0., .05, .5])
def test_dcl_matches_primary_equations_and_gradients(prior):
    pos = torch.tensor([1., -.2], dtype=torch.float64, requires_grad=True)
    # Test both smooth branches, avoiding the non-unique derivative at the kink.
    neg = torch.tensor([[-1., -.99, 1.], [.1, .2, -.4]], dtype=pos.dtype, requires_grad=True)
    valid = torch.tensor([[True, True, False], [True, True, True]])
    observed = debiased_loss(pos, neg, valid, tau_plus=prior)
    losses = []
    for s, row, mask in zip(pos, neg, valid):
        u = (s / .2).exp()
        v = (row[mask] / .2).exp()
        g = torch.maximum((v.mean() - prior*u) / (1-prior), torch.tensor(math.exp(-5.), dtype=u.dtype))
        losses.append(-torch.log(u / (u + len(v)*g)))
    expected = torch.stack(losses).mean()
    torch.testing.assert_close(observed, expected)
    for got, want in zip(torch.autograd.grad(observed, (pos, neg)),
                         torch.autograd.grad(expected, (pos, neg))):
        torch.testing.assert_close(got, want)
    if prior == 0.:
        scores = torch.cat([pos[:, None], neg.masked_fill(~valid, -torch.inf)], dim=1)
        torch.testing.assert_close(observed, F.cross_entropy(scores/.2, torch.zeros(2, dtype=torch.long)))


def test_dcl_rejects_no_negatives():
    with pytest.raises(ValueError, match="at least one"):
        debiased_loss(torch.zeros(1), torch.zeros(1, 1), torch.zeros(1, 1, dtype=torch.bool))


def test_half_precision_inputs_remain_finite_for_opposite_cosines():
    p = torch.tensor([-1.], dtype=torch.float16, requires_grad=True)
    n = torch.ones(1, 35, dtype=p.dtype, requires_grad=True)
    loss = debiased_loss(p, n, torch.ones_like(n, dtype=torch.bool))
    loss.backward()
    assert torch.isfinite(loss) and torch.isfinite(p.grad).all() and torch.isfinite(n.grad).all()


def test_loader_rejects_a_resealed_manifest_before_cache_access(tmp_path):
    (tmp_path / "manifest.json").write_text('{"format_version":1,"files":{}}', encoding="utf-8")
    with pytest.raises(ValueError, match="Checksum mismatch"):
        PairWindows(tmp_path, tmp_path / "absent-cache", "validation", "classical")
