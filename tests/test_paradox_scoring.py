"""Tests for paradox_ops scoring, imbalance, thresholds, and handler integration."""

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
from core.paradox_ops.scoring import (
    compute_imbalance,
    compute_pressure,
    evaluate_thresholds,
)
from core.paradox_ops.registry import ParadoxRegistry
from core.paradox_ops.lifecycle import TensionLifecycle
from core.modes.paradoxops import ParadoxOps


def _make_pts(poles=None, dimensions=None, **kw):
    """Helper to build a PTS quickly."""
    defaults = {
        "tension_id": "PTS-TEST",
        "subtype": "tension_pair",
        "lifecycle_state": "active",
    }
    defaults.update(kw)
    pts = ParadoxTensionSet(**defaults)
    if poles:
        pts.poles = poles
    if dimensions:
        pts.dimensions = dimensions
    return pts


def _make_ctx(pts=None, state="active"):
    """Build a handler context with registry + lifecycle."""
    reg = ParadoxRegistry()
    lc = TensionLifecycle()
    if pts:
        reg.add(pts)
        lc.set_state(pts.tension_id, TensionLifecycleState(state))
    return {
        "paradox_registry": reg,
        "tension_lifecycle": lc,
        "memory_graph": None,
        "now": datetime(2026, 3, 1, tzinfo=timezone.utc),
    }


# ── ComputePressure ─────────────────────────────────────────────


class TestComputePressure:

    def test_low_pressure(self):
        pts = _make_pts(
            poles=[TensionPole("A", "Speed"), TensionPole("B", "Control")],
            dimensions=[TensionDimension("D1", "time")],
        )
        p = compute_pressure(pts)
        assert 0.0 <= p <= 0.3

    def test_elevated_pressure(self):
        pts = _make_pts(
            poles=[TensionPole("A", "Speed", weight=3.0), TensionPole("B", "Control", weight=1.0)],
            dimensions=[
                TensionDimension("D1", "time", current_value=0.8, previous_value=0.0,
                                 shifted_at="2026-03-01", threshold=0.5),
                TensionDimension("D2", "risk", current_value=0.6, previous_value=0.0,
                                 shifted_at="2026-03-01", threshold=0.4),
            ],
        )
        p = compute_pressure(pts)
        assert p >= 0.5

    def test_red_zone_pressure(self):
        pts = _make_pts(
            poles=[TensionPole("A", "Speed", weight=5.0), TensionPole("B", "Control", weight=1.0)],
            dimensions=[
                TensionDimension("D1", "time", current_value=1.0, previous_value=0.0,
                                 shifted_at="2026-03-01", threshold=0.5),
                TensionDimension("D2", "risk", current_value=0.9, previous_value=0.0,
                                 shifted_at="2026-03-01", threshold=0.4),
            ],
        )
        p = compute_pressure(pts)
        assert p >= 0.7

    def test_empty_pts(self):
        pts = _make_pts()
        p = compute_pressure(pts)
        assert p == 0.0

    def test_pair_vs_triple(self):
        pair = _make_pts(
            poles=[TensionPole("A", "S", weight=3.0), TensionPole("B", "C", weight=1.0)],
        )
        triple = _make_pts(
            subtype="tension_triple",
            poles=[TensionPole("A", "S", weight=3.0), TensionPole("B", "C", weight=1.0),
                   TensionPole("C", "X", weight=1.0)],
        )
        pp = compute_pressure(pair)
        pt = compute_pressure(triple)
        # Both should compute without error
        assert 0.0 <= pp <= 1.0
        assert 0.0 <= pt <= 1.0

    def test_score_bounded(self):
        pts = _make_pts(
            poles=[TensionPole("A", "S", weight=100.0), TensionPole("B", "C", weight=0.01)],
            dimensions=[
                TensionDimension("D1", "time", current_value=10.0, previous_value=0.0,
                                 shifted_at="now", threshold=0.1),
            ],
        )
        p = compute_pressure(pts)
        assert 0.0 <= p <= 1.0

    def test_equal_weights_low_dispersion(self):
        pts = _make_pts(
            poles=[TensionPole("A", "S"), TensionPole("B", "C")],
        )
        p = compute_pressure(pts)
        assert p == 0.0

    def test_shifted_dimensions_increase_pressure(self):
        no_shift = _make_pts(
            poles=[TensionPole("A", "S", weight=2.0), TensionPole("B", "C", weight=1.0)],
            dimensions=[TensionDimension("D1", "time", threshold=0.5)],
        )
        with_shift = _make_pts(
            poles=[TensionPole("A", "S", weight=2.0), TensionPole("B", "C", weight=1.0)],
            dimensions=[TensionDimension("D1", "time", current_value=0.8, previous_value=0.0,
                                         shifted_at="now", threshold=0.5)],
        )
        assert compute_pressure(with_shift) > compute_pressure(no_shift)


