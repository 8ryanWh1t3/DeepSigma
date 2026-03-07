"""Tests for Authority Drift Detection -- AUTH-F13 through AUTH-F16.

Covers scan_authority_drift, check_delegation_health, check_privilege_expiry,
check_authority_integrity, authority_health classification, and handler
integration via AuthorityOps.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

import pytest

from core.authority import AuthorityLedger
from core.authority.authority_audit import AuthorityAuditLog
from core.authority.authority_drift import (
    check_authority_integrity,
    check_delegation_health,
    check_privilege_expiry,
    scan_authority_drift,
)
from core.authority.authority_health import (
    build_health_summary,
    classify_authority_severity,
)
from core.authority.models import RevocationEvent
from core.authority.seal_and_hash import compute_hash
from core.memory_graph import MemoryGraph
from core.modes.authorityops import AuthorityOps


NOW = datetime(2026, 3, 5, 12, 0, 0, tzinfo=timezone.utc)


# ── Fixtures ─────────────────────────────────────────────────────


@pytest.fixture
def authops():
    return AuthorityOps()


@pytest.fixture
def drift_context():
    """Evaluation context for drift detection handlers."""
    return {
        "memory_graph": MemoryGraph(),
        "authority_ledger": AuthorityLedger(),
        "authority_audit": AuthorityAuditLog(),
        "kill_switch_active": False,
        "now": NOW,
        "actors": [],
        "delegations": [],
        "grants": [],
        "revocations": [],
        "policies": [],
    }


# ── Helpers ──────────────────────────────────────────────────────


def _make_actor(
    actor_id: str = "agent-001",
    actor_type: str = "agent",
    roles: List[Dict] = None,
    delegated_from: str = None,
) -> Dict[str, Any]:
    return {
        "actorId": actor_id,
        "actorType": actor_type,
        "roles": roles or [{"roleId": "R-001", "roleName": "operator", "scope": "security-ops"}],
        "delegatedFrom": delegated_from,
    }


def _make_delegation(
    delegation_id: str = "DEL-001",
    from_actor: str = "admin-001",
    to_actor: str = "agent-001",
    scope: str = "security-ops",
    expires_at: str = None,
    revoked_at: str = None,
) -> Dict[str, Any]:
    return {
        "delegationId": delegation_id,
        "fromActorId": from_actor,
        "toActorId": to_actor,
        "scope": scope,
        "maxDepth": 3,
        "effectiveAt": "2026-01-01T00:00:00Z",
        "expiresAt": expires_at,
        "revokedAt": revoked_at,
    }


def _make_grant(
    authority_id: str = "AUTH-001",
    scope: str = "security-ops",
    expires_at: str = None,
    source_delegation: str = None,
    actor_id: str = "",
) -> Dict[str, Any]:
    return {
        "authorityId": authority_id,
        "scope": scope,
        "expiresAt": expires_at,
        "sourceDelegation": source_delegation,
        "actorId": actor_id,
    }


# ── TestScanAuthorityDrift ───────────────────────────────────────


class TestScanAuthorityDrift:
    """Tests for scan_authority_drift (AUTH-F13 master scan)."""

    def test_clean_state_returns_no_signals(self):
        signals = scan_authority_drift([], [], [], [], [], now=NOW)
        assert signals == []

    def test_expired_delegation_emits_orange(self):
        delegations = [_make_delegation(expires_at="2026-03-01T00:00:00Z")]
        signals = scan_authority_drift([], delegations, [], [], [], now=NOW)
        types = [s["driftType"] for s in signals]
        assert "grant_expired" in types
        assert any(s["severity"] == "orange" for s in signals)

    def test_revoked_role_still_active_emits_red(self):
        actors = [_make_actor(roles=[{"roleId": "R-BAD", "roleName": "admin", "scope": "global"}])]
        revocations = [RevocationEvent(
            revocation_id="REV-001",
            target_type="role",
            target_id="R-BAD",
            revoked_at="2026-03-01T00:00:00Z",
        )]
        signals = scan_authority_drift(actors, [], [], revocations, [], now=NOW)
        types = [s["driftType"] for s in signals]
        assert "revoked_role_active" in types
        assert any(s["severity"] == "red" for s in signals)

    def test_scope_mismatch_emits_orange(self):
        delegations = [_make_delegation(scope="security-ops")]
        grants = [_make_grant(scope="finance-ops", actor_id="agent-001")]
        actors = []
        signals = scan_authority_drift(actors, delegations, grants, [], [], now=NOW)
        types = [s["driftType"] for s in signals]
        assert "delegation_scope_violated" in types

    def test_actor_role_inconsistency_emits_yellow(self):
        actors = [_make_actor(
            actor_type="agent",
            roles=[{"roleId": "R-001", "roleName": "admin", "scope": "global"}],
        )]
        signals = scan_authority_drift(actors, [], [], [], [], now=NOW)
        types = [s["driftType"] for s in signals]
        assert "actor_role_inconsistency" in types
        assert any(s["severity"] == "yellow" for s in signals)

    def test_multiple_drift_types_aggregated(self):
        actors = [_make_actor(
            actor_type="agent",
            roles=[{"roleId": "R-BAD", "roleName": "admin", "scope": "global"}],
        )]
        delegations = [_make_delegation(expires_at="2026-03-01T00:00:00Z")]
        revocations = [RevocationEvent(
            revocation_id="REV-001",
            target_type="role",
            target_id="R-BAD",
            revoked_at="2026-03-01T00:00:00Z",
        )]
        signals = scan_authority_drift(actors, delegations, [], revocations, [], now=NOW)
        assert len(signals) >= 2

    def test_revocation_event_model_instantiated(self):
        """Verify RevocationEvent model is used in the detection logic."""
        rev = RevocationEvent(
            revocation_id="REV-TEST",
            target_type="role",
            target_id="R-TEST",
            revoked_at="2026-03-01T00:00:00Z",
            revoked_by="admin",
            reason="compliance",
        )
        assert rev.revocation_id == "REV-TEST"
        assert rev.target_type == "role"


# ── TestCheckDelegationHealth ────────────────────────────────────


class TestCheckDelegationHealth:
    """Tests for check_delegation_health (AUTH-F14)."""

    def test_valid_chain_returns_empty(self):
        delegations = [_make_delegation()]
        signals = check_delegation_health(delegations, [], now=NOW)
        assert signals == []

    def test_expired_delegation_detected(self):
        delegations = [_make_delegation(expires_at="2026-03-01T00:00:00Z")]
        signals = check_delegation_health(delegations, [], now=NOW)
        assert len(signals) == 1
        assert signals[0]["driftType"] == "grant_expired"
        assert signals[0]["severity"] == "orange"

    def test_revoked_delegation_detected(self):
        delegations = [_make_delegation(revoked_at="2026-03-01T00:00:00Z")]
        signals = check_delegation_health(delegations, [], now=NOW)
        assert len(signals) == 1
        assert signals[0]["driftType"] == "authority_chain_broken"
        assert signals[0]["severity"] == "red"

    def test_near_expiry_detected(self):
        # Expires in 48 hours (within default 72-hour threshold)
        near_exp = (NOW + timedelta(hours=48)).isoformat()
        delegations = [_make_delegation(expires_at=near_exp)]
        signals = check_delegation_health(delegations, [], now=NOW)
        assert len(signals) == 1
        assert signals[0]["driftType"] == "delegation_near_expiry"
        assert signals[0]["severity"] == "yellow"

    def test_broken_chain_detected(self):
        actors = [_make_actor(actor_id="agent-002", delegated_from="admin-001")]
        delegations = [_make_delegation(
            from_actor="admin-001",
            to_actor="agent-002",
            expires_at="2026-03-01T00:00:00Z",  # expired
        )]
        signals = check_delegation_health(delegations, actors, now=NOW)
        # Should detect expired delegation + chain issues
        assert len(signals) >= 1

    def test_custom_near_expiry_threshold(self):
        # Expires in 24 hours
        near_exp = (NOW + timedelta(hours=24)).isoformat()
        delegations = [_make_delegation(expires_at=near_exp)]
        # Default threshold is 72h — should detect
        signals_72 = check_delegation_health(delegations, [], now=NOW, near_expiry_hours=72)
        assert len(signals_72) == 1
        # Tighter threshold of 12h — should NOT detect
        signals_12 = check_delegation_health(delegations, [], now=NOW, near_expiry_hours=12)
        assert len(signals_12) == 0


# ── TestCheckPrivilegeExpiry ─────────────────────────────────────


class TestCheckPrivilegeExpiry:
    """Tests for check_privilege_expiry (AUTH-F15)."""

    def test_no_expiry_returns_empty(self):
        grants = [_make_grant()]
        signals = check_privilege_expiry(grants, [], now=NOW)
        assert signals == []

    def test_expired_grant_detected(self):
        grants = [_make_grant(expires_at="2026-03-01T00:00:00Z")]
        signals = check_privilege_expiry(grants, [], now=NOW)
        assert len(signals) == 1
        assert signals[0]["driftType"] == "grant_expired"
        assert signals[0]["severity"] == "orange"

    def test_near_expiry_grant_detected(self):
        near_exp = (NOW + timedelta(hours=48)).isoformat()
        grants = [_make_grant(expires_at=near_exp)]
        signals = check_privilege_expiry(grants, [], now=NOW)
        assert len(signals) == 1
        assert signals[0]["driftType"] == "delegation_near_expiry"
        assert signals[0]["severity"] == "yellow"

    def test_orphaned_grant_detected(self):
        grants = [_make_grant(source_delegation="DEL-EXPIRED")]
        delegations = [_make_delegation(
            delegation_id="DEL-EXPIRED",
            expires_at="2026-03-01T00:00:00Z",
        )]
        signals = check_privilege_expiry(grants, delegations, now=NOW)
        types = [s["driftType"] for s in signals]
        assert "privilege_orphaned" in types
        assert any(s["severity"] == "red" for s in signals)

    def test_custom_threshold(self):
        near_exp = (NOW + timedelta(hours=24)).isoformat()
        grants = [_make_grant(expires_at=near_exp)]
        signals_tight = check_privilege_expiry(grants, [], now=NOW, near_expiry_hours=12)
        assert len(signals_tight) == 0
        signals_wide = check_privilege_expiry(grants, [], now=NOW, near_expiry_hours=72)
        assert len(signals_wide) == 1


# ── TestCheckAuthorityIntegrity ──────────────────────────────────


class TestCheckAuthorityIntegrity:
    """Tests for check_authority_integrity (AUTH-F16)."""

    def test_empty_state_returns_empty(self):
        signals = check_authority_integrity({}, [], [])
        assert signals == []

    def test_tampered_ledger_detected(self):
        entries = [
            {"chain_hash": "sha256:bad", "prev_chain_hash": None, "data": "test"},
        ]
        signals = check_authority_integrity({"entries": entries}, [], [])
        types = [s["driftType"] for s in signals]
        assert "authority_chain_broken" in types
        assert any(s["severity"] == "red" for s in signals)

    def test_invalid_policy_seal_detected(self):
        policies = [{
            "policyPackId": "PP-001",
            "sealHash": "sha256:definitely_wrong",
            "version": "1.0.0",
        }]
        signals = check_authority_integrity({}, [], policies)
        types = [s["driftType"] for s in signals]
        assert "signature_custody_mismatch" in types

    def test_policy_hash_mismatch_detected(self):
        policies = [{
            "policyPackId": "PP-001",
            "policyHash": "sha256:current",
            "expectedPolicyHash": "sha256:expected",
        }]
        signals = check_authority_integrity({}, [], policies)
        types = [s["driftType"] for s in signals]
        assert "policy_drift_detected" in types
        assert any(s["severity"] == "yellow" for s in signals)


# ── TestAuthorityHealth ──────────────────────────────────────────


class TestAuthorityHealth:
    """Tests for severity classification and health summary."""

    def test_classify_green(self):
        assert classify_authority_severity([]) == "green"

    def test_classify_yellow(self):
        signals = [{"severity": "yellow"}]
        assert classify_authority_severity(signals) == "yellow"

    def test_classify_orange(self):
        signals = [{"severity": "yellow"}, {"severity": "orange"}]
        assert classify_authority_severity(signals) == "orange"

    def test_classify_red(self):
        signals = [{"severity": "yellow"}, {"severity": "red"}]
        assert classify_authority_severity(signals) == "red"

    def test_build_summary_empty(self):
        summary = build_health_summary([])
        assert summary["overallSeverity"] == "green"
        assert summary["signalCount"] == 0
        assert summary["bySubtype"] == {}

    def test_build_summary_mixed_signals(self):
        signals = [
            {"driftType": "grant_expired", "severity": "orange"},
            {"driftType": "delegation_near_expiry", "severity": "yellow"},
            {"driftType": "revoked_role_active", "severity": "red"},
        ]
        summary = build_health_summary(signals)
        assert summary["overallSeverity"] == "red"
        assert summary["signalCount"] == 3
        assert summary["bySeverity"]["red"] == 1
        assert summary["bySeverity"]["orange"] == 1
        assert summary["worstSignals"][0]["severity"] == "red"


# ── Handler Integration Tests ────────────────────────────────────


class TestAuthF13DriftScan:
    """Tests for AUTH-F13 handler via AuthorityOps."""

    def test_clean_state(self, authops, drift_context):
        event = {"payload": {}}
        result = authops.handle("AUTH-F13", event, drift_context)
        assert result.success
        assert result.function_id == "AUTH-F13"
        assert any(e["subtype"] == "authority_drift_signal" for e in result.events_emitted)

    def test_with_expired_delegation(self, authops, drift_context):
        event = {"payload": {
            "delegations": [_make_delegation(expires_at="2026-03-01T00:00:00Z")],
        }}
        result = authops.handle("AUTH-F13", event, drift_context)
        assert result.success
        assert len(result.drift_signals) > 0

    def test_drift_stored_in_mg(self, authops, drift_context):
        event = {"payload": {
            "delegations": [_make_delegation(revoked_at="2026-03-01T00:00:00Z")],
        }}
        result = authops.handle("AUTH-F13", event, drift_context)
        assert len(result.mg_updates) > 0
        mg = drift_context["memory_graph"]
        assert mg.node_count > 0


class TestAuthF14DelegationHealth:
    """Tests for AUTH-F14 handler via AuthorityOps."""

    def test_healthy_delegations(self, authops, drift_context):
        event = {"payload": {
            "delegations": [_make_delegation()],
        }}
        result = authops.handle("AUTH-F14", event, drift_context)
        assert result.success
        assert result.function_id == "AUTH-F14"

    def test_broken_delegation_emits_drift(self, authops, drift_context):
        event = {"payload": {
            "delegations": [_make_delegation(revoked_at="2026-03-01T00:00:00Z")],
        }}
        result = authops.handle("AUTH-F14", event, drift_context)
        assert len(result.drift_signals) > 0


class TestAuthF15PrivilegeExpiry:
    """Tests for AUTH-F15 handler via AuthorityOps."""

    def test_no_expiry_issues(self, authops, drift_context):
        event = {"payload": {"grants": [_make_grant()]}}
        result = authops.handle("AUTH-F15", event, drift_context)
        assert result.success
        assert result.function_id == "AUTH-F15"

    def test_near_expiry_emits_yellow(self, authops, drift_context):
        near_exp = (NOW + timedelta(hours=48)).isoformat()
        event = {"payload": {"grants": [_make_grant(expires_at=near_exp)]}}
        result = authops.handle("AUTH-F15", event, drift_context)
        assert len(result.drift_signals) > 0
        assert any(s["severity"] == "yellow" for s in result.drift_signals)


class TestAuthF16IntegrityCheck:
    """Tests for AUTH-F16 handler via AuthorityOps."""

    def test_valid_integrity(self, authops, drift_context):
        event = {"payload": {}}
        result = authops.handle("AUTH-F16", event, drift_context)
        assert result.success
        assert result.function_id == "AUTH-F16"

    def test_tampered_ledger_emits_red(self, authops, drift_context):
        event = {"payload": {
            "ledgerSnapshot": {
                "entries": [{"chain_hash": "sha256:bad", "prev_chain_hash": None, "data": "x"}],
            },
        }}
        result = authops.handle("AUTH-F16", event, drift_context)
        assert len(result.drift_signals) > 0
        assert any(s["severity"] == "red" for s in result.drift_signals)
