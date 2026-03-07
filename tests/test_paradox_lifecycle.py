"""Tests for paradox lifecycle, handler integration, and full lifecycle scenarios."""

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
    TensionSubtype,
)
from core.paradox_ops.lifecycle import TensionLifecycle
from core.paradox_ops.registry import ParadoxRegistry
from core.paradox_ops.dimensions import DimensionRegistry
from core.memory_graph import MemoryGraph
from core.modes.paradoxops import ParadoxOps


def _make_ctx(pts=None, state="detected", use_mg=False):
    reg = ParadoxRegistry()
    lc = TensionLifecycle()
    dr = DimensionRegistry()
    if pts:
        reg.add(pts)
        lc.set_state(pts.tension_id, TensionLifecycleState(state))
    return {
        "paradox_registry": reg,
        "tension_lifecycle": lc,
        "dimension_registry": dr,
        "memory_graph": MemoryGraph() if use_mg else None,
        "now": datetime(2026, 3, 1, tzinfo=timezone.utc),
    }


# ── TensionLifecycle ─────────────────────────────────────────────


class TestTensionLifecycle:

    def test_set_and_get(self):
        lc = TensionLifecycle()
        lc.set_state("PTS-1", TensionLifecycleState.DETECTED)
        assert lc.get_state("PTS-1") == TensionLifecycleState.DETECTED

    def test_get_unknown(self):
        lc = TensionLifecycle()
        assert lc.get_state("unknown") is None

    def test_valid_transition(self):
        lc = TensionLifecycle()
        lc.set_state("PTS-1", TensionLifecycleState.DETECTED)
        assert lc.transition("PTS-1", TensionLifecycleState.ACTIVE) is True
        assert lc.get_state("PTS-1") == TensionLifecycleState.ACTIVE

    def test_invalid_transition(self):
        lc = TensionLifecycle()
        lc.set_state("PTS-1", TensionLifecycleState.DETECTED)
        assert lc.transition("PTS-1", TensionLifecycleState.SEALED) is False

    def test_terminal_state(self):
        lc = TensionLifecycle()
        lc.set_state("PTS-1", TensionLifecycleState.ARCHIVED)
        assert lc.is_terminal("PTS-1") is True

    def test_non_terminal_state(self):
        lc = TensionLifecycle()
        lc.set_state("PTS-1", TensionLifecycleState.ACTIVE)
        assert lc.is_terminal("PTS-1") is False

    def test_full_path(self):
        lc = TensionLifecycle()
        lc.set_state("PTS-1", TensionLifecycleState.DETECTED)
        assert lc.transition("PTS-1", TensionLifecycleState.ACTIVE)
        assert lc.transition("PTS-1", TensionLifecycleState.ELEVATED)
        assert lc.transition("PTS-1", TensionLifecycleState.PROMOTED_TO_DRIFT)
        assert lc.transition("PTS-1", TensionLifecycleState.SEALED)
        assert lc.transition("PTS-1", TensionLifecycleState.PATCHED)
        assert lc.transition("PTS-1", TensionLifecycleState.REBALANCED)
        assert lc.transition("PTS-1", TensionLifecycleState.ARCHIVED)
        assert lc.is_terminal("PTS-1")

    def test_deescalation(self):
        lc = TensionLifecycle()
        lc.set_state("PTS-1", TensionLifecycleState.ELEVATED)
        assert lc.transition("PTS-1", TensionLifecycleState.ACTIVE) is True


# ── PDX-F01: Tension Set Create ─────────────────────────────────


