"""Tests for paradox_ops models, enums, validators, registry, and dimensions."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC_ROOT = _REPO_ROOT / "src"
if str(_SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(_SRC_ROOT))

from core.paradox_ops.models import (
    DimensionKind,
    InterDimensionalDrift,
    ParadoxTensionSet,
    PatchAction,
    TensionDimension,
    TensionLifecycleState,
    TensionPatch,
    TensionPole,
    TensionSubtype,
)
from core.paradox_ops.dimensions import (
    COMMON_DIMENSIONS,
    COMMON_DIMENSION_NAMES,
    UNCOMMON_DIMENSIONS,
    DimensionRegistry,
)
from core.paradox_ops.validators import (
    validate_dimension_shift,
    validate_patch,
    validate_tension_set,
)
from core.paradox_ops.registry import ParadoxRegistry


# ── TensionPole ──────────────────────────────────────────────────


class TestTensionPole:

    def test_construction(self):
        p = TensionPole(pole_id="P-1", label="Speed")
        assert p.pole_id == "P-1"
        assert p.label == "Speed"

    def test_defaults(self):
        p = TensionPole(pole_id="P-1", label="X")
        assert p.weight == 1.0
        assert p.evidence_refs == []

    def test_custom_weight(self):
        p = TensionPole(pole_id="P-1", label="X", weight=2.5)
        assert p.weight == 2.5

    def test_evidence_refs(self):
        p = TensionPole(pole_id="P-1", label="X", evidence_refs=["a", "b"])
        assert p.evidence_refs == ["a", "b"]


# ── TensionDimension ────────────────────────────────────────────


class TestTensionDimension:

    def test_construction(self):
        d = TensionDimension(dimension_id="D-1", name="time")
        assert d.dimension_id == "D-1"
        assert d.name == "time"

    def test_default_kind(self):
        d = TensionDimension(dimension_id="D-1", name="time")
        assert d.kind == "common"

    def test_governance_flag(self):
        d = TensionDimension(dimension_id="D-1", name="authority", is_governance_relevant=True)
        assert d.is_governance_relevant is True

    def test_threshold(self):
        d = TensionDimension(dimension_id="D-1", name="risk", threshold=0.4)
        assert d.threshold == 0.4

    def test_shift_values(self):
        d = TensionDimension(dimension_id="D-1", name="time", current_value=0.8, previous_value=0.2)
        assert d.current_value == 0.8
        assert d.previous_value == 0.2


# ── ParadoxTensionSet ───────────────────────────────────────────


class TestParadoxTensionSet:

    def test_construction(self):
        pts = ParadoxTensionSet(tension_id="PTS-1", subtype="tension_pair")
        assert pts.tension_id == "PTS-1"
        assert pts.subtype == "tension_pair"

    def test_subtype_values(self):
        for st in ("tension_pair", "tension_triple", "higher_order"):
            pts = ParadoxTensionSet(tension_id="PTS-1", subtype=st)
            assert pts.subtype == st

    def test_default_lifecycle(self):
        pts = ParadoxTensionSet(tension_id="PTS-1", subtype="tension_pair")
        assert pts.lifecycle_state == "detected"

    def test_empty_poles(self):
        pts = ParadoxTensionSet(tension_id="PTS-1", subtype="tension_pair")
        assert pts.poles == []

    def test_empty_dimensions(self):
        pts = ParadoxTensionSet(tension_id="PTS-1", subtype="tension_pair")
        assert pts.dimensions == []

    def test_version_default(self):
        pts = ParadoxTensionSet(tension_id="PTS-1", subtype="tension_pair")
        assert pts.version == "1.0.0"


# ── TensionPatch ─────────────────────────────────────────────────


class TestTensionPatch:

    def test_construction(self):
        p = TensionPatch(patch_id="TP-1", tension_id="PTS-1")
        assert p.patch_id == "TP-1"
        assert p.tension_id == "PTS-1"

    def test_actions_list(self):
        p = TensionPatch(patch_id="TP-1", tension_id="PTS-1",
                         recommended_actions=["clarify_authority"])
        assert "clarify_authority" in p.recommended_actions

    def test_rationale(self):
        p = TensionPatch(patch_id="TP-1", tension_id="PTS-1", rationale="test reason")
        assert p.rationale == "test reason"

    def test_applied_at_default(self):
        p = TensionPatch(patch_id="TP-1", tension_id="PTS-1")
        assert p.applied_at is None


# ── InterDimensionalDrift ───────────────────────────────────────


class TestInterDimensionalDriftModel:

    def test_construction(self):
        d = InterDimensionalDrift(drift_id="DS-1", tension_id="PTS-1")
        assert d.drift_id == "DS-1"

    def test_severity_default(self):
        d = InterDimensionalDrift(drift_id="DS-1", tension_id="PTS-1")
        assert d.severity == "red"

    def test_shifted_stale_lists(self):
        d = InterDimensionalDrift(
            drift_id="DS-1", tension_id="PTS-1",
            shifted_dimensions=["time", "risk"],
            stale_dimensions=["authority"],
        )
        assert len(d.shifted_dimensions) == 2
        assert len(d.stale_dimensions) == 1

    def test_promoted_from_pressure(self):
        d = InterDimensionalDrift(drift_id="DS-1", tension_id="PTS-1",
                                  promoted_from_pressure=0.85)
        assert d.promoted_from_pressure == 0.85


# ── Enums ────────────────────────────────────────────────────────


class TestEnums:

    def test_tension_subtype_values(self):
        assert TensionSubtype.TENSION_PAIR.value == "tension_pair"
        assert TensionSubtype.TENSION_TRIPLE.value == "tension_triple"
        assert TensionSubtype.HIGHER_ORDER.value == "higher_order"

    def test_lifecycle_state_values(self):
        assert len(TensionLifecycleState) == 8

    def test_dimension_kind_values(self):
        assert DimensionKind.COMMON.value == "common"
        assert DimensionKind.UNCOMMON.value == "uncommon"

    def test_patch_action_values(self):
        assert len(PatchAction) == 8
        assert PatchAction.CLARIFY_AUTHORITY.value == "clarify_authority"

    def test_lifecycle_str_compat(self):
        assert TensionLifecycleState.DETECTED == "detected"

    def test_subtype_str_compat(self):
        assert TensionSubtype.TENSION_PAIR == "tension_pair"


# ── DimensionRegistry ───────────────────────────────────────────


class TestDimensionRegistry:

    def test_common_loaded(self):
        reg = DimensionRegistry()
        assert len(reg.list_common()) == 6

    def test_get_known(self):
        reg = DimensionRegistry()
        t = reg.get("time")
        assert t is not None
        assert t["name"] == "time"

    def test_get_unknown(self):
        reg = DimensionRegistry()
        assert reg.get("nonexistent") is None

    def test_register_custom(self):
        reg = DimensionRegistry()
        reg.register("custom_dim", threshold=0.6)
        assert reg.get("custom_dim") is not None

    def test_create_dimension(self):
        reg = DimensionRegistry()
        dim = reg.create_dimension("authority")
        assert dim.name == "authority"
        assert dim.is_governance_relevant is True
        assert dim.dimension_id.startswith("DIM-")

    def test_create_dimension_unknown(self):
        reg = DimensionRegistry()
        with pytest.raises(ValueError, match="Unknown dimension"):
            reg.create_dimension("nonexistent")

    def test_create_defaults(self):
        reg = DimensionRegistry()
        dims = reg.create_default_dimensions("PTS-001")
        assert len(dims) == 6
        names = {d.name for d in dims}
        assert "time" in names
        assert "authority" in names

    def test_list_all(self):
        reg = DimensionRegistry()
        all_dims = reg.list_all()
        assert len(all_dims) == 16  # 6 common + 10 uncommon


# ── ValidateTensionSet ──────────────────────────────────────────


class TestValidateTensionSet:

    def test_valid_pair(self):
        data = {
            "subtype": "tension_pair",
            "poles": [
                {"poleId": "A", "label": "Speed", "weight": 1.0},
                {"poleId": "B", "label": "Control", "weight": 1.0},
            ],
        }
        assert validate_tension_set(data) == []

    def test_valid_triple(self):
        data = {
            "subtype": "tension_triple",
            "poles": [
                {"poleId": "A", "label": "Speed", "weight": 1.0},
                {"poleId": "B", "label": "Control", "weight": 1.0},
                {"poleId": "C", "label": "Stability", "weight": 1.0},
            ],
        }
        assert validate_tension_set(data) == []

    def test_valid_higher_order(self):
        data = {
            "subtype": "higher_order",
            "poles": [{"poleId": f"P-{i}", "label": f"L{i}", "weight": 1.0} for i in range(4)],
        }
        assert validate_tension_set(data) == []

    def test_too_few_poles(self):
        data = {"subtype": "tension_pair", "poles": [{"poleId": "A", "label": "X"}]}
        errors = validate_tension_set(data)
        assert any("at least 2" in e for e in errors)

    def test_wrong_subtype_count_pair(self):
        data = {
            "subtype": "tension_pair",
            "poles": [{"poleId": f"P-{i}", "label": f"L{i}"} for i in range(3)],
        }
        errors = validate_tension_set(data)
        assert any("exactly 2" in e for e in errors)

    def test_wrong_subtype_count_triple(self):
        data = {
            "subtype": "tension_triple",
            "poles": [{"poleId": f"P-{i}", "label": f"L{i}"} for i in range(2)],
        }
        errors = validate_tension_set(data)
        assert any("exactly 3" in e or "3 poles" in e for e in errors)

    def test_duplicate_pole_ids(self):
        data = {
            "subtype": "tension_pair",
            "poles": [
                {"poleId": "A", "label": "Speed"},
                {"poleId": "A", "label": "Control"},
            ],
        }
        errors = validate_tension_set(data)
        assert any("unique" in e.lower() for e in errors)

    def test_zero_weight(self):
        data = {
            "subtype": "tension_pair",
            "poles": [
                {"poleId": "A", "label": "Speed", "weight": 0},
                {"poleId": "B", "label": "Control", "weight": 1.0},
            ],
        }
        errors = validate_tension_set(data)
        assert any("weight" in e.lower() for e in errors)

    def test_invalid_pressure(self):
        data = {
            "subtype": "tension_pair",
            "poles": [
                {"poleId": "A", "label": "Speed"},
                {"poleId": "B", "label": "Control"},
            ],
            "pressureScore": 1.5,
        }
        errors = validate_tension_set(data)
        assert any("pressure" in e.lower() for e in errors)

    def test_no_common_dimension(self):
        data = {
            "subtype": "tension_pair",
            "poles": [
                {"poleId": "A", "label": "Speed"},
                {"poleId": "B", "label": "Control"},
            ],
            "dimensions": [{"name": "reversibility"}],
        }
        errors = validate_tension_set(data)
        assert any("common dimension" in e.lower() for e in errors)


# ── ValidateDimensionShift ──────────────────────────────────────


class TestValidateDimensionShift:

    def _make_pts(self):
        return ParadoxTensionSet(
            tension_id="PTS-1", subtype="tension_pair",
            dimensions=[
                TensionDimension(dimension_id="DIM-01", name="time"),
            ],
        )

    def test_valid_shift(self):
        pts = self._make_pts()
        data = {"dimensionId": "DIM-01", "newValue": 0.8}
        assert validate_dimension_shift(data, pts) == []

    def test_unknown_dimension(self):
        pts = self._make_pts()
        data = {"dimensionId": "DIM-99", "newValue": 0.5}
        errors = validate_dimension_shift(data, pts)
        assert any("unknown" in e.lower() for e in errors)

    def test_non_numeric_value(self):
        pts = self._make_pts()
        data = {"dimensionId": "DIM-01", "newValue": "high"}
        errors = validate_dimension_shift(data, pts)
        assert any("numeric" in e.lower() for e in errors)

    def test_camel_and_snake_keys(self):
        pts = self._make_pts()
        data = {"dimension_id": "DIM-01", "new_value": 0.5}
        assert validate_dimension_shift(data, pts) == []


# ── ParadoxRegistry ─────────────────────────────────────────────


class TestParadoxRegistry:

    def _make_pts(self, tid="PTS-1", state="detected"):
        return ParadoxTensionSet(tension_id=tid, subtype="tension_pair",
                                 lifecycle_state=state)

    def test_add_and_get(self):
        reg = ParadoxRegistry()
        pts = self._make_pts()
        reg.add(pts)
        assert reg.get("PTS-1") is pts

    def test_get_not_found(self):
        reg = ParadoxRegistry()
        assert reg.get("nonexistent") is None

    def test_update(self):
        reg = ParadoxRegistry()
        pts = self._make_pts()
        reg.add(pts)
        pts.pressure_score = 0.9
        reg.update(pts)
        assert reg.get("PTS-1").pressure_score == 0.9

    def test_remove(self):
        reg = ParadoxRegistry()
        pts = self._make_pts()
        reg.add(pts)
        assert reg.remove("PTS-1") is True
        assert reg.get("PTS-1") is None

    def test_list_active(self):
        reg = ParadoxRegistry()
        reg.add(self._make_pts("PTS-1", "active"))
        reg.add(self._make_pts("PTS-2", "archived"))
        active = reg.list_active()
        assert len(active) == 1
        assert active[0].tension_id == "PTS-1"

    def test_list_by_state(self):
        reg = ParadoxRegistry()
        reg.add(self._make_pts("PTS-1", "active"))
        reg.add(self._make_pts("PTS-2", "elevated"))
        reg.add(self._make_pts("PTS-3", "active"))
        by_active = reg.list_by_state("active")
        assert len(by_active) == 2
