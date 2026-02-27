"""Tests for DeepSigmaAgentWrapper."""
from __future__ import annotations

import pytest

from openai_deepsigma.wrapper import DeepSigmaAgentWrapper, AgentRunResult


class TestDeepSigmaAgentWrapper:

    def test_run_returns_agent_run_result(self, mock_agent, session):
        wrapper = DeepSigmaAgentWrapper(mock_agent, session)
        result = wrapper.run("hello")
        assert isinstance(result, AgentRunResult)
        assert result.output == "The answer is 4"

    def test_run_logs_intent_and_completion(self, mock_agent, session):
        wrapper = DeepSigmaAgentWrapper(mock_agent, session)
        wrapper.run("test input")
        # Should have at least intent + completion = 2 episodes
        assert len(session._episodes) >= 2

    def test_run_logs_tool_calls(self, mock_agent_with_tools, session):
        wrapper = DeepSigmaAgentWrapper(mock_agent_with_tools, session)
        result = wrapper.run("calculate something")
        # intent + 2 tool calls + completion = 4
        assert len(session._episodes) == 4
        types = [ep["decisionType"] for ep in session._episodes]
        assert types.count("tool_call") == 2

    def test_run_increments_count(self, mock_agent, session):
        wrapper = DeepSigmaAgentWrapper(mock_agent, session)
        assert wrapper.run_count == 0
        wrapper.run("first")
        assert wrapper.run_count == 1
        wrapper.run("second")
        assert wrapper.run_count == 2

    def test_episode_count_in_result(self, mock_agent, session):
        wrapper = DeepSigmaAgentWrapper(mock_agent, session)
        r1 = wrapper.run("first")
        assert r1.episode_count == 2  # intent + completion
        r2 = wrapper.run("second")
        assert r2.episode_count == 4  # cumulative

    def test_drift_detection_disabled(self, mock_agent, session):
        wrapper = DeepSigmaAgentWrapper(mock_agent, session, detect_drift=False)
        wrapper.run("first")
        result = wrapper.run("second")
        assert result.drift_signals == []

    def test_drift_detection_enabled(self, mock_agent, session):
        wrapper = DeepSigmaAgentWrapper(mock_agent, session, detect_drift=True)
        wrapper.run("first")
        result = wrapper.run("second")
        # May or may not have signals depending on data, but should not error
        assert isinstance(result.drift_signals, list)

    def test_raw_result_preserved(self, mock_agent, session):
        wrapper = DeepSigmaAgentWrapper(mock_agent, session)
        result = wrapper.run("hello")
        assert result.raw_result is not None
        assert result.raw_result.output == "The answer is 4"

    def test_session_property(self, mock_agent, session):
        wrapper = DeepSigmaAgentWrapper(mock_agent, session)
        assert wrapper.session is session

    def test_final_output_extraction(self, session):
        """Agents with .final_output should also work."""
        class FinalOutputAgent:
            def run(self, text, **kw):
                class R:
                    final_output = "final result"
                    tool_calls = []
                return R()

        wrapper = DeepSigmaAgentWrapper(FinalOutputAgent(), session)
        result = wrapper.run("test")
        assert result.output == "final result"

    def test_dict_tool_calls(self, session):
        """Tool calls as dicts should also work."""
        class DictToolAgent:
            def run(self, text, **kw):
                class R:
                    output = "done"
                    tool_calls = [
                        {"name": "search", "input": "query"},
                    ]
                return R()

        wrapper = DeepSigmaAgentWrapper(DictToolAgent(), session)
        result = wrapper.run("test")
        # intent + 1 tool call + completion = 3
        assert len(session._episodes) == 3