class TestPdxF01TensionSetCreate:

    def test_valid_pair(self):
        ctx = _make_ctx()
        mode = ParadoxOps()
        event = {"payload": {
            "tensionId": "PTS-001",
            "subtype": "tension_pair",
            "poles": [
                {"poleId": "A", "label": "Speed", "weight": 1.0},
                {"poleId": "B", "label": "Control", "weight": 1.0},
            ],
            "episodeId": "EP-001",
        }}
        r = mode.handle("PDX-F01", event, ctx)
        assert r.success
        pts = ctx["paradox_registry"].get("PTS-001")
        assert pts is not None
        assert len(pts.poles) == 2

    def test_valid_triple(self):
        ctx = _make_ctx()
        mode = ParadoxOps()
        event = {"payload": {
            "subtype": "tension_triple",
            "poles": [
                {"poleId": "A", "label": "Speed"},
                {"poleId": "B", "label": "Control"},
                {"poleId": "C", "label": "Stability"},
            ],
        }}
        r = mode.handle("PDX-F01", event, ctx)
        assert r.success

    def test_valid_higher_order(self):
        ctx = _make_ctx()
        mode = ParadoxOps()
        event = {"payload": {
            "subtype": "higher_order",
            "poles": [{"poleId": f"P-{i}", "label": f"L{i}"} for i in range(4)],
        }}
        r = mode.handle("PDX-F01", event, ctx)
        assert r.success

    def test_validation_failure(self):
        ctx = _make_ctx()
        mode = ParadoxOps()
        event = {"payload": {
            "subtype": "tension_pair",
            "poles": [{"poleId": "A", "label": "Speed"}],  # only 1 pole
        }}
        r = mode.handle("PDX-F01", event, ctx)
        assert not r.success

    def test_mg_node_created(self):
        ctx = _make_ctx(use_mg=True)
        mode = ParadoxOps()
        event = {"payload": {
            "tensionId": "PTS-MG",
            "subtype": "tension_pair",
            "poles": [
                {"poleId": "A", "label": "Speed"},
                {"poleId": "B", "label": "Control"},
            ],
        }}
        r = mode.handle("PDX-F01", event, ctx)
        assert r.success
        assert "PTS-MG" in r.mg_updates
        mg = ctx["memory_graph"]
        assert mg.node_count >= 1


# ── PDX-F02: Pole Manage ────────────────────────────────────────


class TestPdxF02PoleManage:

    def _setup(self):
        pts = ParadoxTensionSet(
            tension_id="PTS-PM", subtype="tension_pair",
            poles=[TensionPole("A", "Speed"), TensionPole("B", "Control")],
        )
        ctx = _make_ctx(pts)
        return pts, ctx

    def test_add_pole(self):
        pts, ctx = self._setup()
        mode = ParadoxOps()
        r = mode.handle("PDX-F02", {"payload": {
            "tensionId": "PTS-PM",
            "operation": "add",
            "pole": {"poleId": "C", "label": "Stability"},
        }}, ctx)
        assert r.success
        updated = ctx["paradox_registry"].get("PTS-PM")
        assert len(updated.poles) == 3
        assert updated.subtype == "tension_triple"

    def test_remove_pole(self):
        pts, ctx = self._setup()
        # First add a third so we still have 2 after removal
        pts.poles.append(TensionPole("C", "Stability"))
        ctx["paradox_registry"].update(pts)

        mode = ParadoxOps()
        r = mode.handle("PDX-F02", {"payload": {
            "tensionId": "PTS-PM",
            "operation": "remove",
            "pole": {"poleId": "C"},
        }}, ctx)
        assert r.success
        updated = ctx["paradox_registry"].get("PTS-PM")
        assert len(updated.poles) == 2

    def test_update_weight(self):
        pts, ctx = self._setup()
        mode = ParadoxOps()
        r = mode.handle("PDX-F02", {"payload": {
            "tensionId": "PTS-PM",
            "operation": "update",
            "pole": {"poleId": "A", "weight": 3.0},
        }}, ctx)
        assert r.success
        updated = ctx["paradox_registry"].get("PTS-PM")
        pole_a = next(p for p in updated.poles if p.pole_id == "A")
        assert pole_a.weight == 3.0

    def test_subtype_adjusts(self):
        pts, ctx = self._setup()
        mode = ParadoxOps()
        # Add 2 more poles
        mode.handle("PDX-F02", {"payload": {
            "tensionId": "PTS-PM", "operation": "add",
            "pole": {"poleId": "C", "label": "X"},
        }}, ctx)
        mode.handle("PDX-F02", {"payload": {
            "tensionId": "PTS-PM", "operation": "add",
            "pole": {"poleId": "D", "label": "Y"},
        }}, ctx)
        updated = ctx["paradox_registry"].get("PTS-PM")
        assert updated.subtype == "higher_order"


# ── PDX-F03: Dimension Attach ───────────────────────────────────


