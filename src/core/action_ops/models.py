"""ActionOps models -- dataclasses and enums for commitment tracking.

Defines the canonical object model for commitments, deliverables,
compliance checks, and remediation records.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class CommitmentState(str, Enum):
    """Lifecycle states for a commitment."""

    PROPOSED = "proposed"
    ACTIVE = "active"
    AT_RISK = "at_risk"
    BREACHED = "breached"
    REMEDIATED = "remediated"
    ESCALATED = "escalated"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class CommitmentType(str, Enum):
    """Commitment categories."""

    DELIVERY = "delivery"
    SLA = "sla"
    RESOURCE = "resource"
    COMPLIANCE = "compliance"


class DeliverableStatus(str, Enum):
    """Status of a single deliverable."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    DELIVERED = "delivered"
    FAILED = "failed"


class BreachSeverity(str, Enum):
    """Severity of a commitment breach."""

    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"


@dataclass
class Deliverable:
    """A trackable unit of work within a commitment."""

    deliverable_id: str
    description: str
    status: str = "pending"
    due_date: Optional[str] = None
    completed_at: Optional[str] = None


@dataclass
class ComplianceCheck:
    """Result of a compliance evaluation against a commitment."""

    check_id: str
    commitment_id: str
    check_type: str  # deadline | quality | resource_utilization
    passed: bool = True
    details: str = ""
    checked_at: str = ""


@dataclass
class Commitment:
    """An operational commitment tracked through the ActionOps lifecycle."""

    commitment_id: str
    commitment_type: str
    text: str
    domain: str
    owner: str
    lifecycle_state: str = "proposed"
    deadline: Optional[str] = None
    claim_refs: List[str] = field(default_factory=list)
    deliverables: List[Deliverable] = field(default_factory=list)
    risk_score: float = 0.0
    created_at: str = ""
    updated_at: Optional[str] = None
    escalated_at: Optional[str] = None
    completed_at: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RemediationRecord:
    """Record of a remediation action taken on a breached commitment."""

    remediation_id: str
    commitment_id: str
    action: str  # adjust_deadline | reduce_scope | reassign | escalate
    rationale: str = ""
    issued_at: str = ""
    applied_at: Optional[str] = None
