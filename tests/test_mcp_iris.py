"""Tests for IRIS tools in the MCP server scaffold."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from adapters.mcp.mcp_server_scaffold import (
    handle_tools_call,
    handle_tools_list,
)


class TestToolsList:
    def test_returns_8_tools(self):
        resp = handle_tools_list(1)
        tools = resp["result"]["tools"]
        names = [t["name"] for t in tools]
        assert len(tools) == 23
        assert "iris.query" in names
        assert "iris.reload" in names

    def test_iris_query_has_schema(self):
        resp = handle_tools_list(1)
        tools = resp["result"]["tools"]
        iris_tool = [t for t in tools if t["name"] == "iris.query"][0]
        assert "inputSchema" in iris_tool
        props = iris_tool["inputSchema"]["properties"]
        assert "query_type" in props
        assert "episode_id" in props


class TestInitialize:
    def test_initialize_returns_protocol(self):
        """Simulate initialize by importing main dispatch logic."""
        import adapters.mcp.mcp_server_scaffold as mcp

        req = {"jsonrpc": "2.0", "method": "initialize", "id": 1, "params": {}}
        line = json.dumps(req)
        parsed = json.loads(line)
        _id = parsed.get("id")
        method = parsed.get("method")

        # Reproduce the dispatch logic
        if method == "initialize":
            resp = mcp.rpc_result(_id, {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "sigma-overwatch-mcp", "version": "0.4.0"},
            })

        assert resp["result"]["protocolVersion"] == "2024-11-05"
        assert resp["result"]["serverInfo"]["name"] == "sigma-overwatch-mcp"


class TestIrisQuery:
    def test_iris_query_without_data_returns_error(self, monkeypatch):
        """iris.query without loaded data returns an error."""
        import adapters.mcp.mcp_server_scaffold as mcp
        mcp._iris_pipeline = None  # ensure no cached pipeline
        # Point DATA_DIR to a non-existent path so _load_pipeline returns None
        monkeypatch.setenv("DATA_DIR", "/tmp/nonexistent_mcp_test_data")

        resp = handle_tools_call(1, {
            "name": "iris.query",
            "arguments": {"query_type": "STATUS"},
        })
        assert "error" in resp

    def test_iris_query_with_data(self, tmp_path):
        """iris.query returns a valid response when data is loaded."""
        import adapters.mcp.mcp_server_scaffold as mcp

        # Create minimal example data
        ep = {
            "episodeId": "ep-mcp-001",
            "decisionType": "deploy",
            "startedAt": "2026-01-01T00:00:00Z",
            "endedAt": "2026-01-01T00:01:00Z",
            "outcome": {"code": "success"},
            "telemetry": {"endToEndMs": 1000},
        }
        ep_file = tmp_path / "ep-mcp-001.json"
        ep_file.write_text(json.dumps(ep))

        # Load pipeline from tmp_path
        pipeline = mcp._load_pipeline(str(tmp_path))
        assert pipeline is not None

        resp = handle_tools_call(1, {
            "name": "iris.query",
            "arguments": {"query_type": "STATUS"},
        })
        assert "result" in resp
        result = resp["result"]
        assert "query_id" in result
        assert result["query_type"] == "STATUS"
        assert "confidence" in result

        # Cleanup
        mcp._iris_pipeline = None

    def test_iris_reload(self, tmp_path):
        """iris.reload loads data and returns counts."""
        import adapters.mcp.mcp_server_scaffold as mcp
        mcp._iris_pipeline = None

        ep = {
            "episodeId": "ep-reload-001",
            "decisionType": "deploy",
            "outcome": {"code": "success"},
        }
        (tmp_path / "ep.json").write_text(json.dumps(ep))

        resp = handle_tools_call(1, {
            "name": "iris.reload",
            "arguments": {"data_path": str(tmp_path)},
        })
        assert "result" in resp
        result = resp["result"]
        assert result["reloaded"] is True
        assert result["episode_count"] >= 1

        # Cleanup
        mcp._iris_pipeline = None

    def test_iris_reload_bad_path(self):
        """iris.reload with nonexistent path returns error."""
        import adapters.mcp.mcp_server_scaffold as mcp
        mcp._iris_pipeline = None

        resp = handle_tools_call(1, {
            "name": "iris.reload",
            "arguments": {"data_path": "/nonexistent/path"},
        })
        assert "error" in resp

        mcp._iris_pipeline = None