class TestPdxF03DimensionAttach:

    def _setup(self):
        pts = ParadoxTensionSet(
            tension_id="PTS-DA", subtype="tension_pair",
            poles=[TensionPole("A", "Speed"), TensionPole("B", "Control")],
        )
        return pts, _make_ctx(pts)

    def test_common_dimension(self):
        pts, ctx = self._setup()
        mode = ParadoxOps()
        r = mode.handle("PDX-F03", {"payload": {
            "tensionId": "PTS-DA", "dimensionName": "time",
        }}, ctx)
        assert r.success
        updated = ctx["paradox_registry"].get("PTS-DA")
        assert len(updated.dimensions) == 1
        assert updated.dimensions[0].name == "time"

    def test_uncommon_dimension(self):
        pts, ctx = self._setup()
        mode = ParadoxOps()
        r = mode.handle("PDX-F03", {"payload": {
            "tensionId": "PTS-DA", "dimensionName": "reversibility",
        }}, ctx)
        assert r.success
        updated = ctx["paradox_registry"].get("PTS-DA")
        assert updated.dimensions[0].kind == "uncommon"

    def test_reject_unknown(self):
        pts, ctx = self._setup()
        mode = ParadoxOps()
        r = mode.handle("PDX-F03", {"payload": {
            "tensionId": "PTS-DA", "dimensionName": "nonexistent_dim",
        }}, ctx)
        assert not r.success
        assert "unknown" in r.error.lower()

    def test_duplicate_rejected(self):
        pts, ctx = self._setup()
        mode = ParadoxOps()
        mode.handle("PDX-F03", {"payload": {
            "tensionId": "PTS-DA", "dimensionName": "time",
        }}, ctx)
        r = mode.handle("PDX-F03", {"payload": {
            "tensionId": "PTS-DA", "dimensionName": "time",
        }}, ctx)
        assert not r.success
        assert "already attached" in r.error.lower()


# ── PDX-F04: Dimension Shift ────────────────────────────────────


class TestPdxF04DimensionShift:

    def _setup(self):
        pts = ParadoxTensionSet(
            tension_id="PTS-DS", subtype="tension_pair",
            poles=[TensionPole("A", "Speed"), TensionPole("B", "Control")],
            dimensions=[TensionDimension("DIM-01", "time", threshold=0.5)],
        )
        return pts, _make_ctx(pts)

    def test_valid_shift(self):
        pts, ctx = self._setup()
        mode = ParadoxOps()
        r = mode.handle("PDX-F04", {"payload": {
            "tensionId": "PTS-DS", "dimensionId": "DIM-01", "newValue": 0.8,
        }}, ctx)
        assert r.success
        updated = ctx["paradox_registry"].get("PTS-DS")
        dim = updated.dimensions[0]
        assert dim.current_value == 0.8
        assert dim.previous_value == 0.0

    def test_shifted_at_set(self):
        pts, ctx = self._setup()
        mode = ParadoxOps()
        mode.handle("PDX-F04", {"payload": {
            "tensionId": "PTS-DS", "dimensionId": "DIM-01", "newValue": 0.8,
        }}, ctx)
        updated = ctx["paradox_registry"].get("PTS-DS")
        assert updated.dimensions[0].shifted_at is not None

    def test_previous_value_preserved(self):
        pts, ctx = self._setup()
        mode = ParadoxOps()
        mode.handle("PDX-F04", {"payload": {
            "tensionId": "PTS-DS", "dimensionId": "DIM-01", "newValue": 0.5,
        }}, ctx)
        mode.handle("PDX-F04", {"payload": {
            "tensionId": "PTS-DS", "dimensionId": "DIM-01", "newValue": 0.9,
        }}, ctx)
        updated = ctx["paradox_registry"].get("PTS-DS")
        assert updated.dimensions[0].previous_value == 0.5
        assert updated.dimensions[0].current_value == 0.9

    def test_unknown_dimension_rejected(self):
        pts, ctx = self._setup()
        mode = ParadoxOps()
        r = mode.handle("PDX-F04", {"payload": {
            "tensionId": "PTS-DS", "dimensionId": "DIM-99", "newValue": 0.5,
        }}, ctx)
        assert not r.success


# ── PDX-F08: Drift Promote ──────────────────────────────────────


