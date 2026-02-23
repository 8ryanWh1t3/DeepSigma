"""Health/readiness/drain semantics for dashboard API server."""

from __future__ import annotations

import asyncio
import time

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

import dashboard.api_server as api_mod


@pytest.fixture(autouse=True)
def _reset_runtime_flags():
    api_mod._draining = False
    api_mod._inflight_requests = 0
    yield
    api_mod._draining = False
    api_mod._inflight_requests = 0


@pytest.fixture
def client():
    return TestClient(api_mod.app)


def test_health_degraded_when_persistence_unavailable(client, monkeypatch):
    monkeypatch.setattr(api_mod, "_persistence_probe", lambda: (False, "store unavailable"))
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "degraded"
    assert data["ready"] is False
    assert data["persistence_ok"] is False


def test_readiness_returns_503_when_not_ready(client, monkeypatch):
    monkeypatch.setattr(api_mod, "_persistence_probe", lambda: (False, "store unavailable"))
    resp = client.get("/api/ready")
    assert resp.status_code == 503
    assert resp.json()["status"] == "degraded"


def test_liveness_stays_live_even_when_degraded(client, monkeypatch):
    monkeypatch.setattr(api_mod, "_persistence_probe", lambda: (False, "store unavailable"))
    resp = client.get("/api/live")
    assert resp.status_code == 200
    assert resp.json()["status"] == "live"


def test_draining_rejects_new_non_health_requests(client):
    api_mod._draining = True
    resp = client.get("/api/episodes")
    assert resp.status_code == 503
    assert resp.json()["status"] == "draining"


def test_drain_waits_for_inflight_to_finish():
    api_mod._inflight_requests = 1

    async def _release():
        await asyncio.sleep(0.05)
        api_mod._inflight_requests = 0

    async def _run():
        task = asyncio.create_task(_release())
        started = time.monotonic()
        await api_mod._drain_inflight_requests(timeout_s=1.0)
        await task
        return time.monotonic() - started

    elapsed = asyncio.run(_run())
    assert elapsed >= 0.04
    assert api_mod._inflight_requests == 0

