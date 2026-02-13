"""Unit tests for dashboard REST API endpoints — closes #21."""
import json
import pytest

# Skip all tests if FastAPI / httpx are not installed
fastapi = pytest.importorskip("fastapi")
httpx = pytest.importorskip("httpx")

from fastapi.testclient import TestClient
from dashboard.server.api import app


@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(app)


# -------------------------------------------------------------------
# Existing endpoints
# -------------------------------------------------------------------

class TestHealthEndpoint:
    def test_health(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


# -------------------------------------------------------------------
# CoherenceOps endpoints
# -------------------------------------------------------------------

class TestCoherenceStatus:
    def test_status_returns_pillars(self, client):
        resp = client.get("/api/coherence/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "pipeline" in data
        assert "pillars" in data
        for pillar in ("dlr", "rs", "ds", "mg"):
            assert pillar in data["pillars"]

    def test_status_has_record_count(self, client):
        resp = client.get("/api/coherence/status")
        data = resp.json()
        assert "record_count" in data


class TestCoherenceDLR:
    def test_dlr_not_found(self, client):
        resp = client.get("/api/coherence/dlr/nonexistent-episode")
        assert resp.status_code == 404


# -------------------------------------------------------------------
# Records endpoints
# -------------------------------------------------------------------

class TestRecordsList:
    def test_list_records(self, client):
        resp = client.get("/api/records")
        assert resp.status_code == 200
        data = resp.json()
        assert "count" in data
        assert "records" in data
        assert isinstance(data["records"], list)

    def test_list_records_filter_by_type(self, client):
        resp = client.get("/api/records?record_type=Metric")
        assert resp.status_code == 200
        data = resp.json()
        for r in data["records"]:
            assert r["record_type"] == "Metric"

    def test_list_records_limit(self, client):
        resp = client.get("/api/records?limit=2")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] <= 2


class TestRecordStats:
    def test_stats_structure(self, client):
        resp = client.get("/api/records/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_records" in data
        assert "by_type" in data
        assert "sealed_count" in data
        assert "seal_rate" in data
        assert "ttl_configured_count" in data


class TestRecordDetail:
    def test_record_not_found(self, client):
        resp = client.get("/api/records/nonexistent-id")
        assert resp.status_code == 404

    def test_record_found_if_exists(self, client):
        # First get the list to find a valid record_id
        list_resp = client.get("/api/records?limit=1")
        records = list_resp.json().get("records", [])
        if records:
            rid = records[0]["record_id"]
            resp = client.get(f"/api/records/{rid}")
            assert resp.status_code == 200
            assert resp.json()["record_id"] == rid
            assert "_seal_verified" in resp.json()
