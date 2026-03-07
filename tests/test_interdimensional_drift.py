"""Tests for inter-dimensional drift detection and patch recommendations."""

from __future__ import annotations

import sys
from pathlib import Path
from datetime import datetime, timezone

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC_ROOT = _REPO_ROOT / "src"
if str(_SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(_SRC_ROOT))

from core.paradox_ops.models import (
    ParadoxTensionSet,
    TensionDimension,
    TensionLifecycleState,
    TensionPole,
)
from core.paradox_ops.drift import (
    build_patch_recommendations,
    detect_interdimensional_drift,
)
from core.paradox_ops.scoring import evaluate_thresholds
from core.paradox_ops.registry import ParadoxRegistry
from core.paradox_ops.lifecycle import TensionLifecycle
from core.memory_graph import MemoryGraph
from core.modes.paradoxops import ParadoxOps


def _make_pts(poles=None, dimensions=None, **kw):
    defaults = {"tension_id": "PTS-TEST", "subtype": "tension_pair"}
    defaults.update(kw)
    pts = ParadoxTensionSet(**defaults)
    if poles:
        pts.poles = poles
    if dimensions:
        pts.dimensions = dimensions
    return pts


def _make_ctx(pts=None, state="active", use_mg=False):
    reg = ParadoxRegistry()
    lc = TensionLifecycle()
    if pts:
        reg.add(pts)
        lc.set_state(pts.tension_id, TensionLifecycleState(state))
    return {
        "paradox_registry": reg,
        "tension_lifecycle": lc,
        "memory_graph": MemoryGraph() if use_mg else None,
        "now": datetime(2026, 3, 1, tzinfo=timezone.utc),
    }


# ── DetectInterdimensionalDrift ─────────────────────────────────


class TestDetectInterdimensionalDrift:

    def test_two_shifted_one_stale_detected(self):
        pts = _make_pts(dimensions=[
            TensionDimension("D1", "time", current_value=0.8, previous_value=0.0, threshold=0.5),
            TensionDimension("D2", "risk", current_value=0.7, previous_value=0.0,
                             threshold=0.4, is_governance_relevant=True),
            TensionDimension("D3", "authority", current_value=0.0, previous_value=0.0,
                             threshold=0.4, is_governance_relevant=True),
        ])
        result = detect_interdimensional_drift(pts)
        assert result is not None
        assert result["driftType"] == "interdimensional_drift"
        assert result["severity"] == "red"

    def test_only_one_shifted_no_drift(self):
        pts = _make_pts(dimensions=[
            TensionDimension("D1", "time", current_value=0.8, previous_value=0.0, threshold=0.5),
            TensionDimension("D2", "authority", current_value=0.0, previous_value=0.0,
                             threshold=0.4, is_governance_relevant=True),
        ])
        result = detect_interdimensional_drift(pts)
        assert result is None

    def test_all_governance_shifted_no_stale(self):
        pts = _make_pts(dimensions=[
            TensionDimension("D1", "time", current_value=0.8, previous_value=0.0, threshold=0.5),
            TensionDimension("D2", "risk", current_value=0.7, previous_value=0.0,
                             threshold=0.4, is_governance_relevant=True),
            TensionDimension("D3", "authority", current_value=0.6, previous_value=0.0,
                             threshold=0.4, is_governance_relevant=True),
        ])
        result = detect_interdimensional_drift(pts)
        assert result is None  # no stale governance dims

    def test_no_dimensions(self):
        pts = _make_pts()
        assert detect_interdimensional_drift(pts) is None

    def test_stale_cutoff_ten_percent(self):
        # Shift of exactly 10% of threshold should be stale
        pts = _make_pts(dimensions=[
            TensionDimension("D1", "time", current_value=0.8, previous_value=0.0, threshold=0.5),
            TensionDimension("D2", "risk", current_value=0.7, previous_value=0.0,
                             threshold=0.4, is_governance_relevant=True),
            TensionDimension("D3", "authority", current_value=0.04, previous_value=0.0,
                             threshold=0.4, is_governance_relevant=True),
        ])
        result = detect_interdimensional_drift(pts)
        assert result is not None  # 0.04 <= 0.4 * 0.1 = 0.04, so stale

    def test_signal_format(self):
        pts = _make_pts(dimensions=[
            TensionDimension("D1", "time", current_value=0.8, previous_value=0.0, threshold=0.5),
            TensionDimension("D2", "risk", current_value=0.7, previous_value=0.0,
                             threshold=0.4, is_governance_relevant=True),
            TensionDimension("D3", "authority", current_value=0.0, previous_value=0.0,
                             threshold=0.4, is_governance_relevant=True),
        ])
        result = detect_interdimensional_drift(pts)
        assert result["driftId"].startswith("DS-pdx-")
        assert "shiftedDimensions" in result
        assert "staleDimensions" in result
        assert "fingerprint" in result

    def test_shifted_and_stale_lists_correct(self):
        pts = _make_pts(dimensions=[
            TensionDimension("D1", "time", current_value=0.8, previous_value=0.0, threshold=0.5),
            TensionDimension("D2", "risk", current_value=0.7, previous_value=0.0,
                             threshold=0.4, is_governance_relevant=True),
            TensionDimension("D3", "authority", current_value=0.0, previous_value=0.0,
                             threshold=0.4, is_governance_relevant=True),
        ])
        result = detect_interdimensional_drift(pts)
        assert "time" in result["shiftedDimensions"]
        assert "risk" in result["shiftedDimensions"]
        assert "authority" in result["staleDimensions"]

    def test_non_governance_stale_not_counted(self):
        # Stale non-governance dims should NOT trigger drift
        pts = _make_pts(dimensions=[
            TensionDimension("D1", "time", current_value=0.8, previous_value=0.0, threshold=0.5),
            TensionDimension("D2", "risk", current_value=0.7, previous_value=0.0,
                             threshold=0.4, is_governance_relevant=True),
            TensionDimension("D3", "objective", current_value=0.0, previous_value=0.0,
                             threshold=0.5, is_governance_relevant=False),
        ])
        result = detect_interdimensional_drift(pts)
        # Only 1 shifted (risk as governance is shifted), need stale governance
        # Actually: time shifts > 0.5 threshold ✓, risk shifts > 0.4 threshold ✓ → 2 shifted
        # objective is NOT governance relevant → doesn't count as stale governance
        # risk is governance AND shifted → not stale
        # No stale governance dims → None
        assert result is None


