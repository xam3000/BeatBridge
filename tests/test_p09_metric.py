from types import SimpleNamespace

import numpy as np
import pytest
import torch
from torch.nn import functional as F

from src.features.p08_windows import VARIANTS
from src.ml.p08_contrastive import batch_order, in_batch_mask, productions
from src.ml.p09_metric import ContinuationMetric
from src.ml.p09_train import evaluate
from src.ml.p09_windows import WindowBank


@pytest.mark.parametrize("family,width,counts", [
    ("classical", 82, (0, 10496, 108288)), ("mert", 768, (0, 98304, 459533)),
])
def test_raw_cosine_directed_bilinear_and_towers(family, width, counts):
    torch.manual_seed(17)
    shape = (4, 13, width) if family == "mert" else (4, width)
    q, t = torch.randn(shape), torch.randn(shape)
    for level, count in enumerate(counts):
        model = ContinuationMetric(family, level)
        assert sum(p.numel() for p in model.parameters()) == count
        scores = model(q, t[None].expand(4, *t.shape))
        a, b = (x.mean(-2) if family == "mert" else x for x in (q, t))
        if level == 0:
            torch.testing.assert_close(scores, F.normalize(a) @ F.normalize(b).T)
        elif level == 1:
            # Materialize the effective matrix independently on unit basis vectors.
            identity = torch.eye(width)
            matrix = model.source(identity) @ model.target(identity).T
            torch.testing.assert_close(scores, F.normalize(a) @ matrix @ F.normalize(b).T)
            assert not torch.allclose(matrix, matrix.T)
            assert torch.linalg.matrix_rank(matrix) <= 64
            assert torch.linalg.matrix_norm(matrix, ord=2) <= 1.00001
        else:
            assert model.encode(q, source=True).shape == (4, 128)
            assert not torch.allclose(model.encode(q, source=True), model.encode(q, source=False))
            scores.diagonal().sum().backward()
            if family == "mert":
                assert model.layer_logits.grad.abs().sum() > 0


def test_tie_order_and_source_recording_weights():
    data = SimpleNamespace(values=torch.ones(2, 82), panels=np.zeros((3, 10), dtype=int),
                           truth=np.array([0, 0, 2]), tracks=np.array([0, 0, 1]))
    metrics, ranks = evaluate(ContinuationMetric("classical", 0), data)
    np.testing.assert_array_equal(ranks, [1, 1, 3])
    assert metrics == pytest.approx({"recall1": .5, "mrr": 2/3})


def test_epoch_cache_matches_p08_physical_masks_and_productions():
    def row(i):
        return dict(query_id=f"a:{8+i:06d}", positive=f"a:{12+i:06d}",
                    negatives={"tempo": ["a:000012", "a:000031"], "foreign": ["a:000030"],
                               "same": ["a:000032"]}, group=str(i//2))

    rows = [row(i) for i in range(9)]
    bars = np.arange(40, dtype=np.float32)[:, None]
    data = SimpleNamespace(split="train", k=4,
                           _load=lambda sha, variant: bars + 100 * VARIANTS.index(variant))
    bank = WindowBank(data, rows, "cpu")
    seed = 20260928
    offsets = bank.production_offsets(seed)
    for epoch in (0, 2, 3, 8, 29):
        _, batches, masks = bank.epoch(seed, epoch, offsets, 7)
        for raw, ids, mask in zip(batch_order(rows, seed, epoch, 7), batches, masks, strict=True):
            torch.testing.assert_close(mask, in_batch_mask(raw))
            for r, windows in zip(raw, bank.values[ids], strict=True):
                a, b = productions(r["query_id"], seed, epoch)
                d = int(r["query_id"].split(":")[1])
                starts = [d-4, d+4, 12, 31, 30, 32]
                views = [a, b, b, b, b, b]
                expected = [i+1.5+100*VARIANTS.index(v) for i, v in zip(starts, views)]
                np.testing.assert_array_equal(windows[:, 0], expected)
