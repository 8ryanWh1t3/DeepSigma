"""Tests for dashboard/server/exhaust_api.py — FastAPI endpoints.

Run from repo root:
    pytest tests/test_exhaust_api.py -v

Uses FastAPI TestClient with monkeypatched DATA_DIR (tmp_path) so no
real filesystem state is mutated.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest

# Make repo root importable
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Skip entire module if FastAPI / httpx not installed
try:
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False

pytestmark = pytest.mark.skipif(not HAS_FASTAPI, reason="fastapi not installed")

import dashboard.server.exhaust_api as api_module  # noqa: E402


# ── Fixtures ──────────────────────────────────────────────────────

@pytest.fixture
def client(tmp_path, monkeypatch):
    """TestClient with all data paths redirected to tmp_path."""
    monkeypatch.setattr(api_module, "DATA_DIR", tmp_path)
    monkeypatch.setattr(api_module, "EVENTS_FILE", tmp_path / "events.jsonl")
    monkeypatch.setattr(api_module, "EPISODES_DIR", tmp_path / "episodes")
    monkeypatch.setattr(api_module, "REFINED_DIR", tmp_path / "refined")
    monkeypatch.setattr(api_module, "MG_DIR", tmp_path / "mg")
    monkeypatch.setattr(api_module, "DRIFT_DIR", tmp_path / "drift")
    monkeypatch.setattr(api_module, "MG_FILE", tmp_path / "mg" / "memory_graph.jsonl")
    monkeypatch.setattr(api_module, "DRIFT_FILE", tmp_path / "drift" / "drift.jsonl")

    app = FastAPI()
    app.include_router(api_module.router)
    return TestClient(app)


def _minimal_event(episode_id: str, seq: int = 0) -> dict:
    return {
        "event_id": f"ev-test-{seq:02d}",
        "episode_id": episode_id,
        "event_type": "metric",
        "timestamp": f"2026-01-01T00:00:0{seq}Z",
        "source": "manual",
        "payload": {"name": "latency_ms", "value": 240, "unit": "ms"},
    }


# ── Health ────────────────────────────────────────────────────────

def test_health_empty(client):
    """Fresh data dir returns status ok and all counts at zero."""
    resp = client.get("/api/exhaust/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["events_count"] == 0
    assert body["episodes_count"] == 0
    assert body["refined_count"] == 0
    assert body["drift_count"] == 0


# ── Event ingestion ───────────────────────────────────────────────

def test_ingest_event(client):
    """POST /events accepts a valid EpisodeEvent and returns accepted."""
    event = _minimal_event("ep-ingest-01")
    resp = client.post("/api/exhaust/events", json=event)
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "accepted"
    assert body["event_id"] == "ev-test-00"
    assert body["episode_id"] == "ep-ingest-01"


def test_ingest_event_increments_health(client):
    """After ingest, health shows events_count = 1."""
    client.post("/api/exhaust/events", json=_minimal_event("ep-h-01"))
    resp = client.get("/api/exhaust/health")
    assert resp.json()["events_count"] == 1


# ── Episode assembly ──────────────────────────────────────────────

def test_assemble_groups_events(client):
    """Two events with same episode_id assemble into one episode."""
    ep_id = "ep-asm-01"
    client.post("/api/exhaust/events", json=_minimal_event(ep_id, 0))
    client.post("/api/exhaust/events", json=_minimal_event(ep_id, 1))

    resp = client.post("/api/exhaust/episodes/assemble")
    assert resp.status_code == 200
    body = resp.json()
    assert body["assembled"] == 1
    assert ep_id in body["episode_ids"]


def test_assemble_idempotent(client):
    """Re-assembling the same episode yields assembled=0 (already done)."""
    ep_id = "ep-idem-01"
    client.post("/api/exhaust/events", json=_minimal_event(ep_id))
    client.post("/api/exhaust/episodes/assemble")

    resp = client.post("/api/exhaust/episodes/assemble")
    assert resp.json()["assembled"] == 0


# ── Episode listing ───────────────────────────────────────────────

def test_list_episodes_empty(client):
    """GET /episodes on a fresh dir returns total=0 and empty list."""
    resp = client.get("/api/exhaust/episodes")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 0
    assert body["episodes"] == []


def test_list_episodes_after_assemble(client):
    """After assembly, listing returns the new episode."""
    ep_id = "ep-list-01"
    client.post("/api/exhaust/events", json=_minimal_event(ep_id))
    client.post("/api/exhaust/episodes/assemble")

    resp = client.get("/api/exhaust/episodes")
    body = resp.json()
    assert body["total"] == 1
    assert body["episodes"][0]["episode_id"] == ep_id


# ── Refinement ────────────────────────────────────────────────────

def test_refine_episode(client, tmp_path):
    """Refine an assembled episode — returns coherence_score in [0, 100]."""
    ep_id = "ep-refine-01"
    episodes_dir = tmp_path / "episodes"
    episodes_dir.mkdir(parents=True, exist_ok=True)

    episode = {
        "episode_id": ep_id,
        "events": [
            {
                "event_id": "ev-r-01",
                "episode_id": ep_id,
                "event_type": "metric",
                "timestamp": "2026-01-01T00:00:00Z",
                "source": "manual",
                "user_hash": "u_test",
                "session_id": "sess-r",
                "project": "test",
                "team": "test",
                "payload": {"name": "latency_ms", "value": 240, "unit": "ms"},
            }
        ],
        "source": "manual",
        "user_hash": "u_test",
        "session_id": "sess-r",
        "project": "test",
        "team": "test",
        "started_at": "2026-01-01T00:00:00Z",
        "ended_at": "2026-01-01T00:00:01Z",
    }
    (episodes_dir / f"{ep_id}.json").write_text(json.dumps(episode))

    resp = client.post(f"/api/exhaust/episodes/{ep_id}/refine")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "refined"
    assert body["episode_id"] == ep_id
    assert 0.0 <= body["coherence_score"] <= 100.0
    assert body["grade"] in ("A", "B", "C", "D")


def test_refine_episode_missing(client):
    """Refining a non-existent episode returns 404."""
    resp = client.post("/api/exhaust/episodes/no-such-ep/refine")
    assert resp.status_code == 404


# ── Item action ───────────────────────────────────────────────────

def test_item_action_accept(client, tmp_path):
    """Accepting a truth item sets its status to 'accepted'."""
    ep_id = "ep-item-01"
    item_id = "truth-item-001"

    refined_dir = tmp_path / "refined"
    refined_dir.mkdir(parents=True, exist_ok=True)

    refined = {
        "episode_id": ep_id,
        "truth": [
            {
                "item_id": item_id,
                "claim": "latency = 240ms",
                "confidence": 0.9,
                "status": "pending",
            }
        ],
        "reasoning": [],
        "memory": [],
        "drift_signals": [],
        "coherence_score": 75.0,
    }
    (refined_dir / f"{ep_id}.json").write_text(json.dumps(refined))

    resp = client.post(
        f"/api/exhaust/episodes/{ep_id}/item",
        json={"item_id": item_id, "bucket": "truth", "action": "accept"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "accept"
    assert body["item_id"] == item_id

    # Verify persisted status
    saved = json.loads((refined_dir / f"{ep_id}.json").read_text())
    assert saved["truth"][0]["status"] == "accepted"


def test_item_action_missing_item(client, tmp_path):
    """Accepting a non-existent item_id returns 404."""
    ep_id = "ep-item-02"
    refined_dir = tmp_path / "refined"
    refined_dir.mkdir(parents=True, exist_ok=True)

    refined = {"episode_id": ep_id, "truth": [], "reasoning": [], "memory": [],
               "drift_signals": [], "coherence_score": 50.0}
    (refined_dir / f"{ep_id}.json").write_text(json.dumps(refined))

    resp = client.post(
        f"/api/exhaust/episodes/{ep_id}/item",
        json={"item_id": "ghost-item", "bucket": "truth", "action": "accept"},
    )
    assert resp.status_code == 404


# ── Commit ────────────────────────────────────────────────────────

def test_commit_episode(client, tmp_path):
    """Commit writes truth to memory graph and marks episode committed."""
    ep_id = "ep-commit-01"

    refined_dir = tmp_path / "refined"
    episodes_dir = tmp_path / "episodes"
    refined_dir.mkdir(parents=True, exist_ok=True)
    episodes_dir.mkdir(parents=True, exist_ok=True)

    refined = {
        "episode_id": ep_id,
        "truth": [
            {"item_id": "t-001", "claim": "x = 1", "confidence": 0.9, "status": "pending"}
        ],
        "reasoning": [],
        "memory": [],
        "drift_signals": [],
        "coherence_score": 80.0,
        "committed": False,
    }
    episode = {"episode_id": ep_id, "source": "manual", "events": []}
    (refined_dir / f"{ep_id}.json").write_text(json.dumps(refined))
    (episodes_dir / f"{ep_id}.json").write_text(json.dumps(episode))

    resp = client.post(f"/api/exhaust/episodes/{ep_id}/commit")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "committed"
    assert body["episode_id"] == ep_id

    # Refined file marked committed
    saved = json.loads((refined_dir / f"{ep_id}.json").read_text())
    assert saved["committed"] is True


def test_commit_episode_missing(client):
    """Committing a non-existent episode returns 404."""
    resp = client.post("/api/exhaust/episodes/no-refined/commit")
    assert resp.status_code == 404
