"""Deliverable tracking and deadline evaluation.

Pure functions for computing risk, evaluating deliverable status,
and checking deadline proximity.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .models import Commitment, ComplianceCheck, DeliverableStatus


def check_deadline_proximity(
    commitment: Commitment,
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Assess deadline proximity and return risk assessment.

    Returns a dict with keys: at_risk, days_remaining, proximity (0.0-1.0).
    """
    if not commitment.deadline:
        return {"at_risk": False, "days_remaining": None, "proximity": 0.0}

    now = now or datetime.now(timezone.utc)
    try:
        deadline = datetime.fromisoformat(commitment.deadline.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return {"at_risk": False, "days_remaining": None, "proximity": 0.0}

    delta = deadline - now
    days_remaining = delta.total_seconds() / 86400

    if days_remaining <= 0:
        return {"at_risk": True, "days_remaining": round(days_remaining, 1), "proximity": 1.0}

    # Heuristic: at_risk when less than 20% of original time remains
    created_at = commitment.created_at
    if created_at:
        try:
            created = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            total_days = (deadline - created).total_seconds() / 86400
            if total_days > 0:
                elapsed_fraction = 1.0 - (days_remaining / total_days)
                proximity = min(1.0, max(0.0, elapsed_fraction))
                return {
                    "at_risk": proximity >= 0.8,
                    "days_remaining": round(days_remaining, 1),
                    "proximity": round(proximity, 3),
                }
        except (ValueError, AttributeError):
            pass

    return {"at_risk": days_remaining < 3, "days_remaining": round(days_remaining, 1), "proximity": 0.5}


def evaluate_deliverables(commitment: Commitment) -> Dict[str, Any]:
    """Evaluate deliverable completion status.

    Returns a dict with counts and an overall compliance flag.
    """
    if not commitment.deliverables:
        return {"total": 0, "delivered": 0, "failed": 0, "pending": 0, "compliant": True}

    total = len(commitment.deliverables)
    delivered = sum(1 for d in commitment.deliverables if d.status == DeliverableStatus.DELIVERED)
    failed = sum(1 for d in commitment.deliverables if d.status == DeliverableStatus.FAILED)
    pending = total - delivered - failed

    return {
        "total": total,
        "delivered": delivered,
        "failed": failed,
        "pending": pending,
        "compliant": failed == 0,
    }


def compute_risk_score(
    commitment: Commitment,
    checks: List[ComplianceCheck],
    now: Optional[datetime] = None,
) -> float:
    """Compute overall risk score 0.0-1.0 from weighted components.

    Components (weights):
        deadline_proximity: 0.4
        deliverable_health: 0.3
        compliance_failures: 0.3
    """
    # Deadline component
    proximity = check_deadline_proximity(commitment, now)
    deadline_risk = proximity["proximity"]

    # Deliverable component
    deliv = evaluate_deliverables(commitment)
    if deliv["total"] == 0:
        deliverable_risk = 0.0
    else:
        deliverable_risk = deliv["failed"] / deliv["total"]

    # Compliance component
    if not checks:
        compliance_risk = 0.0
    else:
        failed_checks = sum(1 for c in checks if not c.passed)
        compliance_risk = failed_checks / len(checks)

    score = (deadline_risk * 0.4) + (deliverable_risk * 0.3) + (compliance_risk * 0.3)
    return round(min(1.0, max(0.0, score)), 3)
