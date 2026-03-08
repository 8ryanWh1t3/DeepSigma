"""Tests for ActionOps domain mode — 19 function handlers."""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC_ROOT = _REPO_ROOT / "src"
if str(_SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(_SRC_ROOT))

from core.action_ops import (
    Commitment,
    CommitmentLifecycle,
    CommitmentRegistry,
    CommitmentState,
    Deliverable,
)
from core.modes.actionops import ActionOps


# ── Helpers ───────────────────────────────────────────────────────


def _make_ctx(commitment=None, state="proposed"):
    reg = CommitmentRegistry()
    lc = CommitmentLifecycle()
    if commitment is not None:
        reg.add(commitment)
        lc.set_state(commitment.commitment_id, CommitmentState(state))
    return {
        "commitment_registry": reg,
        "commitment_lifecycle": lc,
        "memory_graph": None,
        "now": datetime(2026, 3, 1, tzinfo=timezone.utc),
    }


def _base_commitment(cid="CMT-001", state="active", **kwargs):
    defaults = dict(
        commitment_id=cid,
        commitment_type="delivery",
        text="Deliver artifact X by deadline",
        domain="actionops",
        owner="alice",
        lifecycle_state=state,
        deadline="2026-03-15T00:00:00Z",
        created_at="2026-02-01T00:00:00Z",
        claim_refs=["CLAIM-001"],
    )
    defaults.update(kwargs)
    return Commitment(**defaults)


# ── ACTION-F01: Commitment Intake ─────────────────────────────────


class TestActionF01:
    def test_valid_intake(self):
        mode = ActionOps()
        ctx = _make_ctx()
        event = {"payload": {
            "commitmentId": "CMT-001",
            "text": "Deliver X",
            "domain": "actionops",
            "owner": "alice",
            "commitmentType": "delivery",
            "deadline": "2026-03-15T00:00:00Z",
            "claimRefs": ["CLAIM-001"],
            "deliverables": [
                {"deliverableId": "D1", "description": "Artifact X"},
            ],
        }}
        r = mode.handle("ACTION-F01", event, ctx)
        assert r.success
        assert ctx["commitment_registry"].get("CMT-001") is not None
        assert ctx["commitment_lifecycle"].get_state("CMT-001") is CommitmentState.PROPOSED

    def test_missing_required_fields(self):
        mode = ActionOps()
        ctx = _make_ctx()
        r = mode.handle("ACTION-F01", {"payload": {}}, ctx)
        assert not r.success
        assert "required" in r.error.lower()

    def test_events_emitted(self):
        mode = ActionOps()
        ctx = _make_ctx()
        event = {"payload": {
            "text": "T", "domain": "d", "owner": "o",
        }}
        r = mode.handle("ACTION-F01", event, ctx)
        assert r.success
        assert any(e["subtype"] == "commitment_registered" for e in r.events_emitted)


# ── ACTION-F02: Commitment Validate ───────────────────────────────


class TestActionF02:
    def test_valid_activation(self):
        mode = ActionOps()
        c = _base_commitment(state="proposed")
        ctx = _make_ctx(c, "proposed")
        r = mode.handle("ACTION-F02", {"payload": {"commitmentId": "CMT-001"}}, ctx)
        assert r.success
        assert ctx["commitment_registry"].get("CMT-001").lifecycle_state == "active"

    def test_invalid_assumptions(self):
        mode = ActionOps()
        c = _base_commitment(state="proposed")
        ctx = _make_ctx(c, "proposed")
        r = mode.handle("ACTION-F02", {"payload": {
            "commitmentId": "CMT-001",
            "assumptions": [{"name": "resources", "valid": False}],
        }}, ctx)
        assert not r.success
        assert "Invalid assumptions" in r.error

    def test_not_found(self):
        mode = ActionOps()
        ctx = _make_ctx()
        r = mode.handle("ACTION-F02", {"payload": {"commitmentId": "NOPE"}}, ctx)
        assert not r.success


# ── ACTION-F03: Deliverable Track ─────────────────────────────────


class TestActionF03:
    def test_update_deliverable_status(self):
        mode = ActionOps()
        c = _base_commitment(deliverables=[
            Deliverable(deliverable_id="D1", description="Artifact"),
        ])
        ctx = _make_ctx(c, "active")
        r = mode.handle("ACTION-F03", {"payload": {
            "commitmentId": "CMT-001",
            "deliverableId": "D1",
            "status": "delivered",
        }}, ctx)
        assert r.success
        d = ctx["commitment_registry"].get("CMT-001").deliverables[0]
        assert d.status == "delivered"
        assert d.completed_at is not None

    def test_deliverable_not_found(self):
        mode = ActionOps()
        c = _base_commitment()
        ctx = _make_ctx(c, "active")
        r = mode.handle("ACTION-F03", {"payload": {
            "commitmentId": "CMT-001",
            "deliverableId": "NOPE",
        }}, ctx)
        assert not r.success


# ── ACTION-F04: Deadline Check ────────────────────────────────────


