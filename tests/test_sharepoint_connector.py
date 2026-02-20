"""Tests for SharePoint Graph API connector.

Covers helper functions, canonical transformation, ConnectorV1
contract methods (list_records, get_record), and 429 retry logic.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from adapters._connector_helpers import (  # noqa: E402
    strip_html,
    to_iso,
    uuid_from_hash,
    verify_webhook_hmac,
)


# ── Helper tests ─────────────────────────────────────────────


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
        result = strip_html(
            "<div><p>Hello <b>world</b></p></div>"
        )
        assert result == "Hello world"

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
        sig = hmac_mod.new(
            secret.encode(), body, hashlib.sha256,
        ).hexdigest()
        assert verify_webhook_hmac(body, secret, sig)

    def test_invalid_signature(self):
        result = verify_webhook_hmac(
            b"body", "secret", "bad-sig",
        )
        assert result is False

    def test_empty_secret(self):
        result = verify_webhook_hmac(b"body", "", "sig")
        assert result is False


# ── SharePoint connector tests ──────────────────────────────


def _mock_graph_item(
    item_id="1",
    title="Test Item",
    content_type="Item",
    body="<p>Hello</p>",
):
    return {
        "id": item_id,
        "createdDateTime": "2024-01-15T10:00:00Z",
        "lastModifiedDateTime": "2024-01-16T12:00:00Z",
        "createdBy": {
            "user": {"email": "user@example.com"},
        },
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
    from adapters.sharepoint.connector import (
        SharePointConnector,
    )

    with patch.object(
        SharePointConnector,
        "__init__",
        lambda self, **kw: None,
    ):
        c = SharePointConnector.__new__(
            SharePointConnector,
        )
        c._site_id = "site-123"
        c._delta_tokens = {}
        c._auth = MagicMock()
        c._auth.get_token.return_value = "fake-token"
        c._tenant_id = "t"
        c._client_id = "c"
        c._client_secret = "s"
        return c


def _mock_urlopen(data):
    """Create a mock urlopen context manager."""
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(
        data,
    ).encode()
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    return mock_resp


class TestSharePointConnector:
    def test_to_canonical_basic(self):
        c = _make_connector()
        rec = c._to_canonical(
            _mock_graph_item(), "list-1",
        )
        assert rec["record_id"]
        assert rec["record_type"] == "Entity"
        assert rec["source"]["system"] == "sharepoint"
        actor_id = rec["source"]["actor"]["id"]
        assert actor_id == "user@example.com"
        assert rec["content"]["title"] == "Test Item"
        assert "Hello" in rec["content"]["body"]
        assert "<p>" not in rec["content"]["body"]

    def test_to_canonical_document(self):
        c = _make_connector()
        item = _mock_graph_item(content_type="Document")
        rec = c._to_canonical(item, "list-1")
        assert rec["record_type"] == "Document"
        assert rec["ttl"] == 0

    def test_to_canonical_event(self):
        c = _make_connector()
        item = _mock_graph_item(content_type="Event")
        rec = c._to_canonical(item, "list-1")
        assert rec["record_type"] == "Event"

    def test_to_canonical_confidence(self):
        c = _make_connector()
        rec = c._to_canonical(
            _mock_graph_item(), "list-1",
        )
        assert rec["confidence"]["score"] == 0.8

    def test_to_canonical_auto_generated(self):
        c = _make_connector()
        item = _mock_graph_item()
        item["fields"]["Author"] = "System Account"
        rec = c._to_canonical(item, "list-1")
        assert rec["confidence"]["score"] == 0.5

    def test_to_canonical_provenance(self):
        c = _make_connector()
        item = _mock_graph_item(item_id="42")
        rec = c._to_canonical(item, "list-1")
        ref = rec["provenance"][0]["ref"]
        assert ref == "sharepoint://site-123/list-1/42"

    def test_to_canonical_dates(self):
        c = _make_connector()
        rec = c._to_canonical(
            _mock_graph_item(), "list-1",
        )
        assert "2024-01-15" in rec["created_at"]
        assert "2024-01-16" in rec["observed_at"]

    def test_to_canonical_tags(self):
        c = _make_connector()
        item = _mock_graph_item()
        item["fields"]["_ModerationStatus"] = "Approved"
        rec = c._to_canonical(item, "list-1")
        assert "approval:Approved" in rec["labels"]["tags"]

    @patch("urllib.request.urlopen")
    def test_list_items(self, mock_urlopen):
        c = _make_connector()
        data = {"value": [_mock_graph_item()]}
        mock_urlopen.return_value = _mock_urlopen(data)

        records = c.list_items("list-1")
        assert len(records) == 1
        assert records[0]["record_type"] == "Entity"

    @patch("urllib.request.urlopen")
    def test_get_item(self, mock_urlopen):
        c = _make_connector()
        item = _mock_graph_item(item_id="42")
        mock_urlopen.return_value = _mock_urlopen(item)

        rec = c.get_item("list-1", "42")
        assert "42" in rec["provenance"][0]["ref"]

    @patch("urllib.request.urlopen")
    def test_delta_sync(self, mock_urlopen):
        c = _make_connector()
        delta_url = (
            "https://graph.microsoft.com/delta"
            "?token=abc"
        )
        data = {
            "value": [
                _mock_graph_item(),
                _mock_graph_item(item_id="2"),
            ],
            "@odata.deltaLink": delta_url,
        }
        mock_urlopen.return_value = _mock_urlopen(data)

        result = c.delta_sync("list-1")
        assert result["created"] == 2
        assert len(result["records"]) == 2
        assert c._delta_tokens["list-1"] == delta_url

    def test_deterministic_record_ids(self):
        c = _make_connector()
        item = _mock_graph_item(item_id="42")
        r1 = c._to_canonical(item, "list-1")
        r2 = c._to_canonical(item, "list-1")
        assert r1["record_id"] == r2["record_id"]

    def test_different_items_different_ids(self):
        c = _make_connector()
        r1 = c._to_canonical(
            _mock_graph_item(item_id="1"), "list-1",
        )
        r2 = c._to_canonical(
            _mock_graph_item(item_id="2"), "list-1",
        )
        assert r1["record_id"] != r2["record_id"]


# ── ConnectorV1 contract tests ──────────────────────────────


class TestConnectorV1Contract:
    """Verify list_records / get_record protocol methods."""

    @patch("urllib.request.urlopen")
    def test_list_records(self, mock_urlopen):
        c = _make_connector()
        data = {"value": [_mock_graph_item()]}
        mock_urlopen.return_value = _mock_urlopen(data)

        records = c.list_records(list_id="list-1")
        assert len(records) == 1
        assert records[0]["source"]["system"] == "sharepoint"

    def test_list_records_requires_list_id(self):
        c = _make_connector()
        with pytest.raises(ValueError, match="list_id"):
            c.list_records()

    @patch("urllib.request.urlopen")
    def test_get_record(self, mock_urlopen):
        c = _make_connector()
        item = _mock_graph_item(item_id="42")
        mock_urlopen.return_value = _mock_urlopen(item)

        rec = c.get_record("42", list_id="list-1")
        assert "42" in rec["provenance"][0]["ref"]

    def test_get_record_requires_list_id(self):
        c = _make_connector()
        with pytest.raises(ValueError, match="list_id"):
            c.get_record("42")

    @patch("urllib.request.urlopen")
    def test_to_envelopes(self, mock_urlopen):
        c = _make_connector()
        data = {"value": [_mock_graph_item()]}
        mock_urlopen.return_value = _mock_urlopen(data)

        records = c.list_records(list_id="list-1")
        envelopes = c.to_envelopes(records)
        assert len(envelopes) == 1
        assert envelopes[0].source == "sharepoint"
        assert envelopes[0].source_instance == "site-123"


# ── Rate-limit / 429 retry tests ────────────────────────────


class TestThrottleRetry:
    """Verify exponential backoff on HTTP 429 / 503."""

    @patch("time.sleep")
    @patch("urllib.request.urlopen")
    def test_429_retry_succeeds(
        self, mock_urlopen, mock_sleep,
    ):
        import urllib.error

        err = urllib.error.HTTPError(
            "http://graph", 429, "Too Many Requests",
            {"Retry-After": "1"}, None,
        )
        ok = _mock_urlopen({"value": []})
        mock_urlopen.side_effect = [err, ok]

        c = _make_connector()
        result = c._graph_get("http://graph/test")
        assert result == {"value": []}
        assert mock_sleep.call_count == 1

    @patch("time.sleep")
    @patch("urllib.request.urlopen")
    def test_503_retry_succeeds(
        self, mock_urlopen, mock_sleep,
    ):
        import urllib.error

        err = urllib.error.HTTPError(
            "http://graph", 503, "Service Unavailable",
            {}, None,
        )
        ok = _mock_urlopen({"value": []})
        mock_urlopen.side_effect = [err, ok]

        c = _make_connector()
        result = c._graph_get("http://graph/test")
        assert result == {"value": []}

    @patch("time.sleep")
    @patch("urllib.request.urlopen")
    def test_429_exhausted_raises(
        self, mock_urlopen, mock_sleep,
    ):
        import urllib.error

        err = urllib.error.HTTPError(
            "http://graph", 429, "Too Many Requests",
            {}, None,
        )
        mock_urlopen.side_effect = [err] * 10

        c = _make_connector()
        with pytest.raises(urllib.error.HTTPError):
            c._graph_get("http://graph/test")

    @patch("time.sleep")
    @patch("urllib.request.urlopen")
    def test_retry_after_header_honoured(
        self, mock_urlopen, mock_sleep,
    ):
        import urllib.error

        err = urllib.error.HTTPError(
            "http://graph", 429, "Throttled",
            {"Retry-After": "5"}, None,
        )
        ok = _mock_urlopen({"value": []})
        mock_urlopen.side_effect = [err, ok]

        c = _make_connector()
        c._graph_get("http://graph/test")
        mock_sleep.assert_called_once_with(5)

    @patch("urllib.request.urlopen")
    def test_non_retryable_error_raises(
        self, mock_urlopen,
    ):
        import urllib.error

        err = urllib.error.HTTPError(
            "http://graph", 403, "Forbidden",
            {}, None,
        )
        mock_urlopen.side_effect = err

        c = _make_connector()
        with pytest.raises(urllib.error.HTTPError) as exc:
            c._graph_get("http://graph/test")
        assert exc.value.code == 403


# ── Integration tests (skip without creds) ──────────────────

_HAS_SP_CREDS = all(
    os.environ.get(k)
    for k in (
        "SP_TENANT_ID", "SP_CLIENT_ID",
        "SP_CLIENT_SECRET", "SP_SITE_ID",
    )
)


@pytest.mark.skipif(
    not _HAS_SP_CREDS,
    reason="SharePoint credentials not configured",
)
class TestSharePointIntegration:
    """Live integration tests — require real Azure AD creds.

    Set SP_TENANT_ID, SP_CLIENT_ID, SP_CLIENT_SECRET,
    SP_SITE_ID to enable.
    """

    def test_auth_token_acquisition(self):
        from adapters.sharepoint.connector import (
            SharePointConnector,
        )

        c = SharePointConnector()
        token = c._auth.get_token()
        assert token
        assert len(token) > 20

    def test_list_records_live(self):
        from adapters.sharepoint.connector import (
            SharePointConnector,
        )

        c = SharePointConnector()
        list_id = os.environ.get("SP_TEST_LIST_ID", "")
        if not list_id:
            pytest.skip("SP_TEST_LIST_ID not set")
        records = c.list_records(list_id=list_id)
        assert isinstance(records, list)
