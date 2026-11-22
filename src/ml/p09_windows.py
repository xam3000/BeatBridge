"""Index sealed P08 windows once. The only cached operation is the four-bar mean."""

from collections import defaultdict

import numpy as np
import torch

from src.features.p08_pairs import parse_location
from src.features.p08_windows import VARIANTS
from src.ml.p08_contrastive import batch_order, productions


class WindowBank:
    def __init__(self, data, rows, device):
        self.rows = rows
        train = data.split == "train"
        keys = set()
        panels = []
        for row in rows:
            sha, d = parse_location(row["query_id"])
            query = (sha, d - data.k)
            if train:
                neg = row["negatives"]
                targets = [row["positive"], *neg["tempo"], *neg["foreign"], *neg["same"]]
            else:
                targets = row["candidates"]
            panel = [query, *map(parse_location, targets)]
            keys.update(panel)
            panels.append(panel)

        ordered = sorted(keys)
        self.window_count = len(ordered)
        ids = {key: i for i, key in enumerate(ordered)}
        self.panels = np.array([[ids[k] for k in panel] for panel in panels], dtype=np.int64)
        tracks = defaultdict(list)
        for sha, start in ordered:
            tracks[sha].append(start)
        variants = VARIANTS if train else ("original",)
        self.values = None
        for v, variant in enumerate(variants):
            for sha, starts in tracks.items():
                bars = data._load(sha, variant)
                indices = np.array(starts)[:, None] + np.arange(data.k)
                if indices.min() < 0 or indices.max() >= len(bars):
                    raise ValueError("Incomplete P08 window")
                windows = bars[indices].mean(axis=1, dtype=np.float32)
                if not np.isfinite(windows).all():
                    raise ValueError(f"Nonfinite features in {sha}/{variant}")
                if self.values is None:
                    self.values = torch.empty((len(variants)*len(ordered), *windows.shape[1:]),
                                              dtype=torch.float32, device=device)
                offset = v * len(ordered) + ids[sha, starts[0]]
                self.values[offset:offset + len(starts)].copy_(torch.from_numpy(windows))

        if train:
            self.groups = np.unique([row["group"] for row in rows], return_inverse=True)[1]
            if len(set(self.panels[:, 1])) != len(rows):
                raise ValueError("P08 unique positive IDs required for vectorized donor mask")
        else:
            self.truth = np.array([r["candidates"].index(r["positive"]) for r in rows])
            self.tracks = np.unique([parse_location(r["query_id"])[0] for r in rows], return_inverse=True)[1]

    def production_offsets(self, seed):
        return np.array([[VARIANTS.index(v) for v in productions(r["query_id"], seed, 0)]
                         for r in self.rows])

    def epoch(self, seed, epoch, base, batch_size):
        batches = list(batch_order(range(len(self.rows)), seed, epoch, batch_size))
        order = np.concatenate(batches)
        ids = self.panels[order].copy()
        q, p = base[order].T
        ids[:, 0] += (q + epoch) % 3 * self.window_count
        ids[:, 1:] += ((p + epoch + epoch // 3) % 3 * self.window_count)[:, None]
        # Physical IDs exclude colliding explicit negatives in every production.
        # Positive IDs are globally unique, so no second in-batch donor can repeat one.
        masks = []
        for batch in batches:
            groups = self.groups[batch]
            target = self.panels[batch, 1]
            duplicate = (self.panels[batch, 2:, None] == target[None, None, :]).any(axis=1)
            masks.append((groups[:, None] != groups) & ~duplicate)
        device = self.values.device
        # Transfer all full-batch masks at once; keep the sealed partial batch.
        full = len(order) // batch_size
        mask_blocks = []
        if full:
            mask_blocks.extend(torch.as_tensor(np.stack(masks[:full]), device=device).unbind())
        if full < len(masks):
            mask_blocks.append(torch.as_tensor(masks[-1], device=device))
        return order, torch.as_tensor(ids, device=device).split(batch_size), mask_blocks
