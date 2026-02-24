"""Tests for adapters.openclaw.overwatch_openclaw_adapter — OverwatchClient."""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))


def _mock_response(data: dict):
    """Create a mock urllib response."""
    resp = MagicMock()
    resp.read.return_value = json.dumps(data).encode()
    resp.status = 200
    resp.__enter__ = lambda s: s
    resp.__exit__ = MagicMock(return_value=False)
    return resp


class TestOverwatchClient:
    def test_default_base_url(self):
        from adapters.openclaw.overwatch_openclaw_adapter import OverwatchClient
        client = OverwatchClient()
        assert client.base_url == "http://localhost:8000"

    def test_custom_base_url(self):
        from adapters.openclaw.overwatch_openclaw_adapter import OverwatchClient
        client = OverwatchClient(base_url="http://myserver:9000/")
        assert client.base_url == "http://myserver:9000"

    @patch.dict("os.environ", {"OVERWATCH_BASE_URL": "http://env:3000"})
    def test_env_base_url(self):
        from adapters.openclaw.overwatch_openclaw_adapter import OverwatchClient
        client = OverwatchClient()
        assert client.base_url == "http://env:3000"

    @patch.dict("os.environ", {"OVERWATCH_TIMEOUT": "60"})
    def test_env_timeout(self):
        from adapters.openclaw.overwatch_openclaw_adapter import OverwatchClient
        client = OverwatchClient()
        assert client.timeout == 60

    @patch("urllib.request.urlopen")
    def test_submit_task(self, mock_urlopen):
        from adapters.openclaw.overwatch_openclaw_adapter import OverwatchClient
        mock_urlopen.return_value = _mock_response({"episodeId": "ep-123"})
        client = OverwatchClient()
        ep_id = client.submit_task("TestDecision", {"key": "val"}, "agent-1")
        assert ep_id == "ep-123"
        req = mock_urlopen.call_args[0][0]
        assert "/api/episodes" in req.full_url
        body = json.loads(req.data)
        assert body["decisionType"] == "TestDecision"
        assert body["actorId"] == "agent-1"

    @patch("urllib.request.urlopen")
    def test_execute_tool(self, mock_urlopen):
        from adapters.openclaw.overwatch_openclaw_adapter import OverwatchClient
        mock_urlopen.return_value = _mock_response({"status": "ok"})
        client = OverwatchClient()
        result = client.execute_tool("ep-123", "my_tool", {"arg": 1})
        assert result["status"] == "ok"
        req = mock_urlopen.call_args[0][0]
        assert "/api/episodes/ep-123/tool_calls" in req.full_url

    @patch("urllib.request.urlopen")
    def test_dispatch_action(self, mock_urlopen):
        from adapters.openclaw.overwatch_openclaw_adapter import OverwatchClient
        mock_urlopen.return_value = _mock_response({"status": "dispatched"})
        client = OverwatchClient()
        result = client.dispatch_action("ep-123", {"action": "test"})
        assert result["status"] == "dispatched"
        req = mock_urlopen.call_args[0][0]
        assert "/api/episodes/ep-123/actions" in req.full_url

    @patch("urllib.request.urlopen")
    def test_verify(self, mock_urlopen):
        from adapters.openclaw.overwatch_openclaw_adapter import OverwatchClient
        mock_urlopen.return_value = _mock_response({"outcome": "pass"})
        client = OverwatchClient()
        result = client.verify("ep-123", "read_after_write", {})
        assert result["outcome"] == "pass"
        req = mock_urlopen.call_args[0][0]
        assert "/api/episodes/ep-123/verify" in req.full_url

    @patch("urllib.request.urlopen")
    def test_seal(self, mock_urlopen):
        from adapters.openclaw.overwatch_openclaw_adapter import OverwatchClient
        mock_urlopen.return_value = _mock_response({"status": "sealed"})
        client = OverwatchClient()
        result = client.seal("ep-123", {"verificationResult": {"outcome": "pass"}})
        assert result["status"] == "sealed"
        req = mock_urlopen.call_args[0][0]
        assert "/api/episodes/ep-123/seal" in req.full_url

    @patch("urllib.request.urlopen")
    def test_health(self, mock_urlopen):
        from adapters.openclaw.overwatch_openclaw_adapter import OverwatchClient
        mock_urlopen.return_value = _mock_response({"status": "healthy"})
        client = OverwatchClient()
        result = client.health()
        assert result["status"] == "healthy"
        req = mock_urlopen.call_args[0][0]
        assert "/api/health" in req.full_url
        assert req.method == "GET"

    @patch("urllib.request.urlopen")
    def test_http_error_raises(self, mock_urlopen):
        import urllib.error
        from adapters.openclaw.overwatch_openclaw_adapter import OverwatchClient
        mock_urlopen.side_effect = urllib.error.HTTPError(
            "http://localhost:8000/api/health", 500, "Internal Server Error",
            {}, MagicMock(read=lambda: b"error body"),
        )
        client = OverwatchClient()
        with pytest.raises(RuntimeError, match="Overwatch API 500"):
            client.health()

    @patch("urllib.request.urlopen")
    def test_url_error_raises(self, mock_urlopen):
        import urllib.error
        from adapters.openclaw.overwatch_openclaw_adapter import OverwatchClient
        mock_urlopen.side_effect = urllib.error.URLError("Connection refused")
        client = OverwatchClient()
        with pytest.raises(RuntimeError, match="unreachable"):
            client.health()


class TestSkillRun:
    def test_skill_run_dataclass(self):
        from adapters.openclaw.overwatch_openclaw_adapter import SkillRun
        sr = SkillRun(skill_name="Test", payload={"a": 1}, actor_id="agent-1")
        assert sr.skill_name == "Test"
        assert sr.payload == {"a": 1}

    def test_map_skill_to_decision_type(self):
        from adapters.openclaw.overwatch_openclaw_adapter import map_skill_to_decision_type
        assert map_skill_to_decision_type("Quarantine") == "OpenClaw::Quarantine"


class TestRunSkillWithOverwatch:
    @patch("urllib.request.urlopen")
    def test_full_lifecycle(self, mock_urlopen):
        from adapters.openclaw.overwatch_openclaw_adapter import (
            OverwatchClient, SkillRun, run_skill_with_overwatch,
        )
        responses = [
            _mock_response({"episodeId": "ep-999"}),           # submit_task
            _mock_response({"outcome": "pass"}),               # verify
            _mock_response({"status": "sealed"}),              # seal
        ]
        mock_urlopen.side_effect = responses
        client = OverwatchClient()
        skill = SkillRun(skill_name="Test", payload={"x": 1}, actor_id="agent-1")
        result = run_skill_with_overwatch(skill, client)
        assert result["session_id"] == "ep-999"
        assert result["status"] == "sealed"
        assert mock_urlopen.call_count == 3
