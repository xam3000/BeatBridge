"""Score the continuation from the four original A bars before S to four B bars at T."""

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import soundfile as sf
import torch

from src.analysis.models import unpack_analysis_result
from src.analysis.pre_analysis import _beat_grid_sha256
from src.features.p07_audio import bar_geometry
from src.features.p07_mert import FrozenMert, HIDDEN_SIZE, LAYER_COUNT, SAMPLE_RATE, file_sha256, model_identity
from src.features.p08_windows import checked, contiguous_starts, read_json
from src.ml.p09_metric import ContinuationMetric
from src.ranking.feature_baseline import RankingFailure


METHOD = "mert_continuation_v1"
ISOLATED_METHOD = "mert_continuation_v2"
ISOLATED_SELECTION = Path("docs/masterarbeit/review_jp_20261118/mert_fenster/selection.json")
SELECTION = Path("docs/masterarbeit/review_jp_20261118/p10/selection.json")
P09_AUDIT = Path("docs/masterarbeit/P09_VERIFIED_20261119.json")
MODEL_DIR = Path("output/review_jp_20261118/p07/model")


def load_head(row, run, config_sha):
    head = ContinuationMetric(row["family"], row["level"])
    if row["level"]:
        state = torch.load(checked(run / row["checkpoint"], row["checkpoint_sha256"]),
                           map_location="cpu", weights_only=True)
        if (state["config_sha256"] != config_sha or state["epoch"] != row["best_epoch"] or
                any(row[key] != state[key] for key in ("seed", "family", "level"))):
            raise ValueError("P09 checkpoint has a different training contract")
        head.load_state_dict(state["state_dict"])
    return head.eval()


@dataclass
class BarWindows:
    """Map native beat IDs to four-bar windows on each side of a complete eight-bar run."""

    starts: dict
    samples: dict
    grid_sha: str
    bars: np.ndarray

    @classmethod
    def from_bars(cls, beats, bounds, values, native_frames, grid_sha, sample_factor):
        if len(beats) != len(values) or len(beats) != len(bounds):
            raise ValueError("Bar features and bar grid differ")
        centres = contiguous_starts(beats, bounds, 8) + 4
        starts = {int(beats[i]): int(i) for i in centres}
        samples = {b: round(int(native_frames[b][0]) * sample_factor) for b in starts}
        return cls(starts, samples, grid_sha, values)

    def cue_row(self, cut, grid):
        if grid is None or not grid.is_verified_detection or grid.beat_grid_sha256 != self.grid_sha:
            raise ValueError("Candidate and representation require the same detected grid")
        b = cut.beat_index
        if b in self.starts and self.samples[b] != cut.sample:
            raise ValueError("Candidate sample differs from the native downbeat at render rate")
        return self.starts.get(b)


def live_windows(track, analysis, rate, encoder, *, isolated=False):
    import soxr

    if file_sha256(track.path) != track.sha256:
        raise ValueError("Candidate audio identity changed")
    _, frames, grid = unpack_analysis_result(analysis(track.path))
    if (not grid.is_verified_detection or grid.grid_source != "auftakt_matched_to_librosa_partial_v2"
            or grid.beat_grid_sha256 != _beat_grid_sha256(frames)):
        raise ValueError("Continuation inference requires a verified native beat grid")
    audio, native_rate = sf.read(track.path, dtype="float32", always_2d=True)
    mono = audio.mean(axis=1, dtype=np.float32)
    if native_rate != SAMPLE_RATE:
        mono = soxr.resample(mono, native_rate, SAMPLE_RATE, quality="HQ")
    grid24 = np.array(frames, dtype=np.int64)
    grid24[:, 0] = np.rint(grid24[:, 0] * (SAMPLE_RATE / native_rate))
    beats, bounds = bar_geometry(grid24, len(mono))
    if isolated:
        starts = contiguous_starts(beats, bounds, 4)
        values = np.full((len(bounds), LAYER_COUNT, HIDDEN_SIZE), np.nan, dtype=np.float32)
        if len(starts):
            values[starts] = encoder.isolated_means(mono, bounds, starts)
    else:
        values, _ = encoder.encode(mono, bounds)
    return BarWindows.from_bars(beats, bounds, values, frames, grid.beat_grid_sha256, rate / native_rate)


