"""Tests for MEE demo and CLI integration."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC_ROOT = _REPO_ROOT / "src"
if str(_SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(_SRC_ROOT))

from core.model_exchange import ModelExchangeEngine  # noqa: E402
from core.model_exchange.adapters import (  # noqa: E402
    ApexAdapter,
    ClaudeAdapter,
    GGUFAdapter,
    MockAdapter,
    OpenAIAdapter,
)
from core.model_exchange.models import EvaluationResult, ReasoningResult  # noqa: E402


def _build_engine():
    engine = ModelExchangeEngine()
    engine.registry.register("apex", ApexAdapter())
    engine.registry.register("mock", MockAdapter())
    engine.registry.register("openai", OpenAIAdapter())
    engine.registry.register("claude", ClaudeAdapter())
    engine.registry.register("gguf", GGUFAdapter())
    return engine


def _sample_packet():
    return {
        "request_id": "REQ-DEMO-TEST-001",
        "topic": "SLA Compliance Review",
        "question": "Is the current deployment within SLA targets?",
        "evidence": ["EVIDENCE-LATENCY-P99", "EVIDENCE-ERROR-RATE"],
        "ttl": 3600,
    }


class TestModelExchangeEngine:
    def test_run_all_adapters(self):
        engine = _build_engine()
        ev = engine.run(_sample_packet(), engine.registry.list_adapters())
        assert isinstance(ev, EvaluationResult)
        assert len(ev.adapter_results) == 5

    def test_run_single(self):
        engine = _build_engine()
        result = engine.run_single(_sample_packet(), "apex")
        assert isinstance(result, ReasoningResult)
        assert result.adapter_name == "apex"

    def test_health(self):
        engine = _build_engine()
        health = engine.health()
        assert health["ok"] is True
        assert health["adapter_count"] == 5

    def test_evaluation_scores_bounded(self):
        engine = _build_engine()
        ev = engine.run(_sample_packet(), ["apex", "mock"])
        for attr in [
            "agreement_score",
            "contradiction_score",
            "novelty_score",
            "evidence_coverage_score",
            "drift_likelihood",
        ]:
            val = getattr(ev, attr)
            assert 0 <= val <= 1, f"{attr} = {val} out of bounds"

    def test_escalation_is_valid(self):
        engine = _build_engine()
        ev = engine.run(_sample_packet(), ["apex", "mock"])
        valid = {"accept-for-drafting", "human-review", "authority-review", "reject"}
        assert ev.recommended_escalation in valid

    def test_evaluation_to_dict(self):
        engine = _build_engine()
        ev = engine.run(_sample_packet(), ["apex", "mock"])
        d = ev.to_dict()
        assert "requestId" in d
        assert "agreementScore" in d
        assert isinstance(d["adapterResults"], list)

    def test_evaluation_json_serializable(self):
        engine = _build_engine()
        ev = engine.run(_sample_packet(), ["apex", "mock"])
        raw = json.dumps(ev.to_dict())
        assert len(raw) > 0
        data = json.loads(raw)
        assert data["requestId"] == "REQ-DEMO-TEST-001"

    def test_run_with_no_evidence(self):
        engine = _build_engine()
        packet = {
            "request_id": "REQ-NO-EV",
            "question": "Any issues?",
        }
        ev = engine.run(packet, ["mock"])
        assert isinstance(ev, EvaluationResult)


class TestDemoScript:
    def test_demo_runs(self, capsys):
        """The demo script should run without errors."""
        from core.examples.model_exchange_demo import run_demo
        run_demo()
        captured = capsys.readouterr()
        assert "MODEL EXCHANGE ENGINE" in captured.out
        assert "Escalation" in captured.out

    def test_demo_prints_all_adapters(self, capsys):
        from core.examples.model_exchange_demo import run_demo
        run_demo()
        captured = capsys.readouterr()
        for name in ["apex", "mock", "openai", "claude", "gguf"]:
            assert name in captured.out


class TestCLIIntegration:
    def test_mee_demo(self, capsys, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["coherence", "mee", "demo"])
        from core.cli import main
        try:
            main()
        except SystemExit:
            pass
        captured = capsys.readouterr()
        assert "Model Exchange Engine" in captured.out

    def test_mee_demo_json(self, capsys, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["coherence", "mee", "demo", "--json"])
        from core.cli import main
        try:
            main()
        except SystemExit:
            pass
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert "requestId" in data
        assert "agreementScore" in data

    def test_mee_health(self, capsys, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["coherence", "mee", "health"])
        from core.cli import main
        try:
            main()
        except SystemExit:
            pass
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["ok"] is True
        assert data["adapter_count"] == 5


class TestBoundaryEnforcement:
    """Verify MEE cannot commit canon or bypass authority."""

    def test_boundary_note_constant(self):
        from core.model_exchange.models import MODEL_EXCHANGE_BOUNDARY_NOTE
        assert "exhaust" in MODEL_EXCHANGE_BOUNDARY_NOTE
        assert "judgment" in MODEL_EXCHANGE_BOUNDARY_NOTE

    def test_engine_has_no_commit_method(self):
        engine = _build_engine()
        assert not hasattr(engine, "commit")
        assert not hasattr(engine, "apply")
        assert not hasattr(engine, "patch")
        assert not hasattr(engine, "approve")

    def test_adapter_has_no_write_methods(self):
        for cls in [ApexAdapter, MockAdapter, OpenAIAdapter, ClaudeAdapter, GGUFAdapter]:
            adapter = cls()
            assert not hasattr(adapter, "commit")
            assert not hasattr(adapter, "write_canon")
            assert not hasattr(adapter, "approve")
