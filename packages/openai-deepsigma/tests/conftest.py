"""Shared fixtures for openai-deepsigma tests."""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List

import pytest

# Ensure the package src is importable
PKG_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PKG_ROOT / "src"))

# Also ensure core is importable from repo root
REPO_ROOT = PKG_ROOT.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))


@dataclass
class MockToolCall:
    name: str = "calculator"
    input: str = "2+2"


@dataclass
class MockAgentResult:
    output: str = "The answer is 4"
    tool_calls: List[Any] = field(default_factory=list)


class MockAgent:
    """Mock agent with a .run() method."""

    def __init__(self, result=None):
        self._result = result or MockAgentResult()
        self.run_count = 0

    def run(self, input_text, **kwargs):
        self.run_count += 1
        return self._result


@pytest.fixture
def mock_agent():
    return MockAgent()


@pytest.fixture
def mock_agent_with_tools():
    result = MockAgentResult(
        output="Calculated",
        tool_calls=[
            MockToolCall(name="calculator", input="2+2"),
            MockToolCall(name="search", input="weather"),
        ],
    )
    return MockAgent(result=result)


@pytest.fixture
def session():
    from core.agent import AgentSession
    return AgentSession("test-agent")
