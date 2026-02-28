"""Tests for IntelOps domain mode — 12 function handlers."""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC_ROOT = _REPO_ROOT / "src"
if str(_SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(_SRC_ROOT))

from core.modes.base import DomainMode, FunctionResult
from core.modes.intelops import IntelOps
from core.memory_graph import MemoryGraph
from core.drift_signal import DriftSignalCollector


# ── Fixtures ─────────────────────────────────────────────────────


@pytest.fixture
def intelops() -> IntelOps:
    return IntelOps()


@pytest.fixture
def mg() -> MemoryGraph:
    return MemoryGraph()


@pytest.fixture
def ds() -> DriftSignalCollector:
    return DriftSignalCollector()


@pytest.fixture
def base_context(mg, ds):
    return {
        "memory_graph": mg,
        "drift_collector": ds,
        "canon_store": None,
        "canon_claims": [],
        "now": datetime(2026, 2, 28, tzinfo=timezone.utc),
    }


@pytest.fixture
def claim_payload():
    return {
        "claimId": "CLAIM-TEST-001",
        "statement": "Test claim statement",
        "confidence": {"score": 0.92},
        "statusLight": "green",
        "sources": [{"ref": "test-source", "type": "document"}],
        "evidence": [{"ref": "test-evidence", "type": "metric", "method": "test"}],
        "owner": "test-owner",
        "timestampCreated": "2026-02-27T10:00:00Z",
        "version": "1.0.0",
        "halfLife": {"value": 24, "unit": "hours"},
        "graph": {},
        "seal": {"hash": "sha256:test", "sealedAt": "2026-02-27T10:00:01Z", "version": 1},
    }


# ── Registration Tests ───────────────────────────────────────────


class TestIntelOpsRegistration:

    def test_domain_name(self, intelops):
        assert intelops.domain == "intelops"

    def test_all_12_handlers_registered(self, intelops):
        assert len(intelops.function_ids) == 12

    def test_function_ids_well_formed(self, intelops):
        for fid in intelops.function_ids:
            assert fid.startswith("INTEL-F")

    def test_has_handler(self, intelops):
        assert intelops.has_handler("INTEL-F01")
        assert not intelops.has_handler("FRAN-F01")

    def test_unknown_handler_returns_error(self, intelops, base_context):
        result = intelops.handle("NONEXISTENT-F99", {}, base_context)
        assert not result.success
        assert "No handler" in result.error


# ── INTEL-F01: Claim Ingest ──────────────────────────────────────


class TestClaimIngest:

    def test_basic_ingest(self, intelops, base_context, claim_payload):
        result = intelops.handle("INTEL-F01", {"payload": claim_payload}, base_context)
        assert result.success
        assert result.function_id == "INTEL-F01"
        assert len(result.events_emitted) == 1
        assert result.events_emitted[0]["subtype"] == "claim_accepted"

    def test_ingest_updates_mg(self, intelops, base_context, claim_payload, mg):
        base_context["memory_graph"] = mg
        result = intelops.handle("INTEL-F01", {"payload": claim_payload}, base_context)
        assert len(result.mg_updates) > 0

    def test_replay_hash_computed(self, intelops, base_context, claim_payload):
        result = intelops.handle("INTEL-F01", {"payload": claim_payload}, base_context)
        assert result.replay_hash.startswith("sha256:")

    def test_replay_deterministic(self, intelops, claim_payload):
        ctx1 = {"memory_graph": None, "canon_store": None}
        ctx2 = {"memory_graph": None, "canon_store": None}
        r1 = intelops.handle("INTEL-F01", {"payload": claim_payload}, ctx1)
        r2 = intelops.handle("INTEL-F01", {"payload": claim_payload}, ctx2)
        assert r1.replay_hash == r2.replay_hash


# ── INTEL-F02: Claim Validate ────────────────────────────────────


