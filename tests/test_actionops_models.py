"""Tests for action_ops models, enums, registry, lifecycle, validators, tracking, compliance."""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC_ROOT = _REPO_ROOT / "src"
if str(_SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(_SRC_ROOT))

from core.action_ops.models import (
    BreachSeverity,
    Commitment,
    CommitmentState,
    CommitmentType,
    ComplianceCheck,
    Deliverable,
    DeliverableStatus,
    RemediationRecord,
)
from core.action_ops.registry import CommitmentRegistry
from core.action_ops.lifecycle import CommitmentLifecycle
from core.action_ops.validators import (
    validate_commitment,
    validate_compliance_check,
    validate_deliverable_update,
)
from core.action_ops.tracking import (
    check_deadline_proximity,
    compute_risk_score,
    evaluate_deliverables,
)
from core.action_ops.compliance import assess_breach_severity, run_compliance_check


# ── Enum Tests ────────────────────────────────────────────────────


class TestEnums:
    def test_commitment_state_values(self):
        assert len(CommitmentState) == 8
        assert CommitmentState.PROPOSED == "proposed"
        assert CommitmentState.ARCHIVED == "archived"

    def test_commitment_type_values(self):
        assert len(CommitmentType) == 4
        assert CommitmentType.DELIVERY == "delivery"
        assert CommitmentType.SLA == "sla"

    def test_deliverable_status_values(self):
        assert len(DeliverableStatus) == 4
        assert DeliverableStatus.PENDING == "pending"
        assert DeliverableStatus.DELIVERED == "delivered"

    def test_breach_severity_values(self):
        assert len(BreachSeverity) == 3
        assert BreachSeverity.GREEN == "green"
        assert BreachSeverity.RED == "red"


# ── Model Construction ────────────────────────────────────────────


class TestModels:
    def test_deliverable_defaults(self):
        d = Deliverable(deliverable_id="D1", description="Test")
        assert d.status == "pending"
        assert d.due_date is None
        assert d.completed_at is None

    def test_commitment_defaults(self):
        c = Commitment(
            commitment_id="CMT-001",
            commitment_type="delivery",
            text="Deliver X",
            domain="actionops",
            owner="alice",
        )
        assert c.lifecycle_state == "proposed"
        assert c.risk_score == 0.0
        assert c.deliverables == []
        assert c.claim_refs == []

    def test_compliance_check(self):
        cc = ComplianceCheck(
            check_id="CHK-001",
            commitment_id="CMT-001",
            check_type="deadline",
            passed=False,
            details="Missed",
        )
        assert not cc.passed
        assert cc.check_type == "deadline"

    def test_remediation_record(self):
        rr = RemediationRecord(
            remediation_id="REM-001",
            commitment_id="CMT-001",
            action="adjust_deadline",
            rationale="Extension needed",
        )
        assert rr.action == "adjust_deadline"


# ── Registry Tests ────────────────────────────────────────────────


class TestCommitmentRegistry:
    def _make_commitment(self, cid="CMT-001", state="active", domain="actionops"):
        return Commitment(
            commitment_id=cid,
            commitment_type="delivery",
            text="Test",
            domain=domain,
            owner="alice",
            lifecycle_state=state,
        )

    def test_add_and_get(self):
        reg = CommitmentRegistry()
        c = self._make_commitment()
        reg.add(c)
        assert reg.get("CMT-001") is c

    def test_get_missing_returns_none(self):
        reg = CommitmentRegistry()
        assert reg.get("NOPE") is None

    def test_update(self):
        reg = CommitmentRegistry()
        c = self._make_commitment()
        reg.add(c)
        c.risk_score = 0.9
        reg.update(c)
        assert reg.get("CMT-001").risk_score == 0.9

    def test_remove(self):
        reg = CommitmentRegistry()
        reg.add(self._make_commitment())
        assert reg.remove("CMT-001") is True
        assert reg.remove("CMT-001") is False
        assert reg.get("CMT-001") is None

    def test_list_active(self):
        reg = CommitmentRegistry()
        reg.add(self._make_commitment("A", "active"))
        reg.add(self._make_commitment("B", "archived"))
        active = reg.list_active()
        assert len(active) == 1
        assert active[0].commitment_id == "A"

    def test_list_by_state(self):
        reg = CommitmentRegistry()
        reg.add(self._make_commitment("A", "active"))
        reg.add(self._make_commitment("B", "breached"))
        reg.add(self._make_commitment("C", "active"))
        assert len(reg.list_by_state("active")) == 2
        assert len(reg.list_by_state("breached")) == 1

    def test_list_by_domain(self):
        reg = CommitmentRegistry()
        reg.add(self._make_commitment("A", domain="infra"))
        reg.add(self._make_commitment("B", domain="actionops"))
        assert len(reg.list_by_domain("infra")) == 1


