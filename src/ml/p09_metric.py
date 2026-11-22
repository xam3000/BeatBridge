"""P09 directional continuation scores on arithmetic means of four P07 bars."""

import torch
from torch import nn
from torch.nn import functional as F


DIMENSIONS = {"classical": 82, "mert": 768}
RANK, HIDDEN, OUTPUT, LAYERS = 64, 256, 128, 13


class BilinearFactor(nn.Linear):
    """A contraction keeps the true bilinear score within the P08 DCL bounds."""

    def forward(self, x):
        gram = self.weight @ self.weight.T
        # ||W||_2^4 = spectral_radius(gram²) <= max absolute row sum.
        bound = (gram @ gram).abs().sum(-1).max().clamp_min(1e-12).pow(.25)
        return F.linear(F.normalize(x, dim=-1), self.weight / bound)


class ContinuationMetric(nn.Module):
    def __init__(self, family, level):
        super().__init__()
        dim = DIMENSIONS[family]
        if level not in (0, 1, 2):
            raise ValueError("P09 defines levels 0–2")
        self.family, self.level = family, level
        self.layer_logits = nn.Parameter(torch.zeros(LAYERS)) if (family, level) == ("mert", 2) else None

        def tower():
            if level == 0:
                return nn.Identity()
            if level == 1:
                return BilinearFactor(dim, RANK, bias=False)
            return nn.Sequential(nn.Linear(dim, HIDDEN), nn.ReLU(), nn.Linear(HIDDEN, OUTPUT))

        self.source, self.target = tower(), tower()

    def encode(self, windows, *, source):
        """Input (..., 82) or (..., 13, 768), already averaged over time."""
        if self.family == "mert":
            if self.layer_logits is None:
                windows = windows.mean(dim=-2)
            else:
                windows = self.layer_logits.softmax(0) @ windows
        encoded = (self.source if source else self.target)(windows)
        return encoded if self.level == 1 else F.normalize(encoded, dim=-1)

    def forward(self, query, candidates):
        """Score candidates (..., N, features) for each query in sealed order."""
        q = self.encode(query, source=True)
        targets = self.encode(candidates, source=False)
        return (q.unsqueeze(-2) * targets).sum(-1)