def candidate_windows(candidates, windows):
    accepted, indices, excluded = [], [], []
    for c in candidates:
        if (c.transition_length_bars, c.transition_length_beats) != (4, 16):
            raise ValueError("The continuation ranker requires four 4/4 bars")
        a, b = windows[c.source_track.sha256], windows[c.target_track.sha256]
        source = a.cue_row(c.source_cutpoint, c.source_grid)
        target = b.cue_row(c.target_cutpoint, c.target_grid)
        if source is None or target is None:
            excluded.append(RankingFailure(c.candidate_id, "incomplete_bar_window",
                                           "Cue lacks contiguous P07 bars before and after the downbeat"))
            continue
        accepted.append(c)
        indices.append((source - 4, target))
    return accepted, np.asarray(indices, dtype=np.int64).reshape(-1, 2), tuple(excluded)


@torch.inference_mode()
def score_pair(head, indices, a, b, *, isolated=False):
    """Encode each distinct four-bar mean once per role on one directed track pair."""
    encoded, lookups = [], []
    for source, rows, bars in ((True, indices[:, 0], a), (False, indices[:, 1], b)):
        starts, inverse = np.unique(rows, return_inverse=True)
        means = bars[starts] if isolated else bars[starts[:, None] + np.arange(4)].mean(axis=1, dtype=np.float32)
        encoded.append(head.encode(torch.from_numpy(means), source=source))
        lookups.append(torch.from_numpy(inverse))
    scores = torch.cat([(encoded[0][i] * encoded[1][j]).sum(-1)
                        for i, j in zip(lookups[0].split(512), lookups[1].split(512), strict=True)]).numpy()
    if not np.isfinite(scores).all():
        raise ValueError("Nonfinite continuation scores")
    return scores


@dataclass(frozen=True)
class ContinuationScore:
    candidate_id: str
    rank: int
    total_score: float


@dataclass
class ContinuationRanking:
    scores: tuple
    provenance: dict
    failures: tuple = ()
    method: str = METHOD

    def to_dict(self):
        return dict(format_version=1, ranker=self.method, provenance=self.provenance,
                    scores=[vars(s) for s in self.scores], failures=[f.to_dict() for f in self.failures])


def encoder_runtime():
    """Match the P07 cache extraction, including native bfloat16 support."""
    if not torch.cuda.is_available() or not torch.cuda.is_bf16_supported(including_emulation=False):
        raise ValueError("P10 MERT inference requires CUDA with native bfloat16 support")
    device = torch.device("cuda", torch.cuda.current_device())
    return dict(device=str(device), gpu=torch.cuda.get_device_name(device),
                autocast="bfloat16", pooling_dtype="float32", head_device="cpu")


def rank_continuations(candidates, analysis, rate, selection_path=ISOLATED_SELECTION):
    selection = read_json(selection_path)
    method = selection["ranking_method"]
    isolated = method == ISOLATED_METHOD
    row = selection.get("selected", {})
    if (selection["status"] != "selected" or method not in (METHOD, ISOLATED_METHOD) or row.get("family") != "mert"
            or selection["representation"] != model_identity()):
        raise ValueError("Invalid MERT continuation selection")
    config = read_json(checked(Path(selection["run"]) / "config.json", selection["config_sha256"]))
    if config.get("input_encoding", METHOD) != method or (isolated and config.get("representation") != model_identity()):
        raise ValueError("MERT checkpoint and requested window encoding differ")
    runtime = encoder_runtime()
    head = load_head(row, Path(selection["run"]), selection["config_sha256"])
    provenance = dict(selection_sha256=file_sha256(selection_path), **row,
                      representation=selection["representation"], encoder_runtime=runtime,
                      input="isolated four-bar audio" if isolated else "native four-bar means")
    if not candidates:
        return ContinuationRanking((), provenance, method=method)
    first = candidates[0]
    if any((c.source_track, c.target_track) != (first.source_track, first.target_track) for c in candidates):
        raise ValueError("Continuation ranking requires a single directed pair")
    encoder = FrozenMert(MODEL_DIR, runtime["device"])
    windows = {t.sha256: live_windows(t, analysis, rate, encoder, isolated=isolated)
               for t in (first.source_track, first.target_track)}
    candidates, indices, excluded = candidate_windows(candidates, windows)
    if not candidates:
        return ContinuationRanking((), provenance, excluded, method)
    scores = score_pair(head, indices, windows[first.source_track.sha256].bars,
                        windows[first.target_track.sha256].bars, isolated=isolated)
    ordered = sorted(zip(candidates, scores, strict=True), key=lambda p: (-p[1], p[0].candidate_id))
    return ContinuationRanking(tuple(ContinuationScore(c.candidate_id, i, float(s))
                                     for i, (c, s) in enumerate(ordered, 1)), provenance, excluded, method)