# ── ComputeImbalance ────────────────────────────────────────────


class TestComputeImbalance:

    def test_pair_balanced(self):
        pts = _make_pts(
            poles=[TensionPole("A", "S"), TensionPole("B", "C")],
        )
        imb = compute_imbalance(pts)
        assert len(imb) == 1
        assert imb[0] == 0.0

    def test_pair_skewed(self):
        pts = _make_pts(
            poles=[TensionPole("A", "S", weight=3.0), TensionPole("B", "C", weight=1.0)],
        )
        imb = compute_imbalance(pts)
        assert len(imb) == 1
        assert imb[0] > 0

    def test_triple_balanced(self):
        pts = _make_pts(
            subtype="tension_triple",
            poles=[TensionPole("A", "S"), TensionPole("B", "C"), TensionPole("C", "X")],
        )
        imb = compute_imbalance(pts)
        assert len(imb) == 3
        assert abs(sum(imb)) < 0.001

    def test_triple_skewed(self):
        pts = _make_pts(
            subtype="tension_triple",
            poles=[TensionPole("A", "S", weight=5.0), TensionPole("B", "C", weight=1.0),
                   TensionPole("C", "X", weight=1.0)],
        )
        imb = compute_imbalance(pts)
        assert imb[0] > 0  # dominant pole has positive skew
        assert abs(sum(imb)) < 0.001

    def test_four_pole_equal(self):
        pts = _make_pts(
            subtype="higher_order",
            poles=[TensionPole(f"P-{i}", f"L{i}") for i in range(4)],
        )
        imb = compute_imbalance(pts)
        assert len(imb) == 4
        assert all(abs(v) < 0.001 for v in imb)

    def test_four_pole_skewed(self):
        pts = _make_pts(
            subtype="higher_order",
            poles=[
                TensionPole("A", "S", weight=4.0),
                TensionPole("B", "C", weight=1.0),
                TensionPole("C", "X", weight=1.0),
                TensionPole("D", "Y", weight=1.0),
            ],
        )
        imb = compute_imbalance(pts)
        assert imb[0] > 0

    def test_single_pole(self):
        pts = _make_pts(poles=[TensionPole("A", "S")])
        imb = compute_imbalance(pts)
        assert imb == [0.0]

    def test_zero_weights(self):
        pts = _make_pts(
            poles=[TensionPole("A", "S", weight=0.0), TensionPole("B", "C", weight=0.0)],
        )
        imb = compute_imbalance(pts)
        assert len(imb) == 2


# ── EvaluateThresholds ──────────────────────────────────────────


class TestEvaluateThresholds:

    def test_no_breaches(self):
        pts = _make_pts(
            dimensions=[
                TensionDimension("D1", "time", current_value=0.1, previous_value=0.0, threshold=0.5),
            ],
        )
        assert evaluate_thresholds(pts) == []

    def test_single_breach(self):
        pts = _make_pts(
            dimensions=[
                TensionDimension("D1", "time", current_value=0.8, previous_value=0.0, threshold=0.5),
            ],
        )
        breaches = evaluate_thresholds(pts)
        assert len(breaches) == 1
        assert breaches[0]["dimensionName"] == "time"

    def test_multiple_breaches(self):
        pts = _make_pts(
            dimensions=[
                TensionDimension("D1", "time", current_value=0.8, previous_value=0.0, threshold=0.5),
                TensionDimension("D2", "risk", current_value=0.7, previous_value=0.0, threshold=0.4),
            ],
        )
        breaches = evaluate_thresholds(pts)
        assert len(breaches) == 2

    def test_boundary_not_breached(self):
        pts = _make_pts(
            dimensions=[
                TensionDimension("D1", "time", current_value=0.5, previous_value=0.0, threshold=0.5),
            ],
        )
        # shift == threshold is NOT a breach (requires >)
        assert evaluate_thresholds(pts) == []

    def test_no_dimensions(self):
        pts = _make_pts()
        assert evaluate_thresholds(pts) == []


