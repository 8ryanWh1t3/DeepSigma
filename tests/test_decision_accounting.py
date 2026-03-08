"""Tests for decision_accounting package and ACTION-F13→F19 handlers."""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC_ROOT = _REPO_ROOT / "src"
if str(_SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(_SRC_ROOT))

from core.decision_accounting.models import (
    CostBudget,
    CostCategory,
    CostRecord,
    DecisionDebt,
    ROIReport,
    TimeToDecision,
    ValueAssessment,
)
from core.decision_accounting.registry import AccountingRegistry
from core.decision_accounting.cost_tracking import (
    compute_budget_status,
    detect_overrun,
    record_handler_cost,
)
from core.decision_accounting.value_scoring import (
    compute_composite_value,
    compute_outcome_quality,
    compute_roi,
)
from core.decision_accounting.debt_engine import detect_debt, estimate_debt_cost
from core.decision_accounting.validators import validate_cost_record, validate_value_assessment


# ── Model Tests ──────────────────────────────────────────────────


class TestModels:
    def test_cost_category_enum(self):
        assert len(CostCategory) == 5
        assert CostCategory.TIME == "time"
        assert CostCategory.REWORK == "rework"

    def test_cost_record_defaults(self):
        cr = CostRecord(cost_id="C-1", commitment_id="CMT-1",
                        category="time", amount=1.5)
        assert cr.handler_id is None

    def test_decision_debt_defaults(self):
        d = DecisionDebt(debt_id="D-1", commitment_id="CMT-1",
                         debt_type="rework")
        assert d.resolved is False
        assert d.estimated_cost == 0.0


# ── Registry Tests ───────────────────────────────────────────────


class TestAccountingRegistry:
    def test_add_and_get_costs(self):
        reg = AccountingRegistry()
        cost = CostRecord(cost_id="C-1", commitment_id="CMT-1",
                          category="time", amount=2.0)
        reg.add_cost(cost)
        costs = reg.get_costs("CMT-1")
        assert len(costs) == 1
        assert reg.total_cost("CMT-1") == 2.0

    def test_total_cost_empty(self):
        reg = AccountingRegistry()
        assert reg.total_cost("nonexistent") == 0.0

    def test_budget_lifecycle(self):
        reg = AccountingRegistry()
        budget = CostBudget(budget_id="B-1", commitment_id="CMT-1",
                            max_amount=10.0)
        reg.set_budget(budget)
        assert reg.get_budget("CMT-1") is budget
        assert reg.get_budget("CMT-X") is None

    def test_assessment_lifecycle(self):
        reg = AccountingRegistry()
        va = ValueAssessment(assessment_id="VA-1", commitment_id="CMT-1",
                             outcome_quality=0.8, composite_value=0.7)
        reg.set_assessment(va)
        assert reg.get_assessment("CMT-1") is va

    def test_debt_lifecycle(self):
        reg = AccountingRegistry()
        d = DecisionDebt(debt_id="D-1", commitment_id="CMT-1",
                         debt_type="rework", estimated_cost=3.0)
        reg.add_debt(d)
        assert len(reg.get_debts("CMT-1")) == 1
        assert reg.outstanding_debt("CMT-1") == 3.0

    def test_outstanding_debt_resolved(self):
        reg = AccountingRegistry()
        d = DecisionDebt(debt_id="D-1", commitment_id="CMT-1",
                         debt_type="rework", estimated_cost=3.0, resolved=True)
        reg.add_debt(d)
        assert reg.outstanding_debt("CMT-1") == 0.0


# ── Cost Tracking Tests ─────────────────────────────────────────


class TestCostTracking:
    def test_record_handler_cost(self):
        reg = AccountingRegistry()
        cost = record_handler_cost(reg, "CMT-1", "compute", 5.0, "ACTION-F01")
        assert cost.amount == 5.0
        assert cost.handler_id == "ACTION-F01"
        assert reg.total_cost("CMT-1") == 5.0

    def test_compute_budget_status_no_budget(self):
        reg = AccountingRegistry()
        record_handler_cost(reg, "CMT-1", "time", 2.0)
        status = compute_budget_status(reg, "CMT-1")
        assert status["budget_set"] is False
        assert status["total_cost"] == 2.0

    def test_compute_budget_status_with_budget(self):
        reg = AccountingRegistry()
        reg.set_budget(CostBudget(budget_id="B-1", commitment_id="CMT-1",
                                  max_amount=10.0))
        record_handler_cost(reg, "CMT-1", "time", 7.0)
        status = compute_budget_status(reg, "CMT-1")
        assert status["budget_set"] is True
        assert status["utilization"] == pytest.approx(0.7, abs=0.01)
        assert status["overrun"] is False

    def test_detect_overrun(self):
        reg = AccountingRegistry()
        reg.set_budget(CostBudget(budget_id="B-1", commitment_id="CMT-1",
                                  max_amount=5.0))
        record_handler_cost(reg, "CMT-1", "time", 6.0)
        assert detect_overrun(reg, "CMT-1") is True

    def test_detect_overrun_no_budget(self):
        reg = AccountingRegistry()
        assert detect_overrun(reg, "CMT-1") is False


