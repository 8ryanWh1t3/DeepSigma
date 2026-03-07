"""Compliance evaluation for ActionOps commitments.

SLA and performance evaluation functions that produce ComplianceCheck
records and assess breach severity.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from .models import BreachSeverity, Commitment, ComplianceCheck, DeliverableStatus


def run_compliance_check(
    commitment: Commitment,
    observed_state: Dict[str, Any],
    now: Optional[datetime] = None,
) -> ComplianceCheck:
    """Run a compliance check against the observed state.

    Evaluates deadline and deliverable status from observed_state.
    """
    now = now or datetime.now(timezone.utc)
    now_iso = now.isoformat()
    check_id = f"CHK-{uuid.uuid4().hex[:8]}"

    # Deadline check
    if commitment.deadline:
        try:
            deadline = datetime.fromisoformat(
                commitment.deadline.replace("Z", "+00:00"),
            )
            if now > deadline:
                status = observed_state.get("status", "")
                if status in ("failed", "not_delivered", "missed"):
                    return ComplianceCheck(
                        check_id=check_id,
                        commitment_id=commitment.commitment_id,
                        check_type="deadline",
                        passed=False,
                        details=f"Deadline {commitment.deadline} missed; status={status}",
                        checked_at=now_iso,
                    )
        except (ValueError, AttributeError):
            pass

    # Deliverable check
    failed = [
        d for d in commitment.deliverables
        if d.status == DeliverableStatus.FAILED
    ]
    if failed:
        names = ", ".join(d.deliverable_id for d in failed)
        return ComplianceCheck(
            check_id=check_id,
            commitment_id=commitment.commitment_id,
            check_type="quality",
            passed=False,
            details=f"Failed deliverables: {names}",
            checked_at=now_iso,
        )

    return ComplianceCheck(
        check_id=check_id,
        commitment_id=commitment.commitment_id,
        check_type="quality",
        passed=True,
        details="All checks passed",
        checked_at=now_iso,
    )


def assess_breach_severity(commitment: Commitment) -> str:
    """Assess the severity of a commitment breach.

    Returns green/yellow/red based on deliverable failures and risk score.
    """
    failed_count = sum(
        1 for d in commitment.deliverables
        if d.status == DeliverableStatus.FAILED
    )
    total = len(commitment.deliverables) or 1

    failure_rate = failed_count / total

    if commitment.risk_score >= 0.8 or failure_rate >= 0.5:
        return BreachSeverity.RED
    if commitment.risk_score >= 0.5 or failure_rate >= 0.2:
        return BreachSeverity.YELLOW
    return BreachSeverity.GREEN
