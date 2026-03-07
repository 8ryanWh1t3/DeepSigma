"""Tests for VantageAdapter contract — all methods raise NotImplementedError."""

from __future__ import annotations

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
    PatchRecommendation,
)
from core.decision_surface.surface_adapter import SurfaceAdapter
from core.decision_surface.vantage_adapter import VantageAdapter
from core.decision_surface.runtime import DecisionSurface


# ── VantageAdapter Contract ─────────────────────────────────────────


class TestVantageAdapterContract:

    def setup_method(self):
        self.adapter = VantageAdapter()

    def test_ingest_claims_raises(self):
        with pytest.raises(NotImplementedError, match="Foundry SDK"):
            self.adapter.ingest_claims([Claim(claim_id="C1", statement="X")])

    def test_ingest_events_raises(self):
        with pytest.raises(NotImplementedError, match="Foundry SDK"):
            self.adapter.ingest_events([Event(event_id="E1", event_type="ok")])

    def test_get_claims_raises(self):
        with pytest.raises(NotImplementedError, match="Foundry SDK"):
            self.adapter.get_claims()

    def test_get_events_raises(self):
        with pytest.raises(NotImplementedError, match="Foundry SDK"):
            self.adapter.get_events()

    def test_get_evidence_raises(self):
        with pytest.raises(NotImplementedError, match="Foundry SDK"):
            self.adapter.get_evidence()

    def test_store_drift_signals_raises(self):
        with pytest.raises(NotImplementedError, match="Foundry SDK"):
            self.adapter.store_drift_signals([DriftSignal(signal_id="S1", drift_type="x")])

    def test_store_patches_raises(self):
        with pytest.raises(NotImplementedError, match="Foundry SDK"):
            self.adapter.store_patches([PatchRecommendation(patch_id="P1", drift_signal_id="S1")])

    def test_store_evaluation_result_raises(self):
        with pytest.raises(NotImplementedError, match="Foundry SDK"):
            self.adapter.store_evaluation_result(EvaluationResult())


# ── VantageAdapter Properties ───────────────────────────────────────


class TestVantageAdapterProperties:

    def test_surface_name(self):
        adapter = VantageAdapter()
        assert adapter.surface_name == "vantage"

    def test_isinstance_surface_adapter(self):
        adapter = VantageAdapter()
        assert isinstance(adapter, SurfaceAdapter)

    def test_from_surface_vantage(self):
        ds = DecisionSurface.from_surface("vantage")
        assert ds.surface_name == "vantage"
        assert isinstance(ds.get_adapter(), VantageAdapter)
