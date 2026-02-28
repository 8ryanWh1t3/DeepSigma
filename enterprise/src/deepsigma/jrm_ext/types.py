"""Enterprise JRM types — cross-environment drift and federation."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class CrossEnvDriftType(str, Enum):
    """Cross-environment drift types (enterprise only)."""

    VERSION_SKEW = "VERSION_SKEW"
    POSTURE_DIVERGENCE = "POSTURE_DIVERGENCE"
    REFINEMENT_CONFLICT = "REFINEMENT_CONFLICT"
    PACKET_POLICY_VIOLATION = "PACKET_POLICY_VIOLATION"
    ASSUMPTION_DIVERGENCE = "ASSUMPTION_DIVERGENCE"


@dataclass
class GateResult:
    """Result of a gate validation."""

    accepted: bool
    reason_code: str = "ok"
    violations: List[str] = field(default_factory=list)


@dataclass
class CrossEnvDrift:
    """A detected cross-environment drift event."""

    drift_id: str
    drift_type: CrossEnvDriftType
    severity: str
    environments: List[str]
    signature_id: str = ""
    detail: str = ""
    evidence: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Advisory:
    """A patch advisory published by the hub."""

    advisory_id: str
    drift_type: str
    source_env: str
    target_envs: List[str]
    recommendation: str
    status: str = "published"
    detail: Dict[str, Any] = field(default_factory=dict)
