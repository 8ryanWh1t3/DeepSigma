"""Tests for MCP resources/list, resources/read, prompts/list, prompts/get."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from adapters.mcp.mcp_server_scaffold import (
    handle_prompts_get,
    handle_prompts_list,
    handle_resources_list,
    handle_resources_read,
)


class TestResourcesList:
    def test_returns_resources(self, tmp_path, monkeypatch):
        """resources/list returns episode, drift, schema, and stats resources."""
        # Create sample data
        ep = {"episodeId": "ep-res-001", "decisionType": "deploy"}
        (tmp_path / "ep-res-001.json").write_text(json.dumps(ep))
        drift = {"driftId": "drift-res-001", "driftType": "freshness"}
        (tmp_path / "drift-res-001.drift.json").write_text(json.dumps(drift))
        monkeypatch.setenv("DATA_DIR", str(tmp_path))

        resp = handle_resources_list(1)
        assert "result" in resp
        resources = resp["result"]["resources"]
        uris = [r["uri"] for r in resources]
        assert "episode://ep-res-001" in uris
        assert "drift://drift-res-001" in uris
        assert "stats://coherence" in uris
        # Schemas from specs/ directory should be present
        schema_uris = [u for u in uris if u.startswith("schema://")]
        assert len(schema_uris) > 0

    def test_empty_data_dir(self, tmp_path, monkeypatch):
        """resources/list with empty data dir still returns schemas + stats."""
        monkeypatch.setenv("DATA_DIR", str(tmp_path))
        resp = handle_resources_list(1)
        resources = resp["result"]["resources"]
        assert any(r["uri"] == "stats://coherence" for r in resources)

    def test_resources_have_mime_type(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DATA_DIR", str(tmp_path))
        resp = handle_resources_list(1)
        for r in resp["result"]["resources"]:
            assert "mimeType" in r
            assert r["mimeType"] == "application/json"


class TestResourcesRead:
    def test_read_episode(self, tmp_path, monkeypatch):
        ep = {"episodeId": "ep-read-001", "decisionType": "deploy"}
        (tmp_path / "ep-read-001.json").write_text(json.dumps(ep))
        monkeypatch.setenv("DATA_DIR", str(tmp_path))

        resp = handle_resources_read(1, {"uri": "episode://ep-read-001"})
        assert "result" in resp
        contents = resp["result"]["contents"]
        assert len(contents) == 1
        data = json.loads(contents[0]["text"])
        assert data["episodeId"] == "ep-read-001"

    def test_read_drift(self, tmp_path, monkeypatch):
        drift = {"driftId": "drift-read-001", "driftType": "freshness"}
        (tmp_path / "drift-read-001.drift.json").write_text(json.dumps(drift))
        monkeypatch.setenv("DATA_DIR", str(tmp_path))

        resp = handle_resources_read(1, {"uri": "drift://drift-read-001"})
        assert "result" in resp
        data = json.loads(resp["result"]["contents"][0]["text"])
        assert data["driftId"] == "drift-read-001"

    def test_read_schema(self):
        resp = handle_resources_read(1, {"uri": "schema://episode"})
        assert "result" in resp
        data = json.loads(resp["result"]["contents"][0]["text"])
        assert "$schema" in data or "title" in data

    def test_read_coherence_stats(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DATA_DIR", str(tmp_path))
        import adapters.mcp.mcp_server_scaffold as mcp
        mcp._iris_pipeline = None

        resp = handle_resources_read(1, {"uri": "stats://coherence"})
        assert "result" in resp
        data = json.loads(resp["result"]["contents"][0]["text"])
        assert "total_nodes" in data

    def test_read_missing_episode(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DATA_DIR", str(tmp_path))
        resp = handle_resources_read(1, {"uri": "episode://nonexistent"})
        assert "error" in resp

    def test_read_unknown_uri(self):
        resp = handle_resources_read(1, {"uri": "unknown://foo"})
        assert "error" in resp

    def test_read_missing_uri_param(self):
        resp = handle_resources_read(1, {})
        assert "error" in resp


class TestPromptsList:
    def test_returns_three_prompts(self):
        resp = handle_prompts_list(1)
        assert "result" in resp
        prompts = resp["result"]["prompts"]
        assert len(prompts) == 3
        names = {p["name"] for p in prompts}
        assert names == {"assemble_context", "trace_decision", "check_contradictions"}

    def test_prompts_have_arguments(self):
        resp = handle_prompts_list(1)
        for prompt in resp["result"]["prompts"]:
            assert "arguments" in prompt
            assert len(prompt["arguments"]) > 0
            for arg in prompt["arguments"]:
                assert "name" in arg
                assert "required" in arg


class TestPromptsGet:
    def test_assemble_context(self):
        resp = handle_prompts_get(1, {
            "name": "assemble_context",
            "arguments": {"decision_type": "deploy"},
        })
        assert "result" in resp
        messages = resp["result"]["messages"]
        assert len(messages) == 1
        assert messages[0]["role"] == "user"
        assert "deploy" in messages[0]["content"]["text"]

    def test_trace_decision(self):
        resp = handle_prompts_get(1, {
            "name": "trace_decision",
            "arguments": {"episode_id": "ep-001"},
        })
        assert "result" in resp
        assert "ep-001" in resp["result"]["messages"][0]["content"]["text"]

    def test_check_contradictions(self):
        resp = handle_prompts_get(1, {
            "name": "check_contradictions",
            "arguments": {"episode_id": "ep-002"},
        })
        assert "result" in resp
        assert "ep-002" in resp["result"]["messages"][0]["content"]["text"]

    def test_unknown_prompt(self):
        resp = handle_prompts_get(1, {"name": "nonexistent"})
        assert "error" in resp
