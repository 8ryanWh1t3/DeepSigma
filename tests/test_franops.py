"""Tests for FranOps domain mode — 12 function handlers."""

from __future__ import annotations

import sqlite3
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC_ROOT = _REPO_ROOT / "src"
if str(_SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(_SRC_ROOT))

from core.modes.base import DomainMode, FunctionResult
from core.modes.franops import FranOps
from core.feeds.canon.workflow import CanonState, CanonWorkflow
from core.feeds.canon.retcon_executor import (
    RetconAssessment,
    assess_retcon,
    compute_propagation_targets,
    execute_retcon,
)
from core.feeds.canon.inflation_monitor import (
    InflationMetrics,
    check_inflation,
)
from core.memory_graph import MemoryGraph
from core.drift_signal import DriftSignalCollector


# ── Fixtures ─────────────────────────────────────────────────────


@pytest.fixture
def franops() -> FranOps:
    return FranOps()


@pytest.fixture
def mg() -> MemoryGraph:
    return MemoryGraph()


@pytest.fixture
def workflow() -> CanonWorkflow:
    return CanonWorkflow()


@pytest.fixture
def base_context(mg, workflow):
    return {
        "memory_graph": mg,
        "workflow": workflow,
        "canon_store": None,
        "canon_claims": [],
        "all_canon_entries": [],
        "all_claims": [],
        "now": datetime(2026, 2, 28, tzinfo=timezone.utc),
    }


# ── Registration Tests ───────────────────────────────────────────


class TestFranOpsRegistration:

    def test_domain_name(self, franops):
        assert franops.domain == "franops"

    def test_all_12_handlers_registered(self, franops):
        assert len(franops.function_ids) == 12

    def test_function_ids_well_formed(self, franops):
        for fid in franops.function_ids:
            assert fid.startswith("FRAN-F")

    def test_has_handler(self, franops):
        assert franops.has_handler("FRAN-F01")
        assert not franops.has_handler("INTEL-F01")

    def test_unknown_handler_returns_error(self, franops, base_context):
        result = franops.handle("NONEXISTENT-F99", {}, base_context)
        assert not result.success
        assert "No handler" in result.error


# ── FRAN-F01: Canon Propose ──────────────────────────────────────


class TestCanonPropose:

    def test_basic_propose(self, franops, base_context):
        event = {"payload": {"canonId": "CANON-001", "title": "Test", "claimIds": ["C1"]}}
        result = franops.handle("FRAN-F01", event, base_context)
        assert result.success
        assert result.events_emitted[0]["subtype"] == "canon_proposed"

    def test_propose_sets_workflow_state(self, franops, base_context, workflow):
        event = {"payload": {"canonId": "CANON-002", "title": "Test", "claimIds": []}}
        franops.handle("FRAN-F01", event, base_context)
        assert workflow.get_state("CANON-002") == CanonState.PROPOSED

    def test_replay_deterministic(self, franops):
        ctx1 = {"workflow": None, "canon_store": None}
        ctx2 = {"workflow": None, "canon_store": None}
        event = {"payload": {"canonId": "CANON-X", "title": "T", "claimIds": []}}
        r1 = franops.handle("FRAN-F01", event, ctx1)
        r2 = franops.handle("FRAN-F01", event, ctx2)
        assert r1.replay_hash == r2.replay_hash


# ── FRAN-F02: Canon Bless ────────────────────────────────────────


class TestCanonBless:

    def test_bless_proposed_entry(self, franops, base_context, workflow):
        workflow.set_state("CANON-001", CanonState.PROPOSED)
        event = {"payload": {"canonId": "CANON-001", "blessedBy": "admin"}}
        result = franops.handle("FRAN-F02", event, base_context)
        assert result.success
        assert result.events_emitted[0]["subtype"] == "canon_blessed"
        # After bless + auto-activate:
        assert workflow.get_state("CANON-001") == CanonState.ACTIVE

    def test_bless_wrong_state_emits_drift(self, franops, base_context, workflow):
        workflow.set_state("CANON-001", CanonState.ACTIVE)
        event = {"payload": {"canonId": "CANON-001", "blessedBy": "admin"}}
        result = franops.handle("FRAN-F02", event, base_context)
        assert result.success
        assert len(result.drift_signals) > 0
        assert len(result.events_emitted) == 0


