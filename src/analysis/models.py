"""Stable provenance model for beat/bar analysis results."""

from dataclasses import dataclass
import math


GRID_METADATA_FORMAT_VERSION = 1


@dataclass(frozen=True)
class BeatGridMetadata:
    """Describe where a bar grid came from without changing its beat tuples."""

    grid_source: str
    fallback_used: bool | None
    backend_version: str | None
    confidence: float | None
    format_version: int = GRID_METADATA_FORMAT_VERSION

    def __post_init__(self):
        if not str(self.grid_source).strip():
            raise ValueError("grid_source must not be empty")
        if self.fallback_used is not None and not isinstance(self.fallback_used, bool):
            raise ValueError("fallback_used must be true, false, or null")
        if self.backend_version is not None and not isinstance(self.backend_version, str):
            raise ValueError("backend_version must be a string or null")
        if self.confidence is not None:
            confidence = float(self.confidence)
            if not math.isfinite(confidence) or not 0.0 <= confidence <= 1.0:
                raise ValueError("confidence must be null or a finite value in [0, 1]")
            object.__setattr__(self, "confidence", confidence)

    @property
    def is_verified_detection(self):
        return self.fallback_used is False

    def to_dict(self):
        return {
            "format_version": self.format_version,
            "grid_source": self.grid_source,
            "fallback_used": self.fallback_used,
            "backend_version": self.backend_version,
            "confidence": self.confidence,
        }

    @classmethod
    def from_dict(cls, payload):
        if not isinstance(payload, dict):
            raise ValueError("Grid metadata must be a JSON object")
        return cls(
            format_version=int(payload.get("format_version", GRID_METADATA_FORMAT_VERSION)),
            grid_source=str(payload["grid_source"]),
            fallback_used=payload.get("fallback_used"),
            backend_version=payload.get("backend_version"),
            confidence=payload.get("confidence"),
        )


@dataclass(frozen=True)
class AnalysisResult:
    """Additive analysis result that remains compatible with two-value unpacking."""

    bpm: float
    beat_frames: tuple[tuple[int, int, int], ...]
    grid_metadata: BeatGridMetadata

    def __iter__(self):
        yield self.bpm
        yield list(self.beat_frames)

    def __len__(self):
        return 2

    def __getitem__(self, index):
        values = (self.bpm, list(self.beat_frames))
        return values[index]


def unknown_grid_metadata(grid_source="external_unknown"):
    return BeatGridMetadata(
        grid_source=grid_source,
        fallback_used=None,
        backend_version=None,
        confidence=None,
    )


def unpack_analysis_result(result):
    """Return BPM, frames, and validated provenance from old or new results."""
    bpm, beat_frames = result
    metadata = getattr(result, "grid_metadata", None)
    if metadata is None:
        metadata = unknown_grid_metadata()
    elif isinstance(metadata, dict):
        metadata = BeatGridMetadata.from_dict(metadata)
    elif not isinstance(metadata, BeatGridMetadata):
        raise TypeError("grid_metadata must be BeatGridMetadata or a metadata dictionary")
    return bpm, beat_frames, metadata
