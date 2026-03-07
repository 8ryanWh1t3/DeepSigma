"""DecisionSurface models — portable surface-layer dataclasses and enums.

Defines the data model for claims, events, evidence, assumptions,
drift signals, patch recommendations, decision artifacts, and
evaluation results used across all surface adapters.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class ClaimStatus(str, Enum):
    """Status of a claim after evaluation."""

    SATISFIED = "satisfied"
    AT_RISK = "at_risk"
    DRIFTED = "drifted"
    PENDING = "pending"


@dataclass
class Claim:
    """A decision claim to be evaluated against events."""

    claim_id: str
    statement: str
    confidence: float = 1.0
    assumptions: List[str] = field(default_factory=list)
    evidence_refs: List[str] = field(default_factory=list)
    status: str = "pending"
    created_at: str = ""


@dataclass
class Event:
    """An observable event that may support or contradict claims."""

    event_id: str
    event_type: str
    source: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = ""
    claim_refs: List[str] = field(default_factory=list)


@dataclass
class Evidence:
    """A link between a claim and a supporting event."""

    evidence_id: str
    claim_id: str
    event_id: str
    strength: float = 1.0
    notes: str = ""


@dataclass
class Assumption:
    """A time-bound assumption linked to one or more claims."""

    assumption_id: str
    statement: str
    expires_at: Optional[str] = None
    expired: bool = False
    linked_claim_ids: List[str] = field(default_factory=list)


@dataclass
class DriftSignal:
    """A drift signal emitted when evaluation detects anomalies."""

    signal_id: str
    drift_type: str
    severity: str = "yellow"
    source_claim_id: str = ""
    detail: str = ""
    detected_at: str = ""


@dataclass
class PatchRecommendation:
    """A recommended corrective action for a drift signal."""

    patch_id: str
    drift_signal_id: str
    action: str = ""
    rationale: str = ""
    issued_at: str = ""


@dataclass
class DecisionArtifact:
    """A sealed snapshot of a complete decision surface evaluation."""

    artifact_id: str
    claims: List[Claim] = field(default_factory=list)
    events: List[Event] = field(default_factory=list)
    evidence: List[Evidence] = field(default_factory=list)
    drift_signals: List[DriftSignal] = field(default_factory=list)
    patches: List[PatchRecommendation] = field(default_factory=list)
    sealed_at: Optional[str] = None
    seal_hash: str = ""


@dataclass
class MemoryGraphUpdate:
    """A batch of nodes and edges to write to the Memory Graph."""

    nodes: List[Dict[str, Any]] = field(default_factory=list)
    edges: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class EvaluationResult:
    """Aggregate result of evaluating claims against events."""

    claims_evaluated: int = 0
    satisfied: int = 0
    at_risk: int = 0
    drifted: int = 0
    pending: int = 0
    drift_signals: List[DriftSignal] = field(default_factory=list)
    patches: List[PatchRecommendation] = field(default_factory=list)
    memory_graph_update: Optional[MemoryGraphUpdate] = None
