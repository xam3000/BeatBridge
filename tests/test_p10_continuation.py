from dataclasses import replace

import numpy as np
import pytest
import torch

from src.analysis.models import BeatGridMetadata
from src.candidates import CutPoint
from src.candidates.models import TrackReference, TransitionCandidate
from src.evaluation.p10_validation import control, decision
from src.features.p08_pairs import MODEL_SEEDS
from src.ml.p09_metric import ContinuationMetric
from src.ranking.continuation import BarWindows, candidate_windows, score_pair


@pytest.mark.parametrize("cuda,bf16", [(False, False), (True, False)])
def test_encoder_requires_p07_precision(monkeypatch, cuda, bf16):
    from src.ranking.continuation import encoder_runtime
    monkeypatch.setattr(torch.cuda, "is_available", lambda: cuda)
    monkeypatch.setattr(torch.cuda, "is_bf16_supported", lambda **kwargs: bf16)
    with pytest.raises(ValueError, match="CUDA with native bfloat16"):
        encoder_runtime()


def test_final_stimulus_carries_only_bound_ssl_provenance():
    from copy import deepcopy
    from src.evaluation.comparison_study import final_ssl_provenance
    from src.features.p07_mert import file_sha256
    from src.ranking.continuation import METHOD, SELECTION
    manifest = {"ranking_method": METHOD, "cue_ranking": {"ranker": METHOD,
                "scores": [{"rank": 1, "candidate_id": "cue"}],
                "provenance": {"selection_sha256": file_sha256(SELECTION),
                               "encoder_runtime": {"device": "cuda:0", "autocast": "bfloat16", "gpu": "fixture"}}}}
    assert final_ssl_provenance(manifest, "cue") == manifest["cue_ranking"]["provenance"]
    for field, value in (("autocast", "float32"), ("device", "cpu"), ("gpu", "")):
        altered = deepcopy(manifest)
        altered["cue_ranking"]["provenance"]["encoder_runtime"][field] = value
        with pytest.raises(ValueError, match="Final SSL"):
            final_ssl_provenance(altered, "cue")
    with pytest.raises(ValueError, match="Final SSL"):
        final_ssl_provenance(manifest, "other")


def test_control_uses_half_ties_and_group_macro():
    # First group has one win and one tie, second group has one loss.
    assert control(np.array([1., 0., 0.]), np.array([0., 0., 1.]), ["a", "a", "b"]) == .375
    assert control(np.array([]), np.array([]), []) is None


def test_study_seed_mean_group_minimum_and_tiebreak():
    rows = [dict(family="mert", level=l, seed=s, recall1=.8, same=.8, intro_drop=.8,
                 same_groups=5, intro_drop_groups=5) for l in (1, 2) for s in MODEL_SEEDS]
    assert decision(rows)[1]["level"] == 1
    rows[0]["intro_drop"] = .5  # Study seed fails despite a passing mean.
    assert decision(rows)[1]["level"] == 2
    rows[5]["same_groups"] = 4
    assert decision(rows)[1] is None
    rows[5]["same_groups"] = 5
    rows[4]["same"] = rows[5]["same"] = .3
    assert decision(rows)[1] is None
    rows[0]["intro_drop"] = None
    assert decision(rows)[1] is None


def test_native_cues_use_original_bar_indices_across_missing_rows_and_sample_rates():
    beats = np.arange(14) * 4
    bounds = 100 * beats[:, None] + np.arange(9) * 50
    keep = np.arange(14) != 1
    bars = np.arange(14 * 82, dtype=np.float32).reshape(14, 82)
    frames = [[int(i) * 100, int(i) % 4 + 1, 4] for i in range(57)]
    w = BarWindows.from_bars(beats[keep], bounds[keep], bars[keep], frames, "grid", 44100 / 48000)
    meta = BeatGridMetadata("detector", False, None, None, beat_grid_sha256="grid")
    a = TrackReference("a", "a")
    b = TrackReference("b", "b")

    def cut(bar):
        return CutPoint(round(bar * 400 * 44100 / 48000), bar * 4, bar, 1, 4)
    good = TransitionCandidate("good", a, b, cut(7), cut(9), 4, 16, 160., 150., .0625,
                               "test", source_grid=meta, target_grid=meta)
    gap = replace(good, candidate_id="gap", source_cutpoint=cut(4))
    accepted, indices, failures = candidate_windows([gap, good], {"a": w, "b": w})
    assert accepted == [good] and [f.candidate_id for f in failures] == ["gap"]
    np.testing.assert_array_equal(indices, [[2, 8]])
    head = ContinuationMetric("classical", 2).eval()
    direct = head(torch.from_numpy(bars[3:7].mean(0)), torch.from_numpy(bars[9:13].mean(0)[None]))
    np.testing.assert_allclose(score_pair(head, indices, w.bars, w.bars), direct.detach().numpy(), atol=1e-6)
    with pytest.raises(ValueError, match="sample differs"):
        candidate_windows([replace(good, target_cutpoint=replace(cut(9), sample=3600))], {"a": w, "b": w})
    with pytest.raises(ValueError, match="same detected grid"):
        candidate_windows([replace(good, target_grid=replace(meta, beat_grid_sha256="other"))], {"a": w, "b": w})
    with pytest.raises(ValueError, match="four 4/4"):
        candidate_windows([replace(good, transition_length_bars=2)], {"a": w, "b": w})
