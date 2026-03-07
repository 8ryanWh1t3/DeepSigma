"""Tests for NotebookAdapter and CLI adapter end-to-end lifecycle."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC_ROOT = _REPO_ROOT / "src"
if str(_SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(_SRC_ROOT))

from core.decision_surface.models import (
    Claim,
    DriftSignal,
    EvaluationResult,
    Event,
    Evidence,
    PatchRecommendation,
)
from core.decision_surface.notebook_adapter import NotebookAdapter
from core.decision_surface.cli_adapter import CLIAdapter
from core.decision_surface.runtime import DecisionSurface


# ── NotebookAdapter ─────────────────────────────────────────────────


class TestNotebookAdapter:

    def test_ingest_claims(self):
        adapter = NotebookAdapter()
        claims = [Claim(claim_id="C1", statement="X")]
        adapter.ingest_claims(claims)
        assert len(adapter.get_claims()) == 1

    def test_ingest_events(self):
        adapter = NotebookAdapter()
        events = [Event(event_id="E1", event_type="ok")]
        adapter.ingest_events(events)
        assert len(adapter.get_events()) == 1

    def test_get_claims_returns_copy(self):
        adapter = NotebookAdapter()
        adapter.ingest_claims([Claim(claim_id="C1", statement="X")])
        result = adapter.get_claims()
        result.clear()
        assert len(adapter.get_claims()) == 1

    def test_get_events_returns_copy(self):
        adapter = NotebookAdapter()
        adapter.ingest_events([Event(event_id="E1", event_type="ok")])
        result = adapter.get_events()
        result.clear()
        assert len(adapter.get_events()) == 1

    def test_get_evidence_initially_empty(self):
        adapter = NotebookAdapter()
        assert adapter.get_evidence() == []

    def test_store_drift_signals(self):
        adapter = NotebookAdapter()
        signals = [DriftSignal(signal_id="S1", drift_type="test")]
        adapter.store_drift_signals(signals)
        assert len(adapter._drift_signals) == 1

    def test_store_patches(self):
        adapter = NotebookAdapter()
        patches = [PatchRecommendation(patch_id="P1", drift_signal_id="S1")]
        adapter.store_patches(patches)
        assert len(adapter._patches) == 1

    def test_store_evaluation_result(self):
        adapter = NotebookAdapter()
        result = EvaluationResult(claims_evaluated=3, satisfied=2)
        adapter.store_evaluation_result(result)
        assert adapter._evaluation_result is not None
        assert adapter._evaluation_result.satisfied == 2


# ── NotebookAdapter End-to-End ──────────────────────────────────────


class TestNotebookEndToEnd:

    def test_full_lifecycle(self):
        ds = DecisionSurface.from_surface("notebook")
        claims = [
            Claim(claim_id="C1", statement="System healthy"),
            Claim(claim_id="C2", statement="No threats"),
        ]
        events = [
            Event(event_id="E1", event_type="confirmed", claim_refs=["C1"]),
        ]
        ds.ingest(claims=claims, events=events)
        result = ds.evaluate()
        assert result.satisfied == 1
        assert result.pending == 1

        artifact = ds.seal()
        assert artifact.seal_hash.startswith("sha256:")
        assert len(artifact.claims) == 2

    def test_multiple_evaluations(self):
        ds = DecisionSurface.from_surface("notebook")
        ds.ingest(claims=[Claim(claim_id="C1", statement="X")])
        r1 = ds.evaluate()
        assert r1.pending == 1

        ds.ingest(events=[Event(event_id="E1", event_type="ok", claim_refs=["C1"])])
        r2 = ds.evaluate()
        assert r2.satisfied == 1

    def test_empty_state(self):
        ds = DecisionSurface.from_surface("notebook")
        result = ds.evaluate()
        assert result.claims_evaluated == 0
        assert result.satisfied == 0

    def test_claim_status_updates(self):
        claims = [Claim(claim_id="C1", statement="X")]
        ds = DecisionSurface.from_surface("notebook")
        ds.ingest(claims=claims)
        ds.evaluate()
        stored = ds.get_adapter().get_claims()
        assert stored[0].status == "pending"


# ── CLIAdapter ──────────────────────────────────────────────────────


class TestCLIAdapter:

    def test_surface_name(self):
        adapter = CLIAdapter()
        assert adapter.surface_name == "cli"

    def test_to_json_empty(self):
        adapter = CLIAdapter()
        output = adapter.to_json()
        data = json.loads(output)
        assert data["claims"] == []
        assert "evaluationResult" not in data

    def test_to_json_with_data(self):
        ds = DecisionSurface.from_surface("cli")
        ds.ingest(claims=[Claim(claim_id="C1", statement="Test")])
        ds.evaluate()
        output = ds.get_adapter().to_json()
        data = json.loads(output)
        assert len(data["claims"]) == 1
        assert "evaluationResult" in data
        assert data["evaluationResult"]["claimsEvaluated"] == 1

    def test_cli_full_lifecycle(self):
        ds = DecisionSurface.from_surface("cli")
        ds.ingest(
            claims=[Claim(claim_id="C1", statement="X")],
            events=[Event(event_id="E1", event_type="ok", claim_refs=["C1"])],
        )
        result = ds.evaluate()
        assert result.satisfied == 1
        artifact = ds.seal()
        assert artifact.seal_hash.startswith("sha256:")
