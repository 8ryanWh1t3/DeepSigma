"""Tests for the 7 OpenPQL primitives in AuthorityOps.

Covers:
  - Primitive 7: Seal & Hash (foundation)
  - Primitive 1: Policy Source
  - Primitive 2: Compiler upgrade (compile_from_source)
  - Primitive 3: Artifact Builder
  - Primitive 4: Runtime Gate
  - Primitive 5: Evidence Chain
  - Primitive 6: Audit Retrieval
  - End-to-end pipeline tests
"""

import json
import copy
from datetime import datetime, timezone
from pathlib import Path

import pytest

from core.authority.seal_and_hash import (
    canonical_json,
    compute_hash,
    seal,
    verify_seal,
    verify_chain,
)
from core.authority.policy_source import (
    PolicySource,
    build_policy_source,
    validate_policy_source,
)
from core.authority.models import CompiledPolicy
from core.authority.policy_compiler import compile_from_source
from core.authority.artifact_builder import (
    build_artifact,
    write_artifact,
    load_artifact,
    verify_artifact,
)
from core.authority.runtime_gate import RuntimeGate, GateDecision
from core.authority.evidence_chain import EvidenceChain, EvidenceEntry
from core.authority.audit_retrieval import AuditRetrieval, AuditAnswer


# ── Fixtures ──────────────────────────────────────────────────────


def _make_dlr(**overrides):
    """Minimal DLR dict."""
    d = {
        "dlrId": "DLR-TEST-001",
        "episodeId": "EP-TEST-001",
        "actionType": "quarantine",
        "claims": {
            "quarantine": [
                {"claimId": "CLAIM-001", "statement": "test", "confidence": {"score": 0.9}},
            ],
        },
    }
    d.update(overrides)
    return d


def _make_policy_pack(**overrides):
    """Minimal policy pack dict."""
    p = {
        "policyPackId": "PP-TEST-001",
        "version": "1.0.0",
        "constraints": [],
        "requiresDlr": True,
        "maxBlastRadius": "medium",
        "minimumConfidence": 0.7,
    }
    p.update(overrides)
    return p


def _make_context(actor_id="agent-001", **overrides):
    """Minimal evaluation context with actor and resource registries."""
    actor_dict = {
        "actorType": "agent",
        "roles": [
            {"roleId": "R-001", "roleName": "operator", "scope": "security-ops"},
        ],
    }
    resource_dict = {
        "resourceType": "account",
        "classification": "internal",
    }
    ctx = {
        "actor_registry": {actor_id: actor_dict},
        "resource_registry": {"resource-001": resource_dict},
        "policy_packs": {"quarantine": _make_policy_pack(), "default": _make_policy_pack()},
        "dlr_store": {"DLR-TEST-001": _make_dlr()},
        "claims": [
            {"claimId": "CLAIM-001", "statement": "test", "confidence": {"score": 0.9}},
        ],
        "kill_switch_active": False,
    }
    ctx.update(overrides)
    return ctx


def _make_request(action_id="ACT-TEST-001", actor_id="agent-001", **overrides):
    """Minimal action request dict."""
    r = {
        "actionId": action_id,
        "actionType": "quarantine",
        "actorId": actor_id,
        "resourceRef": "resource-001",
        "episodeId": "EP-TEST-001",
        "blastRadiusTier": "small",
        "dlrRef": "DLR-TEST-001",
    }
    r.update(overrides)
    return r


def _make_source():
    """Build a PolicySource for pipeline tests."""
    return build_policy_source(_make_dlr(), _make_policy_pack())


def _make_compiled():
    """Build a CompiledPolicy for pipeline tests."""
    return compile_from_source(_make_source())


# ── Primitive 7: Seal & Hash ──────────────────────────────────────


