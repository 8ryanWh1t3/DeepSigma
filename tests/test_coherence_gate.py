"""Tests for core.coherence_gate — composable enforcement gate."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC_ROOT = _REPO_ROOT / "src"
if str(_SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(_SRC_ROOT))

from core.coherence_gate import CoherenceGate, GateConfig, GateResult, Signal  # noqa: E402


class TestSignal:
    def test_three_values(self):
        assert len(Signal) == 3

    def test_values(self):
        assert Signal.GREEN.value == "GREEN"
        assert Signal.YELLOW.value == "YELLOW"
        assert Signal.RED.value == "RED"

    def test_str_enum(self):
        assert isinstance(Signal.GREEN, str)


class TestGateConfig:
    def test_defaults(self):
        cfg = GateConfig()
        assert cfg.green_threshold == 80.0
        assert cfg.yellow_threshold == 60.0
        assert cfg.tool_allowlist == []
        assert cfg.cost_cap_usd == 0.0


class TestGateResult:
    def test_fields(self):
        r = GateResult(signal=Signal.GREEN, score=85.0, grade="A")
        assert r.signal == Signal.GREEN
        assert r.enforcement == ""
        assert r.violations == []


class TestCoherenceGateEvaluate:
    """Tests for CoherenceGate.evaluate() using the coherence_pipeline fixture."""

    def test_green_signal(self, coherence_pipeline):
        dlr, rs, ds, mg = coherence_pipeline
        gate = CoherenceGate(config=GateConfig(green_threshold=0, yellow_threshold=0))
        result = gate.evaluate(dlr_builder=dlr, rs=rs, ds=ds, mg=mg)
        assert result.signal == Signal.GREEN
        assert result.enforcement == ""

    def test_result_has_score(self, coherence_pipeline):
        dlr, rs, ds, mg = coherence_pipeline
        gate = CoherenceGate()
        result = gate.evaluate(dlr_builder=dlr, rs=rs, ds=ds, mg=mg)
        assert isinstance(result.score, (int, float))

    def test_result_has_grade(self, coherence_pipeline):
        dlr, rs, ds, mg = coherence_pipeline
        gate = CoherenceGate()
        result = gate.evaluate(dlr_builder=dlr, rs=rs, ds=ds, mg=mg)
        assert isinstance(result.grade, str)

    def test_red_on_high_threshold(self, coherence_pipeline):
        dlr, rs, ds, mg = coherence_pipeline
        gate = CoherenceGate(config=GateConfig(green_threshold=999, yellow_threshold=998))
        result = gate.evaluate(dlr_builder=dlr, rs=rs, ds=ds, mg=mg)
        assert result.signal == Signal.RED
        assert "BLOCKED" in result.enforcement

    def test_yellow_on_mid_threshold(self, coherence_pipeline):
        dlr, rs, ds, mg = coherence_pipeline
        gate = CoherenceGate(config=GateConfig(green_threshold=999, yellow_threshold=0))
        result = gate.evaluate(dlr_builder=dlr, rs=rs, ds=ds, mg=mg)
        assert result.signal == Signal.YELLOW
        assert "CAUTION" in result.enforcement

    def test_tool_allowlist_blocks(self, coherence_pipeline):
        dlr, rs, ds, mg = coherence_pipeline
        gate = CoherenceGate(config=GateConfig(
            green_threshold=0, yellow_threshold=0,
            tool_allowlist=["safe_tool"],
        ))
        result = gate.evaluate(dlr_builder=dlr, rs=rs, ds=ds, mg=mg, tool_name="bad_tool")
        assert result.signal == Signal.RED
        assert any("allowlist" in v for v in result.violations)

    def test_tool_allowlist_allows(self, coherence_pipeline):
        dlr, rs, ds, mg = coherence_pipeline
        gate = CoherenceGate(config=GateConfig(
            green_threshold=0, yellow_threshold=0,
            tool_allowlist=["safe_tool"],
        ))
        result = gate.evaluate(dlr_builder=dlr, rs=rs, ds=ds, mg=mg, tool_name="safe_tool")
        assert result.signal == Signal.GREEN

    def test_cost_cap_blocks(self, coherence_pipeline):
        dlr, rs, ds, mg = coherence_pipeline
        gate = CoherenceGate(config=GateConfig(
            green_threshold=0, yellow_threshold=0,
            cost_cap_usd=1.0,
        ))
        result = gate.evaluate(dlr_builder=dlr, rs=rs, ds=ds, mg=mg, cost_usd=5.0)
        assert result.signal == Signal.RED
        assert any("Cost" in v for v in result.violations)

    def test_cost_cap_within(self, coherence_pipeline):
        dlr, rs, ds, mg = coherence_pipeline
        gate = CoherenceGate(config=GateConfig(
            green_threshold=0, yellow_threshold=0,
            cost_cap_usd=10.0,
        ))
        result = gate.evaluate(dlr_builder=dlr, rs=rs, ds=ds, mg=mg, cost_usd=5.0)
        assert result.signal == Signal.GREEN

    def test_details_has_dimensions(self, coherence_pipeline):
        dlr, rs, ds, mg = coherence_pipeline
        gate = CoherenceGate()
        result = gate.evaluate(dlr_builder=dlr, rs=rs, ds=ds, mg=mg)
        assert "dimensions" in result.details

    def test_no_pipeline_still_works(self):
        gate = CoherenceGate(config=GateConfig(green_threshold=0, yellow_threshold=0))
        result = gate.evaluate()
        assert isinstance(result.signal, Signal)

    def test_default_config(self, coherence_pipeline):
        dlr, rs, ds, mg = coherence_pipeline
        gate = CoherenceGate()
        result = gate.evaluate(dlr_builder=dlr, rs=rs, ds=ds, mg=mg)
        assert isinstance(result, GateResult)
