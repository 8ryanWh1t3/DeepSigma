"""Value scoring functions for decision accounting."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List

from .models import ROIReport, ValueAssessment
from .registry import AccountingRegistry


def compute_outcome_quality(
    deliverable_statuses: List[str],
) -> float:
    """Compute outcome quality from deliverable completion statuses.

    Returns a float in [0.0, 1.0].
    """
    if not deliverable_statuses:
        return 0.0
    delivered = sum(1 for s in deliverable_statuses if s == "delivered")
    return round(delivered / len(deliverable_statuses), 4)


def compute_composite_value(
    outcome_quality: float,
    deliverable_completion: float,
    quality_weight: float = 0.6,
    completion_weight: float = 0.4,
) -> float:
    """Compute weighted composite value score."""
    return round(
        quality_weight * outcome_quality + completion_weight * deliverable_completion,
        4,
    )


def compute_roi(
    registry: AccountingRegistry,
    commitment_id: str,
) -> ROIReport:
    """Compute ROI for a commitment: (value - cost) / cost."""
    total_cost = registry.total_cost(commitment_id)
    assessment = registry.get_assessment(commitment_id)
    total_value = assessment.composite_value if assessment else 0.0
    debt = registry.outstanding_debt(commitment_id)

    roi = 0.0
    if total_cost > 0:
        roi = round((total_value - total_cost) / total_cost, 4)

    return ROIReport(
        report_id=f"ROI-{uuid.uuid4().hex[:8]}",
        scope="commitment",
        scope_id=commitment_id,
        total_cost=total_cost,
        total_value=total_value,
        roi=roi,
        debt_outstanding=debt,
        computed_at=datetime.now(timezone.utc).isoformat(),
    )