class TestActionF04:
    def test_not_at_risk(self):
        mode = ActionOps()
        c = _base_commitment()
        ctx = _make_ctx(c, "active")
        r = mode.handle("ACTION-F04", {"payload": {"commitmentId": "CMT-001"}}, ctx)
        assert r.success
        # March 1 is before March 15 deadline, not yet at risk
        assert len(r.drift_signals) == 0

    def test_at_risk_near_deadline(self):
        mode = ActionOps()
        c = _base_commitment()
        ctx = _make_ctx(c, "active")
        ctx["now"] = datetime(2026, 3, 14, tzinfo=timezone.utc)  # 1 day before
        r = mode.handle("ACTION-F04", {"payload": {"commitmentId": "CMT-001"}}, ctx)
        assert r.success
        assert len(r.drift_signals) == 1
        assert r.drift_signals[0]["severity"] == "yellow"


# ── ACTION-F05: Compliance Evaluate ───────────────────────────────


class TestActionF05:
    def test_compliance_check_passes(self):
        mode = ActionOps()
        c = _base_commitment()
        ctx = _make_ctx(c, "active")
        r = mode.handle("ACTION-F05", {"payload": {
            "commitmentId": "CMT-001",
            "observedState": {},
        }}, ctx)
        assert r.success
        assert any(e["subtype"] == "compliance_checked" for e in r.events_emitted)


# ── ACTION-F06: Risk Assess ──────────────────────────────────────


class TestActionF06:
    def test_risk_assessment(self):
        mode = ActionOps()
        c = _base_commitment()
        ctx = _make_ctx(c, "active")
        r = mode.handle("ACTION-F06", {"payload": {
            "commitmentId": "CMT-001",
            "checks": [],
        }}, ctx)
        assert r.success
        updated = ctx["commitment_registry"].get("CMT-001")
        assert isinstance(updated.risk_score, float)


# ── ACTION-F07: Breach Detect ─────────────────────────────────────


class TestActionF07:
    def test_no_breach(self):
        mode = ActionOps()
        c = _base_commitment()
        ctx = _make_ctx(c, "active")
        r = mode.handle("ACTION-F07", {"payload": {"commitmentId": "CMT-001"}}, ctx)
        assert r.success
        assert len(r.drift_signals) == 0

    def test_breach_detected(self):
        mode = ActionOps()
        c = _base_commitment(
            risk_score=0.9,
            deliverables=[
                Deliverable(deliverable_id="D1", description="A", status="failed"),
            ],
        )
        ctx = _make_ctx(c, "at_risk")
        r = mode.handle("ACTION-F07", {"payload": {"commitmentId": "CMT-001"}}, ctx)
        assert r.success
        assert len(r.drift_signals) == 1
        assert r.drift_signals[0]["severity"] == "red"
        assert ctx["commitment_registry"].get("CMT-001").lifecycle_state == "breached"


# ── ACTION-F08: Escalation Trigger ────────────────────────────────


class TestActionF08:
    def test_escalation(self):
        mode = ActionOps()
        c = _base_commitment(state="breached")
        ctx = _make_ctx(c, "breached")
        r = mode.handle("ACTION-F08", {"payload": {"commitmentId": "CMT-001"}}, ctx)
        assert r.success
        assert ctx["commitment_registry"].get("CMT-001").lifecycle_state == "escalated"
        assert any(e["subtype"] == "commitment_escalated" for e in r.events_emitted)

    def test_cannot_escalate_non_breached(self):
        mode = ActionOps()
        c = _base_commitment(state="active")
        ctx = _make_ctx(c, "active")
        r = mode.handle("ACTION-F08", {"payload": {"commitmentId": "CMT-001"}}, ctx)
        assert not r.success


# ── ACTION-F09: Remediation Recommend ─────────────────────────────


class TestActionF09:
    def test_recommendations_generated(self):
        mode = ActionOps()
        c = _base_commitment(state="breached", risk_score=0.9)
        ctx = _make_ctx(c, "breached")
        r = mode.handle("ACTION-F09", {"payload": {"commitmentId": "CMT-001"}}, ctx)
        assert r.success
        recs = r.events_emitted[0].get("recommendations", [])
        assert len(recs) >= 1


# ── ACTION-F10: Commitment Adjust ─────────────────────────────────


class TestActionF10:
    def test_adjust_deadline(self):
        mode = ActionOps()
        c = _base_commitment(state="at_risk")
        ctx = _make_ctx(c, "at_risk")
        r = mode.handle("ACTION-F10", {"payload": {
            "commitmentId": "CMT-001",
            "deadline": "2026-04-01T00:00:00Z",
        }}, ctx)
        assert r.success
        updated = ctx["commitment_registry"].get("CMT-001")
        assert updated.deadline == "2026-04-01T00:00:00Z"
        assert updated.lifecycle_state == "active"  # recovered from at_risk
        assert updated.risk_score == 0.0


# ── ACTION-F11: Commitment Complete ───────────────────────────────


