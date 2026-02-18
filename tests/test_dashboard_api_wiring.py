"""Tests for new dashboard API endpoints (Tier 1 wiring)."""
import json
import os

import pytest

# Skip if FastAPI not installed
try:
    from fastapi.testclient import TestClient
    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False

pytestmark = pytest.mark.skipif(not HAS_FASTAPI, reason="FastAPI not installed")


@pytest.fixture
def client(tmp_path):
    """Create a test client with temp data directory."""
    # Write a sample episode
    ep = {
        "episodeId": "ep-wire-001",
        "decisionType": "deploy",
        "startedAt": "2026-01-01T00:00:00Z",
        "endedAt": "2026-01-01T00:01:00Z",
        "outcome": {"code": "success"},
        "telemetry": {"endToEndMs": 1500},
        "seal": {"sealHash": "abc123"},
    }
    (tmp_path / "ep-wire-001.json").write_text(json.dumps(ep))

    # Write a sample drift event
    drift = {
        "driftId": "drift-wire-001",
        "episodeId": "ep-wire-001",
        "driftType": "freshness",
        "severity": "yellow",
    }
    (tmp_path / "drift-wire-001.drift.json").write_text(json.dumps(drift))

    os.environ["DATA_DIR"] = str(tmp_path)

    # Force reload of the module to pick up new DATA_DIR
    import dashboard.server.api as api_mod
    api_mod.DATA_DIR = tmp_path
    # Clear pipeline cache
    api_mod._pipeline_cache = None
    api_mod._pipeline_cache_time = 0.0

    from dashboard.server.api import app
    return TestClient(app)


class TestIrisEndpoint:
    def test_post_iris_status(self, client):
        resp = client.post("/api/iris", json={"query_type": "STATUS"})
        assert resp.status_code == 200
        data = resp.json()
        assert "query_type" in data or "status" in data

    def test_post_iris_why(self, client):
        resp = client.post("/api/iris", json={
            "query_type": "WHY",
            "episode_id": "ep-wire-001",
        })
        assert resp.status_code == 200


class TestDriftsEndpoint:
    def test_get_drifts_plural(self, client):
        resp = client.get("/api/drifts")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_get_drifts_with_severity_filter(self, client):
        resp = client.get("/api/drifts?severity=yellow")
        assert resp.status_code == 200


class TestAgentsEndpoint:
    def test_get_agents(self, client):
        resp = client.get("/api/agents")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        if data:
            assert "agentName" in data[0]
            assert "episodeCount" in data[0]


class TestMemoryGraphStats:
    def test_get_mg_stats(self, client):
        resp = client.get("/api/memory-graph/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_nodes" in data
        assert "total_edges" in data


class TestExistingEndpoints:
    def test_health(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_episodes(self, client):
        resp = client.get("/api/episodes")
        assert resp.status_code == 200

    def test_drift_original(self, client):
        resp = client.get("/api/drift")
        assert resp.status_code == 200
