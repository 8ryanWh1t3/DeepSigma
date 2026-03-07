"""Tests for AuthorityOps domain mode — AUTH-F01 through AUTH-F12.

Covers registration, per-handler behavior, and integration scenarios.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from core.authority import AuthorityLedger
from core.authority.authority_audit import AuthorityAuditLog
from core.authority.models import AuditRecord, AuthorityVerdict
from core.memory_graph import MemoryGraph
from core.modes.authorityops import AuthorityOps


@pytest.fixture
def authops():
    return AuthorityOps()


@pytest.fixture
def authority_context():
    """Full evaluation context for AuthorityOps handlers."""
    return {
        "memory_graph": MemoryGraph(),
        "authority_ledger": AuthorityLedger(),
        "authority_audit": AuthorityAuditLog(),
        "kill_switch_active": False,
        "policy_packs": {
            "default": {
                "policyPackId": "PP-DEFAULT",
                "version": "1.0.0",
                "constraints": [],
                "requiresDlr": True,
                "maxBlastRadius": "medium",
                "minimumConfidence": 0.7,
            },
            "quarantine": {
                "policyPackId": "PP-QUARANTINE",
                "version": "1.0.0",
                "constraints": [],
                "requiresDlr": True,
                "maxBlastRadius": "medium",
                "minimumConfidence": 0.7,
            },
        },
        "actor_registry": {
            "agent-001": {
                "actorType": "agent",
                "roles": [{"roleId": "R-001", "roleName": "operator", "scope": "security-ops"}],
            },
        },
        "resource_registry": {
            "resource-001": {
                "resourceType": "account",
                "owner": "platform",
                "classification": "internal",
            },
        },
        "dlr_store": {"EP-TEST-001": {"dlrId": "DLR-test-001"}},
        "claims": [],
        "now": datetime(2026, 3, 5, tzinfo=timezone.utc),
    }


# ── Registration Tests ───────────────────────────────────────────


class TestAuthorityOpsRegistration:
    """Verify domain registration and handler setup."""

    def test_domain_name(self, authops):
        assert authops.domain == "authorityops"

    def test_all_19_handlers_registered(self, authops):
        assert len(authops.function_ids) == 19

    def test_function_ids_well_formed(self, authops):
        for fid in authops.function_ids:
            assert fid.startswith("AUTH-F")
            num = int(fid.split("AUTH-F")[1])
            assert 1 <= num <= 19

    def test_has_handler(self, authops):
        assert authops.has_handler("AUTH-F01")
        assert authops.has_handler("AUTH-F12")
        assert not authops.has_handler("INTEL-F01")

    def test_unknown_handler_returns_error(self, authops, authority_context):
        result = authops.handle("AUTH-F99", {}, authority_context)
        assert not result.success
        assert "No handler" in result.error


# ── AUTH-F01: Action Request Intake ──────────────────────────────


class TestAuthF01ActionIntake:
    def test_valid_intake(self, authops, authority_context):
        event = {
            "payload": {
                "actionId": "ACT-001",
                "actionType": "quarantine",
                "actorId": "agent-001",
                "resourceRef": "resource-001",
                "episodeId": "EP-001",
            }
        }
        result = authops.handle("AUTH-F01", event, authority_context)
        assert result.success
        assert result.function_id == "AUTH-F01"
        assert any(
            e["subtype"] == "authority_evaluation_started"
            for e in result.events_emitted
        )

    def test_missing_fields_emits_drift(self, authops, authority_context):
        event = {"payload": {"actionId": "ACT-002"}}
        result = authops.handle("AUTH-F01", event, authority_context)
        assert result.success  # Still succeeds (soft validation)
        assert len(result.drift_signals) > 0
        assert result.drift_signals[0]["subtype"] == "authority_intake_incomplete"


# ── AUTH-F02: Actor Resolution ───────────────────────────────────


class TestAuthF02ActorResolve:
    def test_known_actor_resolves(self, authops, authority_context):
        event = {"payload": {"actorId": "agent-001"}}
        result = authops.handle("AUTH-F02", event, authority_context)
        assert result.success
        assert any(e["subtype"] == "actor_resolved" for e in result.events_emitted)

    def test_unknown_actor_emits_drift(self, authops, authority_context):
        event = {"payload": {"actorId": "unknown-actor"}}
        result = authops.handle("AUTH-F02", event, authority_context)
        assert result.success
        assert any(e["subtype"] == "actor_unknown" for e in result.events_emitted)
        assert len(result.drift_signals) > 0


# ── AUTH-F03: Resource Resolution ────────────────────────────────


class TestAuthF03ResourceResolve:
    def test_known_resource_resolves(self, authops, authority_context):
        event = {"payload": {"resourceRef": "resource-001"}}
        result = authops.handle("AUTH-F03", event, authority_context)
        assert result.success
        assert any(e["subtype"] == "resource_resolved" for e in result.events_emitted)

    def test_unknown_resource(self, authops, authority_context):
        event = {"payload": {"resourceRef": "unknown-resource"}}
        result = authops.handle("AUTH-F03", event, authority_context)
        assert result.success
        assert any(e["subtype"] == "resource_unknown" for e in result.events_emitted)


# ── AUTH-F04: Policy Load ────────────────────────────────────────


class TestAuthF04PolicyLoad:
    def test_policy_loaded(self, authops, authority_context):
        event = {"payload": {"actionType": "quarantine"}}
        result = authops.handle("AUTH-F04", event, authority_context)
        assert result.success
        assert any(e["subtype"] == "policy_loaded" for e in result.events_emitted)

    def test_policy_missing(self, authops, authority_context):
        authority_context["policy_packs"] = {}
        event = {"payload": {"actionType": "unknown_action"}}
        result = authops.handle("AUTH-F04", event, authority_context)
        assert result.success
        assert any(e["subtype"] == "policy_missing" for e in result.events_emitted)


# ── AUTH-F05: DLR Presence Check ─────────────────────────────────


class TestAuthF05DlrPresence:
    def test_dlr_present(self, authops, authority_context):
        event = {"payload": {"dlrRef": "EP-TEST-001"}}
        result = authops.handle("AUTH-F05", event, authority_context)
        assert result.success
        assert any(e["subtype"] == "dlr_present" for e in result.events_emitted)

    def test_dlr_missing(self, authops, authority_context):
        event = {"payload": {"dlrRef": "NONEXISTENT-DLR"}}
        result = authops.handle("AUTH-F05", event, authority_context)
        assert result.success
        assert any(e["subtype"] == "dlr_missing" for e in result.events_emitted)


# ── AUTH-F06: Assumption Validation ──────────────────────────────


class TestAuthF06AssumptionValidate:
    def test_fresh_assumptions_pass(self, authops, authority_context):
        authority_context["claims"] = [
            {
                "claimId": "CLAIM-001",
                "truthType": "assumption",
                "halfLife": {"expiresAt": "2027-01-01T00:00:00Z"},
            }
        ]
        event = {"payload": {}}
        result = authops.handle("AUTH-F06", event, authority_context)
        assert result.success
        assert any(e["subtype"] == "assumptions_valid" for e in result.events_emitted)

    def test_stale_assumptions_emit_drift(self, authops, authority_context):
        authority_context["claims"] = [
            {
                "claimId": "CLAIM-STALE",
                "truthType": "assumption",
                "halfLife": {"expiresAt": "2025-01-01T00:00:00Z"},
            }
        ]
        event = {"payload": {}}
        result = authops.handle("AUTH-F06", event, authority_context)
        assert result.success
        assert any(e["subtype"] == "assumptions_stale" for e in result.events_emitted)
        assert len(result.drift_signals) > 0


# ── AUTH-F07: Half-Life Check ────────────────────────────────────


class TestAuthF07HalfLifeCheck:
    def test_fresh_claims_pass(self, authops, authority_context):
        authority_context["claims"] = [
            {"claimId": "CLAIM-FRESH", "halfLife": {"expiresAt": "2027-01-01T00:00:00Z"}}
        ]
        event = {"payload": {}}
        result = authops.handle("AUTH-F07", event, authority_context)
        assert result.success
        assert any(e["subtype"] == "claims_fresh" for e in result.events_emitted)

    def test_expired_claims_emit_drift(self, authops, authority_context):
        authority_context["claims"] = [
            {"claimId": "CLAIM-OLD", "halfLife": {"expiresAt": "2025-01-01T00:00:00Z"}}
        ]
        event = {"payload": {}}
        result = authops.handle("AUTH-F07", event, authority_context)
        assert result.success
        assert any(e["subtype"] == "claims_expired" for e in result.events_emitted)
        assert len(result.drift_signals) > 0


# ── AUTH-F08: Blast Radius Threshold ─────────────────────────────


class TestAuthF08BlastRadius:
    def test_blast_radius_within_limit(self, authops, authority_context):
        event = {"payload": {"blastRadiusTier": "small", "actionType": "quarantine"}}
        result = authops.handle("AUTH-F08", event, authority_context)
        assert result.success
        assert any(e["subtype"] == "blast_radius_ok" for e in result.events_emitted)

    def test_blast_radius_exceeded(self, authops, authority_context):
        event = {"payload": {"blastRadiusTier": "large", "actionType": "quarantine"}}
        result = authops.handle("AUTH-F08", event, authority_context)
        assert result.success
        assert any(
            e["subtype"] == "blast_radius_exceeded" for e in result.events_emitted
        )


# ── AUTH-F09: Kill Switch Check ──────────────────────────────────


class TestAuthF09KillSwitch:
    def test_killswitch_inactive_passes(self, authops, authority_context):
        event = {"payload": {}}
        result = authops.handle("AUTH-F09", event, authority_context)
        assert result.success
        assert any(e["subtype"] == "killswitch_clear" for e in result.events_emitted)

    def test_killswitch_active_blocks(self, authops, authority_context):
        authority_context["kill_switch_active"] = True
        event = {"payload": {}}
        result = authops.handle("AUTH-F09", event, authority_context)
        assert result.success
        assert any(e["subtype"] == "killswitch_active" for e in result.events_emitted)


# ── AUTH-F10: Decision Gate ──────────────────────────────────────


class TestAuthF10DecisionGate:
    def test_all_checks_pass_allows(self, authops, authority_context):
        event = {
            "payload": {
                "actionId": "ACT-001",
                "actionType": "quarantine",
                "actorId": "agent-001",
                "resourceRef": "resource-001",
                "episodeId": "EP-TEST-001",
                "blastRadiusTier": "small",
            }
        }
        result = authops.handle("AUTH-F10", event, authority_context)
        assert result.success
        assert any(
            e.get("verdict") == "ALLOW" for e in result.events_emitted
        )

    def test_missing_dlr_blocks(self, authops, authority_context):
        authority_context["dlr_store"] = {}
        event = {
            "payload": {
                "actionId": "ACT-002",
                "actionType": "quarantine",
                "actorId": "agent-001",
                "resourceRef": "resource-001",
                "blastRadiusTier": "small",
            }
        }
        result = authops.handle("AUTH-F10", event, authority_context)
        assert result.success
        assert any(
            e.get("verdict") in ("MISSING_REASONING", "BLOCK")
            for e in result.events_emitted
        )

    def test_killswitch_blocks(self, authops, authority_context):
        authority_context["kill_switch_active"] = True
        event = {
            "payload": {
                "actionId": "ACT-003",
                "actionType": "quarantine",
                "actorId": "agent-001",
                "resourceRef": "resource-001",
                "blastRadiusTier": "small",
            }
        }
        result = authops.handle("AUTH-F10", event, authority_context)
        assert result.success
        verdicts = [e.get("verdict") for e in result.events_emitted]
        assert "KILL_SWITCH_ACTIVE" in verdicts


# ── AUTH-F11: Audit Record Emit ──────────────────────────────────


class TestAuthF11AuditEmit:
    def test_audit_record_emitted(self, authops, authority_context):
        event = {
            "payload": {
                "actionId": "ACT-001",
                "actorId": "agent-001",
                "resourceRef": "resource-001",
                "verdict": "ALLOW",
            }
        }
        result = authops.handle("AUTH-F11", event, authority_context)
        assert result.success
        assert any(e["subtype"] == "authority_audited" for e in result.events_emitted)
        assert any("chainHash" in e for e in result.events_emitted)

    def test_audit_written_to_mg(self, authops, authority_context):
        event = {
            "payload": {
                "actionId": "ACT-001",
                "actorId": "agent-001",
                "verdict": "BLOCK",
            }
        }
        result = authops.handle("AUTH-F11", event, authority_context)
        assert result.success
        assert len(result.mg_updates) > 0


# ── AUTH-F12: Delegation Chain Validate ──────────────────────────


class TestAuthF12DelegationChain:
    def test_valid_delegation_chain(self, authops, authority_context):
        event = {
            "payload": {
                "actorId": "agent-001",
                "delegations": [
                    {
                        "delegationId": "DEL-001",
                        "fromActorId": "admin-001",
                        "toActorId": "agent-001",
                        "scope": "security-ops",
                        "effectiveAt": "2026-01-01T00:00:00Z",
                    }
                ],
            }
        }
        result = authops.handle("AUTH-F12", event, authority_context)
        assert result.success
        assert any(e["subtype"] == "delegation_valid" for e in result.events_emitted)

    def test_broken_delegation_chain(self, authops, authority_context):
        event = {
            "payload": {
                "actorId": "agent-001",
                "delegations": [
                    {
                        "delegationId": "DEL-EXPIRED",
                        "fromActorId": "admin-001",
                        "toActorId": "agent-001",
                        "scope": "security-ops",
                        "effectiveAt": "2024-01-01T00:00:00Z",
                        "expiresAt": "2024-06-01T00:00:00Z",
                    }
                ],
            }
        }
        result = authops.handle("AUTH-F12", event, authority_context)
        assert result.success
        assert any(e["subtype"] == "delegation_broken" for e in result.events_emitted)
        assert len(result.drift_signals) > 0


# ── Integration Tests ────────────────────────────────────────────


class TestAuthorityOpsIntegration:
    def test_full_pipeline_allow(self, authops, authority_context):
        """End-to-end: F01 → F02 → F03 → F04 → F05 → F10 → F11."""
        request = {
            "payload": {
                "actionId": "ACT-E2E-001",
                "actionType": "quarantine",
                "actorId": "agent-001",
                "resourceRef": "resource-001",
                "episodeId": "EP-TEST-001",
                "blastRadiusTier": "small",
            }
        }

        # Run pipeline steps
        r1 = authops.handle("AUTH-F01", request, authority_context)
        assert r1.success

        r2 = authops.handle("AUTH-F02", request, authority_context)
        assert r2.success

        r3 = authops.handle("AUTH-F03", request, authority_context)
        assert r3.success

        r4 = authops.handle("AUTH-F04", request, authority_context)
        assert r4.success

        r5 = authops.handle("AUTH-F05", request, authority_context)
        assert r5.success

        r10 = authops.handle("AUTH-F10", request, authority_context)
        assert r10.success
        assert any(e.get("verdict") == "ALLOW" for e in r10.events_emitted)

        r11 = authops.handle("AUTH-F11", {
            "payload": {
                "actionId": "ACT-E2E-001",
                "actorId": "agent-001",
                "verdict": "ALLOW",
            }
        }, authority_context)
        assert r11.success
        assert any(e["subtype"] == "authority_audited" for e in r11.events_emitted)

    def test_killswitch_short_circuit(self, authops, authority_context):
        """Kill-switch active should block at F09 / F10."""
        authority_context["kill_switch_active"] = True
        request = {
            "payload": {
                "actionId": "ACT-KS-001",
                "actionType": "quarantine",
                "actorId": "agent-001",
                "resourceRef": "resource-001",
                "blastRadiusTier": "small",
            }
        }

        r9 = authops.handle("AUTH-F09", request, authority_context)
        assert r9.success
        assert any(e["subtype"] == "killswitch_active" for e in r9.events_emitted)

        r10 = authops.handle("AUTH-F10", request, authority_context)
        assert r10.success
        verdicts = [e.get("verdict") for e in r10.events_emitted]
        assert "KILL_SWITCH_ACTIVE" in verdicts

    def test_replay_hash_is_deterministic(self, authops, authority_context):
        """Same input → same replay hash."""
        event = {
            "payload": {
                "actionId": "ACT-REPLAY",
                "actionType": "quarantine",
                "actorId": "agent-001",
                "resourceRef": "resource-001",
            }
        }
        r1 = authops.handle("AUTH-F01", event, authority_context)
        r2 = authops.handle("AUTH-F01", event, authority_context)
        assert r1.replay_hash == r2.replay_hash
        assert r1.replay_hash.startswith("sha256:")