# ── Value Scoring Tests ──────────────────────────────────────────


class TestValueScoring:
    def test_compute_outcome_quality(self):
        assert compute_outcome_quality(["delivered", "delivered", "failed"]) == pytest.approx(2 / 3, abs=0.01)
        assert compute_outcome_quality([]) == 0.0

    def test_compute_composite_value(self):
        val = compute_composite_value(0.8, 0.6)
        # 0.6*0.8 + 0.4*0.6 = 0.48 + 0.24 = 0.72
        assert val == pytest.approx(0.72, abs=0.01)

    def test_compute_roi(self):
        reg = AccountingRegistry()
        record_handler_cost(reg, "CMT-1", "time", 10.0)
        va = ValueAssessment(assessment_id="VA-1", commitment_id="CMT-1",
                             composite_value=15.0)
        reg.set_assessment(va)
        report = compute_roi(reg, "CMT-1")
        # ROI = (15 - 10) / 10 = 0.5
        assert report.roi == pytest.approx(0.5, abs=0.01)
        assert report.scope == "commitment"

    def test_compute_roi_zero_cost(self):
        reg = AccountingRegistry()
        report = compute_roi(reg, "CMT-X")
        assert report.roi == 0.0


# ── Debt Engine Tests ────────────────────────────────────────────


class TestDebtEngine:
    def test_detect_debt_rework(self):
        debts = detect_debt("CMT-1", ["delivered"], rework_count=2)
        rework = [d for d in debts if d.debt_type == "rework"]
        assert len(rework) == 1
        assert rework[0].estimated_cost == 2.0

    def test_detect_debt_scope_reduction(self):
        debts = detect_debt("CMT-1", ["delivered", "failed", "failed"])
        scope = [d for d in debts if d.debt_type == "scope_reduction"]
        assert len(scope) == 1
        assert scope[0].estimated_cost == 4.0  # 2 * 2.0

    def test_detect_debt_quality_shortfall(self):
        debts = detect_debt("CMT-1", ["delivered", "pending", "pending", "pending"],
                            risk_score=0.7)
        quality = [d for d in debts if d.debt_type == "quality_shortfall"]
        assert len(quality) == 1

    def test_detect_debt_no_issues(self):
        debts = detect_debt("CMT-1", ["delivered", "delivered"])
        assert len(debts) == 0

    def test_estimate_debt_cost(self):
        debts = [
            DecisionDebt(debt_id="D-1", commitment_id="C",
                         debt_type="rework", estimated_cost=3.0),
            DecisionDebt(debt_id="D-2", commitment_id="C",
                         debt_type="scope_reduction", estimated_cost=2.0,
                         resolved=True),
        ]
        assert estimate_debt_cost(debts) == 3.0


# ── Validator Tests ──────────────────────────────────────────────


class TestValidators:
    def test_validate_cost_record_valid(self):
        errors = validate_cost_record({
            "commitmentId": "CMT-1",
            "category": "time",
            "amount": 5.0,
        })
        assert errors == []

    def test_validate_cost_record_missing_commitment(self):
        errors = validate_cost_record({"category": "time", "amount": 1.0})
        assert any("commitmentId" in e for e in errors)

    def test_validate_cost_record_invalid_category(self):
        errors = validate_cost_record({
            "commitmentId": "CMT-1",
            "category": "invalid",
            "amount": 1.0,
        })
        assert any("category" in e for e in errors)

    def test_validate_value_assessment_valid(self):
        errors = validate_value_assessment({
            "commitmentId": "CMT-1",
            "outcomeQuality": 0.8,
        })
        assert errors == []


# ── Handler Tests (ACTION-F13 through ACTION-F19) ────────────────