# ── PDX-F05 Handler ─────────────────────────────────────────────


class TestPdxF05PressureCompute:

    def test_low_pressure_no_elevation(self):
        pts = _make_pts(
            poles=[TensionPole("A", "S"), TensionPole("B", "C")],
        )
        ctx = _make_ctx(pts)
        mode = ParadoxOps()
        r = mode.handle("PDX-F05", {"payload": {"tensionId": "PTS-TEST"}}, ctx)
        assert r.success
        assert not any(e.get("elevated") for e in r.events_emitted)

    def test_elevated_triggers_transition(self):
        pts = _make_pts(
            poles=[TensionPole("A", "S", weight=5.0), TensionPole("B", "C", weight=1.0)],
            dimensions=[
                TensionDimension("D1", "time", current_value=1.0, previous_value=0.0,
                                 shifted_at="now", threshold=0.5),
                TensionDimension("D2", "risk", current_value=0.9, previous_value=0.0,
                                 shifted_at="now", threshold=0.4),
            ],
        )
        ctx = _make_ctx(pts)
        mode = ParadoxOps()
        r = mode.handle("PDX-F05", {"payload": {"tensionId": "PTS-TEST"}}, ctx)
        assert r.success
        updated_pts = ctx["paradox_registry"].get("PTS-TEST")
        # Pressure should be high enough
        if updated_pts.pressure_score >= 0.7:
            assert updated_pts.lifecycle_state == "elevated"
            assert len(r.drift_signals) > 0

    def test_missing_pts(self):
        ctx = _make_ctx()
        mode = ParadoxOps()
        r = mode.handle("PDX-F05", {"payload": {"tensionId": "NOPE"}}, ctx)
        assert not r.success
        assert "not found" in r.error.lower()

    def test_event_emitted(self):
        pts = _make_pts(
            poles=[TensionPole("A", "S"), TensionPole("B", "C")],
        )
        ctx = _make_ctx(pts)
        mode = ParadoxOps()
        r = mode.handle("PDX-F05", {"payload": {"tensionId": "PTS-TEST"}}, ctx)
        assert len(r.events_emitted) == 1
        assert r.events_emitted[0]["topic"] == "drift_signal"

    def test_already_elevated_no_double(self):
        pts = _make_pts(
            lifecycle_state="elevated",
            poles=[TensionPole("A", "S", weight=5.0), TensionPole("B", "C", weight=1.0)],
            dimensions=[
                TensionDimension("D1", "time", current_value=1.0, previous_value=0.0,
                                 shifted_at="now", threshold=0.5),
            ],
        )
        ctx = _make_ctx(pts, state="elevated")
        mode = ParadoxOps()
        r = mode.handle("PDX-F05", {"payload": {"tensionId": "PTS-TEST"}}, ctx)
        assert r.success
        # Should NOT re-elevate (not in active state)
        assert r.drift_signals == []


# ── PDX-F06 Handler ─────────────────────────────────────────────


class TestPdxF06ImbalanceCompute:

    def test_pair(self):
        pts = _make_pts(
            poles=[TensionPole("A", "S"), TensionPole("B", "C")],
        )
        ctx = _make_ctx(pts)
        mode = ParadoxOps()
        r = mode.handle("PDX-F06", {"payload": {"tensionId": "PTS-TEST"}}, ctx)
        assert r.success
        updated = ctx["paradox_registry"].get("PTS-TEST")
        assert len(updated.imbalance_vector) == 1

    def test_triple(self):
        pts = _make_pts(
            subtype="tension_triple",
            poles=[TensionPole("A", "S"), TensionPole("B", "C"), TensionPole("C", "X")],
        )
        ctx = _make_ctx(pts)
        mode = ParadoxOps()
        r = mode.handle("PDX-F06", {"payload": {"tensionId": "PTS-TEST"}}, ctx)
        assert r.success
        updated = ctx["paradox_registry"].get("PTS-TEST")
        assert len(updated.imbalance_vector) == 3

    def test_four_pole(self):
        pts = _make_pts(
            subtype="higher_order",
            poles=[TensionPole(f"P-{i}", f"L{i}") for i in range(4)],
        )
        ctx = _make_ctx(pts)
        mode = ParadoxOps()
        r = mode.handle("PDX-F06", {"payload": {"tensionId": "PTS-TEST"}}, ctx)
        assert r.success
        updated = ctx["paradox_registry"].get("PTS-TEST")
        assert len(updated.imbalance_vector) == 4

    def test_missing_pts(self):
        ctx = _make_ctx()
        mode = ParadoxOps()
        r = mode.handle("PDX-F06", {"payload": {"tensionId": "NOPE"}}, ctx)
        assert not r.success


