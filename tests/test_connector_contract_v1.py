"""Tests for the Connector Contract v1.0 — schema, envelope, and connector compliance."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from adapters.contract import (
    RecordEnvelope,
    canonical_to_envelope,
    compute_hash,
    normalize_envelope_fields,
    validate_envelope,
)

FIXTURE_DIR = Path(__file__).parent.parent / "src" / "demos" / "golden_path" / "fixtures" / "sharepoint_small"


# ── RecordEnvelope Tests ─────────────────────────────────────────────────────


class TestRecordEnvelope:
    def test_default_values(self):
        env = RecordEnvelope(source="test", record_id="r1", record_type="Document")
        assert env.envelope_version == "1.0"
        assert env.source == "test"
        assert env.collected_at  # auto-populated

    def test_auto_hash(self):
        env = RecordEnvelope(source="test", record_id="r1", record_type="Document", raw={"a": 1})
        assert "raw_sha256" in env.hashes
        assert len(env.hashes["raw_sha256"]) == 64

    def test_deterministic_hash(self):
        raw = {"key": "value", "nested": {"a": 1}}
        e1 = RecordEnvelope(source="s", record_id="r", record_type="T", raw=raw, collected_at="2026-01-01T00:00:00Z")
        e2 = RecordEnvelope(source="s", record_id="r", record_type="T", raw=raw, collected_at="2026-01-01T00:00:00Z")
        assert e1.hashes["raw_sha256"] == e2.hashes["raw_sha256"]

    def test_to_dict(self):
        env = RecordEnvelope(source="test", record_id="r1", record_type="Doc", raw="hello")
        d = env.to_dict()
        assert isinstance(d, dict)
        assert d["source"] == "test"
        assert d["record_id"] == "r1"
        assert d["raw"] == "hello"

    def test_to_dict_all_fields(self):
        env = RecordEnvelope(
            source="test",
            source_instance="inst",
            record_id="r1",
            record_type="Doc",
            raw={"a": 1},
            acl_tags=["admin"],
            metadata={"key": "val"},
        )
        d = env.to_dict()
        for key in ("envelope_version", "source", "source_instance", "collected_at",
                     "record_id", "record_type", "provenance", "hashes", "acl_tags",
                     "raw", "metadata"):
            assert key in d, f"Missing key: {key}"


# ── compute_hash Tests ───────────────────────────────────────────────────────


class TestComputeHash:
    def test_string_hash(self):
        h = compute_hash("hello")
        assert len(h) == 64
        assert h == compute_hash("hello")

    def test_dict_hash(self):
        h = compute_hash({"b": 2, "a": 1})
        assert h == compute_hash({"a": 1, "b": 2})  # sorted keys

    def test_different_data(self):
        assert compute_hash("a") != compute_hash("b")


# ── validate_envelope Tests ──────────────────────────────────────────────────


class TestValidateEnvelope:
    def test_valid_envelope(self):
        env = RecordEnvelope(
            source="sharepoint",
            source_instance="site-1",
            record_id="r1",
            record_type="Document",
            provenance={"uri": "sharepoint://site/list/1"},
            raw={"title": "Test"},
        )
        errors = validate_envelope(env.to_dict())
        assert errors == [], f"Unexpected errors: {errors}"

    def test_missing_required_fields(self):
        errors = validate_envelope({})
        assert len(errors) > 0

    def test_missing_source(self):
        env = RecordEnvelope(record_id="r1", record_type="Doc", raw={"a": 1})
        env.source = ""
        d = env.to_dict()
        errors = validate_envelope(d)
        assert len(errors) > 0  # empty source violates minLength

    def test_missing_provenance_uri(self):
        d = RecordEnvelope(
            source="test",
            source_instance="inst",
            record_id="r1",
            record_type="Doc",
            provenance={},
            raw={"a": 1},
        ).to_dict()
        errors = validate_envelope(d)
        assert any("uri" in e.lower() for e in errors)

    def test_invalid_hash_format(self):
        d = RecordEnvelope(
            source="test",
            source_instance="inst",
            record_id="r1",
            record_type="Doc",
            provenance={"uri": "test://a"},
            raw={"a": 1},
        ).to_dict()
        d["hashes"]["raw_sha256"] = "not-a-sha256"
        errors = validate_envelope(d)
        assert len(errors) > 0


# ── normalize_envelope_fields Tests ──────────────────────────────────────────


class TestNormalizeEnvelopeFields:
    def test_adds_defaults(self):
        d = {"source": "test", "record_id": "r1", "record_type": "Doc", "raw": {"a": 1}}
        result = normalize_envelope_fields(d)
        assert result["envelope_version"] == "1.0"
        assert result["acl_tags"] == []
        assert result["metadata"] == {}
        assert "raw_sha256" in result["hashes"]

    def test_coerce_acl_tags_string(self):
        d = {"acl_tags": "admin"}
        normalize_envelope_fields(d)
        assert d["acl_tags"] == ["admin"]

    def test_preserves_existing(self):
        d = {"envelope_version": "1.0", "acl_tags": ["x"], "hashes": {"raw_sha256": "abc" * 21 + "a"}, "metadata": {"k": "v"}}
        normalize_envelope_fields(d)
        assert d["acl_tags"] == ["x"]
        assert d["metadata"] == {"k": "v"}


# ── canonical_to_envelope Tests ──────────────────────────────────────────────


class TestCanonicalToEnvelope:
    def _load_records(self):
        return json.loads((FIXTURE_DIR / "baseline.json").read_text())

    def test_converts_sharepoint_record(self):
        records = self._load_records()
        env = canonical_to_envelope(records[0], source_instance="contoso")
        assert env.source == "sharepoint"
        assert env.source_instance == "contoso"
        assert env.record_id == records[0]["record_id"]
        assert env.record_type == "Document"
        assert env.raw == records[0]
        assert "raw_sha256" in env.hashes

    def test_envelope_validates(self):
        records = self._load_records()
        for rec in records:
            env = canonical_to_envelope(rec, source_instance="contoso")
            errors = validate_envelope(env.to_dict())
            assert errors == [], f"Validation errors for {rec['record_id']}: {errors}"

    def test_all_fixture_records_valid(self):
        records = self._load_records()
        for rec in records:
            env = canonical_to_envelope(rec, source_instance="contoso")
            d = env.to_dict()
            assert d["source"] == rec["source"]["system"]
            assert d["record_id"] == rec["record_id"]
            assert d["record_type"] == rec["record_type"]

    def test_provenance_uri(self):
        records = self._load_records()
        env = canonical_to_envelope(records[0])
        assert "sharepoint://" in env.provenance["uri"]

    def test_metadata_includes_confidence(self):
        records = self._load_records()
        env = canonical_to_envelope(records[0])
        assert env.metadata["confidence"] == 0.85

    def test_hash_stability(self):
        records = self._load_records()
        e1 = canonical_to_envelope(records[0], source_instance="x")
        e2 = canonical_to_envelope(records[0], source_instance="x")
        assert e1.hashes["raw_sha256"] == e2.hashes["raw_sha256"]


# ── Connector to_envelopes Tests ────────────────────────────────────────────


class TestConnectorToEnvelopes:
    def _load_fixture_records(self):
        return json.loads((FIXTURE_DIR / "baseline.json").read_text())

    def test_sharepoint_to_envelopes(self):
        from unittest.mock import patch, MagicMock
        from adapters.sharepoint.connector import SharePointConnector

        with patch.object(SharePointConnector, "__init__", lambda self, **kw: None):
            c = SharePointConnector.__new__(SharePointConnector)
            c._site_id = "site-123"
            c._delta_tokens = {}
            c._auth = MagicMock()
            c._tenant_id = "t"
            c._client_id = "c"
            c._client_secret = "s"

        records = self._load_fixture_records()
        envs = c.to_envelopes(records)
        assert len(envs) == 5
        for env in envs:
            errors = validate_envelope(env.to_dict())
            assert errors == [], f"Validation failed: {errors}"
        assert envs[0].source == "sharepoint"
        assert envs[0].source_instance == "site-123"

    def test_dataverse_to_envelopes(self):
        from unittest.mock import patch, MagicMock
        from adapters.powerplatform.connector import DataverseConnector

        with patch.object(DataverseConnector, "__init__", lambda self, **kw: None):
            c = DataverseConnector.__new__(DataverseConnector)
            c._env_url = "https://org.crm.dynamics.com"
            c._auth = MagicMock()
            c._client_id = "c"
            c._client_secret = "s"
            c._tenant_id = "t"

        records = self._load_fixture_records()
        envs = c.to_envelopes(records)
        assert len(envs) == 5
        for env in envs:
            errors = validate_envelope(env.to_dict())
            assert errors == [], f"Validation failed: {errors}"

    def test_snowflake_to_envelopes(self):
        from unittest.mock import patch, MagicMock
        from adapters.snowflake.warehouse import SnowflakeWarehouseConnector

        with patch.object(SnowflakeWarehouseConnector, "__init__", lambda self, **kw: None):
            c = SnowflakeWarehouseConnector.__new__(SnowflakeWarehouseConnector)
            c._auth = MagicMock()
            c._auth.account = "acme-account"
            c._database = "DB"
            c._schema = "PUBLIC"
            c._warehouse = "WH"

        records = self._load_fixture_records()
        envs = c.to_envelopes(records)
        assert len(envs) == 5
        for env in envs:
            errors = validate_envelope(env.to_dict())
            assert errors == [], f"Validation failed: {errors}"

    def test_asksage_to_envelopes(self):
        from unittest.mock import patch
        from adapters.asksage.connector import AskSageConnector

        with patch.object(AskSageConnector, "__init__", lambda self, **kw: None):
            c = AskSageConnector.__new__(AskSageConnector)
            c._base_url = "https://api.asksage.ai"
            c._email = ""
            c._api_key = ""
            c._cached_token = None
            c._token_expiry = 0.0

        records = self._load_fixture_records()
        envs = c.to_envelopes(records)
        assert len(envs) == 5
        for env in envs:
            errors = validate_envelope(env.to_dict())
            assert errors == [], f"Validation failed: {errors}"


# ── Source name attribute Tests ──────────────────────────────────────────────


class TestSourceNameAttribute:
    def test_sharepoint(self):
        from adapters.sharepoint.connector import SharePointConnector
        assert SharePointConnector.source_name == "sharepoint"

    def test_dataverse(self):
        from adapters.powerplatform.connector import DataverseConnector
        assert DataverseConnector.source_name == "dataverse"

    def test_asksage(self):
        from adapters.asksage.connector import AskSageConnector
        assert AskSageConnector.source_name == "asksage"

    def test_snowflake(self):
        from adapters.snowflake.warehouse import SnowflakeWarehouseConnector
        assert SnowflakeWarehouseConnector.source_name == "snowflake"

    def test_langgraph(self):
        from adapters.langgraph.connector import LangGraphConnector
        assert LangGraphConnector.source_name == "langgraph"


# ── ConnectorV1 method presence ───────────────────────


class TestConnectorV1Methods:
    """Every adapter must have list_records, get_record,
    to_envelopes, and source_name."""

    _ADAPTERS = [
        "adapters.sharepoint.connector.SharePointConnector",
        "adapters.powerplatform.connector.DataverseConnector",
        "adapters.asksage.connector.AskSageConnector",
        "adapters.snowflake.warehouse.SnowflakeWarehouseConnector",
        "adapters.langgraph.connector.LangGraphConnector",
    ]

    def _load(self, fqn: str):
        mod_path, cls_name = fqn.rsplit(".", 1)
        import importlib
        mod = importlib.import_module(mod_path)
        return getattr(mod, cls_name)

    def test_all_have_source_name(self):
        for fqn in self._ADAPTERS:
            cls = self._load(fqn)
            assert hasattr(cls, "source_name"), (
                f"{fqn} missing source_name"
            )

    def test_all_have_list_records(self):
        for fqn in self._ADAPTERS:
            cls = self._load(fqn)
            assert hasattr(cls, "list_records"), (
                f"{fqn} missing list_records"
            )

    def test_all_have_get_record(self):
        for fqn in self._ADAPTERS:
            cls = self._load(fqn)
            assert hasattr(cls, "get_record"), (
                f"{fqn} missing get_record"
            )

    def test_all_have_to_envelopes(self):
        for fqn in self._ADAPTERS:
            cls = self._load(fqn)
            assert hasattr(cls, "to_envelopes"), (
                f"{fqn} missing to_envelopes"
            )

    def test_query_based_raise_not_implemented(self):
        """AskSage + LangGraph should raise."""
        import pytest
        from unittest.mock import patch
        from adapters.asksage.connector import (
            AskSageConnector,
        )
        from adapters.langgraph.connector import (
            LangGraphConnector,
        )

        with patch.object(
            AskSageConnector, "__init__",
            lambda self, **kw: None,
        ):
            c = AskSageConnector.__new__(
                AskSageConnector,
            )
        with pytest.raises(NotImplementedError):
            c.list_records()
        with pytest.raises(NotImplementedError):
            c.get_record("x")

        with patch.object(
            LangGraphConnector, "__init__",
            lambda self, **kw: None,
        ):
            lg = LangGraphConnector.__new__(
                LangGraphConnector,
            )
        with pytest.raises(NotImplementedError):
            lg.list_records()
        with pytest.raises(NotImplementedError):
            lg.get_record("x")
