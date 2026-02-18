"""Tests for adapters.sharepoint.connector — SharePoint Graph API connector."""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch


import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from adapters._connector_helpers import strip_html, to_iso, uuid_from_hash, verify_webhook_hmac


# ── Helper tests ──────────────────────────────────────────────────────────────

class TestUUIDFromHash:
    def test_deterministic(self):
        a = uuid_from_hash("sp", "12345")
        b = uuid_from_hash("sp", "12345")
        assert a == b

    def test_different_prefix(self):
        a = uuid_from_hash("sp", "12345")
        b = uuid_from_hash("dv", "12345")
        assert a != b

    def test_format(self):
        result = uuid_from_hash("sp", "abc")
        assert len(result) == 36
        assert result.count("-") == 4


class TestToISO:
    def test_iso_passthrough(self):
        result = to_iso("2024-01-15T10:00:00Z")
        assert "2024-01-15" in result

    def test_epoch_ms(self):
        result = to_iso("1705312800000")
        assert result != ""

    def test_empty(self):
        assert to_iso("") == ""
        assert to_iso(None) == ""


class TestStripHTML:
    def test_basic(self):
        assert strip_html("<p>Hello</p>") == "Hello"

    def test_nested(self):
        assert strip_html("<div><p>Hello <b>world</b></p></div>") == "Hello world"

    def test_none(self):
        assert strip_html(None) == ""

    def test_no_html(self):
        assert strip_html("plain text") == "plain text"


class TestVerifyWebhookHMAC:
    def test_valid_signature(self):
        import hashlib
        import hmac as hmac_mod
        secret = "test-secret"
        body = b'{"test": true}'
        sig = hmac_mod.new(secret.encode(), body, hashlib.sha256).hexdigest()
        assert verify_webhook_hmac(body, secret, sig) is True

    def test_invalid_signature(self):
        assert verify_webhook_hmac(b"body", "secret", "bad-sig") is False

    def test_empty_secret(self):
        assert verify_webhook_hmac(b"body", "", "sig") is False


# ── SharePoint connector tests ───────────────────────────────────────────────

def _mock_graph_item(item_id="1", title="Test Item", content_type="Item", body="<p>Hello</p>"):
    return {
        "id": item_id,
        "createdDateTime": "2024-01-15T10:00:00Z",
        "lastModifiedDateTime": "2024-01-16T12:00:00Z",
        "createdBy": {"user": {"email": "user@example.com"}},
        "fields": {
            "id": item_id,
            "Title": title,
            "ContentType": {"Name": content_type},
            "Body": body,
            "Created": "2024-01-15T10:00:00Z",
            "Modified": "2024-01-16T12:00:00Z",
            "Author": "user@example.com",
            "FileLeafRef": "test.docx",
        },
    }


def _make_connector():
    from adapters.sharepoint.connector import SharePointConnector
    with patch.object(SharePointConnector, "__init__", lambda self, **kw: None):
        c = SharePointConnector.__new__(SharePointConnector)
        c._site_id = "site-123"
        c._delta_tokens = {}
        c._auth = MagicMock()
        c._auth.get_token.return_value = "fake-token"
        # Bind internal methods
        c._tenant_id = "t"
        c._client_id = "c"
        c._client_secret = "s"
        return c


class TestSharePointConnector:
    def test_to_canonical_basic(self):
        c = _make_connector()
        record = c._to_canonical(_mock_graph_item(), "list-1")
        assert record["record_id"]
        assert record["record_type"] == "Entity"  # "Item" maps to Entity
        assert record["source"]["system"] == "sharepoint"
        assert record["source"]["actor"]["id"] == "user@example.com"
        assert record["content"]["title"] == "Test Item"
        assert "Hello" in record["content"]["body"]
        assert "<p>" not in record["content"]["body"]

    def test_to_canonical_document(self):
        c = _make_connector()
        record = c._to_canonical(_mock_graph_item(content_type="Document"), "list-1")
        assert record["record_type"] == "Document"
        assert record["ttl"] == 0  # perpetual for docs

    def test_to_canonical_event(self):
        c = _make_connector()
        record = c._to_canonical(_mock_graph_item(content_type="Event"), "list-1")
        assert record["record_type"] == "Event"

    def test_to_canonical_confidence(self):
        c = _make_connector()
        record = c._to_canonical(_mock_graph_item(), "list-1")
        assert record["confidence"]["score"] == 0.8

    def test_to_canonical_auto_generated(self):
        c = _make_connector()
        item = _mock_graph_item()
        item["fields"]["Author"] = "System Account"
        record = c._to_canonical(item, "list-1")
        assert record["confidence"]["score"] == 0.5

    def test_to_canonical_provenance(self):
        c = _make_connector()
        record = c._to_canonical(_mock_graph_item(item_id="42"), "list-1")
        assert record["provenance"][0]["ref"] == "sharepoint://site-123/list-1/42"

    def test_to_canonical_dates(self):
        c = _make_connector()
        record = c._to_canonical(_mock_graph_item(), "list-1")
        assert "2024-01-15" in record["created_at"]
        assert "2024-01-16" in record["observed_at"]

    def test_to_canonical_tags(self):
        c = _make_connector()
        item = _mock_graph_item()
        item["fields"]["_ModerationStatus"] = "Approved"
        record = c._to_canonical(item, "list-1")
        assert "approval:Approved" in record["labels"]["tags"]

    @patch("urllib.request.urlopen")
    def test_list_items(self, mock_urlopen):
        c = _make_connector()
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({"value": [_mock_graph_item()]}).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        records = c.list_items("list-1")
        assert len(records) == 1
        assert records[0]["record_type"] == "Entity"

    @patch("urllib.request.urlopen")
    def test_get_item(self, mock_urlopen):
        c = _make_connector()
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(_mock_graph_item(item_id="42")).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        record = c.get_item("list-1", "42")
        assert "42" in record["provenance"][0]["ref"]

    @patch("urllib.request.urlopen")
    def test_delta_sync(self, mock_urlopen):
        c = _make_connector()
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({
            "value": [_mock_graph_item(), _mock_graph_item(item_id="2")],
            "@odata.deltaLink": "https://graph.microsoft.com/delta?token=abc",
        }).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        result = c.delta_sync("list-1")
        assert result["created"] == 2
        assert len(result["records"]) == 2
        assert c._delta_tokens["list-1"] == "https://graph.microsoft.com/delta?token=abc"

    def test_deterministic_record_ids(self):
        c = _make_connector()
        r1 = c._to_canonical(_mock_graph_item(item_id="42"), "list-1")
        r2 = c._to_canonical(_mock_graph_item(item_id="42"), "list-1")
        assert r1["record_id"] == r2["record_id"]

    def test_different_items_different_ids(self):
        c = _make_connector()
        r1 = c._to_canonical(_mock_graph_item(item_id="1"), "list-1")
        r2 = c._to_canonical(_mock_graph_item(item_id="2"), "list-1")
        assert r1["record_id"] != r2["record_id"]