class TestClaimValidate:

    def test_valid_claim_no_issues(self, intelops, base_context, claim_payload):
        base_context["claims"] = {"CLAIM-TEST-001": claim_payload}
        result = intelops.handle(
            "INTEL-F02",
            {"payload": {"claimId": "CLAIM-TEST-001"}},
            base_context,
        )
        assert result.success
        assert len(result.drift_signals) == 0
        assert any(e["subtype"] == "claim_valid" for e in result.events_emitted)

    def test_contradiction_detected(self, intelops, base_context, claim_payload):
        # Set up contradiction
        contradiction_claim = dict(claim_payload)
        contradiction_claim["graph"] = {"contradicts": ["CANON-EXISTING"]}
        base_context["claims"] = {"CLAIM-TEST-001": contradiction_claim}
        base_context["canon_claims"] = [{"claimId": "CANON-EXISTING"}]

        result = intelops.handle(
            "INTEL-F02",
            {"payload": {"claimId": "CLAIM-TEST-001"}},
            base_context,
        )
        assert result.success
        assert len(result.drift_signals) > 0
        assert any(e["subtype"] == "claim_contradiction" for e in result.events_emitted)

    def test_expired_claim(self, intelops, base_context, claim_payload):
        expired_claim = dict(claim_payload)
        expired_claim["timestampCreated"] = "2020-01-01T00:00:00Z"
        expired_claim["halfLife"] = {"value": 1, "unit": "hours"}
        base_context["claims"] = {"CLAIM-TEST-001": expired_claim}

        result = intelops.handle(
            "INTEL-F02",
            {"payload": {"claimId": "CLAIM-TEST-001"}},
            base_context,
        )
        assert result.success
        assert len(result.drift_signals) > 0


# ── INTEL-F03: Claim Drift Detect ────────────────────────────────


class TestClaimDriftDetect:

    def test_drift_recorded(self, intelops, base_context, ds):
        base_context["drift_collector"] = ds
        signal = {
            "driftId": "DS-test-001",
            "driftType": "authority_mismatch",
            "severity": "red",
            "detectedAt": "2026-02-28T00:00:00Z",
            "fingerprint": {"key": "test", "version": "1"},
        }
        result = intelops.handle(
            "INTEL-F03",
            {"payload": {"drift_signals": [signal]}},
            base_context,
        )
        assert result.success
        assert ds.event_count > 0


# ── INTEL-F04: Claim Patch Recommend ─────────────────────────────


class TestClaimPatchRecommend:

    def test_patch_generated(self, intelops, base_context):
        result = intelops.handle(
            "INTEL-F04",
            {"payload": {"driftType": "freshness", "fingerprint": {"key": "test", "version": "1"}}},
            base_context,
        )
        assert result.success
        assert len(result.events_emitted) == 1
        assert result.events_emitted[0]["subtype"] == "patch_recommended"
        assert result.events_emitted[0]["patch"]["patchType"] == "ttl_change"


# ── INTEL-F05: Claim MG Update ───────────────────────────────────


class TestClaimMGUpdate:

    def test_claim_added_to_mg(self, intelops, base_context, mg, claim_payload):
        base_context["memory_graph"] = mg
        result = intelops.handle(
            "INTEL-F05",
            {"payload": claim_payload},
            base_context,
        )
        assert result.success


# ── INTEL-F06: Claim Canon Promote ───────────────────────────────


class TestClaimCanonPromote:

    def test_high_confidence_promotes(self, intelops, base_context, claim_payload):
        result = intelops.handle(
            "INTEL-F06",
            {"payload": claim_payload},
            base_context,
        )
        assert result.success
        assert any(e["subtype"] == "canon_promoted" for e in result.events_emitted)

    def test_low_confidence_rejects(self, intelops, base_context):
        low_conf = {"claimId": "CLAIM-LOW", "confidence": {"score": 0.3}}
        result = intelops.handle("INTEL-F06", {"payload": low_conf}, base_context)
        assert result.success
        assert len(result.events_emitted) == 0


# ── INTEL-F07: Claim Authority Check ────────────────────────────


class TestClaimAuthorityCheck:

    def test_blessed_passes(self, intelops, base_context):
        base_context["blessed_claims"] = {"CLAIM-001"}
        event = {"payload": {"claims": {"action": ["CLAIM-001"]}}}
        result = intelops.handle("INTEL-F07", event, base_context)
        assert result.success
        assert len(result.drift_signals) == 0

    def test_unblessed_fails(self, intelops, base_context):
        base_context["blessed_claims"] = set()
        event = {"payload": {"claims": {"action": ["CLAIM-ROGUE"]}}}
        result = intelops.handle("INTEL-F07", event, base_context)
        assert result.success
        assert len(result.drift_signals) > 0
        assert result.drift_signals[0]["driftType"] == "authority_mismatch"


# ── INTEL-F08: Claim Evidence Verify ─────────────────────────────


class TestClaimEvidenceVerify:

    def test_all_evidence_present(self, intelops, base_context):
        base_context["manifest_artifacts"] = {"ev-001", "ev-002"}
        event = {"payload": {"evidenceRefs": ["ev-001", "ev-002"]}}
        result = intelops.handle("INTEL-F08", event, base_context)
        assert result.success
        assert len(result.drift_signals) == 0

    def test_missing_evidence(self, intelops, base_context):
        base_context["manifest_artifacts"] = {"ev-001"}
        event = {"payload": {"evidenceRefs": ["ev-001", "ev-missing"]}}
        result = intelops.handle("INTEL-F08", event, base_context)
        assert len(result.drift_signals) > 0