class TestPdxF08DriftPromote:

    def _setup(self):
        pts = ParadoxTensionSet(
            tension_id="PTS-DP", subtype="tension_pair",
            poles=[TensionPole("A", "Speed"), TensionPole("B", "Control")],
            lifecycle_state="elevated",
            pressure_score=0.85,
        )
        return pts, _make_ctx(pts, state="elevated")

    def test_elevated_promotes(self):
        pts, ctx = self._setup()
        mode = ParadoxOps()
        r = mode.handle("PDX-F08", {"payload": {"tensionId": "PTS-DP"}}, ctx)
        assert r.success
        updated = ctx["paradox_registry"].get("PTS-DP")
        assert updated.lifecycle_state == "promoted_to_drift"
        assert updated.promoted_drift_id is not None

    def test_not_elevated_rejected(self):
        pts = ParadoxTensionSet(
            tension_id="PTS-DP2", subtype="tension_pair",
            lifecycle_state="active",
        )
        ctx = _make_ctx(pts, state="active")
        mode = ParadoxOps()
        r = mode.handle("PDX-F08", {"payload": {"tensionId": "PTS-DP2"}}, ctx)
        assert not r.success
        assert "elevated" in r.error.lower()

    def test_drift_signal_emitted(self):
        pts, ctx = self._setup()
        mode = ParadoxOps()
        r = mode.handle("PDX-F08", {"payload": {"tensionId": "PTS-DP"}}, ctx)
        assert len(r.drift_signals) == 1
        assert r.drift_signals[0]["driftType"] == "tension_pressure"

    def test_severity(self):
        pts, ctx = self._setup()
        mode = ParadoxOps()
        r = mode.handle("PDX-F08", {"payload": {"tensionId": "PTS-DP"}}, ctx)
        assert r.drift_signals[0]["severity"] in ("red", "yellow")

    def test_mg_drift_node(self):
        pts = ParadoxTensionSet(
            tension_id="PTS-DP3", subtype="tension_pair",
            poles=[TensionPole("A", "Speed"), TensionPole("B", "Control")],
            lifecycle_state="elevated",
            pressure_score=0.85,
        )
        ctx = _make_ctx(pts, state="elevated", use_mg=True)
        mode = ParadoxOps()
        r = mode.handle("PDX-F08", {"payload": {"tensionId": "PTS-DP3"}}, ctx)
        assert len(r.mg_updates) == 1
        mg = ctx["memory_graph"]
        assert mg.node_count >= 1


# ── PDX-F10: Seal Snapshot ──────────────────────────────────────


class TestPdxF10SealSnapshot:

    def _setup(self):
        pts = ParadoxTensionSet(
            tension_id="PTS-SEAL", subtype="tension_pair",
            poles=[TensionPole("A", "Speed"), TensionPole("B", "Control")],
            lifecycle_state="promoted_to_drift",
        )
        return pts, _make_ctx(pts, state="promoted_to_drift")

    def test_hash_computed(self):
        pts, ctx = self._setup()
        mode = ParadoxOps()
        r = mode.handle("PDX-F10", {"payload": {"tensionId": "PTS-SEAL"}}, ctx)
        assert r.success
        updated = ctx["paradox_registry"].get("PTS-SEAL")
        assert updated.seal_hash.startswith("sha256:")

    def test_version_bumped(self):
        pts, ctx = self._setup()
        mode = ParadoxOps()
        r = mode.handle("PDX-F10", {"payload": {"tensionId": "PTS-SEAL"}}, ctx)
        updated = ctx["paradox_registry"].get("PTS-SEAL")
        assert updated.seal_version == 2  # started at 1, bumped

    def test_sealed_at_set(self):
        pts, ctx = self._setup()
        mode = ParadoxOps()
        r = mode.handle("PDX-F10", {"payload": {"tensionId": "PTS-SEAL"}}, ctx)
        updated = ctx["paradox_registry"].get("PTS-SEAL")
        assert updated.sealed_at is not None

    def test_lifecycle_transitions(self):
        pts, ctx = self._setup()
        mode = ParadoxOps()
        r = mode.handle("PDX-F10", {"payload": {"tensionId": "PTS-SEAL"}}, ctx)
        updated = ctx["paradox_registry"].get("PTS-SEAL")
        assert updated.lifecycle_state == "sealed"


# ── PDX-F11: Patch Issue ────────────────────────────────────────


