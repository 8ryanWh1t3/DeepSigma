"""Agent wrapper that logs decisions through the coherence pipeline.

Wraps any agent object that exposes a ``.run(input)`` method.
Each invocation logs intent, tool calls, and completion as sealed
episodes in the decision log.

Usage::

    from openai_deepsigma import DeepSigmaAgentWrapper
    from core import AgentSession

    session = AgentSession("my-agent")
    wrapper = DeepSigmaAgentWrapper(agent, session)
    result = wrapper.run("What is the weather?")
    print(result.output)
    print(result.episode_count)
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class AgentRunResult:
    """Result of a wrapped agent run."""

    output: str
    episode_count: int
    drift_signals: List[Dict[str, Any]] = field(default_factory=list)
    raw_result: Any = None


class DeepSigmaAgentWrapper:
    """Wraps an agent with coherence pipeline logging.

    The wrapped agent must expose a ``.run(input_text)`` method that
    returns an object with:
    - ``.output`` or ``.final_output`` (str): the agent's response
    - ``.tool_calls`` (list, optional): tool calls made during the run

    Parameters
    ----------
    agent
        The agent to wrap.
    session
        An ``AgentSession`` instance for decision logging.
    detect_drift : bool
        When True and run_count > 1, automatically detect drift.
    """

    def __init__(
        self,
        agent: Any,
        session: Any,
        detect_drift: bool = False,
    ) -> None:
        self._agent = agent
        self._session = session
        self._detect_drift = detect_drift
        self._run_count = 0

    @property
    def session(self) -> Any:
        return self._session

    @property
    def run_count(self) -> int:
        return self._run_count

    def run(self, input_text: str, **kwargs: Any) -> AgentRunResult:
        """Run the agent and log decisions.

        Steps:
        1. Log intent decision (pre-run)
        2. Execute agent.run()
        3. Log each tool call as a separate decision
        4. Log completion decision (post-run)
        5. Optionally detect drift
        """
        self._run_count += 1

        # 1. Log intent
        intent_ep = self._session.log_decision({
            "action": "agent_intent",
            "reason": f"Agent invoked with: {input_text[:200]}",
            "decision_type": "intent",
            "actor": {"type": "agent", "id": self._session.agent_id},
        })

        # 2. Execute the agent
        raw_result = self._agent.run(input_text, **kwargs)

        # 3. Log tool calls
        tool_calls = getattr(raw_result, "tool_calls", None) or []
        for tc in tool_calls:
            tool_name = tc.get("name", "unknown") if isinstance(tc, dict) else getattr(tc, "name", "unknown")
            tool_input = tc.get("input", "") if isinstance(tc, dict) else getattr(tc, "input", "")
            self._session.log_decision({
                "action": f"tool_call:{tool_name}",
                "reason": f"Tool call: {tool_name}",
                "decision_type": "tool_call",
                "actor": {"type": "agent", "id": self._session.agent_id},
            })

        # 4. Log completion
        output = self._extract_output(raw_result)
        self._session.log_decision({
            "action": "agent_completion",
            "reason": f"Agent completed: {output[:200]}",
            "decision_type": "completion",
            "actor": {"type": "agent", "id": self._session.agent_id},
        })

        # 5. Detect drift
        drift_signals: List[Dict[str, Any]] = []
        if self._detect_drift and self._run_count > 1:
            drift_signals = self._session.detect_drift({
                "action": "drift_check",
                "reason": "Periodic drift detection",
                "actor": {"type": "agent", "id": self._session.agent_id},
            })

        episode_count = len(self._session._episodes)

        return AgentRunResult(
            output=output,
            episode_count=episode_count,
            drift_signals=drift_signals,
            raw_result=raw_result,
        )

    @staticmethod
    def _extract_output(result: Any) -> str:
        """Extract output string from agent result."""
        if hasattr(result, "final_output"):
            return str(result.final_output)
        if hasattr(result, "output"):
            return str(result.output)
        return str(result)
