"""Versioned, serialisable transition-candidate contract."""

from dataclasses import dataclass

from src.analysis.models import BeatGridMetadata


CANDIDATE_FORMAT_VERSION = 1


@dataclass(frozen=True)
class TrackReference:
    """A reproducible reference to one source track."""

    path: str
    sha256: str

    def to_dict(self):
        return {"path": self.path, "sha256": self.sha256}


@dataclass(frozen=True)
class CutPoint:
    """A downbeat on the normalised sample grid of one track."""

    sample: int
    beat_index: int
    bar_index: int
    count_in_bar: int
    beats_in_bar: int

    def to_dict(self):
        return {
            "sample": self.sample,
            "beat_index": self.beat_index,
            "bar_index": self.bar_index,
            "count_in_bar": self.count_in_bar,
            "beats_in_bar": self.beats_in_bar,
        }


@dataclass(frozen=True)
class TransitionCandidate:
    """One accepted, bar-aligned transition candidate."""

    candidate_id: str
    source_track: TrackReference
    target_track: TrackReference
    source_cutpoint: CutPoint
    target_cutpoint: CutPoint
    transition_length_bars: int
    transition_length_beats: int
    source_bpm: float
    target_bpm: float
    tempo_relative_difference: float
    generator: str
    filter_status: str = "accepted"
    format_version: int = CANDIDATE_FORMAT_VERSION
    source_grid: BeatGridMetadata | None = None
    target_grid: BeatGridMetadata | None = None

    def to_dict(self):
        return {
            "format_version": self.format_version,
            "candidate_id": self.candidate_id,
            "source_track": self.source_track.to_dict(),
            "target_track": self.target_track.to_dict(),
            "source_cutpoint": self.source_cutpoint.to_dict(),
            "target_cutpoint": self.target_cutpoint.to_dict(),
            "transition_length_bars": self.transition_length_bars,
            "transition_length_beats": self.transition_length_beats,
            "source_bpm": self.source_bpm,
            "target_bpm": self.target_bpm,
            "tempo_relative_difference": self.tempo_relative_difference,
            "generator": self.generator,
            "source_grid": None if self.source_grid is None else self.source_grid.to_dict(),
            "target_grid": None if self.target_grid is None else self.target_grid.to_dict(),
            "filter_status": self.filter_status,
        }


@dataclass(frozen=True)
class CandidateRejection:
    """An auditable hard-filter outcome from one generation run."""

    code: str
    message: str

    def to_dict(self):
        return {"code": self.code, "message": self.message}


@dataclass(frozen=True)
class CandidateGenerationResult:
    """Accepted candidates plus all pair- or track-level hard-filter outcomes."""

    candidates: tuple[TransitionCandidate, ...]
    rejections: tuple[CandidateRejection, ...]
    format_version: int = CANDIDATE_FORMAT_VERSION
    source_grid: BeatGridMetadata | None = None
    target_grid: BeatGridMetadata | None = None
    approximate_grid_policy: str = "reject"

    def to_dict(self):
        return {
            "format_version": self.format_version,
            "approximate_grid_policy": self.approximate_grid_policy,
            "source_grid": None if self.source_grid is None else self.source_grid.to_dict(),
            "target_grid": None if self.target_grid is None else self.target_grid.to_dict(),
            "candidates": [candidate.to_dict() for candidate in self.candidates],
            "rejections": [rejection.to_dict() for rejection in self.rejections],
        }