class TestPdxF11PatchIssue:

    def _setup(self):
        pts = ParadoxTensionSet(
            tension_id="PTS-PATCH", subtype="tension_pair",
            poles=[TensionPole("A", "Speed"), TensionPole("B", "Control")],
            dimensions=[
                TensionDimension("D1", "time", current_value=0.8, previous_value=0.0, threshold=0.5),
                TensionDimension("D2", "authority", current_value=0.0, previous_value=0.0,
                                 threshold=0.4, is_governance_relevant=True),
            ],
            lifecycle_state="sealed",
            pressure_score=0.75,
        )
        return pts, _make_ctx(pts, state="sealed")

    def test_patch_with_actions(self):
        pts, ctx = self._setup()
        mode = ParadoxOps()
        r = mode.handle("PDX-F11", {"payload": {"tensionId": "PTS-PATCH"}}, ctx)
        assert r.success
        ev = r.events_emitted[0]
        assert "recommendedActions" in ev
        assert len(ev["recommendedActions"]) > 0

    def test_rationale(self):
        pts, ctx = self._setup()
        mode = ParadoxOps()
        r = mode.handle("PDX-F11", {"payload": {"tensionId": "PTS-PATCH"}}, ctx)
        ev = r.events_emitted[0]
        assert ev["patchId"].startswith("TPATCH-")

    def test_lifecycle_to_patched(self):
        pts, ctx = self._setup()
        mode = ParadoxOps()
        mode.handle("PDX-F11", {"payload": {"tensionId": "PTS-PATCH"}}, ctx)
        updated = ctx["paradox_registry"].get("PTS-PATCH")
        assert updated.lifecycle_state == "patched"

    def test_mg_patch_node(self):
        pts = ParadoxTensionSet(
            tension_id="PTS-PG", subtype="tension_pair",
            poles=[TensionPole("A", "Speed"), TensionPole("B", "Control")],
            dimensions=[
                TensionDimension("D1", "time", current_value=0.8, previous_value=0.0, threshold=0.5),
            ],
            lifecycle_state="sealed",
        )
        ctx = _make_ctx(pts, state="sealed", use_mg=True)
        mode = ParadoxOps()
        r = mode.handle("PDX-F11", {"payload": {"tensionId": "PTS-PG"}}, ctx)
        assert len(r.mg_updates) == 1

    def test_all_actions_valid(self):
        from core.paradox_ops.models import PatchAction
        valid_actions = {a.value for a in PatchAction}
        pts, ctx = self._setup()
        mode = ParadoxOps()
        r = mode.handle("PDX-F11", {"payload": {"tensionId": "PTS-PATCH"}}, ctx)
        ev = r.events_emitted[0]
        for action in ev["recommendedActions"]:
            assert action in valid_actions, f"Invalid action: {action}"


# ── PDX-F12: Lifecycle Transition ───────────────────────────────


class TestPdxF12LifecycleTransition:

    def test_rebalance(self):
        pts = ParadoxTensionSet(
            tension_id="PTS-LT", subtype="tension_pair",
            lifecycle_state="patched",
        )
        ctx = _make_ctx(pts, state="patched")
        mode = ParadoxOps()
        r = mode.handle("PDX-F12", {"payload": {
            "tensionId": "PTS-LT", "targetState": "rebalanced",
        }}, ctx)
        assert r.success
        assert ctx["paradox_registry"].get("PTS-LT").lifecycle_state == "rebalanced"

    def test_archive(self):
        pts = ParadoxTensionSet(
            tension_id="PTS-LT2", subtype="tension_pair",
            lifecycle_state="rebalanced",
        )
        ctx = _make_ctx(pts, state="rebalanced")
        mode = ParadoxOps()
        r = mode.handle("PDX-F12", {"payload": {
            "tensionId": "PTS-LT2", "targetState": "archived",
        }}, ctx)
        assert r.success
        assert ctx["paradox_registry"].get("PTS-LT2").lifecycle_state == "archived"

    def test_invalid_rejected(self):
        pts = ParadoxTensionSet(
            tension_id="PTS-LT3", subtype="tension_pair",
            lifecycle_state="detected",
        )
        ctx = _make_ctx(pts, state="detected")
        mode = ParadoxOps()
        r = mode.handle("PDX-F12", {"payload": {
            "tensionId": "PTS-LT3", "targetState": "sealed",
        }}, ctx)
        assert not r.success

    def test_terminal(self):
        pts = ParadoxTensionSet(
            tension_id="PTS-LT4", subtype="tension_pair",
            lifecycle_state="archived",
        )
        ctx = _make_ctx(pts, state="archived")
        mode = ParadoxOps()
        r = mode.handle("PDX-F12", {"payload": {
            "tensionId": "PTS-LT4", "targetState": "active",
        }}, ctx)
        assert not r.success


