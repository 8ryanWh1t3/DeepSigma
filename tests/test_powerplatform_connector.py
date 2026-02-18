"""Tests for adapters.powerplatform.connector — Dataverse Web API connector."""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch


import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))


def _mock_account_row(account_id="a1b2c3d4-e5f6-7890-abcd-ef1234567890"):
    return {
        "accountid": account_id,
        "name": "Contoso Ltd",
        "createdon": "2024-01-10T08:00:00Z",
        "modifiedon": "2024-06-15T14:30:00Z",
        "_ownerid_value": "user-guid-1",
        "_ownerid_type": "systemuser",
        "statecode": 0,
        "statuscode": 1,
        "telephone1": "555-0100",
        "address1_city": "Seattle",
    }


def _mock_incident_row(incident_id="inc-001"):
    return {
        "incidentid": incident_id,
        "title": "Login issue",
        "createdon": "2024-03-01T09:00:00Z",
        "modifiedon": "2024-03-02T10:00:00Z",
        "_ownerid_value": "team-guid-1",
        "_ownerid_type": "team",
        "statecode": 0,
        "statuscode": 1,
    }


def _mock_resolved_incident():
    row = _mock_incident_row()
    row["statecode"] = 2
    row["statuscode"] = 5
    return row


def _make_connector():
    from adapters.powerplatform.connector import DataverseConnector
    with patch.object(DataverseConnector, "__init__", lambda self, **kw: None):
        c = DataverseConnector.__new__(DataverseConnector)
        c._env_url = "https://org.crm.dynamics.com"
        c._client_id = "c"
        c._client_secret = "s"
        c._tenant_id = "t"
        c._auth = MagicMock()
        c._auth.get_token.return_value = "fake-token"
        return c


class TestDataverseConnector:
    def test_to_canonical_account(self):
        c = _make_connector()
        record = c._to_canonical(_mock_account_row(), "accounts")
        assert record["record_type"] == "Entity"
        assert record["record_id"].startswith("rec_")
        assert record["confidence"]["score"] == 0.95
        assert record["ttl"] == 86400000
        assert record["source"]["actor"]["type"] == "human"

    def test_to_canonical_incident(self):
        c = _make_connector()
        record = c._to_canonical(_mock_incident_row(), "incidents")
        assert record["record_type"] == "Event"
        assert record["confidence"]["score"] == 0.75
        assert record["ttl"] == 3600000
        assert record["source"]["actor"]["type"] == "system"  # team → system

    def test_to_canonical_resolved_incident(self):
        c = _make_connector()
        record = c._to_canonical(_mock_resolved_incident(), "incidents")
        assert record["ttl"] == 0  # perpetual for resolved
        assert record["confidence"]["score"] >= 0.80

    def test_to_canonical_provenance(self):
        c = _make_connector()
        record = c._to_canonical(_mock_account_row(), "accounts")
        prov = record["provenance"][0]
        assert prov["type"] == "source"
        assert "dataverse://org/accounts/" in prov["ref"]

    def test_to_canonical_dates(self):
        c = _make_connector()
        record = c._to_canonical(_mock_account_row(), "accounts")
        assert "2024-01-10" in record["created_at"]
        assert "2024-06-15" in record["observed_at"]

    def test_to_canonical_tags(self):
        c = _make_connector()
        record = c._to_canonical(_mock_account_row(), "accounts")
        assert "state:Active" in record["labels"]["tags"]

    def test_to_canonical_resolved_tags(self):
        c = _make_connector()
        record = c._to_canonical(_mock_resolved_incident(), "incidents")
        assert "state:Resolved" in record["labels"]["tags"]

    def test_to_canonical_content(self):
        c = _make_connector()
        record = c._to_canonical(_mock_account_row(), "accounts")
        assert "telephone1" in record["content"]
        assert record["content"]["name"] == "Contoso Ltd"

    def test_to_canonical_content_excludes_metadata(self):
        c = _make_connector()
        record = c._to_canonical(_mock_account_row(), "accounts")
        assert "createdon" not in record["content"]
        assert "modifiedon" not in record["content"]
        assert "statecode" not in record["content"]

    def test_extract_pk_accounts(self):
        from adapters.powerplatform.connector import DataverseConnector
        pk = DataverseConnector._extract_pk(_mock_account_row(), "accounts")
        assert pk == "a1b2c3d4-e5f6-7890-abcd-ef1234567890"

    def test_extract_pk_incidents(self):
        from adapters.powerplatform.connector import DataverseConnector
        pk = DataverseConnector._extract_pk(_mock_incident_row(), "incidents")
        assert pk == "inc-001"

    def test_extract_pk_fallback(self):
        from adapters.powerplatform.connector import DataverseConnector
        row = {"activityid": "act-guid-12345678-1234-1234-1234-123456789012"}
        pk = DataverseConnector._extract_pk(row, "activities")
        assert pk == "act-guid-12345678-1234-1234-1234-123456789012"

    def test_unknown_table_type(self):
        c = _make_connector()
        record = c._to_canonical({"createdon": "", "modifiedon": ""}, "custom_table")
        assert record["record_type"] == "Claim"
        assert record["confidence"]["score"] == 0.70

    @patch("urllib.request.urlopen")
    def test_list_records(self, mock_urlopen):
        c = _make_connector()
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({
            "value": [_mock_account_row()],
        }).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        records = c.list_records("accounts")
        assert len(records) == 1
        assert records[0]["record_type"] == "Entity"

    @patch("urllib.request.urlopen")
    def test_get_record(self, mock_urlopen):
        c = _make_connector()
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(_mock_account_row()).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        record = c.get_record("accounts", "a1b2c3d4-e5f6-7890-abcd-ef1234567890")
        assert record["record_id"].startswith("rec_")

    @patch("urllib.request.urlopen")
    def test_query(self, mock_urlopen):
        c = _make_connector()
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({
            "value": [_mock_incident_row(), _mock_incident_row(incident_id="inc-002")],
        }).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        records = c.query("incidents", "$filter=statecode eq 0")
        assert len(records) == 2

    @patch("urllib.request.urlopen")
    def test_odata_headers(self, mock_urlopen):
        c = _make_connector()
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({"value": []}).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        c.list_records("accounts")
        req = mock_urlopen.call_args[0][0]
        assert req.get_header("Odata-maxversion") == "4.0"
        assert req.get_header("Odata-version") == "4.0"


class TestCustomConnectorJSON:
    def test_valid_json(self):
        path = Path(__file__).parent.parent / "adapters" / "powerplatform" / "custom_connector.json"
        data = json.loads(path.read_text())
        assert data["swagger"] == "2.0"
        assert "IngestRecord" in str(data)
        assert "QueryIRIS" in str(data)
        assert "CheckCoherence" in str(data)
        assert "EmitDrift" in str(data)