class TestActionOpsDecisionAccounting:
    """Test the ACTION-F13→F19 handlers via ActionOps mode."""

    def _make_mode(self):
        from core.modes.actionops import ActionOps
        return ActionOps()

    def _ctx(self, **extras):
        from core.memory_graph import MemoryGraph
        from core.action_ops import CommitmentRegistry, Commitment, Deliverable
        reg = CommitmentRegistry()
        # Pre-populate a test commitment
        reg.add(Commitment(
            commitment_id="CMT-TEST",
            commitment_type="delivery",
            text="Test commitment",
            domain="test",
            owner="tester",
            lifecycle_state="active",
            deliverables=[
                Deliverable(deliverable_id="DLV-1", description="Item 1", status="delivered"),
                Deliverable(deliverable_id="DLV-2", description="Item 2", status="failed"),
            ],
            risk_score=0.6,
            created_at=datetime.now(timezone.utc).isoformat(),
        ))
        ctx = {
            "memory_graph": MemoryGraph(),
            "commitment_registry": reg,
            "accounting_registry": AccountingRegistry(),
            "now": datetime.now(timezone.utc),
        }
        ctx.update(extras)
        return ctx

    def test_action_f13_cost_record(self):
        mode = self._make_mode()
        ctx = self._ctx()
        result = mode.handle("ACTION-F13", {
            "payload": {
                "commitmentId": "CMT-TEST",
                "category": "time",
                "amount": 3.5,
            }
        }, ctx)
        assert result.success
        assert len(result.mg_updates) == 1
        ev = result.events_emitted[0]
        assert ev["subtype"] == "cost_recorded"
        assert ev["amount"] == 3.5

    def test_action_f13_validation_error(self):
        mode = self._make_mode()
        ctx = self._ctx()
        result = mode.handle("ACTION-F13", {
            "payload": {"category": "time", "amount": -1}
        }, ctx)
        assert not result.success

    def test_action_f14_time_to_decision(self):
        mode = self._make_mode()
        ctx = self._ctx()
        result = mode.handle("ACTION-F14", {
            "payload": {
                "commitmentId": "CMT-TEST",
                "episodeId": "EP-001",
                "elapsedMs": 1500.0,
                "handlerChainMs": {"ACTION-F01": 200, "ACTION-F02": 150},
            }
        }, ctx)
        assert result.success
        ev = result.events_emitted[0]
        assert ev["subtype"] == "time_to_decision_measured"

    def test_action_f15_value_assess(self):
        mode = self._make_mode()
        ctx = self._ctx()
        result = mode.handle("ACTION-F15", {
            "payload": {"commitmentId": "CMT-TEST"}
        }, ctx)
        assert result.success
        assert len(result.mg_updates) == 1
        ev = result.events_emitted[0]
        assert ev["subtype"] == "value_assessed"
        assert ev["outcomeQuality"] == 0.5  # 1 delivered / 2 total

    def test_action_f15_commitment_not_found(self):
        mode = self._make_mode()
        ctx = self._ctx()
        result = mode.handle("ACTION-F15", {
            "payload": {"commitmentId": "CMT-NOPE"}
        }, ctx)
        assert not result.success

    def test_action_f16_debt_detect(self):
        mode = self._make_mode()
        ctx = self._ctx()
        result = mode.handle("ACTION-F16", {
            "payload": {
                "commitmentId": "CMT-TEST",
                "reworkCount": 2,
            }
        }, ctx)
        assert result.success
        ev = result.events_emitted[0]
        assert ev["subtype"] == "decision_debt_detected"
        assert ev["debtCount"] >= 1

    def test_action_f17_roi_compute(self):
        mode = self._make_mode()
        ctx = self._ctx()
        # Record some costs and value first
        acct = ctx["accounting_registry"]
        record_handler_cost(acct, "CMT-TEST", "time", 10.0)
        acct.set_assessment(ValueAssessment(
            assessment_id="VA-1", commitment_id="CMT-TEST",
            composite_value=15.0,
        ))
        result = mode.handle("ACTION-F17", {
            "payload": {"commitmentId": "CMT-TEST"}
        }, ctx)
        assert result.success
        ev = result.events_emitted[0]
        assert ev["subtype"] == "roi_computed"
        assert ev["roi"] == pytest.approx(0.5, abs=0.01)

    def test_action_f18_budget_enforce_no_overrun(self):
        mode = self._make_mode()
        ctx = self._ctx()
        result = mode.handle("ACTION-F18", {
            "payload": {
                "commitmentId": "CMT-TEST",
                "maxAmount": 100.0,
            }
        }, ctx)
        assert result.success
        ev = result.events_emitted[0]
        assert ev["subtype"] == "budget_checked"
        assert ev["overrun"] is False

    def test_action_f18_budget_overrun(self):
        mode = self._make_mode()
        ctx = self._ctx()
        # Record costs that exceed budget
        acct = ctx["accounting_registry"]
        record_handler_cost(acct, "CMT-TEST", "time", 15.0)
        result = mode.handle("ACTION-F18", {
            "payload": {
                "commitmentId": "CMT-TEST",
                "maxAmount": 10.0,
            }
        }, ctx)
        assert result.success
        assert len(result.drift_signals) == 1
        assert result.drift_signals[0]["driftType"] == "budget_overrun"

    def test_action_f19_accounting_report(self):
        mode = self._make_mode()
        ctx = self._ctx()
        acct = ctx["accounting_registry"]
        record_handler_cost(acct, "CMT-TEST", "time", 5.0)
        record_handler_cost(acct, "CMT-TEST", "rework", 3.0)
        acct.set_assessment(ValueAssessment(
            assessment_id="VA-1", commitment_id="CMT-TEST",
            outcome_quality=0.8, composite_value=12.0,
        ))
        result = mode.handle("ACTION-F19", {
            "payload": {"commitmentId": "CMT-TEST"}
        }, ctx)
        assert result.success
        ev = result.events_emitted[0]
        assert ev["subtype"] == "accounting_report_generated"
        report = ev["report"]
        assert report["totalCost"] == 8.0
        assert "time" in report["costBreakdown"]
        assert "rework" in report["costBreakdown"]

    def test_all_handlers_registered(self):
        mode = self._make_mode()
        for fid in [f"ACTION-F{i}" for i in range(13, 20)]:
            assert mode.has_handler(fid), f"Handler {fid} not registered"