# ── FRAN-F03: Canon Enforce ──────────────────────────────────────


class TestCanonEnforce:

    def test_all_claims_in_canon(self, franops, base_context):
        base_context["canon_claims"] = [{"claimId": "C1"}, {"claimId": "C2"}]
        event = {"payload": {"canonId": "CANON-001", "decisionClaims": ["C1", "C2"]}}
        result = franops.handle("FRAN-F03", event, base_context)
        assert result.success
        assert len(result.drift_signals) == 0
        assert result.events_emitted[0]["subtype"] == "canon_pass"

    def test_violation_detected(self, franops, base_context):
        base_context["canon_claims"] = [{"claimId": "C1"}]
        event = {"payload": {"canonId": "CANON-001", "decisionClaims": ["C1", "C-ROGUE"]}}
        result = franops.handle("FRAN-F03", event, base_context)
        assert result.success
        assert len(result.drift_signals) == 1
        assert result.events_emitted[0]["subtype"] == "canon_violation"


# ── FRAN-F04: Retcon Assess ──────────────────────────────────────


class TestRetconAssess:

    def test_assess_with_dependents(self, franops, base_context):
        event = {"payload": {
            "originalClaimId": "CLAIM-OLD",
            "dependents": ["C1", "C2", "C3"],
        }}
        result = franops.handle("FRAN-F04", event, base_context)
        assert result.success
        assert result.events_emitted[0]["subtype"] == "retcon_assessed"
        assert "retconId" in result.events_emitted[0]

    def test_assess_no_dependents(self, franops, base_context):
        event = {"payload": {"originalClaimId": "CLAIM-OLD", "dependents": []}}
        result = franops.handle("FRAN-F04", event, base_context)
        assert result.success
        assert result.events_emitted[0]["impactSeverity"] == "green"


# ── FRAN-F05: Retcon Execute ─────────────────────────────────────


class TestRetconExecute:

    def test_execute_retcon(self, franops, base_context):
        event = {"payload": {
            "retconId": "RETCON-001",
            "originalClaimId": "CLAIM-OLD",
            "newClaimId": "CLAIM-NEW",
            "reason": "correction",
        }}
        result = franops.handle("FRAN-F05", event, base_context)
        assert result.success
        assert result.events_emitted[0]["subtype"] == "retcon_executed"
        assert len(result.drift_signals) > 0

    def test_execute_updates_mg(self, franops, base_context, mg):
        event = {"payload": {
            "originalClaimId": "CLAIM-OLD",
            "newClaimId": "CLAIM-NEW",
        }}
        result = franops.handle("FRAN-F05", event, base_context)
        assert len(result.mg_updates) > 0

    def test_execute_updates_workflow(self, franops, base_context, workflow):
        workflow.set_state("CANON-CLAIM-OLD", CanonState.ACTIVE)
        event = {"payload": {
            "originalClaimId": "CLAIM-OLD",
            "newClaimId": "CLAIM-NEW",
        }}
        franops.handle("FRAN-F05", event, base_context)
        assert workflow.get_state("CANON-CLAIM-OLD") == CanonState.RETCONNED


# ── FRAN-F06: Retcon Propagate ───────────────────────────────────


class TestRetconPropagate:

    def test_propagate_with_targets(self, franops, base_context):
        event = {"payload": {
            "retconId": "RETCON-001",
            "originalClaimId": "CLAIM-OLD",
            "affectedClaimIds": ["C1", "C2"],
            "affectedCanonIds": ["CANON-1"],
        }}
        result = franops.handle("FRAN-F06", event, base_context)
        assert result.success
        assert result.events_emitted[0]["subtype"] == "retcon_cascade"
        assert len(result.drift_signals) > 0

    def test_propagate_no_targets(self, franops, base_context):
        event = {"payload": {
            "retconId": "RETCON-001",
            "originalClaimId": "CLAIM-OLD",
            "affectedClaimIds": [],
            "affectedCanonIds": [],
        }}
        result = franops.handle("FRAN-F06", event, base_context)
        assert result.success
        assert len(result.drift_signals) == 0


