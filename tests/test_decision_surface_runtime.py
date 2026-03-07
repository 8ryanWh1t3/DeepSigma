"""Tests for DecisionSurface runtime, claim-event engine, and evaluation."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC_ROOT = _REPO_ROOT / "src"
if str(_SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(_SRC_ROOT))

from core.decision_surface.models import (
    Assumption,
    Claim,
    ClaimStatus,
    DriftSignal,
    Event,
    EvaluationResult,
    PatchRecommendation,
)
from core.decision_surface.claim_event_engine import (
    build_memory_graph_update,
    build_patch_recommendation,
    compute_blast_radius,
    detect_contradictions,
    detect_expired_assumptions,
    evaluate,
    match_events_to_claims,
)
from core.decision_surface.runtime import DecisionSurface


# ── ClaimEventEngine ────────────────────────────────────────────────


class TestMatchEventsToClaims:

    def test_basic_matching(self):
        claims = [Claim(claim_id="C1", statement="X")]
        events = [Event(event_id="E1", event_type="ok", claim_refs=["C1"])]
        matches = match_events_to_claims(claims, events)
        assert matches["C1"] == ["E1"]

    def test_no_matches(self):
        claims = [Claim(claim_id="C1", statement="X")]
        events = [Event(event_id="E1", event_type="ok", claim_refs=["C99"])]
        matches = match_events_to_claims(claims, events)
        assert matches["C1"] == []

    def test_multiple_events_per_claim(self):
        claims = [Claim(claim_id="C1", statement="X")]
        events = [
            Event(event_id="E1", event_type="a", claim_refs=["C1"]),
            Event(event_id="E2", event_type="b", claim_refs=["C1"]),
        ]
        matches = match_events_to_claims(claims, events)
        assert len(matches["C1"]) == 2


class TestDetectContradictions:

    def test_contradiction_detected(self):
        claims = [Claim(claim_id="C1", statement="X")]
        events = [
            Event(event_id="E1", event_type="approved", claim_refs=["C1"]),
            Event(event_id="E2", event_type="denied", claim_refs=["C1"]),
        ]
        signals = detect_contradictions(claims, events)
        assert len(signals) == 1
        assert signals[0].drift_type == "contradiction"
        assert signals[0].severity == "red"

    def test_no_contradiction(self):
        claims = [Claim(claim_id="C1", statement="X")]
        events = [
            Event(event_id="E1", event_type="approved", claim_refs=["C1"]),
            Event(event_id="E2", event_type="confirmed", claim_refs=["C1"]),
        ]
        signals = detect_contradictions(claims, events)
        assert len(signals) == 0


class TestDetectExpiredAssumptions:

    def test_expired_assumption(self):
        claims = [Claim(claim_id="C1", statement="X")]
        assumptions = [
            Assumption(assumption_id="A1", statement="old",
                       expires_at="2020-01-01T00:00:00Z",
                       linked_claim_ids=["C1"]),
        ]
        signals = detect_expired_assumptions(claims, assumptions)
        assert len(signals) == 1
        assert signals[0].drift_type == "expired_assumption"

    def test_active_assumption(self):
        claims = [Claim(claim_id="C1", statement="X")]
        assumptions = [
            Assumption(assumption_id="A1", statement="future",
                       expires_at="2099-12-31T23:59:59Z",
                       linked_claim_ids=["C1"]),
        ]
        signals = detect_expired_assumptions(claims, assumptions)
        assert len(signals) == 0


class TestComputeBlastRadius:

    def test_shared_evidence(self):
        c1 = Claim(claim_id="C1", statement="X", evidence_refs=["ev-1", "ev-2"])
        c2 = Claim(claim_id="C2", statement="Y", evidence_refs=["ev-2", "ev-3"])
        c3 = Claim(claim_id="C3", statement="Z", evidence_refs=["ev-4"])
        assert compute_blast_radius(c1, [c1, c2, c3]) == 1

    def test_no_shared_evidence(self):
        c1 = Claim(claim_id="C1", statement="X", evidence_refs=["ev-1"])
        c2 = Claim(claim_id="C2", statement="Y", evidence_refs=["ev-2"])
        assert compute_blast_radius(c1, [c1, c2]) == 0

    def test_empty_evidence(self):
        c1 = Claim(claim_id="C1", statement="X")
        assert compute_blast_radius(c1, [c1]) == 0


class TestBuildPatchRecommendation:

    def test_contradiction_action(self):
        sig = DriftSignal(signal_id="S1", drift_type="contradiction")
        patch = build_patch_recommendation(sig)
        assert patch.action == "investigate_contradiction"

    def test_expired_assumption_action(self):
        sig = DriftSignal(signal_id="S1", drift_type="expired_assumption")
        patch = build_patch_recommendation(sig)
        assert patch.action == "review_assumption"

    def test_default_action(self):
        sig = DriftSignal(signal_id="S1", drift_type="unknown_type")
        patch = build_patch_recommendation(sig)
        assert patch.action == "review_claim"


class TestEvaluate:

    def test_satisfied_claim(self):
        claims = [Claim(claim_id="C1", statement="X")]
        events = [Event(event_id="E1", event_type="ok", claim_refs=["C1"])]
        result = evaluate(claims, events)
        assert result.claims_evaluated == 1
        assert result.satisfied == 1
        assert claims[0].status == ClaimStatus.SATISFIED.value

    def test_pending_claim(self):
        claims = [Claim(claim_id="C1", statement="X")]
        events = []
        result = evaluate(claims, events)
        assert result.pending == 1

    def test_drifted_from_contradiction(self):
        claims = [Claim(claim_id="C1", statement="X")]
        events = [
            Event(event_id="E1", event_type="approved", claim_refs=["C1"]),
            Event(event_id="E2", event_type="denied", claim_refs=["C1"]),
        ]
        result = evaluate(claims, events)
        assert result.drifted == 1
        assert len(result.drift_signals) == 1
        assert len(result.patches) == 1

    def test_at_risk_low_confidence(self):
        claims = [Claim(claim_id="C1", statement="X", confidence=0.3)]
        events = [Event(event_id="E1", event_type="ok", claim_refs=["C1"])]
        result = evaluate(claims, events)
        assert result.at_risk == 1

    def test_memory_graph_update_populated(self):
        claims = [Claim(claim_id="C1", statement="X")]
        events = [Event(event_id="E1", event_type="ok", claim_refs=["C1"])]
        result = evaluate(claims, events)
        assert result.memory_graph_update is not None
        assert len(result.memory_graph_update.nodes) >= 1


# ── DecisionSurface Runtime ─────────────────────────────────────────


class TestDecisionSurfaceRuntime:

    def test_from_surface_notebook(self):
        ds = DecisionSurface.from_surface("notebook")
        assert ds.surface_name == "notebook"

    def test_from_surface_cli(self):
        ds = DecisionSurface.from_surface("cli")
        assert ds.surface_name == "cli"

    def test_from_surface_vantage(self):
        ds = DecisionSurface.from_surface("vantage")
        assert ds.surface_name == "vantage"

    def test_from_surface_unknown(self):
        with pytest.raises(ValueError, match="Unknown surface"):
            DecisionSurface.from_surface("nonexistent")

    def test_ingest_and_evaluate(self):
        ds = DecisionSurface.from_surface("notebook")
        claims = [Claim(claim_id="C1", statement="Test claim")]
        events = [Event(event_id="E1", event_type="ok", claim_refs=["C1"])]
        ds.ingest(claims=claims, events=events)
        result = ds.evaluate()
        assert result.claims_evaluated == 1
        assert result.satisfied == 1

    def test_seal_produces_hash(self):
        ds = DecisionSurface.from_surface("notebook")
        claims = [Claim(claim_id="C1", statement="Test claim")]
        ds.ingest(claims=claims)
        artifact = ds.seal()
        assert artifact.seal_hash.startswith("sha256:")
        assert artifact.sealed_at is not None

    def test_get_adapter(self):
        ds = DecisionSurface.from_surface("notebook")
        adapter = ds.get_adapter()
        assert adapter.surface_name == "notebook"


# ── EvaluationResult ────────────────────────────────────────────────


class TestEvaluationResult:

    def test_counts_correct(self):
        claims = [
            Claim(claim_id="C1", statement="OK"),
            Claim(claim_id="C2", statement="Pending"),
            Claim(claim_id="C3", statement="Low conf", confidence=0.3),
        ]
        events = [
            Event(event_id="E1", event_type="ok", claim_refs=["C1"]),
            Event(event_id="E3", event_type="ok", claim_refs=["C3"]),
        ]
        result = evaluate(claims, events)
        assert result.claims_evaluated == 3
        assert result.satisfied == 1
        assert result.at_risk == 1
        assert result.pending == 1

    def test_drift_and_patches_populated(self):
        claims = [Claim(claim_id="C1", statement="X")]
        events = [
            Event(event_id="E1", event_type="approved", claim_refs=["C1"]),
            Event(event_id="E2", event_type="denied", claim_refs=["C1"]),
        ]
        result = evaluate(claims, events)
        assert len(result.drift_signals) >= 1
        assert len(result.patches) >= 1
        assert result.patches[0].drift_signal_id == result.drift_signals[0].signal_id
