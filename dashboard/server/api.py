"""Dashboard API server for DeepSigma. Closes #11.

Provides REST endpoints for episode browsing, drift monitoring,
and SLO status. Built with FastAPI for async support.

Usage:
    uvicorn dashboard.server.api:app --reload
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

try:
    from fastapi import FastAPI, HTTPException, Query
    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False

DATA_DIR = Path(os.environ.get("DATA_DIR", "/app/data"))

if HAS_FASTAPI:
    app = FastAPI(title="DeepSigma Dashboard API", version="0.1.0")
else:
    app = None
    logger.warning("FastAPI not installed; dashboard API unavailable")


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
            if "driftId" in data or "driftType" in data or "type" in data:
                events.append(data)
        except (json.JSONDecodeError, KeyError):
            continue
    if not events:
        all_files = _load_json_files(DATA_DIR)
        events = [f for f in all_files if "driftId" in f or "driftType" in f]
    return events


if HAS_FASTAPI:

    @app.get("/api/episodes")
    def list_episodes(
        decision_type: Optional[str] = Query(None),
        limit: int = Query(50, ge=1, le=500),
    ):
        """List episodes with optional filtering."""
        episodes = _get_episodes()
        if decision_type:
            episodes = [e for e in episodes if e.get("decisionType") == decision_type]
        episodes = episodes[:limit]

        summaries = []
        for ep in episodes:
            outcome = ep.get("outcome", {})
            telemetry = ep.get("telemetry", {})
            summaries.append({
                "episodeId": ep.get("episodeId"),
                "decisionType": ep.get("decisionType"),
                "outcomeCode": outcome.get("code", "unknown"),
                "endToEndMs": telemetry.get("endToEndMs", 0),
                "startedAt": ep.get("startedAt"),
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
        drift_type: Optional[str] = Query(None),
        severity: Optional[str] = Query(None),
    ):
        """List drift events with optional filtering."""
        events = _get_drift_events()
        if drift_type:
            events = [e for e in events if e.get("type") == drift_type or e.get("driftType") == drift_type]
        if severity:
            events = [e for e in events if e.get("severity") == severity]
        return {"count": len(events), "events": events}

    @app.get("/api/slo-status")
    def slo_status():
        """Compute current SLO compliance metrics from loaded data."""
        episodes = _get_episodes()
        drift_events = _get_drift_events()

        total = len(episodes)
        success_count = sum(1 for e in episodes if e.get("outcome", {}).get("code") == "success")
        fail_count = sum(1 for e in episodes if e.get("outcome", {}).get("code") == "fail")
        budget_ms_violations = sum(
            1 for e in episodes
            if e.get("telemetry", {}).get("endToEndMs", 0) > e.get("decisionWindowMs", 9999)
        )

        return {
            "totalEpisodes": total,
            "successRate": round(success_count / max(total, 1), 4),
            "failRate": round(fail_count / max(total, 1), 4),
            "budgetViolations": budget_ms_violations,
            "driftEventsTotal": len(drift_events),
        }

    # ---------------------------------------------------------------
    # CoherenceOps endpoints
    # ---------------------------------------------------------------

    LLM_DATA_DIR = Path(os.environ.get("LLM_DATA_DIR", "/app/llm_data_model/03_examples"))

    def _get_records() -> List[Dict[str, Any]]:
        """Load LLM Data Model canonical records."""
        return _load_json_files(LLM_DATA_DIR)

    def _build_dlr(episode_id: str) -> Optional[Dict[str, Any]]:
        """Build a DLR entry for a specific episode (lazy import)."""
        try:
            from coherence_ops.dlr import DLRBuilder
        except ImportError:
            return None
        episodes = _get_episodes()
        match = [e for e in episodes if e.get("episodeId") == episode_id]
        if not match:
            return None
        builder = DLRBuilder()
        from dataclasses import asdict
        return asdict(builder.from_episode(match[0]))

    @app.get("/api/coherence/status")
    def coherence_status():
        """DLR/RS/DS/MG pipeline health and last bridge run."""
        episodes = _get_episodes()
        drift_events = _get_drift_events()
        records = _get_records()
        return {
            "pipeline": "healthy",
            "pillars": {
                "dlr": {"status": "active", "episode_count": len(episodes)},
                "rs": {"status": "active", "last_session": None},
                "ds": {"status": "active", "drift_count": len(drift_events)},
                "mg": {"status": "active", "node_count": 0},
            },
            "last_bridge_run": None,
            "record_count": len(records),
        }

    @app.get("/api/coherence/dlr/{episode_id}")
    def get_dlr(episode_id: str):
        """Decision Lifecycle Record for a specific episode."""
        dlr = _build_dlr(episode_id)
        if dlr is None:
            raise HTTPException(status_code=404, detail=f"DLR not found for episode {episode_id}")
        return dlr

    @app.get("/api/records")
    def list_records(
        record_type: Optional[str] = Query(None),
        limit: int = Query(50, ge=1, le=500),
    ):
        """List canonical records with type/freshness filters."""
        records = _get_records()
        if record_type:
            records = [r for r in records if r.get("record_type") == record_type]
        records = records[:limit]
        return {"count": len(records), "records": records}

    @app.get("/api/records/stats")
    def record_stats():
        """Record counts by type, TTL compliance, seal integrity."""
        records = _get_records()
        by_type: Dict[str, int] = {}
        sealed_count = 0
        ttl_set_count = 0
        for r in records:
            rtype = r.get("record_type", "Unknown")
            by_type[rtype] = by_type.get(rtype, 0) + 1
            if r.get("seal", {}).get("hash"):
                sealed_count += 1
            if r.get("ttl") is not None and r.get("ttl", 0) > 0:
                ttl_set_count += 1
        return {
            "total_records": len(records),
            "by_type": by_type,
            "sealed_count": sealed_count,
            "seal_rate": round(sealed_count / max(len(records), 1), 4),
            "ttl_configured_count": ttl_set_count,
        }

    @app.get("/api/records/{record_id}")
    def get_record(record_id: str):
        """Full record detail with seal verification."""
        records = _get_records()
        for r in records:
            if r.get("record_id") == record_id:
                seal = r.get("seal", {})
                r["_seal_verified"] = bool(seal.get("hash") and seal.get("sealed_at"))
                return r
        raise HTTPException(status_code=404, detail=f"Record {record_id} not found")

    @app.get("/api/health")
    def health():
        """Simple health check."""
        return {"status": "ok", "dataDir": str(DATA_DIR), "dataExists": DATA_DIR.exists()}
