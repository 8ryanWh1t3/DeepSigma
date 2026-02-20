"""Tests for MCP production features: auth, rate limiting, coherence tools, catalog.

Run:  pytest tests/test_mcp_production.py -v
"""
import json
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import adapters.mcp.mcp_server_scaffold as mcp
from adapters.mcp.mcp_server_scaffold import (
    _RateLimiter,
    handle_initialize,
    handle_tools_call,
    handle_tools_list,
)

ROOT = Path(__file__).resolve().parents[1]


# ── Authentication ──────────────────────────────────────────────


class TestMCPAuthentication:
    """Test API key authentication."""

    def test_initialize_with_valid_key(self):
        """Auth succeeds when valid API key is provided."""
        orig_enabled = mcp._AUTH_ENABLED
        orig_keys = mcp._AUTH_KEYS
        try:
            mcp._AUTH_KEYS = {"test-key-abc"}
            mcp._AUTH_ENABLED = True
            resp = handle_initialize(1, {"apiKey": "test-key-abc"})
            assert "result" in resp
            assert "sessionId" in resp["result"]
            session_id = resp["result"]["sessionId"]
            assert session_id in mcp._AUTHED_SESSIONS
            # Cleanup
            mcp._AUTHED_SESSIONS.discard(session_id)
        finally:
            mcp._AUTH_ENABLED = orig_enabled
            mcp._AUTH_KEYS = orig_keys

    def test_initialize_without_key_when_required(self):
        """Auth fails when required but no key provided."""
        orig_enabled = mcp._AUTH_ENABLED
        orig_keys = mcp._AUTH_KEYS
        try:
            mcp._AUTH_KEYS = {"test-key-abc"}
            mcp._AUTH_ENABLED = True
            resp = handle_initialize(1, {})
            assert "error" in resp
            assert "Authentication failed" in resp["error"]["message"]
        finally:
            mcp._AUTH_ENABLED = orig_enabled
            mcp._AUTH_KEYS = orig_keys

    def test_initialize_with_invalid_key(self):
        """Auth fails with wrong key."""
        orig_enabled = mcp._AUTH_ENABLED
        orig_keys = mcp._AUTH_KEYS
        try:
            mcp._AUTH_KEYS = {"correct-key"}
            mcp._AUTH_ENABLED = True
            resp = handle_initialize(1, {"apiKey": "wrong-key"})
            assert "error" in resp
        finally:
            mcp._AUTH_ENABLED = orig_enabled
            mcp._AUTH_KEYS = orig_keys

    def test_auth_disabled_when_no_env(self):
        """Auth is disabled when no keys are configured (backward compat)."""
        orig_enabled = mcp._AUTH_ENABLED
        orig_keys = mcp._AUTH_KEYS
        try:
            mcp._AUTH_KEYS = set()
            mcp._AUTH_ENABLED = False
            resp = handle_initialize(1, {})
            assert "result" in resp
            assert "sessionId" in resp["result"]
            assert resp["result"]["serverInfo"]["version"] == "1.0.0"
        finally:
            mcp._AUTH_ENABLED = orig_enabled
            mcp._AUTH_KEYS = orig_keys


# ── Rate Limiting ───────────────────────────────────────────────


class TestMCPRateLimiting:
    """Test per-client sliding window rate limiter."""

    def test_rate_limit_allows_normal_traffic(self):
        """Under-limit requests are allowed."""
        rl = _RateLimiter(max_per_minute=10)
        for _ in range(10):
            assert rl.allow("sess-a")

    def test_rate_limit_rejects_excess(self):
        """Over-limit requests are rejected."""
        rl = _RateLimiter(max_per_minute=5)
        for _ in range(5):
            rl.allow("sess-a")
        assert not rl.allow("sess-a")

    def test_rate_limit_per_session_isolation(self):
        """Rate limits are independent per session."""
        rl = _RateLimiter(max_per_minute=3)
        for _ in range(3):
            rl.allow("sess-a")
        # sess-a is exhausted
        assert not rl.allow("sess-a")
        # sess-b still has budget
        assert rl.allow("sess-b")

    def test_rate_limit_recovers_after_window(self):
        """Requests are allowed again after the 60s window elapses."""
        rl = _RateLimiter(max_per_minute=2)
        rl.allow("sess-a")
        rl.allow("sess-a")
        assert not rl.allow("sess-a")

        # Simulate time passing by manually backdating entries
        rl._windows["sess-a"] = [time.monotonic() - 61.0, time.monotonic() - 61.0]
        assert rl.allow("sess-a")


# ── Coherence Tools ─────────────────────────────────────────────


