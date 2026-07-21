"""Stable data model and generation helpers for transition candidates."""

from .generation import CandidateGenerationConfig, generate_candidates
from .models import (
    CANDIDATE_FORMAT_VERSION,
    CandidateGenerationResult,
    CandidateRejection,
    CutPoint,
    TrackReference,
    TransitionCandidate,
)

__all__ = [
    "CANDIDATE_FORMAT_VERSION",
    "CandidateGenerationConfig",
    "CandidateGenerationResult",
    "CandidateRejection",
    "CutPoint",
    "TrackReference",
    "TransitionCandidate",
    "generate_candidates",
]
