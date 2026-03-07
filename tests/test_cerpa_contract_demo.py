"""Tests for CERPA demos — Contract Delivery and Agent Supervision."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC_ROOT = _REPO_ROOT / "src"
if str(_SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(_SRC_ROOT))

from core.examples.cerpa_contract_demo import run_contract_demo  # noqa: E402
from core.examples.cerpa_agent_supervision_demo import (  # noqa: E402
    run_agent_supervision_demo,
)


class TestContractDemo:
    def test_contract_runs(self, capsys: pytest.CaptureFixture[str]) -> None:
        result = run_contract_demo()
        assert isinstance(result, dict)
        captured = capsys.readouterr()
        assert "CLAIM" in captured.out
        assert "EVENT" in captured.out
        assert "REVIEW" in captured.out
        assert "PATCH" in captured.out
        assert "APPLY" in captured.out

    def test_contract_cycle_structure(self) -> None:
        result = run_contract_demo()
        assert "cycle_id" in result
        assert "claim" in result
        assert "event" in result
        assert "review" in result
        assert "patch" in result
        assert "apply_result" in result
        assert result["status"] == "applied"

    def test_contract_domain_is_actionops(self) -> None:
        result = run_contract_demo()
        assert result["domain"] == "actionops"


class TestAgentSupervisionDemo:
    def test_agent_demo_runs(self, capsys: pytest.CaptureFixture[str]) -> None:
        result = run_agent_supervision_demo()
        assert isinstance(result, dict)
        captured = capsys.readouterr()
        assert "CLAIM" in captured.out
        assert "EVENT" in captured.out
        assert "REVIEW" in captured.out
        assert "PATCH" in captured.out
        assert "APPLY" in captured.out

    def test_agent_demo_detects_violation(self) -> None:
        result = run_agent_supervision_demo()
        assert result["review"]["verdict"] == "violation"
        assert result["review"]["drift_detected"] is True

    def test_agent_demo_strengthens(self) -> None:
        result = run_agent_supervision_demo()
        assert result["patch"]["action"] == "strengthen"

    def test_agent_demo_domain_is_authorityops(self) -> None:
        result = run_agent_supervision_demo()
        assert result["domain"] == "authorityops"
