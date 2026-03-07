"""Paradox Tension Set models — dataclasses and enums.

Defines the canonical object model for tension sets, poles, dimensions,
inter-dimensional drift, and tension patches.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class TensionSubtype(str, Enum):
    """Cardinality subtypes for Paradox Tension Sets."""

    TENSION_PAIR = "tension_pair"
    TENSION_TRIPLE = "tension_triple"
    HIGHER_ORDER = "higher_order"


class TensionLifecycleState(str, Enum):
    """Lifecycle states for a Paradox Tension Set."""

    DETECTED = "detected"
    ACTIVE = "active"
    ELEVATED = "elevated"
    PROMOTED_TO_DRIFT = "promoted_to_drift"
    SEALED = "sealed"
    PATCHED = "patched"
    REBALANCED = "rebalanced"
    ARCHIVED = "archived"


class DimensionKind(str, Enum):
    """Whether a dimension is common (canonical) or uncommon (extension)."""

    COMMON = "common"
    UNCOMMON = "uncommon"


class PatchAction(str, Enum):
    """Recommended patch actions for tension remediation."""

    INCREASE_CONTROL_FRICTION = "increase_control_friction"
    CLARIFY_AUTHORITY = "clarify_authority"
    ADD_REVIEW_GATE = "add_review_gate"
    SPLIT_BY_LAYER = "split_by_layer"
    REDUCE_IRREVERSIBILITY = "reduce_irreversibility"
    ELEVATE_VISIBILITY = "elevate_visibility"
    EXPIRE_STALE_ASSUMPTION = "expire_stale_assumption"
    PROMOTE_TO_POLICY_BAND = "promote_to_policy_band"


@dataclass
class TensionPole:
    """A single pole in a Paradox Tension Set."""

    pole_id: str
    label: str
    weight: float = 1.0
    evidence_refs: List[str] = field(default_factory=list)


@dataclass
class TensionDimension:
    """A dimension attached to a Paradox Tension Set."""

    dimension_id: str
    name: str
    kind: str = "common"
    current_value: float = 0.0
    previous_value: float = 0.0
    shifted_at: Optional[str] = None
    is_governance_relevant: bool = False
    threshold: float = 0.5


@dataclass
class ParadoxTensionSet:
    """A set of competing truths in the same operational space."""

    tension_id: str
    subtype: str
    poles: List[TensionPole] = field(default_factory=list)
    dimensions: List[TensionDimension] = field(default_factory=list)
    lifecycle_state: str = "detected"
    pressure_score: float = 0.0
    imbalance_vector: List[float] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""
    sealed_at: Optional[str] = None
    seal_hash: str = ""
    seal_version: int = 1
    episode_id: str = ""
    promoted_drift_id: Optional[str] = None
    patch_id: Optional[str] = None
    version: str = "1.0.0"


@dataclass
class TensionPatch:
    """A patch recommendation for a Paradox Tension Set."""

    patch_id: str
    tension_id: str
    recommended_actions: List[str] = field(default_factory=list)
    rationale: str = ""
    issued_at: str = ""
    applied_at: Optional[str] = None


@dataclass
class InterDimensionalDrift:
    """Record of inter-dimensional drift detection."""

    drift_id: str
    tension_id: str
    shifted_dimensions: List[str] = field(default_factory=list)
    stale_dimensions: List[str] = field(default_factory=list)
    severity: str = "red"
    trigger_reason: str = ""
    promoted_from_pressure: float = 0.0
    created_at: str = ""
