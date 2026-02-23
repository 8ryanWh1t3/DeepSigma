from __future__ import annotations

from fastapi.testclient import TestClient

from dashboard.api_server import app


def test_openapi_json_served_and_contains_required_domains():
    client = TestClient(app)
    resp = client.get("/openapi.json")
    assert resp.status_code == 200

    spec = resp.json()
    paths = spec.get("paths", {})

    assert "/api/credibility/snapshot" in paths
    assert "/mesh/{tenant_id}/summary" in paths
    assert "/api/tenants" in paths
    assert "/api/{tenant_id}/policy" in paths
    assert "/api/{tenant_id}/audit/recent" in paths
