"""Differentiable mixing controls and direct optimization probes."""

from .differentiable import (
    CONTROL_NAMES,
    CONTROL_PROTOCOL_VERSION,
    ControlOptimizationResult,
    DifferentiableRenderResult,
    DifferentiableTransitionObjective,
    DifferentiableTransitionObjectiveConfig,
    DifferentiableTwoBandRenderer,
    OptimizableControlCurves,
    optimize_control_curves,
)

__all__ = [
    "CONTROL_NAMES",
    "CONTROL_PROTOCOL_VERSION",
    "ControlOptimizationResult",
    "DifferentiableRenderResult",
    "DifferentiableTransitionObjective",
    "DifferentiableTransitionObjectiveConfig",
    "DifferentiableTwoBandRenderer",
    "OptimizableControlCurves",
    "optimize_control_curves",
]