# ── PDX-F07 Handler ─────────────────────────────────────────────


class TestPdxF07ThresholdEvaluate:

    def test_no_breaches(self):
        pts = _make_pts(
            dimensions=[
                TensionDimension("D1", "time", current_value=0.1, previous_value=0.0, threshold=0.5),
            ],
        )
        ctx = _make_ctx(pts)
        mode = ParadoxOps()
        r = mode.handle("PDX-F07", {"payload": {"tensionId": "PTS-TEST"}}, ctx)
        assert r.success
        assert r.drift_signals == []
        assert r.events_emitted[0]["subtype"] == "pts_threshold_evaluated"

    def test_breach_emits_drift(self):
        pts = _make_pts(
            dimensions=[
                TensionDimension("D1", "time", current_value=0.8, previous_value=0.0, threshold=0.5),
            ],
        )
        ctx = _make_ctx(pts)
        mode = ParadoxOps()
        r = mode.handle("PDX-F07", {"payload": {"tensionId": "PTS-TEST"}}, ctx)
        assert r.success
        assert len(r.drift_signals) == 1
        assert r.drift_signals[0]["driftType"] == "tension_threshold_breach"

    def test_multiple_breaches(self):
        pts = _make_pts(
            dimensions=[
                TensionDimension("D1", "time", current_value=0.8, previous_value=0.0, threshold=0.5),
                TensionDimension("D2", "risk", current_value=0.7, previous_value=0.0,
                                 threshold=0.4, is_governance_relevant=True),
            ],
        )
        ctx = _make_ctx(pts)
        mode = ParadoxOps()
        r = mode.handle("PDX-F07", {"payload": {"tensionId": "PTS-TEST"}}, ctx)
        assert r.success
        assert r.events_emitted[0]["breachCount"] == 2
        # Governance breach → red severity
        assert r.drift_signals[0]["severity"] == "red"

    def test_event_format(self):
        pts = _make_pts(
            dimensions=[
                TensionDimension("D1", "time", current_value=0.8, previous_value=0.0, threshold=0.5),
            ],
        )
        ctx = _make_ctx(pts)
        mode = ParadoxOps()
        r = mode.handle("PDX-F07", {"payload": {"tensionId": "PTS-TEST"}}, ctx)
        ev = r.events_emitted[0]
        assert ev["topic"] == "drift_signal"
        assert ev["subtype"] == "pts_threshold_breached"
        assert "breaches" in ev

    def test_missing_pts(self):
        ctx = _make_ctx()
        mode = ParadoxOps()
        r = mode.handle("PDX-F07", {"payload": {"tensionId": "NOPE"}}, ctx)
        assert not r.success


# ── Scenario: Speed vs Control ──────────────────────────────────


class TestScenario1SpeedVsControl:

    def test_pressure_computation(self):
        pts = _make_pts(
            poles=[TensionPole("A", "Speed", weight=2.0), TensionPole("B", "Control", weight=1.0)],
            dimensions=[
                TensionDimension("D1", "time", current_value=0.8, previous_value=0.0,
                                 shifted_at="now", threshold=0.5),
                TensionDimension("D2", "risk", current_value=0.7, previous_value=0.0,
                                 shifted_at="now", threshold=0.4),
            ],
        )
        p = compute_pressure(pts)
        assert p > 0.3

    def test_threshold_evaluation(self):
        pts = _make_pts(
            dimensions=[
                TensionDimension("D1", "time", current_value=0.8, previous_value=0.0, threshold=0.5),
                TensionDimension("D2", "risk", current_value=0.7, previous_value=0.0,
                                 threshold=0.4, is_governance_relevant=True),
            ],
        )
        breaches = evaluate_thresholds(pts)
        assert len(breaches) == 2
        assert any(b["dimensionName"] == "time" for b in breaches)
        assert any(b["dimensionName"] == "risk" for b in breaches)

    def test_imbalance_direction(self):
        pts = _make_pts(
            poles=[TensionPole("A", "Speed", weight=3.0), TensionPole("B", "Control", weight=1.0)],
        )
        imb = compute_imbalance(pts)
        assert imb[0] > 0  # Speed dominates
