from __future__ import annotations

import pytest

TestClient = pytest.importorskip("fastapi.testclient").TestClient

from dashboard.api_server import app  # noqa: E402


def test_metrics_endpoint_exposes_required_series():
    client = TestClient(app)

    # Seed a few request and duration metrics.
    client.get("/api/health")
    client.post("/api/iris", json={"query_type": "STATUS"})

    resp = client.get("/metrics")
    assert resp.status_code == 200
    text = resp.text

    required = [
        "deepsigma_claims_total",
        "deepsigma_drift_events_total",
        "deepsigma_packet_seal_duration_seconds",
        "deepsigma_iris_query_duration_seconds",
        "deepsigma_api_requests_total",
        "deepsigma_evidence_tier_count",
    ]
    for name in required:
        assert name in text
