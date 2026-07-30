"""Differentiable mixing controls and direct optimization probes."""

from .differentiable import (
    CONTROL_NAMES,
    CONTROL_PROTOCOL_VERSION,
    DEFAULT_INCREMENT_LOGIT_BOUND,
    ControlOptimizationResult,
    DifferentiableRenderResult,
    DifferentiableTransitionObjective,
    DifferentiableTransitionObjectiveConfig,
    DifferentiableTwoBandRenderer,
    OptimizableControlCurves,
    maximum_control_increment,
    optimize_control_curves,
)

__all__ = [
    "CONTROL_NAMES",
    "CONTROL_PROTOCOL_VERSION",
    "DEFAULT_INCREMENT_LOGIT_BOUND",
    "ControlOptimizationResult",
    "DifferentiableRenderResult",
    "DifferentiableTransitionObjective",
    "DifferentiableTransitionObjectiveConfig",
    "DifferentiableTwoBandRenderer",
    "OptimizableControlCurves",
    "maximum_control_increment",
    "optimize_control_curves",
]
