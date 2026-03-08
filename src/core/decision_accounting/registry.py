"""In-memory accounting registry for costs, budgets, assessments, and debts."""

from __future__ import annotations

from typing import Dict, List, Optional

from .models import CostBudget, CostRecord, DecisionDebt, ValueAssessment


class AccountingRegistry:
    """In-memory store for decision accounting data."""

    def __init__(self) -> None:
        self._costs: Dict[str, List[CostRecord]] = {}  # commitment_id -> costs
        self._budgets: Dict[str, CostBudget] = {}  # commitment_id -> budget
        self._assessments: Dict[str, ValueAssessment] = {}  # commitment_id -> assessment
        self._debts: Dict[str, List[DecisionDebt]] = {}  # commitment_id -> debts

    # ── Cost records ────────────────────────────────────────────

    def add_cost(self, cost: CostRecord) -> str:
        """Add a cost record. Returns the cost_id."""
        costs = self._costs.setdefault(cost.commitment_id, [])
        costs.append(cost)
        return cost.cost_id

    def get_costs(self, commitment_id: str) -> List[CostRecord]:
        """Retrieve all costs for a commitment."""
        return list(self._costs.get(commitment_id, []))

    def total_cost(self, commitment_id: str) -> float:
        """Compute total cost for a commitment."""
        return sum(c.amount for c in self._costs.get(commitment_id, []))

    # ── Budgets ─────────────────────────────────────────────────

    def set_budget(self, budget: CostBudget) -> None:
        """Set or update a budget for a commitment."""
        self._budgets[budget.commitment_id] = budget

    def get_budget(self, commitment_id: str) -> Optional[CostBudget]:
        """Retrieve budget for a commitment."""
        return self._budgets.get(commitment_id)

    # ── Value assessments ───────────────────────────────────────

    def set_assessment(self, assessment: ValueAssessment) -> None:
        """Set or update a value assessment for a commitment."""
        self._assessments[assessment.commitment_id] = assessment

    def get_assessment(self, commitment_id: str) -> Optional[ValueAssessment]:
        """Retrieve value assessment for a commitment."""
        return self._assessments.get(commitment_id)

    # ── Decision debts ──────────────────────────────────────────

    def add_debt(self, debt: DecisionDebt) -> str:
        """Add a decision debt record. Returns the debt_id."""
        debts = self._debts.setdefault(debt.commitment_id, [])
        debts.append(debt)
        return debt.debt_id

    def get_debts(self, commitment_id: str) -> List[DecisionDebt]:
        """Retrieve all debts for a commitment."""
        return list(self._debts.get(commitment_id, []))

    def outstanding_debt(self, commitment_id: str) -> float:
        """Compute outstanding (unresolved) debt for a commitment."""
        return sum(
            d.estimated_cost
            for d in self._debts.get(commitment_id, [])
            if not d.resolved
        )
