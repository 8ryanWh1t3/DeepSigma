"""Tests for Snowflake connectors (Cortex AI + Warehouse).

Covers auth, Cortex connector, warehouse connector,
ConnectorV1 contract, column mapping, and exhaust adapter.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


# ── Auth tests ──────────────────────────────────────────────


class TestSnowflakeAuth:
    def test_pat_token_headers(self):
        from adapters.snowflake._auth import SnowflakeAuth
        auth = SnowflakeAuth(
            account="xy12345", token="my-oauth-token",
        )
        headers = auth.get_headers()
        assert headers["Authorization"] == (
            "Bearer my-oauth-token"
        )
        tok_type = headers[
            "X-Snowflake-Authorization-Token-Type"
        ]
        assert tok_type == "OAUTH"

    def test_pat_programmatic_token(self):
        from adapters.snowflake._auth import SnowflakeAuth
        auth = SnowflakeAuth(
            account="xy12345", token="ver:1:abc123",
        )
        headers = auth.get_headers()
        tok_type = headers[
            "X-Snowflake-Authorization-Token-Type"
        ]
        assert tok_type == "PROGRAMMATIC_ACCESS_TOKEN"

    def test_no_auth_raises(self):
        from adapters.snowflake._auth import SnowflakeAuth
        auth = SnowflakeAuth(account="xy12345")
        with pytest.raises(
            RuntimeError, match="No Snowflake auth",
        ):
            auth.get_headers()

    def test_base_url(self):
        from adapters.snowflake._auth import SnowflakeAuth
        auth = SnowflakeAuth(
            account="xy12345.us-east-1",
        )
        expected = (
            "https://xy12345.us-east-1"
            ".snowflakecomputing.com"
        )
        assert auth.base_url == expected

    def test_jwt_requires_cryptography(self):
        from adapters.snowflake._auth import SnowflakeAuth
        auth = SnowflakeAuth(
            account="xy12345",
            user="USER",
            private_key_path="/nonexistent/key.pem",
        )
        with pytest.raises(Exception):
            auth.get_headers()


# ── Cortex connector tests ──────────────────────────────────


def _mock_sse_response(chunks):
    """Create a mock SSE response with data lines."""
    lines = []
    for chunk in chunks:
        data = json.dumps({
            "choices": [
                {"delta": {"content": chunk}},
            ],
        })
        lines.append(f"data: {data}\n".encode())
    lines.append(b"data: [DONE]\n")

    mock_resp = MagicMock()
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    mock_resp.__iter__ = lambda s: iter(lines)
    return mock_resp


def _mock_json_response(data):
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(
        data,
    ).encode()
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    return mock_resp


class TestCortexConnector:
    @patch("urllib.request.urlopen")
    def test_complete_basic(self, mock_urlopen):
        from adapters.snowflake.cortex import (
            CortexConnector,
        )
        from adapters.snowflake._auth import SnowflakeAuth

        auth = SnowflakeAuth(account="test", token="tok")
        connector = CortexConnector(auth=auth)

        mock_urlopen.return_value = _mock_sse_response(
            ["Hello", " world"],
        )
        msgs = [{"role": "user", "content": "Hi"}]
        chunks = connector.complete(
            "mistral-large", msgs,
        )
        assert chunks == ["Hello", " world"]

    @patch("urllib.request.urlopen")
    def test_complete_sync(self, mock_urlopen):
        from adapters.snowflake.cortex import (
            CortexConnector,
        )
        from adapters.snowflake._auth import SnowflakeAuth

        auth = SnowflakeAuth(account="test", token="tok")
        connector = CortexConnector(auth=auth)

        mock_urlopen.return_value = _mock_sse_response(
            ["Hello", " world"],
        )
        msgs = [{"role": "user", "content": "Hi"}]
        result = connector.complete_sync(
            "mistral-large", msgs,
        )
        assert result["response"] == "Hello world"
        assert result["model"] == "mistral-large"
        assert result["usage"]["chunks"] == 2

    @patch("urllib.request.urlopen")
    def test_embed(self, mock_urlopen):
        from adapters.snowflake.cortex import (
            CortexConnector,
        )
        from adapters.snowflake._auth import SnowflakeAuth

        auth = SnowflakeAuth(account="test", token="tok")
        connector = CortexConnector(auth=auth)

        mock_urlopen.return_value = _mock_json_response({
            "data": [
                {"embedding": [0.1, 0.2, 0.3]},
                {"embedding": [0.4, 0.5, 0.6]},
            ],
        })
        result = connector.embed(
            "e5-base-v2", ["text1", "text2"],
        )
        assert len(result["embeddings"]) == 2
        assert result["model"] == "e5-base-v2"

    @patch("urllib.request.urlopen")
    def test_complete_empty_stream(self, mock_urlopen):
        from adapters.snowflake.cortex import (
            CortexConnector,
        )
        from adapters.snowflake._auth import SnowflakeAuth

        auth = SnowflakeAuth(account="test", token="tok")
        connector = CortexConnector(auth=auth)

        mock_urlopen.return_value = _mock_sse_response([])
        result = connector.complete_sync("model", [])
        assert result["response"] == ""


# ── Warehouse connector tests ───────────────────────────────


def _make_warehouse(column_map=None):
    from adapters.snowflake.warehouse import (
        SnowflakeWarehouseConnector,
    )
    from adapters.snowflake._auth import SnowflakeAuth

    auth = SnowflakeAuth(account="test", token="tok")
    with patch.dict("os.environ", {
        "SNOWFLAKE_DATABASE": "TESTDB",
        "SNOWFLAKE_SCHEMA": "PUBLIC",
        "SNOWFLAKE_WAREHOUSE": "COMPUTE_WH",
    }):
        return SnowflakeWarehouseConnector(
            auth=auth, column_map=column_map,
        )


class TestSnowflakeWarehouseConnector:
    @patch("urllib.request.urlopen")
    def test_query(self, mock_urlopen):
        c = _make_warehouse()
        mock_urlopen.return_value = _mock_json_response({
            "resultSetMetaData": {
                "rowType": [
                    {"name": "ID"},
                    {"name": "NAME"},
                ],
            },
            "data": [["1", "Alice"], ["2", "Bob"]],
        })
        rows = c.query("SELECT * FROM users")
        assert len(rows) == 2
        assert rows[0]["ID"] == "1"
        assert rows[0]["NAME"] == "Alice"

    @patch("urllib.request.urlopen")
    def test_list_tables(self, mock_urlopen):
        c = _make_warehouse()
        mock_urlopen.return_value = _mock_json_response({
            "resultSetMetaData": {
                "rowType": [
                    {"name": "name"},
                    {"name": "kind"},
                ],
            },
            "data": [
                ["users", "TABLE"],
                ["orders", "TABLE"],
            ],
        })
        tables = c.list_tables()
        assert len(tables) == 2

    def test_parse_result_empty(self):
        from adapters.snowflake.warehouse import (
            SnowflakeWarehouseConnector,
        )
        rows = SnowflakeWarehouseConnector._parse_result({
            "resultSetMetaData": {"rowType": []},
            "data": [],
        })
        assert rows == []

    def test_to_canonical(self):
        c = _make_warehouse()
        rows = [
            {"ID": "1", "name": "Alice", "score": 95},
            {"ID": "2", "name": "Bob", "score": 87},
        ]
        records = c.to_canonical(rows, "users")
        assert len(records) == 2
        assert records[0]["record_id"]
        sys = records[0]["source"]["system"]
        assert sys == "snowflake"
        assert records[0]["confidence"]["score"] == 0.90
        tags = records[0]["labels"]["tags"]
        assert "table:users" in tags

    def test_to_canonical_provenance(self):
        c = _make_warehouse()
        records = c.to_canonical(
            [{"ID": "42", "value": 100}], "metrics",
        )
        prov = records[0]["provenance"][0]
        assert prov["type"] == "source"
        assert "snowflake://test/" in prov["ref"]
        assert "metrics" in prov["ref"]

    def test_infer_type_metric(self):
        from adapters.snowflake.warehouse import (
            SnowflakeWarehouseConnector as SWC,
        )
        row = {"value": 100, "metric": "latency"}
        assert SWC._infer_type(row) == "Metric"

    def test_infer_type_entity(self):
        from adapters.snowflake.warehouse import (
            SnowflakeWarehouseConnector as SWC,
        )
        row = {"name": "Alice", "email": "a@b.com"}
        assert SWC._infer_type(row) == "Entity"

    def test_infer_type_claim(self):
        from adapters.snowflake.warehouse import (
            SnowflakeWarehouseConnector as SWC,
        )
        row = {"result": "pass", "detail": "ok"}
        assert SWC._infer_type(row) == "Claim"

    @patch("urllib.request.urlopen")
    def test_sync_table(self, mock_urlopen):
        c = _make_warehouse()
        mock_urlopen.return_value = _mock_json_response({
            "resultSetMetaData": {
                "rowType": [
                    {"name": "ID"},
                    {"name": "NAME"},
                ],
            },
            "data": [["1", "Alice"]],
        })
        result = c.sync_table("users")
        assert result["synced"] == 1
        assert len(result["records"]) == 1

    def test_find_pk(self):
        from adapters.snowflake.warehouse import (
            SnowflakeWarehouseConnector as SWC,
        )
        assert SWC._find_pk(
            {"ID": "42", "name": "test"},
        ) == "42"
        assert SWC._find_pk({"pk": "99"}) == "99"
        assert SWC._find_pk({"col1": "val1"}) == "val1"

    def test_to_canonical_deterministic(self):
        c = _make_warehouse()
        rows = [{"ID": "42"}]
        r1 = c.to_canonical(rows, "t")[0]
        r2 = c.to_canonical(rows, "t")[0]
        assert r1["record_id"] == r2["record_id"]


# ── ConnectorV1 contract tests ──────────────────────────────


class TestSnowflakeV1Contract:
    """Verify list_records / get_record protocol."""

    @patch("urllib.request.urlopen")
    def test_list_records_by_table(
        self, mock_urlopen,
    ):
        c = _make_warehouse()
        mock_urlopen.return_value = _mock_json_response({
            "resultSetMetaData": {
                "rowType": [
                    {"name": "ID"},
                    {"name": "NAME"},
                ],
            },
            "data": [["1", "Alice"]],
        })
        records = c.list_records(table="users")
        assert len(records) == 1
        sys = records[0]["source"]["system"]
        assert sys == "snowflake"

    @patch("urllib.request.urlopen")
    def test_list_records_by_sql(
        self, mock_urlopen,
    ):
        c = _make_warehouse()
        mock_urlopen.return_value = _mock_json_response({
            "resultSetMetaData": {
                "rowType": [{"name": "ID"}],
            },
            "data": [["1"], ["2"]],
        })
        records = c.list_records(
            sql="SELECT ID FROM t", table="t",
        )
        assert len(records) == 2

    def test_list_records_requires_table_or_sql(self):
        c = _make_warehouse()
        with pytest.raises(ValueError):
            c.list_records()

    @patch("urllib.request.urlopen")
    def test_get_record(self, mock_urlopen):
        c = _make_warehouse()
        mock_urlopen.return_value = _mock_json_response({
            "resultSetMetaData": {
                "rowType": [
                    {"name": "ID"},
                    {"name": "NAME"},
                ],
            },
            "data": [["42", "Alice"]],
        })
        rec = c.get_record("42", table="users")
        assert rec["record_id"]
        sys = rec["source"]["system"]
        assert sys == "snowflake"

    def test_get_record_requires_table(self):
        c = _make_warehouse()
        with pytest.raises(ValueError):
            c.get_record("42")

    @patch("urllib.request.urlopen")
    def test_get_record_not_found(
        self, mock_urlopen,
    ):
        c = _make_warehouse()
        mock_urlopen.return_value = _mock_json_response({
            "resultSetMetaData": {
                "rowType": [{"name": "ID"}],
            },
            "data": [],
        })
        with pytest.raises(LookupError):
            c.get_record("999", table="users")

    @patch("urllib.request.urlopen")
    def test_to_envelopes(self, mock_urlopen):
        c = _make_warehouse()
        mock_urlopen.return_value = _mock_json_response({
            "resultSetMetaData": {
                "rowType": [{"name": "ID"}],
            },
            "data": [["1"]],
        })
        records = c.list_records(table="t")
        envelopes = c.to_envelopes(records)
        assert len(envelopes) == 1
        assert envelopes[0].source == "snowflake"
        assert envelopes[0].source_instance == "test"


# ── Column mapping tests ────────────────────────────────────


class TestColumnMapping:
    """Verify configurable column mapping."""

    def test_default_mapping(self):
        c = _make_warehouse()
        rows = [{
            "ID": "1",
            "CREATED_AT": "2024-01-01T00:00:00Z",
            "UPDATED_AT": "2024-01-02T00:00:00Z",
        }]
        records = c.to_canonical(rows, "t")
        assert "2024-01-01" in records[0]["created_at"]
        assert "2024-01-02" in records[0]["observed_at"]

    def test_custom_mapping(self):
        custom = {
            "INSERTED_TS": "created_at",
            "MODIFIED_TS": "observed_at",
        }
        c = _make_warehouse(column_map=custom)
        rows = [{
            "ID": "1",
            "INSERTED_TS": "2024-06-01T00:00:00Z",
            "MODIFIED_TS": "2024-06-02T00:00:00Z",
        }]
        records = c.to_canonical(rows, "t")
        created = records[0]["created_at"]
        observed = records[0]["observed_at"]
        assert "2024-06-01" in created
        assert "2024-06-02" in observed

    def test_missing_mapped_columns(self):
        c = _make_warehouse()
        rows = [{"ID": "1", "OTHER": "val"}]
        records = c.to_canonical(rows, "t")
        assert records[0]["created_at"] == ""
        assert records[0]["observed_at"] == ""


# ── Exhaust adapter tests ──────────────────────────────────


class TestCortexExhaustAdapter:
    @patch("urllib.request.urlopen")
    def test_complete_with_exhaust(
        self, mock_urlopen,
    ):
        from adapters.snowflake.exhaust import (
            CortexExhaustAdapter,
        )

        mock_connector = MagicMock()
        mock_connector.complete_sync.return_value = {
            "response": "Hello",
            "model": "mistral-large",
            "usage": {"chunks": 1},
        }
        mock_urlopen.return_value = _mock_json_response(
            {"ok": True},
        )

        adapter = CortexExhaustAdapter(mock_connector)
        msgs = [{"role": "user", "content": "Hi"}]
        result = adapter.complete_with_exhaust(
            "mistral-large", msgs,
        )
        assert result["response"] == "Hello"
        mock_connector.complete_sync.assert_called_once()

    @patch("urllib.request.urlopen")
    def test_exhaust_events_emitted(
        self, mock_urlopen,
    ):
        from adapters.snowflake.exhaust import (
            CortexExhaustAdapter,
        )

        mock_connector = MagicMock()
        mock_connector.complete_sync.return_value = {
            "response": "x", "usage": {"chunks": 1},
        }
        mock_urlopen.return_value = _mock_json_response(
            {"ok": True},
        )

        adapter = CortexExhaustAdapter(mock_connector)
        adapter.complete_with_exhaust("model", [])

        call_args = mock_urlopen.call_args[0][0]
        body = json.loads(call_args.data)
        assert len(body) == 3
        event_types = [
            e["event_type"] for e in body
        ]
        assert "prompt" in event_types
        assert "response" in event_types
        assert "metric" in event_types