# ── BuildPatchRecommendations ───────────────────────────────────


class TestBuildPatchRecommendations:

    def test_authority_stale(self):
        pts = _make_pts(dimensions=[
            TensionDimension("D1", "authority", current_value=0.0, previous_value=0.0,
                             threshold=0.4, is_governance_relevant=True),
        ])
        actions = build_patch_recommendations(pts, [])
        assert "clarify_authority" in actions

    def test_risk_elevated(self):
        pts = _make_pts(dimensions=[
            TensionDimension("D1", "risk", current_value=0.7, previous_value=0.0,
                             threshold=0.4, is_governance_relevant=True),
        ])
        breaches = [{"dimensionName": "risk", "isGovernanceRelevant": True}]
        actions = build_patch_recommendations(pts, breaches)
        assert "increase_control_friction" in actions
        assert "add_review_gate" in actions

    def test_visibility_low(self):
        pts = _make_pts(dimensions=[
            TensionDimension("D1", "visibility", current_value=0.8, previous_value=0.0,
                             threshold=0.5, is_governance_relevant=False),
        ])
        breaches = [{"dimensionName": "visibility", "isGovernanceRelevant": False}]
        actions = build_patch_recommendations(pts, breaches)
        assert "elevate_visibility" in actions

    def test_time_risk_combo(self):
        pts = _make_pts(dimensions=[
            TensionDimension("D1", "time", current_value=0.8, previous_value=0.0,
                             threshold=0.5, is_governance_relevant=False),
            TensionDimension("D2", "risk", current_value=0.7, previous_value=0.0,
                             threshold=0.4, is_governance_relevant=True),
        ])
        breaches = [
            {"dimensionName": "time", "isGovernanceRelevant": False},
            {"dimensionName": "risk", "isGovernanceRelevant": True},
        ]
        actions = build_patch_recommendations(pts, breaches)
        assert "reduce_irreversibility" in actions

    def test_default_fallback(self):
        pts = _make_pts(dimensions=[
            TensionDimension("D1", "layer", current_value=0.0, previous_value=0.0,
                             threshold=0.5, is_governance_relevant=False),
        ])
        actions = build_patch_recommendations(pts, [])
        assert "promote_to_policy_band" in actions

    def test_no_duplicates(self):
        pts = _make_pts(dimensions=[
            TensionDimension("D1", "risk", current_value=0.7, previous_value=0.0,
                             threshold=0.4, is_governance_relevant=True),
        ])
        breaches = [{"dimensionName": "risk", "isGovernanceRelevant": True}]
        actions = build_patch_recommendations(pts, breaches)
        assert len(actions) == len(set(actions))