# ── ParadoxOps Registration ─────────────────────────────────────


class TestParadoxOpsRegistration:

    def test_domain_name(self):
        mode = ParadoxOps()
        assert mode.domain == "paradoxops"

    def test_twelve_handlers(self):
        mode = ParadoxOps()
        assert len(mode._handlers) == 12

    def test_ids_well_formed(self):
        import re
        mode = ParadoxOps()
        pattern = re.compile(r"^PDX-F\d{2}$")
        for fid in mode._handlers:
            assert pattern.match(fid), f"Malformed: {fid}"

    def test_has_handler(self):
        mode = ParadoxOps()
        for i in range(1, 13):
            assert mode.has_handler(f"PDX-F{i:02d}")

    def test_unknown_handler_error(self):
        mode = ParadoxOps()
        assert not mode.has_handler("PDX-F99")


# ── ParadoxOps Integration ──────────────────────────────────────


class TestParadoxOpsIntegration:

    def _run_full_lifecycle(self, subtype, poles, ctx):
        mode = ParadoxOps()
        tension_id = f"PTS-INT-{subtype}"

        # F01: Create
        r = mode.handle("PDX-F01", {"payload": {
            "tensionId": tension_id,
            "subtype": subtype,
            "poles": poles,
        }}, ctx)
        assert r.success, f"Create failed: {r.error}"

        # Transition to active
        ctx["tension_lifecycle"].transition(tension_id, TensionLifecycleState.ACTIVE)
        pts = ctx["paradox_registry"].get(tension_id)
        pts.lifecycle_state = "active"
        ctx["paradox_registry"].update(pts)

        # F03: Attach dimensions
        for dim_name in ("time", "risk", "authority"):
            r = mode.handle("PDX-F03", {"payload": {
                "tensionId": tension_id, "dimensionName": dim_name,
            }}, ctx)
            assert r.success, f"Attach {dim_name} failed: {r.error}"

        # F04: Shift time and risk
        pts = ctx["paradox_registry"].get(tension_id)
        time_dim = next(d for d in pts.dimensions if d.name == "time")
        risk_dim = next(d for d in pts.dimensions if d.name == "risk")

        mode.handle("PDX-F04", {"payload": {
            "tensionId": tension_id,
            "dimensionId": time_dim.dimension_id,
            "newValue": 0.8,
        }}, ctx)
        mode.handle("PDX-F04", {"payload": {
            "tensionId": tension_id,
            "dimensionId": risk_dim.dimension_id,
            "newValue": 0.7,
        }}, ctx)

        # F05: Compute pressure
        r = mode.handle("PDX-F05", {"payload": {"tensionId": tension_id}}, ctx)
        assert r.success

        # F06: Compute imbalance
        r = mode.handle("PDX-F06", {"payload": {"tensionId": tension_id}}, ctx)
        assert r.success

        # F07: Evaluate thresholds
        r = mode.handle("PDX-F07", {"payload": {"tensionId": tension_id}}, ctx)
        assert r.success

        # F09: Detect interdimensional drift
        r = mode.handle("PDX-F09", {"payload": {"tensionId": tension_id}}, ctx)
        assert r.success

        # Check state
        pts = ctx["paradox_registry"].get(tension_id)
        return pts

    def test_full_lifecycle_pair(self):
        ctx = _make_ctx()
        poles = [
            {"poleId": "A", "label": "Speed", "weight": 2.0},
            {"poleId": "B", "label": "Control", "weight": 1.0},
        ]
        pts = self._run_full_lifecycle("tension_pair", poles, ctx)
        assert pts.pressure_score > 0
        assert len(pts.imbalance_vector) == 1

    def test_full_lifecycle_triple(self):
        ctx = _make_ctx()
        poles = [
            {"poleId": "A", "label": "Speed", "weight": 2.0},
            {"poleId": "B", "label": "Control", "weight": 1.0},
            {"poleId": "C", "label": "Stability", "weight": 1.0},
        ]
        pts = self._run_full_lifecycle("tension_triple", poles, ctx)
        assert len(pts.imbalance_vector) == 3

    def test_money_demo(self):
        """Money demo: Speed-Control-Stability triple with authority stale."""
        ctx = _make_ctx()
        mode = ParadoxOps()
        tid = "PTS-MONEY"

        # Create triple
        r = mode.handle("PDX-F01", {"payload": {
            "tensionId": tid,
            "subtype": "tension_triple",
            "poles": [
                {"poleId": "P1", "label": "Speed", "weight": 1.5},
                {"poleId": "P2", "label": "Control", "weight": 1.0},
                {"poleId": "P3", "label": "Stability", "weight": 1.0},
            ],
        }}, ctx)
        assert r.success

        # Transition to active
        ctx["tension_lifecycle"].transition(tid, TensionLifecycleState.ACTIVE)
        pts = ctx["paradox_registry"].get(tid)
        pts.lifecycle_state = "active"
        ctx["paradox_registry"].update(pts)

        # Attach time, risk, authority
        for dim in ("time", "risk", "authority"):
            mode.handle("PDX-F03", {"payload": {
                "tensionId": tid, "dimensionName": dim,
            }}, ctx)

        pts = ctx["paradox_registry"].get(tid)
        time_d = next(d for d in pts.dimensions if d.name == "time")
        risk_d = next(d for d in pts.dimensions if d.name == "risk")

        # Shift time compressed
        mode.handle("PDX-F04", {"payload": {
            "tensionId": tid, "dimensionId": time_d.dimension_id, "newValue": 0.8,
        }}, ctx)
        # Shift risk increased
        mode.handle("PDX-F04", {"payload": {
            "tensionId": tid, "dimensionId": risk_d.dimension_id, "newValue": 0.7,
        }}, ctx)
        # Authority stays at 0.0 (stale)

        # Compute pressure
        r = mode.handle("PDX-F05", {"payload": {"tensionId": tid}}, ctx)
        assert r.success
        pts = ctx["paradox_registry"].get(tid)

        # Detect interdimensional drift
        r = mode.handle("PDX-F09", {"payload": {"tensionId": tid}}, ctx)
        assert r.success
        assert len(r.drift_signals) == 1
        assert r.drift_signals[0]["severity"] == "red"
        assert "authority" in r.drift_signals[0]["staleDimensions"]

        # If elevated, promote to drift
        if pts.lifecycle_state == "elevated":
            r = mode.handle("PDX-F08", {"payload": {"tensionId": tid}}, ctx)
            assert r.success

        # Seal
        # Need to get to a state that allows sealing
        lc = ctx["tension_lifecycle"]
        current = lc.get_state(tid)
        # Navigate to a sealable state
        if current == TensionLifecycleState.ACTIVE:
            lc.transition(tid, TensionLifecycleState.ELEVATED)
            lc.transition(tid, TensionLifecycleState.PROMOTED_TO_DRIFT)
            pts.lifecycle_state = "promoted_to_drift"
            ctx["paradox_registry"].update(pts)

        r = mode.handle("PDX-F10", {"payload": {"tensionId": tid}}, ctx)
        assert r.success

        # Issue patch
        r = mode.handle("PDX-F11", {"payload": {"tensionId": tid}}, ctx)
        assert r.success
        ev = r.events_emitted[0]
        assert "clarify_authority" in ev["recommendedActions"]

    def test_cross_handler_state(self):
        """State changes from one handler are visible to the next."""
        ctx = _make_ctx()
        mode = ParadoxOps()
        mode.handle("PDX-F01", {"payload": {
            "tensionId": "PTS-CROSS",
            "subtype": "tension_pair",
            "poles": [
                {"poleId": "A", "label": "Speed"},
                {"poleId": "B", "label": "Control"},
            ],
        }}, ctx)
        pts = ctx["paradox_registry"].get("PTS-CROSS")
        assert pts is not None
        assert pts.lifecycle_state == "detected"

    def test_replay_determinism(self):
        """Same inputs produce same results."""
        mode = ParadoxOps()
        event = {"payload": {
            "tensionId": "PTS-DET",
            "subtype": "tension_pair",
            "poles": [
                {"poleId": "A", "label": "Speed"},
                {"poleId": "B", "label": "Control"},
            ],
        }}
        ctx1 = _make_ctx()
        ctx2 = _make_ctx()
        r1 = mode.handle("PDX-F01", event, ctx1)
        r2 = mode.handle("PDX-F01", event, ctx2)
        assert r1.replay_hash == r2.replay_hash