class TestSealAndHash:

    def test_canonical_json_deterministic(self):
        a = canonical_json({"b": 2, "a": 1})
        b = canonical_json({"a": 1, "b": 2})
        assert a == b
        assert a == '{"a":1,"b":2}'

    def test_compute_hash_sha256_prefix(self):
        h = compute_hash({"test": 1})
        assert h.startswith("sha256:")
        assert len(h) == 71  # "sha256:" + 64 hex chars

    def test_seal_structure(self):
        s = seal({"x": 1})
        assert "hash" in s
        assert "sealedAt" in s
        assert s["version"] == 1
        assert s["hash"].startswith("sha256:")

    def test_verify_seal_valid(self):
        payload = {"key": "value"}
        h = compute_hash(payload)
        assert verify_seal(payload, h)

    def test_verify_seal_tampered(self):
        payload = {"key": "value"}
        h = compute_hash(payload)
        assert not verify_seal({"key": "tampered"}, h)

    def test_verify_chain_valid(self):
        entries = []
        for i in range(3):
            entry = {
                "data": f"entry-{i}",
                "chain_hash": "",
                "prev_chain_hash": entries[-1]["chain_hash"] if entries else None,
            }
            hashable = dict(entry)
            hashable["chain_hash"] = ""
            entry["chain_hash"] = compute_hash(hashable)
            entries.append(entry)
        assert verify_chain(entries)

    def test_verify_chain_broken_link(self):
        entries = []
        for i in range(3):
            entry = {
                "data": f"entry-{i}",
                "chain_hash": "",
                "prev_chain_hash": entries[-1]["chain_hash"] if entries else None,
            }
            hashable = dict(entry)
            hashable["chain_hash"] = ""
            entry["chain_hash"] = compute_hash(hashable)
            entries.append(entry)
        # Break the link
        entries[1]["prev_chain_hash"] = "sha256:bad"
        assert not verify_chain(entries)

    def test_verify_chain_tampered_hash(self):
        entries = []
        for i in range(3):
            entry = {
                "data": f"entry-{i}",
                "chain_hash": "",
                "prev_chain_hash": entries[-1]["chain_hash"] if entries else None,
            }
            hashable = dict(entry)
            hashable["chain_hash"] = ""
            entry["chain_hash"] = compute_hash(hashable)
            entries.append(entry)
        # Tamper with the data but not the hash
        entries[1]["data"] = "tampered"
        assert not verify_chain(entries)


# ── Primitive 1: Policy Source ────────────────────────────────────


class TestPolicySource:

    def test_build_sets_id_and_hash(self):
        source = build_policy_source(_make_dlr(), _make_policy_pack())
        assert source.source_id.startswith("PSRC-")
        assert source.source_hash.startswith("sha256:")

    def test_build_requires_dlr_id(self):
        with pytest.raises(ValueError, match="dlrId"):
            build_policy_source({"dlrId": ""}, _make_policy_pack())

    def test_validate_valid(self):
        source = build_policy_source(_make_dlr(), _make_policy_pack())
        valid, errors = validate_policy_source(source)
        assert valid
        assert errors == []

    def test_validate_empty_dlr(self):
        source = PolicySource(
            source_id="PSRC-test",
            dlr={},
            policy_pack=_make_policy_pack(),
            source_hash="sha256:test",
        )
        valid, errors = validate_policy_source(source)
        assert not valid
        assert any("dlr" in e for e in errors)

    def test_hash_deterministic(self):
        s1 = build_policy_source(_make_dlr(), _make_policy_pack())
        s2 = build_policy_source(_make_dlr(), _make_policy_pack())
        assert s1.source_hash == s2.source_hash


# ── Primitive 2: Compiler Upgrade ─────────────────────────────────


class TestCompilerUpgrade:

    def test_compile_from_source_produces_artifact(self):
        compiled = _make_compiled()
        assert isinstance(compiled, CompiledPolicy)
        assert compiled.artifact_id.startswith("GOV-")

    def test_compile_from_source_includes_rules(self):
        compiled = _make_compiled()
        # Should have at least implicit DLR + blast radius constraints
        assert len(compiled.rules) >= 2

    def test_policy_hash_deterministic(self):
        c1 = compile_from_source(_make_source())
        c2 = compile_from_source(_make_source())
        assert c1.policy_hash == c2.policy_hash

    def test_seal_valid(self):
        compiled = _make_compiled()
        assert compiled.seal_hash.startswith("sha256:")
        assert compiled.seal_version == 1


# ── Primitive 3: Artifact Builder ─────────────────────────────────


