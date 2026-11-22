"""Convert sample coordinates between tempos at the same sample rate."""

import math


def aligned_cue_sample(original_sample, *, original_bpm, aligned_bpm):
    """Map an unstretched cue to its position after aligning the track tempo."""
    original_bpm = float(original_bpm)
    aligned_bpm = float(aligned_bpm)
    for name, bpm in (("original_bpm", original_bpm), ("aligned_bpm", aligned_bpm)):
        if not math.isfinite(bpm) or bpm <= 0:
            raise ValueError(f"{name} must be a finite value above 0, got {bpm}")
    # Keep the original dataset export's rounding order.
    return round(int(original_sample) * original_bpm / aligned_bpm)