# ── FRAN-F07: Inflation Monitor ──────────────────────────────────


class TestInflationMonitor:

    def test_breach_detected(self, franops, base_context):
        event = {"payload": {
            "domain": "test",
            "claimCount": 100,
            "contradictionDensity": 0.0,
            "avgClaimAgeDays": 0,
            "supersedesDepth": 0,
        }}
        result = franops.handle("FRAN-F07", event, base_context)
        assert result.success
        assert len(result.drift_signals) > 0
        assert result.events_emitted[0]["subtype"] == "canon_inflation"

    def test_no_breach(self, franops, base_context):
        event = {"payload": {
            "domain": "test",
            "claimCount": 5,
            "contradictionDensity": 0.01,
            "avgClaimAgeDays": 1,
            "supersedesDepth": 1,
        }}
        result = franops.handle("FRAN-F07", event, base_context)
        assert result.success
        assert len(result.drift_signals) == 0
        assert len(result.events_emitted) == 0

    def test_multiple_breaches(self, franops, base_context):
        event = {"payload": {
            "domain": "test",
            "claimCount": 100,
            "contradictionDensity": 0.5,
            "avgClaimAgeDays": 60,
            "supersedesDepth": 10,
        }}
        result = franops.handle("FRAN-F07", event, base_context)
        assert len(result.drift_signals) == 4


# ── FRAN-F08: Canon Expire ───────────────────────────────────────


class TestCanonExpire:

    def test_expired_entry(self, franops, base_context, workflow):
        workflow.set_state("CANON-OLD", CanonState.ACTIVE)
        base_context["all_canon_entries"] = [{
            "canonId": "CANON-OLD",
            "data": {"canonId": "CANON-OLD", "expiresAt": "2020-01-01T00:00:00Z"},
        }]
        result = franops.handle("FRAN-F08", {}, base_context)
        assert result.success
        assert len(result.drift_signals) > 0
        assert workflow.get_state("CANON-OLD") == CanonState.EXPIRED

    def test_no_expired(self, franops, base_context):
        base_context["all_canon_entries"] = [{
            "canonId": "CANON-FRESH",
            "data": {"canonId": "CANON-FRESH", "expiresAt": "2030-01-01T00:00:00Z"},
        }]
        result = franops.handle("FRAN-F08", {}, base_context)
        assert len(result.drift_signals) == 0

    def test_no_expiry_field(self, franops, base_context):
        base_context["all_canon_entries"] = [{
            "canonId": "CANON-NONE",
            "data": {"canonId": "CANON-NONE"},
        }]
        result = franops.handle("FRAN-F08", {}, base_context)
        assert len(result.drift_signals) == 0


# ── FRAN-F09: Canon Supersede ────────────────────────────────────


class TestCanonSupersede:

    def test_supersede(self, franops, base_context, workflow):
        workflow.set_state("CANON-OLD", CanonState.ACTIVE)
        event = {"payload": {
            "canonId": "CANON-OLD",
            "supersededBy": "CANON-NEW",
            "claimIds": ["C-NEW"],
        }}
        result = franops.handle("FRAN-F09", event, base_context)
        assert result.success
        assert result.events_emitted[0]["subtype"] == "canon_superseded"
        assert workflow.get_state("CANON-OLD") == CanonState.SUPERSEDED

    def test_supersede_updates_mg(self, franops, base_context, mg):
        event = {"payload": {
            "canonId": "CANON-OLD",
            "supersededBy": "CANON-NEW",
        }}
        result = franops.handle("FRAN-F09", event, base_context)
        assert len(result.mg_updates) > 0


# ── FRAN-F10: Canon Scope Check ──────────────────────────────────


