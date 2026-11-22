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
from .variable import (
    BaselineCandidateGenerationConfig,
    SUPPORTED_VARIABLE_LENGTHS,
    VARIABLE_CANDIDATE_FORMAT_VERSION,
    VARIABLE_GENERATOR_NAME,
    VariableCandidateGenerationConfig,
    generate_variable_candidates_from_grids,
)

__all__ = [
    "CANDIDATE_FORMAT_VERSION",
    "BaselineCandidateGenerationConfig",
    "CandidateGenerationConfig",
    "CandidateGenerationResult",
    "CandidateRejection",
    "CutPoint",
    "TrackReference",
    "TransitionCandidate",
    "generate_candidates",
    "SUPPORTED_VARIABLE_LENGTHS",
    "VARIABLE_CANDIDATE_FORMAT_VERSION",
    "VARIABLE_GENERATOR_NAME",
    "VariableCandidateGenerationConfig",
    "generate_variable_candidates_from_grids",
]
