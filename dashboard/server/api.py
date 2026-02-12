"""Dashboard API server — serves real episode and drift data.

Closes #11.

Lightweight FastAPI backend that reads episode/drift JSON files from a
configurable data directory and serves them via REST endpoints.

Usage:
    # Start with real data directory
        uvicorn dashboard.server.api:app --reload --port 8080

            # Or set data directory via env
                DEEPSIGMA_DATA_DIR=./episodes_out uvicorn dashboard.server.api:app

                    # Mock mode fallback
                        DEEPSIGMA_MOCK=1 uvicorn dashboard.server.api:app
                        """
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
      from fastapi import FastAPI, HTTPException, Query
      from fastapi.middleware.cors import CORSMiddleware
      HAS_FASTAPI = True
except ImportError:
      HAS_FASTAPI = False

if not HAS_FASTAPI:
      raise ImportError("FastAPI not installed. Run: pip install fastapi uvicorn")

app = FastAPI(title="DeepSigma Dashboard API", version="0.2.0")

app.add_middleware(
      CORSMiddleware,
      allow_origins=["*"],
      allow_methods=["*"],
      allow_headers=["*"],
)

DATA_DIR = Path(os.environ.get("DEEPSIGMA_DATA_DIR", "episodes_out"))
MOCK_MODE = os.environ.get("DEEPSIGMA_MOCK", "").lower() in ("1", "true", "yes")


def _load_json_files(directory: Path, suffix: str = ".json") -> List[Dict[str, Any]]:
      """Load all JSON files from a directory."""
      results = []
      if not directory.exists():
                return results
            for f in sorted(directory.glob(f"*{suffix}")):
                      try:
                                    data = json.loads(f.read_text(encoding="utf-8"))
                                    results.append(data)
except (json.JSONDecodeError, OSError):
            continue
    return results


def _get_episodes() -> List[Dict[str, Any]]:
      """Load episode files (exclude drift files)."""
    all_files = _load_json_files(DATA_DIR)
    return [f for f in all_files if "episodeId" in f and "driftId" not in f]


def _get_drift_events() -> List[Dict[str, Any]]:
      """Load drift event files."""
    events = []
    for f in sorted(DATA_DIR.glob("*.drift.json")) if DATA_DIR.exists() else []:
              try:
                            data = json.loads(f.read_text(encoding="utf-8"))
                            events.append(data)
except (json.JSONDecodeError, OSError):
            continue
    if not events:
              all_files = _load_json_files(DATA_DIR)
              events = [f for f in all_files if "driftId" in f or "driftType" in f]
          return events


@app.get("/api/health")
def health():
      return {"status": "ok", "dataDir": str(DATA_DIR), "mockMode": MOCK_MODE}


@app.get("/api/episodes")
def list_episodes(
      limit: int = Query(50, ge=1, le=500),
      decision_type: Optional[str] = Query(None),
):
      """List episodes with optional filtering."""
    episodes = _get_episodes()
    if decision_type:
              episodes = [e for e in episodes if e.get("decisionType") == decision_type]
          episodes = episodes[:limit]

    summaries = []
    for ep in episodes:
              summaries.append({
                            "episodeId": ep.get("episodeId"),
                            "decisionType": ep.get("decisionType"),
                            "startedAt": ep.get("startedAt"),
                            "endedAt": ep.get("endedAt"),
                            "outcomeCode": ep.get("outcome", {}).get("code"),
                            "endToEndMs": ep.get("telemetry", {}).get("endToEndMs"),
                            "degradeStep": ep.get("degrade", {}).get("step"),
                            "sealHash": ep.get("seal", {}).get("sealHash", "")[:12],
              })
          return {"count": len(summaries), "episodes": summaries}


@app.get("/api/episodes/{episode_id}")
def get_episode(episode_id: str):
      """Get full episode detail by ID."""
    episodes = _get_episodes()
    for ep in episodes:
              if ep.get("episodeId") == episode_id:
                            return ep
                    raise HTTPException(status_code=404, detail=f"Episode {episode_id} not found")


@app.get("/api/drift")
def list_drift(
      limit: int = Query(50, ge=1, le=500),
      drift_type: Optional[str] = Query(None, alias="type"),
      severity: Optional[str] = Query(None),
):
      """List drift events with optional filtering."""
    events = _get_drift_events()
    if drift_type:
              events = [e for e in events if e.get("type") == drift_type or e.get("driftType") == drift_type]
    if severity:
              events = [e for e in events if e.get("severity") == severity]
    return {"count": len(events[:limit]), "driftEvents": events[:limit]}


@app.get("/api/slo-status")
def slo_status():
      """Compute current SLO compliance metrics from loaded data."""
    episodes = _get_episodes()
    drift_events = _get_drift_events()

    total = len(episodes)
    if total == 0:
              return {"totalEpisodes": 0, "message": "No episodes loaded"}

    success_count = sum(1 for e in episodes if e.get("outcome", {}).get("code") == "success")
    fail_count = sum(1 for e in episodes if e.get("outcome", {}).get("code") == "fail")
    fallback_count = sum(1 for e in episodes if e.get("degrade", {}).get("step") not in ("none", None))

    avg_latency = sum(e.get("telemetry", {}).get("endToEndMs", 0) for e in episodes) / total

    return {
              "totalEpisodes": total,
              "successRate": round(success_count / total, 3),
              "failRate": round(fail_count / total, 3),
              "fallbackRate": round(fallback_count / total, 3),
              "avgLatencyMs": round(avg_latency, 1),
              "driftEventsTotal": len(drift_events),
              "driftBySeverity": {
                            "red": sum(1 for d in drift_events if d.get("severity") == "red"),
                            "yellow": sum(1 for d in drift_events if d.get("severity") == "yellow"),
                            "green": sum(1 for d in drift_events if d.get("severity") == "green"),
              },
    }
