"""Decision Accounting models -- dataclasses and enums for cost/value/debt tracking.

Defines the object model for cost records, budgets, time-to-decision,
value assessments, decision debt, and ROI reports.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class CostCategory(str, Enum):
    """Categories of decision cost."""

    TIME = "time"
    COMPUTE = "compute"
    REWORK = "rework"
    OPPORTUNITY = "opportunity"
    ESCALATION = "escalation"


@dataclass
class CostRecord:
    """A single cost event against a commitment."""

    cost_id: str
    commitment_id: str
    category: str  # CostCategory value
    amount: float
    handler_id: Optional[str] = None
    recorded_at: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CostBudget:
    """Budget threshold for a commitment or domain."""

    budget_id: str
    commitment_id: str
    max_amount: float
    current_amount: float = 0.0
    overrun: bool = False


@dataclass
class TimeToDecision:
    """Elapsed time from episode begin to commitment complete."""

    commitment_id: str
    episode_id: str
    elapsed_ms: float = 0.0
    handler_chain_ms: Dict[str, float] = field(default_factory=dict)
    measured_at: str = ""


@dataclass
class ValueAssessment:
    """Assessment of delivered value for a commitment."""

    assessment_id: str
    commitment_id: str
    outcome_quality: float = 0.0  # 0.0-1.0
    deliverable_completion: float = 0.0  # 0.0-1.0
    composite_value: float = 0.0  # weighted combination
    assessed_at: str = ""


@dataclass
class DecisionDebt:
    """Decision debt — rework, scope reduction, or quality shortfall."""

    debt_id: str
    commitment_id: str
    debt_type: str  # rework, scope_reduction, quality_shortfall
    estimated_cost: float = 0.0
    resolved: bool = False
    detected_at: str = ""


@dataclass
class ROIReport:
    """Return on investment report for a scope (commitment, domain, batch)."""

    report_id: str
    scope: str  # commitment, domain, batch
    scope_id: str = ""
    total_cost: float = 0.0
    total_value: float = 0.0
    roi: float = 0.0  # (value - cost) / cost
    debt_outstanding: float = 0.0
    computed_at: str = ""