class TestCanonScopeCheck:

    def test_valid_scope(self, franops, base_context):
        event = {"payload": {"canonId": "CANON-001", "scope": {"domain": "intelops"}}}
        result = franops.handle("FRAN-F10", event, base_context)
        assert result.success
        assert len(result.drift_signals) == 0
        assert result.events_emitted[0]["subtype"] == "scope_pass"

    def test_invalid_scope(self, franops, base_context):
        event = {"payload": {"canonId": "CANON-001", "scope": {"domain": "unknown_domain"}}}
        result = franops.handle("FRAN-F10", event, base_context)
        assert result.success
        assert len(result.drift_signals) > 0
        assert result.events_emitted[0]["subtype"] == "scope_violation"


# ── FRAN-F11: Canon Drift Detect ─────────────────────────────────


class TestCanonDriftDetect:

    def test_orphaned_claims(self, franops, base_context):
        base_context["all_canon_entries"] = [{
            "canonId": "CANON-001",
            "data": {"canonId": "CANON-001", "claimIds": ["C1", "C-GHOST"]},
        }]
        base_context["all_claims"] = [{"claimId": "C1"}]
        result = franops.handle("FRAN-F11", {}, base_context)
        assert result.success
        assert len(result.drift_signals) > 0

    def test_no_orphans(self, franops, base_context):
        base_context["all_canon_entries"] = [{
            "canonId": "CANON-001",
            "data": {"canonId": "CANON-001", "claimIds": ["C1"]},
        }]
        base_context["all_claims"] = [{"claimId": "C1"}]
        result = franops.handle("FRAN-F11", {}, base_context)
        assert len(result.drift_signals) == 0


# ── FRAN-F12: Canon Rollback ─────────────────────────────────────


class TestCanonRollback:

    def test_rollback_not_found(self, franops, base_context):
        event = {"payload": {"canonId": "CANON-001", "targetVersion": "0.0.1"}}
        result = franops.handle("FRAN-F12", event, base_context)
        assert result.success
        assert len(result.drift_signals) > 0
        assert "not found" in result.drift_signals[0]["notes"]

    def test_rollback_with_store(self, franops, base_context, workflow):
        """Test rollback with a real CanonStore."""
        with tempfile.NamedTemporaryFile(suffix=".db") as f:
            from core.feeds.canon.store import CanonStore
            store = CanonStore(f.name)

            # Add two versions
            store.add({"canonId": "CANON-V1", "version": "1.0.0", "title": "Original"})
            store.add({
                "canonId": "CANON-V2", "version": "2.0.0",
                "title": "Updated", "supersedes": "CANON-V1",
            })

            workflow.set_state("CANON-V2", CanonState.ACTIVE)
            base_context["canon_store"] = store

            event = {"payload": {"canonId": "CANON-V2", "targetVersion": "1.0.0"}}
            result = franops.handle("FRAN-F12", event, base_context)
            assert result.success
            assert result.events_emitted[0]["subtype"] == "canon_rolled_back"
            assert workflow.get_state("CANON-V2") == CanonState.SUPERSEDED
            assert workflow.get_state("CANON-V1") == CanonState.ACTIVE

            store.close()


# ── Support Module Tests ─────────────────────────────────────────


class TestCanonWorkflow:

    def test_transition_valid(self):
        wf = CanonWorkflow()
        wf.set_state("C1", CanonState.PROPOSED)
        assert wf.transition("C1", CanonState.BLESSED)
        assert wf.get_state("C1") == CanonState.BLESSED

    def test_transition_invalid(self):
        wf = CanonWorkflow()
        wf.set_state("C1", CanonState.PROPOSED)
        assert not wf.transition("C1", CanonState.ACTIVE)  # must go through BLESSED
        assert wf.get_state("C1") == CanonState.PROPOSED

    def test_terminal_state(self):
        wf = CanonWorkflow()
        wf.set_state("C1", CanonState.SUPERSEDED)
        assert wf.is_terminal("C1")

    def test_active_entries(self):
        wf = CanonWorkflow()
        wf.set_state("C1", CanonState.ACTIVE)
        wf.set_state("C2", CanonState.PROPOSED)
        wf.set_state("C3", CanonState.ACTIVE)
        assert sorted(wf.active_entries()) == ["C1", "C3"]