class TestCoherenceTools:
    """Test the 5 coherence.* tool handlers."""

    @pytest.fixture(autouse=True)
    def _load_pipeline(self, tmp_path, minimal_episode):
        """Load a minimal pipeline before each test."""
        ep = minimal_episode(episode_id="ep-coh-001")
        ep_file = tmp_path / "ep-coh-001.json"
        ep_file.write_text(json.dumps(ep))
        mcp._load_pipeline(str(tmp_path))
        yield
        mcp._iris_pipeline = None

    def test_query_credibility_index(self):
        """Returns score and grade."""
        resp = handle_tools_call(1, {
            "name": "coherence.query_credibility_index",
            "arguments": {},
        })
        assert "result" in resp
        result = resp["result"]
        assert "overall_score" in result
        assert isinstance(result["overall_score"], (int, float))
        assert result["grade"] in ("A", "B", "C", "D")
        assert "dimensions" in result

    def test_list_drift_signals(self):
        """Returns drift summary."""
        resp = handle_tools_call(1, {
            "name": "coherence.list_drift_signals",
            "arguments": {},
        })
        assert "result" in resp
        result = resp["result"]
        assert "total_signals" in result
        assert "buckets" in result
        assert isinstance(result["buckets"], list)

    def test_list_drift_signals_with_severity_filter(self):
        """Severity filter narrows results."""
        resp = handle_tools_call(1, {
            "name": "coherence.list_drift_signals",
            "arguments": {"severity": "red"},
        })
        assert "result" in resp
        result = resp["result"]
        # All returned buckets should match the filter (or be empty)
        for bucket in result["buckets"]:
            assert bucket.get("worst_severity") == "red"

    def test_list_drift_signals_with_limit(self):
        """Limit caps the number of buckets."""
        resp = handle_tools_call(1, {
            "name": "coherence.list_drift_signals",
            "arguments": {"limit": 2},
        })
        assert "result" in resp
        assert len(resp["result"]["buckets"]) <= 2

    def test_get_episode(self, tmp_path):
        """Returns episode data for a known episode."""
        resp = handle_tools_call(1, {
            "name": "coherence.get_episode",
            "arguments": {"episode_id": "ep-coh-001"},
        })
        assert "result" in resp
        result = resp["result"]
        assert result["episode_id"] == "ep-coh-001"

    def test_get_episode_not_found(self, monkeypatch):
        """Returns error for unknown episode."""
        monkeypatch.setenv("DATA_DIR", "/tmp/nonexistent_coh_test")
        resp = handle_tools_call(1, {
            "name": "coherence.get_episode",
            "arguments": {"episode_id": "ep-ghost-999"},
        })
        assert "error" in resp
        assert "not found" in resp["error"]["message"].lower()

    def test_get_episode_missing_id(self):
        """Returns error when episode_id is missing."""
        resp = handle_tools_call(1, {
            "name": "coherence.get_episode",
            "arguments": {},
        })
        assert "error" in resp

    def test_apply_patch(self):
        """Applies a patch and returns confirmation."""
        resp = handle_tools_call(1, {
            "name": "coherence.apply_patch",
            "arguments": {
                "patch": {
                    "patchId": "patch-test-001",
                    "driftId": "drift-001",
                    "driftType": "contradiction",
                    "severity": "yellow",
                    "action": "update",
                    "description": "Fix version mismatch",
                    "field": "version",
                    "suggestion": "2.4.1",
                },
            },
        })
        assert "result" in resp
        result = resp["result"]
        assert result["applied"] is True
        assert result["patch_id"] == "patch-test-001"
        assert "node_id" in result

    def test_apply_patch_missing_id(self):
        """Returns error when patchId is missing."""
        resp = handle_tools_call(1, {
            "name": "coherence.apply_patch",
            "arguments": {"patch": {}},
        })
        assert "error" in resp

    def test_seal_decision(self):
        """Seals a decision episode and returns DLR entry."""
        resp = handle_tools_call(1, {
            "name": "coherence.seal_decision",
            "arguments": {
                "episode": {
                    "episodeId": "ep-seal-001",
                    "decisionType": "deploy",
                    "outcome": {"code": "success"},
                    "events": [],
                },
            },
        })
        assert "result" in resp
        result = resp["result"]
        assert result["sealed"] is True
        assert result["episode_id"] == "ep-seal-001"
        assert "dlr_id" in result

    def test_seal_decision_missing_episode_id(self):
        """Returns error when episodeId is missing."""
        resp = handle_tools_call(1, {
            "name": "coherence.seal_decision",
            "arguments": {"episode": {"decisionType": "test"}},
        })
        assert "error" in resp

    def test_coherence_tools_without_pipeline(self, monkeypatch):
        """Coherence tools return error when no data is loaded."""
        mcp._iris_pipeline = None
        monkeypatch.setenv("DATA_DIR", "/tmp/nonexistent_coh_test")

        resp = handle_tools_call(1, {
            "name": "coherence.query_credibility_index",
            "arguments": {},
        })
        assert "error" in resp
        assert "No data loaded" in resp["error"]["message"]


# ── Tool Catalog ────────────────────────────────────────────────


class TestToolCatalog:
    """Validate the tool catalog has all expected entries."""

    def test_catalog_has_29_tools(self):
        """Catalog contains 24 original + 5 coherence tools."""
        catalog = json.loads(
            (ROOT / "src" / "adapters" / "mcp" / "tool_catalog.json").read_text()
        )
        assert len(catalog["tools"]) == 29

    def test_catalog_version(self):
        """Catalog version is 1.0.0."""
        catalog = json.loads(
            (ROOT / "src" / "adapters" / "mcp" / "tool_catalog.json").read_text()
        )
        assert catalog["version"] == "1.0.0"

    def test_new_tools_have_schemas(self):
        """All 5 coherence tools have inputSchema."""
        catalog = json.loads(
            (ROOT / "src" / "adapters" / "mcp" / "tool_catalog.json").read_text()
        )
        coherence_tools = [t for t in catalog["tools"] if t["name"].startswith("coherence.")]
        assert len(coherence_tools) == 5
        for tool in coherence_tools:
            assert "inputSchema" in tool, f"{tool['name']} missing inputSchema"
            assert tool["inputSchema"]["type"] == "object"

    def test_tools_list_returns_29(self):
        """handle_tools_list returns all 29 tools."""
        resp = handle_tools_list(1)
        tools = resp["result"]["tools"]
        assert len(tools) == 29
        names = [t["name"] for t in tools]
        assert "coherence.query_credibility_index" in names
        assert "coherence.list_drift_signals" in names
        assert "coherence.get_episode" in names
        assert "coherence.apply_patch" in names
        assert "coherence.seal_decision" in names
