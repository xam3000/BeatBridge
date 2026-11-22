"""Pitch-preserving, beat-anchored local correction for the second P11 render."""

import hashlib

import numpy as np

from src.tempo.time_stretch import TimeStretch


class LocalGridFailure(ValueError):
    """A selected cue fails the predeclared local timing contract."""


def sample_hash(audio):
    return hashlib.sha256(np.ascontiguousarray(audio, dtype="<f4").tobytes()).hexdigest()


def check_timing(a, b, frames, rate):
    a, b = np.asarray(a), np.asarray(b)
    if (len(a) != 17 or len(b) != 17 or np.any(np.diff(a) <= 0) or np.any(np.diff(b) <= 0)):
        raise LocalGridFailure("Expected 17 strictly ordered local boundaries per side")
    relative = abs(float(np.median(np.diff(b)) / np.median(np.diff(a))) - 1)
    end_ms = 1000 * abs(int(frames) - int(a[-1] - a[0])) / rate
    if relative > .01 + 1e-12 or end_ms > 20:
        raise LocalGridFailure(f"Local gate failed: relative median {relative}, end error {end_ms} ms")
    return dict(relative_median_error=relative, end_error_ms=end_ms)


def align_target(audio, source_beats, target_beats, rate):
    """Map 16 intervals. Keep exact samples on both sides of every beat.

    Rubber Band sees real surrounding context. Linear crossfades connect the
    stretched interval interior to the native 10 ms on each side of a boundary.
    The downstream context therefore starts at the original target cut.
    """
    edges = np.asarray(target_beats, dtype=int)
    lengths = np.diff(np.asarray(source_beats, dtype=int))
    if (len(edges) != 17 or len(lengths) != 16 or edges[0] < 0 or edges[-1] > audio.shape[1]
            or np.any(np.diff(edges) <= 0) or np.any(lengths <= 0)):
        raise LocalGridFailure("Incomplete local beat interval")
    keep = round(.010 * rate)
    blend = round(.020 * rate)
    margin = round(.25 * rate)
    engine = TimeStretch()
    chunks, marks, receipts = [], [0], []
    for left, right, size in zip(edges[:-1], edges[1:], lengths, strict=True):
        native = audio[:, left:right]
        if min(right-left, size) <= 2*(keep+blend):
            raise LocalGridFailure("Insufficient real audio for local beat anchors")
        backend = "identity"
        if right-left == size:
            chunk = native.copy()
        else:
            speed = float(right-left) / size
            start, stop = max(0, left-margin), min(audio.shape[1], right+margin)
            corrected = engine.adjust_tempo_by_factor(audio[:, start:stop], rate, speed)
            offset = round((left-start) / speed)
            chunk = corrected[:, offset:offset+size].copy()
            if chunk.shape != (2, size):
                raise LocalGridFailure("Incomplete locally stretched interval")
            ramp = np.linspace(0, 1, blend, dtype=np.float32)
            chunk[:, :keep] = native[:, :keep]
            chunk[:, -keep:] = native[:, -keep:]
            head, tail = slice(keep, keep+blend), slice(-keep-blend, -keep)
            chunk[:, head] = native[:, head]*(1-ramp) + chunk[:, head]*ramp
            chunk[:, tail] = native[:, tail]*ramp + chunk[:, tail]*(1-ramp)
            backend = engine.last_backend
        if not (np.array_equal(chunk[:, :keep], native[:, :keep]) and
                np.array_equal(chunk[:, -keep:], native[:, -keep:])):
            raise LocalGridFailure("Boundary samples were displaced")
        receipts.append(dict(backend=backend, head_sha256=sample_hash(native[:, :keep]),
                             tail_sha256=sample_hash(native[:, -keep:])))
        chunks.append(chunk)
        marks.append(marks[-1] + chunk.shape[1])
    aligned = np.concatenate(chunks, axis=1)
    gate = check_timing(source_beats, marks, aligned.shape[1], rate)
    return aligned, dict(output_beats=marks, guard_frames=keep, intervals=receipts, **gate)