# ── Lifecycle Tests ───────────────────────────────────────────────


class TestCommitmentLifecycle:
    def test_set_and_get_state(self):
        lc = CommitmentLifecycle()
        lc.set_state("C1", CommitmentState.PROPOSED)
        assert lc.get_state("C1") is CommitmentState.PROPOSED

    def test_get_unknown_returns_none(self):
        lc = CommitmentLifecycle()
        assert lc.get_state("NOPE") is None

    def test_valid_transition(self):
        lc = CommitmentLifecycle()
        lc.set_state("C1", CommitmentState.PROPOSED)
        assert lc.transition("C1", CommitmentState.ACTIVE) is True
        assert lc.get_state("C1") is CommitmentState.ACTIVE

    def test_invalid_transition(self):
        lc = CommitmentLifecycle()
        lc.set_state("C1", CommitmentState.PROPOSED)
        assert lc.transition("C1", CommitmentState.BREACHED) is False
        assert lc.get_state("C1") is CommitmentState.PROPOSED

    def test_terminal_state(self):
        lc = CommitmentLifecycle()
        lc.set_state("C1", CommitmentState.ARCHIVED)
        assert lc.is_terminal("C1") is True
        assert lc.valid_transitions("C1") == set()

    def test_full_happy_path(self):
        lc = CommitmentLifecycle()
        lc.set_state("C1", CommitmentState.PROPOSED)
        assert lc.transition("C1", CommitmentState.ACTIVE)
        assert lc.transition("C1", CommitmentState.COMPLETED)
        assert lc.transition("C1", CommitmentState.ARCHIVED)
        assert lc.is_terminal("C1")

    def test_breach_escalation_path(self):
        lc = CommitmentLifecycle()
        lc.set_state("C1", CommitmentState.PROPOSED)
        assert lc.transition("C1", CommitmentState.ACTIVE)
        assert lc.transition("C1", CommitmentState.AT_RISK)
        assert lc.transition("C1", CommitmentState.BREACHED)
        assert lc.transition("C1", CommitmentState.ESCALATED)
        assert lc.transition("C1", CommitmentState.REMEDIATED)
        assert lc.transition("C1", CommitmentState.ACTIVE)

    def test_at_risk_recovery(self):
        lc = CommitmentLifecycle()
        lc.set_state("C1", CommitmentState.AT_RISK)
        assert lc.transition("C1", CommitmentState.ACTIVE) is True


# ── Validator Tests ───────────────────────────────────────────────


class TestValidators:
    def test_valid_commitment(self):
        errors = validate_commitment({
            "text": "Deliver X",
            "domain": "actionops",
            "owner": "alice",
        })
        assert errors == []

    def test_missing_required_fields(self):
        errors = validate_commitment({})
        assert len(errors) == 3  # text, domain, owner

    def test_invalid_commitment_type(self):
        errors = validate_commitment({
            "text": "T", "domain": "d", "owner": "o",
            "commitmentType": "bogus",
        })
        assert any("Unknown commitment type" in e for e in errors)

    def test_invalid_risk_score(self):
        errors = validate_commitment({
            "text": "T", "domain": "d", "owner": "o",
            "riskScore": 1.5,
        })
        assert any("Risk score" in e for e in errors)

    def test_valid_deliverable_update(self):
        errors = validate_deliverable_update({
            "commitmentId": "CMT-001",
            "deliverableId": "D1",
            "status": "delivered",
        })
        assert errors == []

    def test_invalid_deliverable_status(self):
        errors = validate_deliverable_update({
            "commitmentId": "CMT-001",
            "deliverableId": "D1",
            "status": "bogus",
        })
        assert any("Unknown deliverable status" in e for e in errors)

    def test_valid_compliance_check(self):
        errors = validate_compliance_check({
            "commitmentId": "CMT-001",
            "checkType": "deadline",
        })
        assert errors == []

    def test_invalid_check_type(self):
        errors = validate_compliance_check({
            "commitmentId": "CMT-001",
            "checkType": "bogus",
        })
        assert any("Unknown check type" in e for e in errors)


