"""Tests for adapters.langchain_exhaust — ExhaustCallbackHandler."""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch
from uuid import uuid4


import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestExhaustCallbackHandler:
    def test_constructor_defaults(self):
        from adapters.langchain_exhaust import ExhaustCallbackHandler
        h = ExhaustCallbackHandler()
        assert h._endpoint == "http://localhost:8000/api/exhaust/events"
        assert h._project == "default"
        assert h._source == "langchain"
        assert h._buffer == []

    def test_constructor_custom(self):
        from adapters.langchain_exhaust import ExhaustCallbackHandler
        h = ExhaustCallbackHandler(
            endpoint="http://custom:9000/events",
            project="myproj",
            team="myteam",
            source="custom",
        )
        assert h._endpoint == "http://custom:9000/events"
        assert h._project == "myproj"
        assert h._team == "myteam"

    def test_on_llm_start_emits_prompt(self):
        from adapters.langchain_exhaust import ExhaustCallbackHandler
        h = ExhaustCallbackHandler(flush_interval=999)  # don't auto-flush
        run_id = uuid4()
        h.on_llm_start(
            {"name": "gpt-4", "kwargs": {"model_name": "gpt-4"}},
            ["Hello world"],
            run_id=run_id,
        )
        assert len(h._buffer) == 1
        event = h._buffer[0]
        assert event["event_type"] == "prompt"
        assert event["source"] == "langchain"
        assert event["session_id"] == str(run_id)

    def test_on_llm_end_emits_response_and_metric(self):
        from adapters.langchain_exhaust import ExhaustCallbackHandler
        h = ExhaustCallbackHandler(flush_interval=999)
        run_id = uuid4()
        # Start first to record timing
        h.on_llm_start({"name": "gpt-4"}, ["test"], run_id=run_id)
        h._buffer.clear()
        # Mock response
        mock_response = MagicMock()
        mock_response.generations = [[MagicMock(text="Hello back")]]
        h.on_llm_end(mock_response, run_id=run_id)
        assert len(h._buffer) == 2  # response + metric
        assert h._buffer[0]["event_type"] == "response"
        assert h._buffer[1]["event_type"] == "metric"
        assert "latency_ms" in h._buffer[1]["payload"]

    def test_on_tool_start_emits_tool_call(self):
        from adapters.langchain_exhaust import ExhaustCallbackHandler
        h = ExhaustCallbackHandler(flush_interval=999)
        run_id = uuid4()
        h.on_tool_start({"name": "search"}, "query text", run_id=run_id)
        assert len(h._buffer) == 1
        event = h._buffer[0]
        assert event["event_type"] == "tool_call"

    def test_on_tool_end_emits_tool_result(self):
        from adapters.langchain_exhaust import ExhaustCallbackHandler
        h = ExhaustCallbackHandler(flush_interval=999)
        run_id = uuid4()
        h.on_tool_end("result text", run_id=run_id)
        assert len(h._buffer) == 1
        assert h._buffer[0]["event_type"] == "tool_result"

    def test_on_llm_error_emits_error(self):
        from adapters.langchain_exhaust import ExhaustCallbackHandler
        h = ExhaustCallbackHandler(flush_interval=999)
        run_id = uuid4()
        h.on_llm_error(RuntimeError("test error"), run_id=run_id)
        assert len(h._buffer) == 1
        assert h._buffer[0]["event_type"] == "error"
        assert "test error" in h._buffer[0]["payload"]

    def test_on_chain_end_flushes(self):
        from adapters.langchain_exhaust import ExhaustCallbackHandler
        h = ExhaustCallbackHandler(flush_interval=999)
        run_id = uuid4()
        h.on_tool_end("some output", run_id=run_id)
        assert len(h._buffer) == 1
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.status = 200
            mock_resp.__enter__ = lambda s: s
            mock_resp.__exit__ = MagicMock(return_value=False)
            mock_urlopen.return_value = mock_resp
            h.on_chain_end({}, run_id=run_id)
        assert len(h._buffer) == 0  # flushed

    @patch("urllib.request.urlopen")
    def test_flush_sends_json(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        from adapters.langchain_exhaust import ExhaustCallbackHandler
        h = ExhaustCallbackHandler()
        run_id = uuid4()
        h.on_tool_end("output", run_id=run_id)
        # on_tool_end with flush_interval=0 triggers auto-flush
        req = mock_urlopen.call_args[0][0]
        assert req.get_header("Content-type") == "application/json"
        payload = json.loads(req.data)
        assert isinstance(payload, list)
        assert len(payload) == 1

    def test_flush_handles_network_error(self):
        from adapters.langchain_exhaust import ExhaustCallbackHandler
        h = ExhaustCallbackHandler()
        h._buffer.append({"event_type": "test"})
        with patch("urllib.request.urlopen", side_effect=Exception("network error")):
            h._flush()  # should not raise
        assert len(h._buffer) == 0  # buffer was cleared despite error

    def test_event_structure(self):
        from adapters.langchain_exhaust import ExhaustCallbackHandler
        h = ExhaustCallbackHandler(
            project="proj1", team="team1", flush_interval=999,
        )
        run_id = uuid4()
        parent_id = uuid4()
        h.on_llm_start(
            {"name": "test-model"},
            ["prompt"],
            run_id=run_id,
            parent_run_id=parent_id,
        )
        event = h._buffer[0]
        assert event["event_id"]  # non-empty
        assert event["session_id"] == str(parent_id)
        assert event["project"] == "proj1"
        assert event["team"] == "team1"
        assert event["timestamp"]  # ISO timestamp

    def test_parent_run_id_used_as_session(self):
        from adapters.langchain_exhaust import ExhaustCallbackHandler
        h = ExhaustCallbackHandler(flush_interval=999)
        run_id = uuid4()
        parent_id = uuid4()
        h.on_tool_start({"name": "tool"}, "input", run_id=run_id, parent_run_id=parent_id)
        assert h._buffer[0]["session_id"] == str(parent_id)

    def test_no_parent_uses_run_id(self):
        from adapters.langchain_exhaust import ExhaustCallbackHandler
        h = ExhaustCallbackHandler(flush_interval=999)
        run_id = uuid4()
        h.on_tool_start({"name": "tool"}, "input", run_id=run_id)
        assert h._buffer[0]["session_id"] == str(run_id)

    def test_model_name_extraction(self):
        from adapters.langchain_exhaust import ExhaustCallbackHandler
        h = ExhaustCallbackHandler(flush_interval=999)
        run_id = uuid4()
        h.on_llm_start(
            {"name": "ChatOpenAI", "kwargs": {"model_name": "gpt-4-turbo"}},
            ["test"],
            run_id=run_id,
        )
        assert h._run_model[str(run_id)] == "gpt-4-turbo"

    def test_buffered_flush(self):
        from adapters.langchain_exhaust import ExhaustCallbackHandler
        h = ExhaustCallbackHandler(flush_interval=999)
        run_id = uuid4()
        h.on_tool_end("out1", run_id=run_id)
        h.on_tool_end("out2", run_id=run_id)
        assert len(h._buffer) == 2  # not flushed due to high interval