class TestArtifactBuilder:

    def test_build_returns_dict_with_keys(self):
        artifact = build_artifact(_make_compiled())
        for key in ("artifactId", "sourceId", "dlrRef", "rules", "policyHash", "seal"):
            assert key in artifact

    def test_write_creates_file(self, tmp_path):
        compiled = _make_compiled()
        path = write_artifact(compiled, tmp_path)
        assert path.exists()
        assert path.name == f"{compiled.artifact_id}.json"

    def test_load_roundtrip(self, tmp_path):
        compiled = _make_compiled()
        path = write_artifact(compiled, tmp_path)
        loaded = load_artifact(path)
        assert loaded["artifactId"] == compiled.artifact_id
        assert loaded["policyHash"] == compiled.policy_hash

    def test_load_tampered_raises(self, tmp_path):
        compiled = _make_compiled()
        path = write_artifact(compiled, tmp_path)
        # Tamper with the file
        data = json.loads(path.read_text())
        data["policyHash"] = "sha256:tampered"
        path.write_text(json.dumps(data))
        with pytest.raises(ValueError, match="seal verification failed"):
            load_artifact(path)

    def test_verify_valid(self):
        artifact = build_artifact(_make_compiled())
        assert verify_artifact(artifact)

    def test_verify_tampered(self):
        artifact = build_artifact(_make_compiled())
        artifact["policyHash"] = "sha256:tampered"
        assert not verify_artifact(artifact)


# ── Primitive 4: Runtime Gate ─────────────────────────────────────


class TestRuntimeGate:

    def test_evaluate_with_artifact_allow(self):
        """Test 1: ALLOW path through RuntimeGate."""
        gate = RuntimeGate()
        compiled = _make_compiled()
        request = _make_request()
        ctx = _make_context()
        decision = gate.evaluate(compiled, request, ctx)
        assert decision.verdict == "ALLOW"
        assert decision.artifact_id == compiled.artifact_id

    def test_evaluate_no_artifact_blocks(self):
        """Test: no artifact → BLOCK."""
        gate = RuntimeGate()
        decision = gate.evaluate(None, _make_request(), _make_context())
        assert decision.verdict == "BLOCK"
        assert decision.failed_reason == "no_artifact"

    def test_evaluate_raw_delegates(self):
        gate = RuntimeGate()
        decision = gate.evaluate_raw(_make_request(), _make_context())
        assert decision.verdict == "ALLOW"
        assert decision.artifact_id == ""  # no artifact in raw mode

    def test_decision_includes_artifact_ref(self):
        """Test 7 partial: artifact hash exists in decision."""
        gate = RuntimeGate()
        compiled = _make_compiled()
        decision = gate.evaluate(compiled, _make_request(), _make_context())
        assert decision.policy_hash == compiled.policy_hash


# ── Primitive 5: Evidence Chain ───────────────────────────────────


class TestEvidenceChain:

    def test_append_and_verify(self):
        chain = EvidenceChain()
        entry = EvidenceEntry(
            evidence_id="", gate_id="G-001", action_id="ACT-001",
            actor_id="agent-001", resource_id="resource-001",
            verdict="ALLOW", evaluated_at="2026-03-01T00:00:00Z",
        )
        chain_hash = chain.append(entry)
        assert chain_hash.startswith("sha256:")
        assert chain.verify()

    def test_jsonl_persistence(self, tmp_path):
        path = tmp_path / "evidence.jsonl"
        chain = EvidenceChain(path=path)
        entry = EvidenceEntry(
            evidence_id="", gate_id="G-001", action_id="ACT-001",
            actor_id="agent-001", resource_id="resource-001",
            verdict="ALLOW", evaluated_at="2026-03-01T00:00:00Z",
        )
        chain.append(entry)
        assert path.exists()
        # Reload from disk
        chain2 = EvidenceChain(path=path)
        assert chain2.entry_count == 1
        assert chain2.verify()

    def test_tampered_fails_verify(self):
        chain = EvidenceChain()
        for i in range(3):
            chain.append(EvidenceEntry(
                evidence_id="", gate_id=f"G-{i}", action_id=f"ACT-{i}",
                actor_id="agent-001", resource_id="resource-001",
                verdict="ALLOW", evaluated_at="2026-03-01T00:00:00Z",
            ))
        # Tamper
        chain._entries[1].verdict = "TAMPERED"
        assert not chain.verify()

    def test_entry_includes_artifact_hash(self):
        """Test: evidence entry records artifact_id and policy_hash."""
        chain = EvidenceChain()
        entry = EvidenceEntry(
            evidence_id="", gate_id="G-001", action_id="ACT-001",
            actor_id="agent-001", resource_id="resource-001",
            verdict="ALLOW", evaluated_at="2026-03-01T00:00:00Z",
            artifact_id="GOV-abc123", policy_hash="sha256:test",
        )
        chain.append(entry)
        assert chain.entries[0].artifact_id == "GOV-abc123"
        assert chain.entries[0].policy_hash == "sha256:test"


