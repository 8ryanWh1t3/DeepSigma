"""Cost tracking functions for decision accounting."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from .models import CostBudget, CostRecord
from .registry import AccountingRegistry


def record_handler_cost(
    registry: AccountingRegistry,
    commitment_id: str,
    category: str,
    amount: float,
    handler_id: Optional[str] = None,
) -> CostRecord:
    """Record a cost event against a commitment."""
    now = datetime.now(timezone.utc).isoformat()
    cost = CostRecord(
        cost_id=f"COST-{uuid.uuid4().hex[:8]}",
        commitment_id=commitment_id,
        category=category,
        amount=amount,
        handler_id=handler_id,
        recorded_at=now,
    )
    registry.add_cost(cost)
    return cost


def compute_budget_status(
    registry: AccountingRegistry,
    commitment_id: str,
) -> Dict[str, Any]:
    """Compute current budget utilization for a commitment."""
    budget = registry.get_budget(commitment_id)
    total = registry.total_cost(commitment_id)

    if budget is None:
        return {
            "commitment_id": commitment_id,
            "total_cost": total,
            "budget_set": False,
            "utilization": 0.0,
            "overrun": False,
        }

    budget.current_amount = total
    utilization = total / budget.max_amount if budget.max_amount > 0 else 0.0
    budget.overrun = total > budget.max_amount

    return {
        "commitment_id": commitment_id,
        "total_cost": total,
        "budget_set": True,
        "max_amount": budget.max_amount,
        "utilization": round(utilization, 4),
        "overrun": budget.overrun,
        "remaining": max(0, budget.max_amount - total),
    }


def detect_overrun(
    registry: AccountingRegistry,
    commitment_id: str,
) -> bool:
    """Return True if the commitment has exceeded its budget."""
    budget = registry.get_budget(commitment_id)
    if budget is None:
        return False
    total = registry.total_cost(commitment_id)
    return total > budget.max_amount
