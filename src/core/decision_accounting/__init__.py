"""Decision Accounting -- cost, value, debt, and ROI tracking for commitments.

Extends ActionOps with financial dimensions: cost accrual, time-to-decision,
value assessment, debt detection, ROI computation, and budget enforcement.
"""

from __future__ import annotations

from .cost_tracking import compute_budget_status, detect_overrun, record_handler_cost
from .debt_engine import detect_debt, estimate_debt_cost
from .models import (
    CostBudget,
    CostCategory,
    CostRecord,
    DecisionDebt,
    ROIReport,
    TimeToDecision,
    ValueAssessment,
)
from .registry import AccountingRegistry
from .validators import validate_cost_record, validate_value_assessment
from .value_scoring import compute_composite_value, compute_outcome_quality, compute_roi

__all__ = [
    "AccountingRegistry",
    "CostBudget",
    "CostCategory",
    "CostRecord",
    "DecisionDebt",
    "ROIReport",
    "TimeToDecision",
    "ValueAssessment",
    "compute_budget_status",
    "compute_composite_value",
    "compute_outcome_quality",
    "compute_roi",
    "detect_debt",
    "detect_overrun",
    "estimate_debt_cost",
    "record_handler_cost",
    "validate_cost_record",
    "validate_value_assessment",
]
