"""ParadoxOps -- paradox tension detection and lifecycle management.

Detects competing truths (tensions) in the same operational space,
tracks them through lifecycle states, computes pressure and imbalance,
and promotes them to drift signals when thresholds are breached.
"""

from __future__ import annotations

from .dimensions import COMMON_DIMENSIONS, DimensionRegistry
from .drift import build_patch_recommendations, detect_interdimensional_drift
from .lifecycle import TensionLifecycle
from .models import (
    DimensionKind,
    InterDimensionalDrift,
    ParadoxTensionSet,
    PatchAction,
    TensionDimension,
    TensionLifecycleState,
    TensionPatch,
    TensionPole,
    TensionSubtype,
)
from .registry import ParadoxRegistry
from .scoring import compute_imbalance, compute_pressure, evaluate_thresholds
from .validators import validate_dimension_shift, validate_patch, validate_tension_set

__all__ = [
    "COMMON_DIMENSIONS",
    "DimensionKind",
    "DimensionRegistry",
    "InterDimensionalDrift",
    "ParadoxRegistry",
    "ParadoxTensionSet",
    "PatchAction",
    "TensionDimension",
    "TensionLifecycle",
    "TensionLifecycleState",
    "TensionPatch",
    "TensionPole",
    "TensionSubtype",
    "build_patch_recommendations",
    "compute_imbalance",
    "compute_pressure",
    "detect_interdimensional_drift",
    "evaluate_thresholds",
    "validate_dimension_shift",
    "validate_patch",
    "validate_tension_set",
]
