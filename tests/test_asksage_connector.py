"""Tests for adapters.asksage — AskSage connector and exhaust adapter."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


def _make_connector():
    from adapters.asksage.connector import AskSageConnector
    c = AskSageConnector(email="test@example.com", api_key="test-key", base_url="https://api.asksage.ai")
    return c


def _mock_urlopen(response_data):
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(response_data).encode()
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    return mock_resp


class TestAskSageConnector:
    @patch("urllib.request.urlopen")
    def test_get_token(self, mock_urlopen_fn):
        mock_urlopen_fn.return_value = _mock_urlopen({"token": "test-token-123"})
        c = _make_connector()
        token = c.get_token()
        assert token == "test-token-123"

    @patch("urllib.request.urlopen")
    def test_token_caching(self, mock_urlopen_fn):
        mock_urlopen_fn.return_value = _mock_urlopen({"token": "cached-token"})
        c = _make_connector()
        t1 = c.get_token()
        t2 = c.get_token()
        assert t1 == t2
        # Only one call (token request), not two
        assert mock_urlopen_fn.call_count == 1

    @patch("urllib.request.urlopen")
    def test_query(self, mock_urlopen_fn):
        # First call: token, second call: query
        responses = [
            _mock_urlopen({"token": "tok"}),
            _mock_urlopen({"response": "NIST CSF is a framework", "model": "gpt-4"}),
        ]
        mock_urlopen_fn.side_effect = responses
        c = _make_connector()
        result = c.query("What is NIST CSF?")
        assert result["response"] == "NIST CSF is a framework"

    @patch("urllib.request.urlopen")
    def test_query_with_model(self, mock_urlopen_fn):
        responses = [
            _mock_urlopen({"token": "tok"}),
            _mock_urlopen({"response": "answer", "model": "claude-3"}),
        ]
        mock_urlopen_fn.side_effect = responses
        c = _make_connector()
        result = c.query("question", model="claude-3")
        assert result["model"] == "claude-3"

    @patch("urllib.request.urlopen")
    def test_query_with_file(self, mock_urlopen_fn):
        responses = [
            _mock_urlopen({"token": "tok"}),
            _mock_urlopen({"response": "file analysis"}),
        ]
        mock_urlopen_fn.side_effect = responses
        c = _make_connector()
        result = c.query_with_file("analyze this", "/path/to/file.pdf")
        assert result["response"] == "file analysis"

    @patch("urllib.request.urlopen")
    def test_get_models(self, mock_urlopen_fn):
        responses = [
            _mock_urlopen({"token": "tok"}),
            _mock_urlopen({"models": [{"id": "gpt-4"}, {"id": "claude-3"}]}),
        ]
        mock_urlopen_fn.side_effect = responses
        c = _make_connector()
        models = c.get_models()
        assert len(models) == 2

    @patch("urllib.request.urlopen")
    def test_get_datasets(self, mock_urlopen_fn):
        responses = [
            _mock_urlopen({"token": "tok"}),
            _mock_urlopen({"datasets": [{"name": "my-dataset"}]}),
        ]
        mock_urlopen_fn.side_effect = responses
        c = _make_connector()
        datasets = c.get_datasets()
        assert len(datasets) == 1

    @patch("urllib.request.urlopen")
    def test_get_personas(self, mock_urlopen_fn):
        responses = [
            _mock_urlopen({"token": "tok"}),
            _mock_urlopen({"personas": [{"name": "default"}]}),
        ]
        mock_urlopen_fn.side_effect = responses
        c = _make_connector()
        personas = c.get_personas()
        assert len(personas) == 1

    @patch("urllib.request.urlopen")
    def test_get_user_logs(self, mock_urlopen_fn):
        responses = [
            _mock_urlopen({"token": "tok"}),
            _mock_urlopen({"logs": [{"prompt": "q1"}, {"prompt": "q2"}]}),
        ]
        mock_urlopen_fn.side_effect = responses
        c = _make_connector()
        logs = c.get_user_logs(limit=10)
        assert len(logs) == 2

    @patch("urllib.request.urlopen")
    def test_train(self, mock_urlopen_fn):
        responses = [
            _mock_urlopen({"token": "tok"}),
            _mock_urlopen({"status": "success"}),
        ]
        mock_urlopen_fn.side_effect = responses
        c = _make_connector()
        result = c.train("training content", "my-dataset")
        assert result["status"] == "success"

    @patch("urllib.request.urlopen")
    def test_token_failure(self, mock_urlopen_fn):
        mock_urlopen_fn.return_value = _mock_urlopen({"error": "invalid key"})
        c = _make_connector()
        with pytest.raises(RuntimeError, match="token acquisition"):
            c.get_token()


class TestAskSageExhaustAdapter:
    @patch("urllib.request.urlopen")
    def test_query_with_exhaust(self, mock_urlopen_fn):
        from adapters.asksage.exhaust import AskSageExhaustAdapter

        mock_connector = MagicMock()
        mock_connector.query.return_value = {"response": "answer", "model": "gpt-4"}

        # Mock the exhaust flush
        mock_urlopen_fn.return_value = _mock_urlopen({"ok": True})

        adapter = AskSageExhaustAdapter(mock_connector)
        result = adapter.query_with_exhaust("test prompt")
        assert result["response"] == "answer"
        mock_connector.query.assert_called_once()

    @patch("urllib.request.urlopen")
    def test_exhaust_events_emitted(self, mock_urlopen_fn):
        from adapters.asksage.exhaust import AskSageExhaustAdapter

        mock_connector = MagicMock()
        mock_connector.query.return_value = {"response": "x"}
        mock_urlopen_fn.return_value = _mock_urlopen({"ok": True})

        adapter = AskSageExhaustAdapter(mock_connector)
        adapter.query_with_exhaust("test")

        # Verify the flush was called with events
        call_args = mock_urlopen_fn.call_args[0][0]
        body = json.loads(call_args.data)
        assert len(body) == 3  # prompt + response + metric
        event_types = [e["event_type"] for e in body]
        assert "prompt" in event_types
        assert "response" in event_types
        assert "metric" in event_types