# ── PDX-F09 Handler ─────────────────────────────────────────────


class TestPdxF09Handler:

    def test_drift_detected_emits_event_and_signal(self):
        pts = _make_pts(dimensions=[
            TensionDimension("D1", "time", current_value=0.8, previous_value=0.0, threshold=0.5),
            TensionDimension("D2", "risk", current_value=0.7, previous_value=0.0,
                             threshold=0.4, is_governance_relevant=True),
            TensionDimension("D3", "authority", current_value=0.0, previous_value=0.0,
                             threshold=0.4, is_governance_relevant=True),
        ])
        ctx = _make_ctx(pts)
        mode = ParadoxOps()
        r = mode.handle("PDX-F09", {"payload": {"tensionId": "PTS-TEST"}}, ctx)
        assert r.success
        assert len(r.drift_signals) == 1
        assert r.events_emitted[0]["subtype"] == "interdimensional_drift_detected"

    def test_no_drift_clean(self):
        pts = _make_pts(dimensions=[
            TensionDimension("D1", "time", current_value=0.1, previous_value=0.0, threshold=0.5),
        ])
        ctx = _make_ctx(pts)
        mode = ParadoxOps()
        r = mode.handle("PDX-F09", {"payload": {"tensionId": "PTS-TEST"}}, ctx)
        assert r.success
        assert r.drift_signals == []
        assert r.events_emitted[0]["subtype"] == "interdimensional_drift_evaluated"

    def test_signal_format(self):
        pts = _make_pts(dimensions=[
            TensionDimension("D1", "time", current_value=0.8, previous_value=0.0, threshold=0.5),
            TensionDimension("D2", "risk", current_value=0.7, previous_value=0.0,
                             threshold=0.4, is_governance_relevant=True),
            TensionDimension("D3", "authority", current_value=0.0, previous_value=0.0,
                             threshold=0.4, is_governance_relevant=True),
        ])
        ctx = _make_ctx(pts)
        mode = ParadoxOps()
        r = mode.handle("PDX-F09", {"payload": {"tensionId": "PTS-TEST"}}, ctx)
        sig = r.drift_signals[0]
        assert sig["driftType"] == "interdimensional_drift"
        assert sig["severity"] == "red"

    def test_mg_updated(self):
        pts = _make_pts(dimensions=[
            TensionDimension("D1", "time", current_value=0.8, previous_value=0.0, threshold=0.5),
            TensionDimension("D2", "risk", current_value=0.7, previous_value=0.0,
                             threshold=0.4, is_governance_relevant=True),
            TensionDimension("D3", "authority", current_value=0.0, previous_value=0.0,
                             threshold=0.4, is_governance_relevant=True),
        ])
        ctx = _make_ctx(pts, use_mg=True)
        mode = ParadoxOps()
        r = mode.handle("PDX-F09", {"payload": {"tensionId": "PTS-TEST"}}, ctx)
        assert len(r.mg_updates) == 1
        mg = ctx["memory_graph"]
        assert mg.node_count >= 1


# ── Scenario 1: Speed vs Control ────────────────────────────────