class TestActionF11:
    def test_complete(self):
        mode = ActionOps()
        c = _base_commitment(state="active")
        ctx = _make_ctx(c, "active")
        r = mode.handle("ACTION-F11", {"payload": {"commitmentId": "CMT-001"}}, ctx)
        assert r.success
        updated = ctx["commitment_registry"].get("CMT-001")
        assert updated.lifecycle_state == "completed"
        assert updated.completed_at is not None
        assert any(e["subtype"] == "commitment_completed" for e in r.events_emitted)

    def test_cannot_complete_from_breached(self):
        mode = ActionOps()
        c = _base_commitment(state="breached")
        ctx = _make_ctx(c, "breached")
        r = mode.handle("ACTION-F11", {"payload": {"commitmentId": "CMT-001"}}, ctx)
        assert not r.success


# ── ACTION-F12: Commitment Report ─────────────────────────────────


class TestActionF12:
    def test_report_generated(self):
        mode = ActionOps()
        c = _base_commitment(state="completed")
        ctx = _make_ctx(c, "completed")
        r = mode.handle("ACTION-F12", {"payload": {"commitmentId": "CMT-001"}}, ctx)
        assert r.success
        report = r.events_emitted[0].get("report", {})
        assert report["commitmentId"] == "CMT-001"
        assert report["state"] == "completed"
        assert "deliverables" in report


# ── Full Lifecycle ────────────────────────────────────────────────


class TestFullLifecycle:
    def test_happy_path(self):
        mode = ActionOps()
        ctx = _make_ctx()

        # F01: Intake
        r = mode.handle("ACTION-F01", {"payload": {
            "commitmentId": "CMT-001",
            "text": "Deliver X",
            "domain": "actionops",
            "owner": "alice",
            "commitmentType": "delivery",
            "deadline": "2026-03-15T00:00:00Z",
            "deliverables": [
                {"deliverableId": "D1", "description": "Artifact X"},
            ],
        }}, ctx)
        assert r.success

        # F02: Validate and activate
        r = mode.handle("ACTION-F02", {"payload": {"commitmentId": "CMT-001"}}, ctx)
        assert r.success
        assert ctx["commitment_registry"].get("CMT-001").lifecycle_state == "active"

        # F03: Track deliverable
        r = mode.handle("ACTION-F03", {"payload": {
            "commitmentId": "CMT-001",
            "deliverableId": "D1",
            "status": "delivered",
        }}, ctx)
        assert r.success

        # F11: Complete
        r = mode.handle("ACTION-F11", {"payload": {"commitmentId": "CMT-001"}}, ctx)
        assert r.success
        assert ctx["commitment_registry"].get("CMT-001").lifecycle_state == "completed"

    def test_breach_escalation_path(self):
        mode = ActionOps()
        ctx = _make_ctx()

        # F01: Intake
        r = mode.handle("ACTION-F01", {"payload": {
            "commitmentId": "CMT-002",
            "text": "Deliver Y",
            "domain": "actionops",
            "owner": "bob",
            "deliverables": [
                {"deliverableId": "D1", "description": "Component A"},
            ],
        }}, ctx)
        assert r.success

        # F02: Activate
        r = mode.handle("ACTION-F02", {"payload": {"commitmentId": "CMT-002"}}, ctx)
        assert r.success

        # F03: Mark deliverable as failed
        r = mode.handle("ACTION-F03", {"payload": {
            "commitmentId": "CMT-002",
            "deliverableId": "D1",
            "status": "failed",
        }}, ctx)
        assert r.success

        # Manually set risk high to trigger breach
        c = ctx["commitment_registry"].get("CMT-002")
        c.risk_score = 0.9
        ctx["commitment_lifecycle"].transition("CMT-002", CommitmentState.AT_RISK)
        c.lifecycle_state = "at_risk"
        ctx["commitment_registry"].update(c)

        # F07: Breach detect
        r = mode.handle("ACTION-F07", {"payload": {"commitmentId": "CMT-002"}}, ctx)
        assert r.success
        assert len(r.drift_signals) == 1
        assert ctx["commitment_registry"].get("CMT-002").lifecycle_state == "breached"

        # F08: Escalate
        r = mode.handle("ACTION-F08", {"payload": {"commitmentId": "CMT-002"}}, ctx)
        assert r.success
        assert ctx["commitment_registry"].get("CMT-002").lifecycle_state == "escalated"


# ── Handler Registration ─────────────────────────────────────────


class TestHandlerRegistration:
    def test_19_handlers_registered(self):
        mode = ActionOps()
        assert len(mode.function_ids) == 19

    def test_function_id_prefix(self):
        mode = ActionOps()
        for fid in mode.function_ids:
            assert fid.startswith("ACTION-F")

    def test_domain_name(self):
        assert ActionOps.domain == "actionops"

    def test_unknown_handler(self):
        mode = ActionOps()
        r = mode.handle("ACTION-F99", {}, {})
        assert not r.success
        assert "No handler" in r.error