class TestRetconExecutorModule:

    def test_assess_with_dependents(self):
        a = assess_retcon("CLAIM-1", ["C2", "C3"])
        assert a.original_claim_id == "CLAIM-1"
        assert a.impact_severity == "yellow"

    def test_assess_high_impact(self):
        deps = [f"C{i}" for i in range(10)]
        a = assess_retcon("CLAIM-1", deps)
        assert a.impact_severity == "red"

    def test_execute(self):
        a = assess_retcon("CLAIM-1", ["C2"])
        record = execute_retcon(a, "CLAIM-NEW", "test reason")
        assert record["sealed"]
        assert record["newClaimId"] == "CLAIM-NEW"

    def test_propagation_targets(self):
        a = RetconAssessment("R1", "CLAIM-1", ["C2"], ["CANON-1"], "yellow")
        targets = compute_propagation_targets(a)
        assert len(targets) == 2
        types = {t["type"] for t in targets}
        assert "claim_review" in types
        assert "canon_review" in types


class TestInflationMonitorModule:

    def test_no_breaches(self):
        m = InflationMetrics(domain="test", claim_count=5)
        assert len(check_inflation(m)) == 0

    def test_claim_count_breach(self):
        m = InflationMetrics(domain="test", claim_count=100)
        signals = check_inflation(m)
        assert len(signals) == 1
        assert signals[0]["driftType"] == "canon_inflation"

    def test_custom_thresholds(self):
        m = InflationMetrics(domain="test", claim_count=10)
        signals = check_inflation(m, {"claim_count": 5})
        assert len(signals) == 1


# ── Integration: Full Canon Lifecycle ────────────────────────────


class TestCanonLifecycle:
    """End-to-end: propose -> bless -> enforce -> retcon -> propagate."""

    def test_full_lifecycle(self, franops):
        wf = CanonWorkflow()
        mg = MemoryGraph()
        ctx = {
            "memory_graph": mg,
            "workflow": wf,
            "canon_store": None,
            "canon_claims": [{"claimId": "C1"}],
            "all_canon_entries": [],
            "all_claims": [{"claimId": "C1"}],
            "now": datetime(2026, 2, 28, tzinfo=timezone.utc),
        }

        # Step 1: Propose
        r1 = franops.handle("FRAN-F01", {"payload": {
            "canonId": "CANON-LC", "title": "Lifecycle test", "claimIds": ["C1"],
        }}, ctx)
        assert r1.success
        assert wf.get_state("CANON-LC") == CanonState.PROPOSED

        # Step 2: Bless
        r2 = franops.handle("FRAN-F02", {"payload": {
            "canonId": "CANON-LC", "blessedBy": "admin",
        }}, ctx)
        assert r2.success
        assert wf.get_state("CANON-LC") == CanonState.ACTIVE

        # Step 3: Enforce (should pass)
        r3 = franops.handle("FRAN-F03", {"payload": {
            "canonId": "CANON-LC", "decisionClaims": ["C1"],
        }}, ctx)
        assert r3.success
        assert r3.events_emitted[0]["subtype"] == "canon_pass"

        # Step 4: Retcon assess
        r4 = franops.handle("FRAN-F04", {"payload": {
            "originalClaimId": "C1", "dependents": ["C2"],
        }}, ctx)
        assert r4.success

        # Step 5: Retcon execute
        r5 = franops.handle("FRAN-F05", {"payload": {
            "originalClaimId": "C1", "newClaimId": "C1-v2",
            "reason": "correction",
        }}, ctx)
        assert r5.success

        # Step 6: Propagate
        r6 = franops.handle("FRAN-F06", {"payload": {
            "retconId": "RETCON-TEST", "originalClaimId": "C1",
            "affectedClaimIds": ["C2"], "affectedCanonIds": [],
        }}, ctx)
        assert r6.success

        # All replay hashes computed
        assert all(r.replay_hash.startswith("sha256:") for r in [r1, r2, r3, r4, r5, r6])
