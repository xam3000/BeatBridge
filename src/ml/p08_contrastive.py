"""Load sealed P08 windows and apply Chuang et al. (2020), eqs. 7–8."""

from functools import lru_cache
import json
import math
from pathlib import Path

import numpy as np
import torch
from torch.nn import functional as F

from src.features.p08_pairs import PRIOR, TEMPERATURE, parse_location, rng_for
from src.features.p08_windows import VARIANTS, checked, p07_views, read_json


VERIFIED_RELEASE = Path("docs/masterarbeit/P08_VERIFIED_20261119.json")


def read_rows(path):
    with path.open(encoding="utf-8") as stream:
        return [json.loads(line) for line in stream]


def batch_order(rows, seed, epoch, batch_size=32):
    ordered = list(rows)
    rng_for("epoch", epoch, seed=seed).shuffle(ordered)
    for i in range(0, len(ordered), batch_size):
        yield ordered[i:i + batch_size]


def productions(qid, seed, epoch):
    """Visit all nine production pairs in nine epochs for each training query."""
    rng = rng_for("production", qid, seed=seed)
    a, b = rng.randrange(3), rng.randrange(3)
    return VARIANTS[(a + epoch) % 3], VARIANTS[(b + epoch + epoch // 3) % 3]


def in_batch_mask(rows):
    """Mask by physical identity even when donor productions differ."""
    mask = torch.zeros((len(rows), len(rows)), dtype=torch.bool)
    for i, row in enumerate(rows):
        seen = {n for family in row["negatives"].values() for n in family}
        for j, donor in enumerate(rows):
            target = donor["positive"]
            if donor["group"] != row["group"] and target not in seen:
                mask[i, j] = True
                seen.add(target)
    return mask


class PairWindows:
    def __init__(self, dataset, p07, split, family, cache_tracks=24):
        if split not in ("train", "validation") or family not in ("mert", "classical"):
            raise ValueError("Unknown P08 split or representation")
        release_digest = read_json(VERIFIED_RELEASE)["manifest_sha256"]
        self.manifest = read_json(checked(dataset / "manifest.json", release_digest))
        if self.manifest["format_version"] != 1:
            raise ValueError("Unsupported P08 format")
        checked(p07 / "manifest.json", self.manifest["p07_manifest_sha256"])
        self.views = {(r["sha256"], r["variant"]): r for r in p07_views(p07)["views"]
                      if r["split"] == split}
        name = f"{split}.jsonl"
        self.rows = read_rows(checked(dataset / name, self.manifest["files"][name]))
        self.k = self.manifest["k"]
        self.split = split
        self.family = family
        self.root = p07
        self._load = lru_cache(maxsize=cache_tracks)(self._load_track)

    def _load_track(self, sha, variant):
        view = self.views[sha, variant]
        if self.family == "mert":
            path = (self.root / view["entry"]).with_name("bars.npz")
            digest = view["sha256_files"]["bars.npz"]
        else:
            path = self.root / view["classical_scaled"]
            digest = view["classical_scaled_sha256"]
        with np.load(checked(path, digest)) as archive:
            return archive[self.family]

    def window(self, key, variant, *, before=False):
        sha, row = parse_location(key)
        start = row - self.k if before else row
        values = self._load(sha, variant)
        if not 0 <= start <= len(values) - self.k:
            raise ValueError(f"Incomplete window: {key}")
        return values[start:start + self.k]

    def training_batch(self, rows, seed, epoch):
        if self.split != "train":
            raise ValueError("Training batches require training groups")
        queries, positives, negatives = [], [], []
        for row in rows:
            left, right = productions(row["query_id"], seed, epoch)
            queries.append(self.window(row["query_id"], left, before=True))
            positives.append(self.window(row["positive"], right))
            keys = (row["negatives"]["tempo"] + row["negatives"]["foreign"]
                    + row["negatives"]["same"])
            negatives.append([self.window(key, right) for key in keys])
        return (torch.from_numpy(np.stack(queries)), torch.from_numpy(np.stack(positives)),
                torch.from_numpy(np.stack(negatives)), in_batch_mask(rows))

    def retrieval_item(self, index):
        if self.split != "validation":
            raise ValueError("Retrieval requires validation originals")
        row = self.rows[index]
        query = self.window(row["query_id"], "original", before=True)
        candidates = np.stack([self.window(key, "original") for key in row["candidates"]])
        return query, candidates, row["candidates"].index(row["positive"])


def debiased_loss(positive, negative, valid, *, temperature=TEMPERATURE, tau_plus=PRIOR):
    """One positive per query, normalized cosine scores, variable N after masking."""
    if (positive.ndim != 1 or negative.ndim != 2 or negative.shape[0] != len(positive)
            or valid.shape != negative.shape or valid.dtype != torch.bool):
        raise ValueError("Expected one positive and a masked negative matrix")
    if not math.isfinite(temperature) or not 0 < temperature or not 0 <= tau_plus < 1:
        raise ValueError("Invalid DCL temperature or positive prior")
    count = valid.sum(dim=1)
    if (count == 0).any():
        raise ValueError("Each query needs at least one negative")
    # Scale all exponentials, including the lower bound, by the same factor.
    # At the frozen t their arguments are in [-10, 0], including for FP32.
    if positive.dtype in (torch.float16, torch.bfloat16):
        positive, negative = positive.float(), negative.float()
    pos = ((positive - 1) / temperature).exp()
    neg = ((negative.masked_fill(~valid, -torch.inf) - 1) / temperature).exp()
    g = ((neg.sum(dim=1) / count - tau_plus * pos) / (1 - tau_plus))
    g = g.clamp_min(math.exp(-2 / temperature))
    return torch.log1p(count * g / pos).mean()


def contrastive_step_loss(query, positive, explicit, in_batch, **kwargs):
    """Combine per-query hard negatives with the other groups' positive windows."""
    q, p, e = (F.normalize(x, dim=-1) for x in (query, positive, explicit))
    pos = (q * p).sum(-1)
    hard = (q[:, None, :] * e).sum(-1)
    scores = torch.cat((hard, q @ p.T), dim=1)
    mask = torch.cat((torch.ones_like(hard, dtype=torch.bool), in_batch.to(hard.device)), dim=1)
    return debiased_loss(pos, scores, mask, **kwargs)
