"""Tests for ExhaustCallbackHandler."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from langchain_deepsigma.exhaust import ExhaustCallbackHandler


class TestExhaustCallbackHandler:

    def test_init_defaults(self):
        h = ExhaustCallbackHandler()
        assert h.name == "exhaust_callback"
        assert h._project == "default"
        assert h._buffer == []

    def test_on_llm_start_buffers_event(self, run_id, parent_run_id):
        h = ExhaustCallbackHandler(flush_interval=999)
        h._flush = MagicMock()
        h.on_llm_start(
            {"name": "test-model", "kwargs": {}},
            ["Hello"],
            run_id=run_id,
            parent_run_id=parent_run_id,
        )
        assert len(h._buffer) == 1
        assert h._buffer[0]["event_type"] == "prompt"

    def test_on_llm_end_emits_response_and_metric(self, run_id):
        h = ExhaustCallbackHandler(flush_interval=999)
        h._flush = MagicMock()
        h._run_start[str(run_id)] = 0
        h._run_model[str(run_id)] = "test"
        response = MagicMock()
        response.generations = [[MagicMock(text="Hi there")]]
        h.on_llm_end(response, run_id=run_id)
        assert len(h._buffer) == 2
        types = [e["event_type"] for e in h._buffer]
        assert "response" in types
        assert "metric" in types

    def test_on_tool_start_emits_tool_call(self, run_id):
        h = ExhaustCallbackHandler(flush_interval=999)
        h._flush = MagicMock()
        h.on_tool_start({"name": "calculator"}, "2+2", run_id=run_id)
        assert h._buffer[-1]["event_type"] == "tool_call"

    def test_on_chain_end_triggers_flush(self, run_id):
        h = ExhaustCallbackHandler()
        h._flush = MagicMock()
        h.on_chain_end({"output": "done"}, run_id=run_id)
        h._flush.assert_called_once()

    def test_session_integration(self, run_id):
        """When session is attached, llm_end logs a decision."""
        mock_session = MagicMock()
        h = ExhaustCallbackHandler(flush_interval=999, session=mock_session)
        h._flush = MagicMock()
        h._run_start[str(run_id)] = 0
        h._run_model[str(run_id)] = "test"
        response = MagicMock()
        response.generations = [[MagicMock(text="output")]]
        h.on_llm_end(response, run_id=run_id)
        mock_session.log_decision.assert_called_once()