# ── INTEL-F09: Claim Triage ──────────────────────────────────────


class TestClaimTriage:

    def test_triage(self, intelops, base_context):
        result = intelops.handle(
            "INTEL-F09",
            {"payload": {"severity": "red", "driftType": "authority_mismatch"}},
            base_context,
        )
        assert result.success
        assert result.events_emitted[0]["subtype"] == "triaged"


# ── INTEL-F10: Claim Supersede ───────────────────────────────────


class TestClaimSupersede:

    def test_supersede(self, intelops, base_context):
        event = {"payload": {"originalClaimId": "CLAIM-OLD", "newClaimId": "CLAIM-NEW"}}
        result = intelops.handle("INTEL-F10", event, base_context)
        assert result.success
        assert result.events_emitted[0]["subtype"] == "claim_superseded"


# ── INTEL-F11: Claim Half-Life Check ─────────────────────────────


class TestClaimHalfLifeCheck:

    def test_finds_expired_claims(self, intelops, base_context):
        expired = {
            "claimId": "CLAIM-EXPIRED",
            "timestampCreated": "2020-01-01T00:00:00Z",
            "halfLife": {"value": 1, "unit": "hours"},
        }
        base_context["all_claims"] = [expired]
        result = intelops.handle("INTEL-F11", {}, base_context)
        assert result.success
        assert len(result.drift_signals) > 0

    def test_no_expired_claims(self, intelops, base_context):
        fresh = {
            "claimId": "CLAIM-FRESH",
            "timestampCreated": "2026-02-28T00:00:00Z",
            "halfLife": {"value": 24, "unit": "hours"},
        }
        base_context["all_claims"] = [fresh]
        result = intelops.handle("INTEL-F11", {}, base_context)
        assert len(result.drift_signals) == 0


# ── INTEL-F12: Claim Confidence Recalc ───────────────────────────


class TestClaimConfidenceRecalc:

    def test_decay_with_contradictions(self, intelops, base_context, claim_payload):
        base_context["claims"] = {"CLAIM-TEST-001": claim_payload}
        base_context["contradiction_count"] = 3
        base_context["evidence_age_days"] = 10

        result = intelops.handle(
            "INTEL-F12",
            {"payload": {"claimId": "CLAIM-TEST-001"}},
            base_context,
        )
        assert result.success
        assert len(result.drift_signals) > 0
        # Old 0.92 - (3*0.1 + 10*0.01) = 0.92 - 0.4 = 0.52
        assert result.events_emitted[0]["newScore"] < 0.92

    def test_no_decay(self, intelops, base_context, claim_payload):
        base_context["claims"] = {"CLAIM-TEST-001": claim_payload}
        base_context["contradiction_count"] = 0
        base_context["evidence_age_days"] = 0

        result = intelops.handle(
            "INTEL-F12",
            {"payload": {"claimId": "CLAIM-TEST-001"}},
            base_context,
        )
        assert result.success
        assert len(result.drift_signals) == 0


# ── Integration: Full Atomic Loop ────────────────────────────────


class TestAtomicLoop:
    """End-to-end: ingest -> validate -> drift detect -> patch -> MG update."""

    def test_full_loop(self, intelops, claim_payload):
        mg = MemoryGraph()
        ds = DriftSignalCollector()
        ctx = {
            "memory_graph": mg,
            "drift_collector": ds,
            "canon_store": None,
            "canon_claims": [],
            "claims": {},
            "now": datetime(2026, 2, 28, tzinfo=timezone.utc),
        }

        # Step 1: Ingest
        r1 = intelops.handle("INTEL-F01", {"payload": claim_payload}, ctx)
        assert r1.success

        # Step 2: Validate
        ctx["claims"] = {"CLAIM-TEST-001": claim_payload}
        r2 = intelops.handle("INTEL-F02", {"payload": {"claimId": "CLAIM-TEST-001"}}, ctx)
        assert r2.success

        # Step 3: Drift detect (if any signals)
        if r2.drift_signals:
            r3 = intelops.handle(
                "INTEL-F03",
                {"payload": {"drift_signals": r2.drift_signals}},
                ctx,
            )
            assert r3.success

        # Step 4: Patch recommend
        r4 = intelops.handle(
            "INTEL-F04",
            {"payload": {"driftType": "freshness", "fingerprint": {"key": "test", "version": "1"}}},
            ctx,
        )
        assert r4.success

        # Step 5: MG update
        r5 = intelops.handle("INTEL-F05", {"payload": claim_payload}, ctx)
        assert r5.success

        # All steps completed
        assert all(r.replay_hash.startswith("sha256:") for r in [r1, r2, r4, r5])
