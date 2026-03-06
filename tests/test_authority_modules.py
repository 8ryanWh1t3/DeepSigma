"""Unit tests for core authority modules — policy_compiler, policy_runtime,
delegation_chain, reasoning_gate, authority_audit.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from core.authority.authority_audit import AuthorityAuditLog
from core.authority.delegation_chain import (
    check_expiry,
    compute_effective_scope,
    validate_chain,
)
from core.authority.models import (
    Actor,
    ActionRequest,
    AuditRecord,
    AuthorityVerdict,
    Delegation,
    Resource,
    Role,
)
from core.authority.policy_compiler import (
    compile_policy,
    extract_constraints,
    extract_reasoning_requirements,
)
from core.authority.policy_runtime import evaluate
from core.authority.reasoning_gate import (
    check_assumption_freshness,
    check_dlr_presence,
    check_minimum_confidence,
    check_required_truth_types,
)
from core.authority.decision_authority_resolver import (
    check_scope_overlap,
    resolve,
)


# ── Policy Compiler Tests ────────────────────────────────────────


class TestPolicyCompiler:
    def test_compile_empty_dlr(self):
        artifact = compile_policy({}, {})
        assert artifact.artifact_id.startswith("GOV-")
        assert artifact.artifact_type == "policy_evaluation"
        assert artifact.seal_hash.startswith("sha256:")

    def test_compile_with_dlr(self):
        dlr = {"dlrId": "DLR-abc123", "episodeId": "EP-001"}
        policy = {"policyPackId": "PP-001"}
        artifact = compile_policy(dlr, policy)
        assert artifact.dlr_ref == "DLR-abc123"
        assert artifact.episode_id == "EP-001"

    def test_extract_reasoning_requirements(self):
        dlr = {"claims": {"context": [1, 2], "rationale": [3]}}
        policy = {"requiresDlr": True, "minimumConfidence": 0.8}
        req = extract_reasoning_requirements(dlr, policy)
        assert req.requires_dlr is True
        assert req.minimum_confidence == 0.8
        assert req.minimum_claims >= 1

    def test_extract_constraints_filters_by_action(self):
        policy = {
            "constraints": [
                {"constraintId": "C-1", "constraintType": "scope_limit",
                 "expression": "scope = ops", "appliesTo": ["quarantine"]},
                {"constraintId": "C-2", "constraintType": "rate_limit",
                 "expression": "rate < 100", "appliesTo": ["deploy"]},
            ],
            "requiresDlr": True,
            "maxBlastRadius": "medium",
        }
        constraints = extract_constraints(policy, "quarantine")
        constraint_ids = [c.constraint_id for c in constraints]
        assert "C-1" in constraint_ids
        assert "C-2" not in constraint_ids
        # Implicit DLR and blast radius constraints always added
        assert any(c.constraint_type == "requires_dlr" for c in constraints)
        assert any(c.constraint_type == "blast_radius_max" for c in constraints)


# ── Policy Runtime Tests ─────────────────────────────────────────


class TestPolicyRuntime:
    def _make_context(self, **overrides):
        ctx = {
            "actor_registry": {
                "agent-001": {
                    "actorType": "agent",
                    "roles": [{"roleId": "R-1", "roleName": "op", "scope": "global"}],
                },
            },
            "resource_registry": {
                "res-001": {"resourceType": "account", "owner": "platform"},
            },
            "policy_packs": {
                "default": {"requiresDlr": True, "maxBlastRadius": "medium"},
            },
            "dlr_store": {"EP-001": {"dlrId": "DLR-001"}},
            "claims": [],
            "kill_switch_active": False,
            "now": datetime(2026, 3, 5, tzinfo=timezone.utc),
        }
        ctx.update(overrides)
        return ctx

    def test_full_pipeline_allow(self):
        request = {
            "actionId": "ACT-001",
            "actionType": "quarantine",
            "actorId": "agent-001",
            "resourceRef": "res-001",
            "episodeId": "EP-001",
            "blastRadiusTier": "small",
        }
        result = evaluate(request, self._make_context())
        assert result.verdict == AuthorityVerdict.ALLOW.value
        assert "kill_switch_check" in result.passed_checks

    def test_pipeline_missing_reasoning(self):
        request = {
            "actionId": "ACT-002",
            "actionType": "quarantine",
            "actorId": "agent-001",
            "resourceRef": "res-001",
            "blastRadiusTier": "small",
        }
        ctx = self._make_context(dlr_store={})
        result = evaluate(request, ctx)
        assert result.verdict == AuthorityVerdict.MISSING_REASONING.value
        assert "dlr_presence" in result.failed_checks

    def test_pipeline_killswitch(self):
        request = {
            "actionId": "ACT-003",
            "actionType": "quarantine",
            "actorId": "agent-001",
            "resourceRef": "res-001",
            "blastRadiusTier": "small",
        }
        ctx = self._make_context(kill_switch_active=True)
        result = evaluate(request, ctx)
        assert result.verdict == AuthorityVerdict.KILL_SWITCH_ACTIVE.value

    def test_pipeline_blast_radius_escalate(self):
        request = {
            "actionId": "ACT-004",
            "actionType": "quarantine",
            "actorId": "agent-001",
            "resourceRef": "res-001",
            "episodeId": "EP-001",
            "blastRadiusTier": "large",
        }
        ctx = self._make_context()
        result = evaluate(request, ctx)
        assert result.verdict == AuthorityVerdict.ESCALATE.value
        assert "blast_radius_threshold" in result.failed_checks


# ── Delegation Chain Tests ───────────────────────────────────────


class TestDelegationChain:
    def test_valid_chain(self):
        actor = Actor(actor_id="agent-001", actor_type="agent")
        delegations = [
            Delegation(
                delegation_id="DEL-001",
                from_actor_id="admin-001",
                to_actor_id="agent-001",
                scope="security-ops",
                effective_at="2026-01-01T00:00:00Z",
            )
        ]
        valid, issues = validate_chain(delegations, actor)
        assert valid
        assert len(issues) == 0

    def test_expired_delegation(self):
        actor = Actor(actor_id="agent-001", actor_type="agent")
        delegations = [
            Delegation(
                delegation_id="DEL-EXP",
                from_actor_id="admin-001",
                to_actor_id="agent-001",
                scope="ops",
                effective_at="2024-01-01T00:00:00Z",
                expires_at="2024-06-01T00:00:00Z",
            )
        ]
        valid, issues = validate_chain(
            delegations, actor,
            now=datetime(2026, 3, 5, tzinfo=timezone.utc),
        )
        assert not valid
        assert any("expired" in i for i in issues)

    def test_depth_exceeded(self):
        actor = Actor(actor_id="a5", actor_type="agent")
        delegations = [
            Delegation(delegation_id=f"DEL-{i}", from_actor_id=f"a{i}",
                       to_actor_id=f"a{i+1}", scope="ops")
            for i in range(6)
        ]
        valid, issues = validate_chain(delegations, actor, max_depth=3)
        assert not valid
        assert any("depth_exceeded" in i for i in issues)

    def test_empty_chain(self):
        actor = Actor(actor_id="a1", actor_type="agent")
        valid, issues = validate_chain([], actor)
        assert not valid
        assert "empty_delegation_chain" in issues

    def test_check_expiry_no_expiry(self):
        d = Delegation(delegation_id="D1", from_actor_id="a", to_actor_id="b", scope="ops")
        assert check_expiry(d) is True

    def test_compute_effective_scope(self):
        chain = [
            Delegation(delegation_id="D1", from_actor_id="a", to_actor_id="b", scope="global"),
            Delegation(delegation_id="D2", from_actor_id="b", to_actor_id="c", scope="security-ops"),
        ]
        assert compute_effective_scope(chain) == "security-ops"


# ── Reasoning Gate Tests ─────────────────────────────────────────


class TestReasoningGate:
    def test_dlr_present(self):
        present, detail = check_dlr_presence("DLR-001", {"dlr_store": {"DLR-001": {}}})
        assert present

    def test_dlr_missing(self):
        present, detail = check_dlr_presence("DLR-GONE", {"dlr_store": {}})
        assert not present

    def test_dlr_no_ref(self):
        present, detail = check_dlr_presence(None, {})
        assert not present

    def test_assumption_freshness_all_fresh(self):
        claims = [
            {"claimId": "C1", "truthType": "assumption",
             "halfLife": {"expiresAt": "2027-01-01T00:00:00Z"}},
        ]
        fresh, stale = check_assumption_freshness(
            claims, now=datetime(2026, 3, 5, tzinfo=timezone.utc))
        assert fresh
        assert len(stale) == 0

    def test_assumption_freshness_stale(self):
        claims = [
            {"claimId": "C-STALE", "truthType": "assumption",
             "halfLife": {"expiresAt": "2025-01-01T00:00:00Z"}},
        ]
        fresh, stale = check_assumption_freshness(
            claims, now=datetime(2026, 3, 5, tzinfo=timezone.utc))
        assert not fresh
        assert "C-STALE" in stale

    def test_minimum_confidence_met(self):
        claims = [
            {"claimId": "C1", "confidence": {"score": 0.9}},
            {"claimId": "C2", "confidence": {"score": 0.8}},
        ]
        met, avg = check_minimum_confidence(claims, threshold=0.7)
        assert met
        assert avg == pytest.approx(0.85)

    def test_minimum_confidence_not_met(self):
        claims = [
            {"claimId": "C1", "confidence": {"score": 0.3}},
        ]
        met, avg = check_minimum_confidence(claims, threshold=0.7)
        assert not met

    def test_required_truth_types_present(self):
        claims = [
            {"claimId": "C1", "truthType": "observation"},
            {"claimId": "C2", "truthType": "inference"},
        ]
        present, missing = check_required_truth_types(
            claims, ["observation", "inference"])
        assert present
        assert len(missing) == 0

    def test_required_truth_types_missing(self):
        claims = [{"claimId": "C1", "truthType": "observation"}]
        present, missing = check_required_truth_types(
            claims, ["observation", "forecast"])
        assert not present
        assert "forecast" in missing


# ── Authority Audit Tests ────────────────────────────────────────


class TestAuthorityAudit:
    def test_append_and_chain(self):
        log = AuthorityAuditLog()
        record = AuditRecord(
            audit_id="", action_id="ACT-001", actor_id="agent-001",
            resource_id="res-001", verdict="ALLOW",
            evaluated_at="2026-03-05T00:00:00Z",
        )
        chain_hash = log.append(record)
        assert chain_hash.startswith("sha256:")
        assert log.record_count == 1
        assert record.audit_id.startswith("AUDIT-")

    def test_verify_chain(self):
        log = AuthorityAuditLog()
        for i in range(5):
            log.append(AuditRecord(
                audit_id="", action_id=f"ACT-{i}", actor_id="agent-001",
                resource_id="res-001", verdict="ALLOW",
                evaluated_at="2026-03-05T00:00:00Z",
            ))
        assert log.verify_chain()

    def test_tampered_chain_fails(self):
        log = AuthorityAuditLog()
        for i in range(3):
            log.append(AuditRecord(
                audit_id="", action_id=f"ACT-{i}", actor_id="a",
                resource_id="r", verdict="ALLOW",
                evaluated_at="2026-03-05T00:00:00Z",
            ))
        # Tamper
        log._records[1].chain_hash = "sha256:tampered"
        assert not log.verify_chain()

    def test_query_by_action(self):
        log = AuthorityAuditLog()
        log.append(AuditRecord(
            audit_id="", action_id="ACT-TARGET", actor_id="a",
            resource_id="r", verdict="BLOCK",
            evaluated_at="2026-03-05T00:00:00Z",
        ))
        log.append(AuditRecord(
            audit_id="", action_id="ACT-OTHER", actor_id="a",
            resource_id="r", verdict="ALLOW",
            evaluated_at="2026-03-05T00:00:00Z",
        ))
        results = log.query_by_action("ACT-TARGET")
        assert len(results) == 1
        assert results[0].verdict == "BLOCK"

    def test_query_by_actor(self):
        log = AuthorityAuditLog()
        log.append(AuditRecord(
            audit_id="", action_id="ACT-1", actor_id="agent-A",
            resource_id="r", verdict="ALLOW",
            evaluated_at="2026-03-05T00:00:00Z",
        ))
        log.append(AuditRecord(
            audit_id="", action_id="ACT-2", actor_id="agent-B",
            resource_id="r", verdict="ALLOW",
            evaluated_at="2026-03-05T00:00:00Z",
        ))
        results = log.query_by_actor("agent-A")
        assert len(results) == 1


# ── Decision Authority Resolver Tests ────────────────────────────


class TestDecisionAuthorityResolver:
    def test_scope_overlap_global(self):
        assert check_scope_overlap("global", "any-scope")
        assert check_scope_overlap("any-scope", "global")

    def test_scope_overlap_prefix(self):
        assert check_scope_overlap("security-ops", "security-ops:tier-1")
        assert check_scope_overlap("security-ops:tier-1", "security-ops")

    def test_scope_overlap_no_match(self):
        assert not check_scope_overlap("security-ops", "finance-ops")

    def test_resolve_with_matching_role(self):
        actor = Actor(
            actor_id="agent-001", actor_type="agent",
            roles=[Role(role_id="R-1", role_name="operator", scope="ops")],
        )
        action = ActionRequest(action_id="A1", action_type="quarantine", resource_ref="r1")
        resource = Resource(resource_id="r1", resource_type="ops-account")
        grant = resolve(actor, action, resource, [])
        assert grant is not None
        assert grant.source_type == "role_binding"
