"""Decision debt detection and estimation."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List

from .models import DecisionDebt
from .registry import AccountingRegistry


def detect_debt(
    commitment_id: str,
    deliverable_statuses: List[str],
    risk_score: float = 0.0,
    rework_count: int = 0,
) -> List[DecisionDebt]:
    """Detect decision debt from commitment state.

    Checks for:
    - rework: deliverables that cycled back to in_progress
    - scope_reduction: failed deliverables
    - quality_shortfall: high risk score with low completion
    """
    now = datetime.now(timezone.utc).isoformat()
    debts: List[DecisionDebt] = []

    # Rework debt
    if rework_count > 0:
        debts.append(DecisionDebt(
            debt_id=f"DEBT-{uuid.uuid4().hex[:8]}",
            commitment_id=commitment_id,
            debt_type="rework",
            estimated_cost=rework_count * 1.0,  # 1.0 unit per rework cycle
            detected_at=now,
        ))

    # Scope reduction debt
    failed = sum(1 for s in deliverable_statuses if s == "failed")
    if failed > 0:
        debts.append(DecisionDebt(
            debt_id=f"DEBT-{uuid.uuid4().hex[:8]}",
            commitment_id=commitment_id,
            debt_type="scope_reduction",
            estimated_cost=failed * 2.0,  # 2.0 units per failed deliverable
            detected_at=now,
        ))

    # Quality shortfall debt
    total = len(deliverable_statuses) or 1
    delivered = sum(1 for s in deliverable_statuses if s == "delivered")
    completion_rate = delivered / total
    if risk_score >= 0.5 and completion_rate < 0.8:
        debts.append(DecisionDebt(
            debt_id=f"DEBT-{uuid.uuid4().hex[:8]}",
            commitment_id=commitment_id,
            debt_type="quality_shortfall",
            estimated_cost=round((1 - completion_rate) * 5.0, 2),
            detected_at=now,
        ))

    return debts


def estimate_debt_cost(debts: List[DecisionDebt]) -> float:
    """Sum the estimated cost of all unresolved debts."""
    return sum(d.estimated_cost for d in debts if not d.resolved)