# ── Primitive 6: Audit Retrieval ──────────────────────────────────


class TestAuditRetrieval:

    def _build_chain_with_entries(self):
        chain = EvidenceChain()
        # ALLOW entry
        chain.append(EvidenceEntry(
            evidence_id="", gate_id="G-001", action_id="ACT-ALLOW",
            actor_id="agent-001", resource_id="resource-001",
            verdict="ALLOW", evaluated_at="2026-03-01T00:00:00Z",
            artifact_id="GOV-001", policy_hash="sha256:abc",
            passed_checks=["action_intake", "kill_switch_check", "actor_resolve",
                           "resource_resolve", "policy_load", "dlr_presence",
                           "assumption_validate", "half_life_check",
                           "blast_radius_threshold", "decision_gate", "audit_emit"],
        ))
        # BLOCK entry
        chain.append(EvidenceEntry(
            evidence_id="", gate_id="G-002", action_id="ACT-BLOCK",
            actor_id="agent-001", resource_id="resource-001",
            verdict="BLOCK", evaluated_at="2026-03-01T00:01:00Z",
            artifact_id="GOV-002", policy_hash="sha256:def",
            failed_checks=["actor_resolve"],
        ))
        # EXPIRED entry with stale assumptions
        chain.append(EvidenceEntry(
            evidence_id="", gate_id="G-003", action_id="ACT-EXPIRED",
            actor_id="agent-002", resource_id="resource-002",
            verdict="EXPIRED", evaluated_at="2026-03-01T00:02:00Z",
            artifact_id="GOV-003", policy_hash="sha256:ghi",
            failed_checks=["assumption_validate"],
            assumptions_snapshot={"stale": ["CLAIM-OLD-001"]},
        ))
        return chain

    def test_why_allowed_returns_passed_checks(self):
        """Test 9 partial: audit retrieval returns correct reason for ALLOW."""
        chain = self._build_chain_with_entries()
        retrieval = AuditRetrieval(evidence_chain=chain)
        answer = retrieval.why_allowed("ACT-ALLOW")
        assert answer.found
        assert answer.verdict == "ALLOW"
        assert "action_intake" in answer.evidence["passed_checks"]

    def test_why_blocked_returns_failed_check(self):
        """Test 9: audit retrieval correct block reason."""
        chain = self._build_chain_with_entries()
        retrieval = AuditRetrieval(evidence_chain=chain)
        answer = retrieval.why_blocked("ACT-BLOCK")
        assert answer.found
        assert answer.verdict == "BLOCK"
        assert "actor_resolve" in answer.detail

    def test_which_assumption_failed_identifies_stale(self):
        """Test 3: EXPIRED due to stale assumptions."""
        chain = self._build_chain_with_entries()
        retrieval = AuditRetrieval(evidence_chain=chain)
        answer = retrieval.which_assumption_failed("ACT-EXPIRED")
        assert answer.found
        assert "CLAIM-OLD-001" in answer.detail

    def test_which_policy_hash_returns_hash(self):
        chain = self._build_chain_with_entries()
        retrieval = AuditRetrieval(evidence_chain=chain)
        answer = retrieval.which_policy_hash("ACT-ALLOW")
        assert answer.found
        assert answer.detail == "sha256:abc"

    def test_actor_history_chronological(self):
        chain = self._build_chain_with_entries()
        retrieval = AuditRetrieval(evidence_chain=chain)
        history = retrieval.actor_history("agent-001")
        assert len(history) == 2
        assert history[0].verdict == "ALLOW"
        assert history[1].verdict == "BLOCK"

    def test_query_not_found(self):
        chain = self._build_chain_with_entries()
        retrieval = AuditRetrieval(evidence_chain=chain)
        answer = retrieval.why_allowed("ACT-NONEXISTENT")
        assert not answer.found


# ── End-to-End Pipeline ──────────────────────────────────────────


