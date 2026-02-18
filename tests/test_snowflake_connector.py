"""Tests for adapters.snowflake — Cortex AI + Data Warehouse connectors."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


# ── Auth tests ───────────────────────────────────────────────────────────────

class TestSnowflakeAuth:
    def test_pat_token_headers(self):
        from adapters.snowflake._auth import SnowflakeAuth
        auth = SnowflakeAuth(account="xy12345", token="my-oauth-token")
        headers = auth.get_headers()
        assert headers["Authorization"] == "Bearer my-oauth-token"
        assert headers["X-Snowflake-Authorization-Token-Type"] == "OAUTH"

    def test_pat_programmatic_token(self):
        from adapters.snowflake._auth import SnowflakeAuth
        auth = SnowflakeAuth(account="xy12345", token="ver:1:abc123")
        headers = auth.get_headers()
        assert headers["X-Snowflake-Authorization-Token-Type"] == "PROGRAMMATIC_ACCESS_TOKEN"

    def test_no_auth_raises(self):
        from adapters.snowflake._auth import SnowflakeAuth
        auth = SnowflakeAuth(account="xy12345")
        with pytest.raises(RuntimeError, match="No Snowflake auth"):
            auth.get_headers()

    def test_base_url(self):
        from adapters.snowflake._auth import SnowflakeAuth
        auth = SnowflakeAuth(account="xy12345.us-east-1")
        assert auth.base_url == "https://xy12345.us-east-1.snowflakecomputing.com"

    def test_jwt_requires_cryptography(self):
        from adapters.snowflake._auth import SnowflakeAuth
        auth = SnowflakeAuth(account="xy12345", user="USER", private_key_path="/nonexistent/key.pem")
        # Will fail because cryptography not installed or key doesn't exist
        with pytest.raises(Exception):
            auth.get_headers()


# ── Cortex connector tests ───────────────────────────────────────────────────

def _mock_sse_response(chunks):
    """Create a mock SSE response with data lines."""
    lines = []
    for chunk in chunks:
        data = json.dumps({"choices": [{"delta": {"content": chunk}}]})
        lines.append(f"data: {data}\n".encode())
    lines.append(b"data: [DONE]\n")

    mock_resp = MagicMock()
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    mock_resp.__iter__ = lambda s: iter(lines)
    return mock_resp


def _mock_json_response(data):
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(data).encode()
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    return mock_resp


class TestCortexConnector:
    @patch("urllib.request.urlopen")
    def test_complete_basic(self, mock_urlopen):
        from adapters.snowflake.cortex import CortexConnector
        from adapters.snowflake._auth import SnowflakeAuth

        auth = SnowflakeAuth(account="test", token="tok")
        connector = CortexConnector(auth=auth)

        mock_urlopen.return_value = _mock_sse_response(["Hello", " world"])
        chunks = connector.complete("mistral-large", [{"role": "user", "content": "Hi"}])
        assert chunks == ["Hello", " world"]

    @patch("urllib.request.urlopen")
    def test_complete_sync(self, mock_urlopen):
        from adapters.snowflake.cortex import CortexConnector
        from adapters.snowflake._auth import SnowflakeAuth

        auth = SnowflakeAuth(account="test", token="tok")
        connector = CortexConnector(auth=auth)

        mock_urlopen.return_value = _mock_sse_response(["Hello", " world"])
        result = connector.complete_sync("mistral-large", [{"role": "user", "content": "Hi"}])
        assert result["response"] == "Hello world"
        assert result["model"] == "mistral-large"
        assert result["usage"]["chunks"] == 2

    @patch("urllib.request.urlopen")
    def test_embed(self, mock_urlopen):
        from adapters.snowflake.cortex import CortexConnector
        from adapters.snowflake._auth import SnowflakeAuth

        auth = SnowflakeAuth(account="test", token="tok")
        connector = CortexConnector(auth=auth)

        mock_urlopen.return_value = _mock_json_response({
            "data": [
                {"embedding": [0.1, 0.2, 0.3]},
                {"embedding": [0.4, 0.5, 0.6]},
            ]
        })
        result = connector.embed("e5-base-v2", ["text1", "text2"])
        assert len(result["embeddings"]) == 2
        assert result["model"] == "e5-base-v2"

    @patch("urllib.request.urlopen")
    def test_complete_empty_stream(self, mock_urlopen):
        from adapters.snowflake.cortex import CortexConnector
        from adapters.snowflake._auth import SnowflakeAuth

        auth = SnowflakeAuth(account="test", token="tok")
        connector = CortexConnector(auth=auth)

        mock_urlopen.return_value = _mock_sse_response([])
        result = connector.complete_sync("model", [])
        assert result["response"] == ""


# ── Warehouse connector tests ────────────────────────────────────────────────

class TestSnowflakeWarehouseConnector:
    def _make_connector(self):
        from adapters.snowflake.warehouse import SnowflakeWarehouseConnector
        from adapters.snowflake._auth import SnowflakeAuth

        auth = SnowflakeAuth(account="test", token="tok")
        with patch.dict("os.environ", {
            "SNOWFLAKE_DATABASE": "TESTDB",
            "SNOWFLAKE_SCHEMA": "PUBLIC",
            "SNOWFLAKE_WAREHOUSE": "COMPUTE_WH",
        }):
            return SnowflakeWarehouseConnector(auth=auth)

    @patch("urllib.request.urlopen")
    def test_query(self, mock_urlopen):
        connector = self._make_connector()
        mock_urlopen.return_value = _mock_json_response({
            "resultSetMetaData": {"rowType": [{"name": "ID"}, {"name": "NAME"}]},
            "data": [["1", "Alice"], ["2", "Bob"]],
        })
        rows = connector.query("SELECT * FROM users")
        assert len(rows) == 2
        assert rows[0]["ID"] == "1"
        assert rows[0]["NAME"] == "Alice"

    @patch("urllib.request.urlopen")
    def test_list_tables(self, mock_urlopen):
        connector = self._make_connector()
        mock_urlopen.return_value = _mock_json_response({
            "resultSetMetaData": {"rowType": [{"name": "name"}, {"name": "kind"}]},
            "data": [["users", "TABLE"], ["orders", "TABLE"]],
        })
        tables = connector.list_tables()
        assert len(tables) == 2

    def test_parse_result_empty(self):
        from adapters.snowflake.warehouse import SnowflakeWarehouseConnector
        rows = SnowflakeWarehouseConnector._parse_result({
            "resultSetMetaData": {"rowType": []},
            "data": [],
        })
        assert rows == []

    def test_to_canonical(self):
        connector = self._make_connector()
        rows = [
            {"ID": "1", "name": "Alice", "score": 95},
            {"ID": "2", "name": "Bob", "score": 87},
        ]
        records = connector.to_canonical(rows, "users")
        assert len(records) == 2
        assert records[0]["record_id"]  # not empty
        assert records[0]["source"]["system"] == "snowflake"
        assert records[0]["confidence"]["score"] == 0.90
        assert "table:users" in records[0]["labels"]["tags"]

    def test_to_canonical_provenance(self):
        connector = self._make_connector()
        records = connector.to_canonical([{"ID": "42", "value": 100}], "metrics")
        prov = records[0]["provenance"][0]
        assert prov["type"] == "source"
        assert "snowflake://test/" in prov["ref"]
        assert "metrics" in prov["ref"]

    def test_infer_type_metric(self):
        from adapters.snowflake.warehouse import SnowflakeWarehouseConnector
        assert SnowflakeWarehouseConnector._infer_type({"value": 100, "metric": "latency"}) == "Metric"

    def test_infer_type_entity(self):
        from adapters.snowflake.warehouse import SnowflakeWarehouseConnector
        assert SnowflakeWarehouseConnector._infer_type({"name": "Alice", "email": "a@b.com"}) == "Entity"

    def test_infer_type_claim(self):
        from adapters.snowflake.warehouse import SnowflakeWarehouseConnector
        assert SnowflakeWarehouseConnector._infer_type({"result": "pass", "detail": "ok"}) == "Claim"

    @patch("urllib.request.urlopen")
    def test_sync_table(self, mock_urlopen):
        connector = self._make_connector()
        mock_urlopen.return_value = _mock_json_response({
            "resultSetMetaData": {"rowType": [{"name": "ID"}, {"name": "NAME"}]},
            "data": [["1", "Alice"]],
        })
        result = connector.sync_table("users")
        assert result["synced"] == 1
        assert len(result["records"]) == 1

    def test_find_pk(self):
        from adapters.snowflake.warehouse import SnowflakeWarehouseConnector
        assert SnowflakeWarehouseConnector._find_pk({"ID": "42", "name": "test"}) == "42"
        assert SnowflakeWarehouseConnector._find_pk({"pk": "99"}) == "99"
        assert SnowflakeWarehouseConnector._find_pk({"col1": "val1"}) == "val1"

    def test_to_canonical_deterministic(self):
        connector = self._make_connector()
        rows = [{"ID": "42"}]
        r1 = connector.to_canonical(rows, "t")[0]
        r2 = connector.to_canonical(rows, "t")[0]
        assert r1["record_id"] == r2["record_id"]


# ── Exhaust adapter tests ───────────────────────────────────────────────────

class TestCortexExhaustAdapter:
    @patch("urllib.request.urlopen")
    def test_complete_with_exhaust(self, mock_urlopen):
        from adapters.snowflake.exhaust import CortexExhaustAdapter

        mock_connector = MagicMock()
        mock_connector.complete_sync.return_value = {
            "response": "Hello",
            "model": "mistral-large",
            "usage": {"chunks": 1},
        }
        mock_urlopen.return_value = _mock_json_response({"ok": True})

        adapter = CortexExhaustAdapter(mock_connector)
        result = adapter.complete_with_exhaust("mistral-large", [{"role": "user", "content": "Hi"}])
        assert result["response"] == "Hello"
        mock_connector.complete_sync.assert_called_once()

    @patch("urllib.request.urlopen")
    def test_exhaust_events_emitted(self, mock_urlopen):
        from adapters.snowflake.exhaust import CortexExhaustAdapter

        mock_connector = MagicMock()
        mock_connector.complete_sync.return_value = {"response": "x", "usage": {"chunks": 1}}
        mock_urlopen.return_value = _mock_json_response({"ok": True})

        adapter = CortexExhaustAdapter(mock_connector)
        adapter.complete_with_exhaust("model", [])

        call_args = mock_urlopen.call_args[0][0]
        body = json.loads(call_args.data)
        assert len(body) == 3
        event_types = [e["event_type"] for e in body]
        assert "prompt" in event_types
        assert "response" in event_types
        assert "metric" in event_types