class TestScenario1SpeedVsControl:

    def test_time_risk_shifted_authority_stale(self):
        pts = _make_pts(dimensions=[
            TensionDimension("D1", "time", current_value=0.8, previous_value=0.0, threshold=0.5),
            TensionDimension("D2", "risk", current_value=0.7, previous_value=0.0,
                             threshold=0.4, is_governance_relevant=True),
            TensionDimension("D3", "authority", current_value=0.0, previous_value=0.0,
                             threshold=0.4, is_governance_relevant=True),
        ])
        result = detect_interdimensional_drift(pts)
        assert result is not None

    def test_patch_includes_clarify_authority(self):
        pts = _make_pts(dimensions=[
            TensionDimension("D1", "time", current_value=0.8, previous_value=0.0, threshold=0.5),
            TensionDimension("D2", "risk", current_value=0.7, previous_value=0.0,
                             threshold=0.4, is_governance_relevant=True),
            TensionDimension("D3", "authority", current_value=0.0, previous_value=0.0,
                             threshold=0.4, is_governance_relevant=True),
        ])
        breaches = evaluate_thresholds(pts)
        actions = build_patch_recommendations(pts, breaches)
        assert "clarify_authority" in actions

    def test_risk_generates_control_friction(self):
        pts = _make_pts(dimensions=[
            TensionDimension("D1", "time", current_value=0.8, previous_value=0.0, threshold=0.5),
            TensionDimension("D2", "risk", current_value=0.7, previous_value=0.0,
                             threshold=0.4, is_governance_relevant=True),
            TensionDimension("D3", "authority", current_value=0.0, previous_value=0.0,
                             threshold=0.4, is_governance_relevant=True),
        ])
        breaches = evaluate_thresholds(pts)
        actions = build_patch_recommendations(pts, breaches)
        assert "increase_control_friction" in actions


# ── Scenario 2: Transparency-Security-Trust (Triple) ────────────


class TestScenario2TransparencySecurityTrust:

    def _make_triple_pts(self):
        return _make_pts(
            subtype="tension_triple",
            poles=[
                TensionPole("P1", "Transparency", weight=1.0),
                TensionPole("P2", "Security", weight=1.5),
                TensionPole("P3", "Trust", weight=0.8),
            ],
            dimensions=[
                TensionDimension("D1", "visibility", current_value=0.8, previous_value=0.0,
                                 threshold=0.5, is_governance_relevant=False),
                TensionDimension("D2", "risk", current_value=0.7, previous_value=0.0,
                                 threshold=0.4, is_governance_relevant=True),
                TensionDimension("D3", "authority", current_value=0.02, previous_value=0.0,
                                 threshold=0.4, is_governance_relevant=True),
            ],
        )

    def test_drift_detected(self):
        pts = self._make_triple_pts()
        result = detect_interdimensional_drift(pts)
        assert result is not None

    def test_visibility_patch(self):
        pts = self._make_triple_pts()
        breaches = evaluate_thresholds(pts)
        actions = build_patch_recommendations(pts, breaches)
        assert "elevate_visibility" in actions

    def test_triple_imbalance(self):
        from core.paradox_ops.scoring import compute_imbalance
        pts = self._make_triple_pts()
        imb = compute_imbalance(pts)
        assert len(imb) == 3
        # Security (1.5) should show positive skew
        assert imb[1] > 0


# ── Scenario 3: Four-Pole ───────────────────────────────────────


class TestScenario3FourPole:

    def _make_four_pole_pts(self):
        return _make_pts(
            subtype="higher_order",
            poles=[
                TensionPole("P1", "LocalOpt", weight=3.0),
                TensionPole("P2", "SystemHealth", weight=1.0),
                TensionPole("P3", "UserSat", weight=1.0),
                TensionPole("P4", "Compliance", weight=1.0),
            ],
            dimensions=[
                TensionDimension("D1", "time", current_value=0.9, previous_value=0.0,
                                 shifted_at="now", threshold=0.5),
                TensionDimension("D2", "risk", current_value=0.8, previous_value=0.0,
                                 shifted_at="now", threshold=0.4, is_governance_relevant=True),
                TensionDimension("D3", "authority", current_value=0.0, previous_value=0.0,
                                 threshold=0.4, is_governance_relevant=True),
            ],
        )

    def test_local_opt_dominates(self):
        from core.paradox_ops.scoring import compute_imbalance
        pts = self._make_four_pole_pts()
        imb = compute_imbalance(pts)
        assert len(imb) == 4
        assert imb[0] > 0  # LocalOpt dominates

    def test_drift_detected(self):
        pts = self._make_four_pole_pts()
        result = detect_interdimensional_drift(pts)
        assert result is not None

    def test_patch_recommendation_generated(self):
        pts = self._make_four_pole_pts()
        breaches = evaluate_thresholds(pts)
        actions = build_patch_recommendations(pts, breaches)
        assert len(actions) > 0
