"""Index the audited P07 release in native bar time for continuation retrieval."""

from dataclasses import dataclass
import json
from pathlib import Path

import numpy as np
import soundfile as sf

from src.features.p07_mert import SAMPLE_RATE, file_sha256
from src.features.p07_population import FREEZE, validate_groups


RECEIPT = Path("docs/masterarbeit/P07_VERIFIED_20261119.json")
P07 = Path("output/review_jp_20261118/p07/full")
VARIANTS = ("original", "warm_room", "bright_room")
STRUCTURE_COLUMNS = ("mean:rms_dbfs", "mean:low_energy_ratio", "mean:kick_prominence",
                     "mean:vocal_activity")


def read_json(path):
    return json.loads(path.read_bytes())


def checked(path, digest):
    if file_sha256(path) != digest:
        raise ValueError(f"Checksum mismatch: {path}")
    return path


def p07_views(root):
    receipt = read_json(RECEIPT)
    manifest = read_json(checked(root / "manifest.json", receipt["manifest_sha256"]))
    if receipt["result"] != "passed" or manifest["freeze_commit"] != FREEZE:
        raise ValueError("P08 requires the audited full P07 release")
    validate_groups(manifest["views"])
    return manifest


def contiguous_starts(beats, bars, length):
    """All starts of length complete rows sharing every internal downbeat."""
    if length < 1:
        raise ValueError("Window length must be positive")
    breaks = (beats[1:] != beats[:-1] + 4) | (bars[1:, 0] != bars[:-1, -1])
    runs = np.split(np.arange(len(beats)), np.flatnonzero(breaks) + 1)
    return np.concatenate([run[:max(0, len(run) - length + 1)] for run in runs])


@dataclass
class Track:
    sha: str
    group: str
    split: str
    bpm: float
    beats: np.ndarray
    bars: np.ndarray
    cues: np.ndarray
    targets: np.ndarray
    structure: np.ndarray  # indexed by target row, in training-standardized units
    sections: dict


def section_types(targets, descriptors, start_samples, bpm):
    rms, kicks = descriptors[:, 0], descriptors[:, 2]
    middle, high = np.quantile(rms, [0.5, 0.75])
    early = start_samples * bpm < 32 * 4 * 60 * SAMPLE_RATE
    intro = early & (rms <= middle)
    drop = ~early & (rms >= high) & (kicks >= np.median(kicks))
    return {int(t): label for t, label in zip(targets, np.select(
        [intro, drop], ["intro_like", "drop_like"], default="other"
    ))}


def index_track(root, row, columns, k, length):
    archive = (root / row["entry"]).with_name("bars.npz")
    with np.load(checked(archive, row["sha256_files"]["bars.npz"])) as z:
        beats, bars = z["bar_start_beat_index"], z["bar_boundaries_24k"]
    analysis = read_json(checked(Path(row["analysis_path"]), row["analysis_sha256"]))
    if analysis["source_audio"]["sha256"] != row["sha256"]:
        raise ValueError("Wrong native analysis")
    native = np.asarray(analysis["result"]["beat_frames"])[beats[:, None] + np.arange(5)]
    rate = sf.info(row["path"]).samplerate
    expected = np.rint(native[:, :, 0] * (SAMPLE_RATE / rate))
    if (not np.array_equal(bars[:, ::2], expected)
            or not np.all(native[:, :, 1] == [1, 2, 3, 4, 1])
            or not np.all(native[:, :4, 2] == 4)):
        raise ValueError(f"Bar coordinates disagree with the native grid: {row['sha256']}")
    cues = contiguous_starts(beats, bars, 2*k + length) + k
    targets = contiguous_starts(beats, bars, length + k) + length
    with np.load(checked(root / row["classical_scaled"], row["classical_scaled_sha256"])) as z:
        descriptors = z["classical"][:, columns].astype(np.float64)
    structure = np.full((len(bars), len(columns)), np.nan)
    structure[targets] = descriptors[targets[:, None] + np.arange(k)].mean(axis=1)
    sections = section_types(targets, structure[targets], bars[targets, 0], row["bpm"]) if len(targets) else {}
    return Track(row["sha256"], row["recording_group_id"], row["split"], row["bpm"],
                 beats, bars, cues, targets, structure, sections)


def same_track_pool(track, d, k, length):
    """Count complete intervening rows outside both windows, ignoring missing bars."""
    t = d + length
    others = track.targets
    gap = np.maximum(d - k - (others + k), others - (t + k))
    different = np.abs(track.structure[others] - track.structure[t]) >= 1.
    return others[(gap > 16) & (different.sum(axis=1) >= 2)]