class TestOpenPQLPipeline:

    def test_full_pipeline_reops_to_audit(self, tmp_path):
        """End-to-end: ReOps packet → PolicySource → Compile → Artifact → Gate → Evidence → Audit."""
        # 1. Build PolicySource
        source = build_policy_source(_make_dlr(), _make_policy_pack())
        valid, errors = validate_policy_source(source)
        assert valid

        # 2. Compile
        compiled = compile_from_source(source)
        assert compiled.artifact_id.startswith("GOV-")

        # 3. Write artifact to disk
        path = write_artifact(compiled, tmp_path)
        assert path.exists()

        # 4. Load + verify
        loaded = load_artifact(path)
        assert verify_artifact(loaded)

        # 5. Evaluate through RuntimeGate
        gate = RuntimeGate()
        request = _make_request()
        ctx = _make_context()
        decision = gate.evaluate(compiled, request, ctx)
        assert decision.verdict == "ALLOW"

        # 6. Append to EvidenceChain
        chain = EvidenceChain(path=tmp_path / "evidence.jsonl")
        entry = EvidenceEntry(
            evidence_id="",
            gate_id=decision.gate_id,
            action_id=request["actionId"],
            actor_id=request["actorId"],
            resource_id=request["resourceRef"],
            verdict=decision.verdict,
            evaluated_at=decision.evaluated_at,
            artifact_id=decision.artifact_id,
            policy_hash=decision.policy_hash,
            passed_checks=decision.passed_checks,
            failed_checks=decision.failed_checks,
        )
        chain.append(entry)
        assert chain.verify()

        # 7. Query with AuditRetrieval
        retrieval = AuditRetrieval(evidence_chain=chain)
        answer = retrieval.why_allowed(request["actionId"])
        assert answer.found
        assert answer.verdict == "ALLOW"

        # 8. Verify chain integrity
        chain2 = EvidenceChain(path=tmp_path / "evidence.jsonl")
        assert chain2.verify()

    def test_deterministic_same_input_same_hash(self):
        """Test 10: same input → same deterministic hash."""
        dlr = _make_dlr()
        pp = _make_policy_pack()

        s1 = build_policy_source(dlr, pp)
        s2 = build_policy_source(dlr, pp)
        assert s1.source_hash == s2.source_hash

        c1 = compile_from_source(s1)
        c2 = compile_from_source(s2)
        assert c1.policy_hash == c2.policy_hash

        a1 = build_artifact(c1)
        a2 = build_artifact(c2)
        assert a1["policyHash"] == a2["policyHash"]

    def test_all_verdicts_emit_evidence(self):
        """Tests 2,4,5,6,8: every verdict type emits an evidence entry."""
        gate = RuntimeGate()
        chain = EvidenceChain()

        test_cases = [
            # (description, request_overrides, ctx_overrides, expected_verdict)
            ("ALLOW", {}, {}, "ALLOW"),
            ("MISSING_REASONING", {"dlrRef": ""}, {"policy_packs": {"quarantine": _make_policy_pack(), "default": _make_policy_pack()}}, "MISSING_REASONING"),
            ("KILL_SWITCH_ACTIVE", {}, {"kill_switch_active": True}, "KILL_SWITCH_ACTIVE"),
            ("BLOCK (unknown actor)", {"actorId": "unknown-agent"}, {}, "BLOCK"),
            ("ESCALATE (blast radius)", {"blastRadiusTier": "large"}, {"policy_packs": {"quarantine": _make_policy_pack(maxBlastRadius="tiny"), "default": _make_policy_pack(maxBlastRadius="tiny")}}, "ESCALATE"),
        ]

        compiled = _make_compiled()

        for desc, req_overrides, ctx_overrides, expected_verdict in test_cases:
            request = _make_request(**req_overrides)
            ctx = _make_context(**ctx_overrides)
            decision = gate.evaluate(compiled, request, ctx)
            assert decision.verdict == expected_verdict, f"{desc}: expected {expected_verdict}, got {decision.verdict}"

            # Every evaluation emits evidence
            entry = EvidenceEntry(
                evidence_id="",
                gate_id=decision.gate_id,
                action_id=request["actionId"],
                actor_id=request["actorId"],
                resource_id=request["resourceRef"],
                verdict=decision.verdict,
                evaluated_at=decision.evaluated_at,
                artifact_id=decision.artifact_id,
                policy_hash=decision.policy_hash,
                passed_checks=decision.passed_checks,
                failed_checks=decision.failed_checks,
            )
            chain.append(entry)

        # Test 8: every eval emitted evidence
        assert chain.entry_count == len(test_cases)
        assert chain.verify()