# ── Tracking Tests ────────────────────────────────────────────────


class TestTracking:
    def test_deadline_proximity_no_deadline(self):
        c = Commitment(
            commitment_id="C1", commitment_type="delivery",
            text="T", domain="d", owner="o",
        )
        result = check_deadline_proximity(c)
        assert result["at_risk"] is False

    def test_deadline_proximity_past_due(self):
        c = Commitment(
            commitment_id="C1", commitment_type="delivery",
            text="T", domain="d", owner="o",
            deadline="2026-01-01T00:00:00Z",
            created_at="2025-12-01T00:00:00Z",
        )
        now = datetime(2026, 1, 2, tzinfo=timezone.utc)
        result = check_deadline_proximity(c, now)
        assert result["at_risk"] is True
        assert result["proximity"] == 1.0

    def test_evaluate_deliverables_all_delivered(self):
        c = Commitment(
            commitment_id="C1", commitment_type="delivery",
            text="T", domain="d", owner="o",
            deliverables=[
                Deliverable(deliverable_id="D1", description="A", status="delivered"),
                Deliverable(deliverable_id="D2", description="B", status="delivered"),
            ],
        )
        result = evaluate_deliverables(c)
        assert result["compliant"] is True
        assert result["delivered"] == 2
        assert result["failed"] == 0

    def test_evaluate_deliverables_with_failure(self):
        c = Commitment(
            commitment_id="C1", commitment_type="delivery",
            text="T", domain="d", owner="o",
            deliverables=[
                Deliverable(deliverable_id="D1", description="A", status="delivered"),
                Deliverable(deliverable_id="D2", description="B", status="failed"),
            ],
        )
        result = evaluate_deliverables(c)
        assert result["compliant"] is False
        assert result["failed"] == 1

    def test_compute_risk_score_zero(self):
        c = Commitment(
            commitment_id="C1", commitment_type="delivery",
            text="T", domain="d", owner="o",
        )
        score = compute_risk_score(c, [])
        assert score == 0.0

    def test_compute_risk_score_high(self):
        c = Commitment(
            commitment_id="C1", commitment_type="delivery",
            text="T", domain="d", owner="o",
            deadline="2026-01-01T00:00:00Z",
            created_at="2025-12-01T00:00:00Z",
            deliverables=[
                Deliverable(deliverable_id="D1", description="A", status="failed"),
            ],
        )
        now = datetime(2026, 1, 2, tzinfo=timezone.utc)
        checks = [
            ComplianceCheck(check_id="CHK1", commitment_id="C1", check_type="deadline", passed=False),
        ]
        score = compute_risk_score(c, checks, now)
        assert score > 0.5


# ── Compliance Tests ──────────────────────────────────────────────


class TestCompliance:
    def test_run_compliance_check_passed(self):
        c = Commitment(
            commitment_id="C1", commitment_type="delivery",
            text="T", domain="d", owner="o",
        )
        result = run_compliance_check(c, {})
        assert result.passed is True

    def test_run_compliance_check_deadline_missed(self):
        c = Commitment(
            commitment_id="C1", commitment_type="delivery",
            text="T", domain="d", owner="o",
            deadline="2026-01-01T00:00:00Z",
        )
        now = datetime(2026, 1, 2, tzinfo=timezone.utc)
        result = run_compliance_check(c, {"status": "not_delivered"}, now)
        assert result.passed is False
        assert "missed" in result.details.lower()

    def test_assess_breach_severity_green(self):
        c = Commitment(
            commitment_id="C1", commitment_type="delivery",
            text="T", domain="d", owner="o",
            risk_score=0.1,
        )
        assert assess_breach_severity(c) == "green"

    def test_assess_breach_severity_red(self):
        c = Commitment(
            commitment_id="C1", commitment_type="delivery",
            text="T", domain="d", owner="o",
            risk_score=0.9,
        )
        assert assess_breach_severity(c) == "red"
