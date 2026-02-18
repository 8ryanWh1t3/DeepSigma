"""Drift Detection API router.

FastAPI router providing standalone drift detection endpoints,
decoupled from the Exhaust Inbox workflow.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

try:
    from fastapi import APIRouter, Query
    from pydantic import BaseModel, Field

    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False

if HAS_FASTAPI:
    from .exhaust_api import DRIFT_FILE, _append_jsonl, _ensure_dirs, _read_jsonl

    router = APIRouter(tags=["drift"])

    class DetectRequest(BaseModel):
        episode: Dict[str, Any] = Field(..., description="Episode dict to analyze")

    class DetectResponse(BaseModel):
        episode_id: str
        signals: List[Dict[str, Any]]
        signal_count: int

    class IngestRequest(BaseModel):
        signals: List[Dict[str, Any]] = Field(
            ..., description="External drift signals"
        )

    @router.post("/drift/detect", response_model=DetectResponse)
    def detect_drift_endpoint(body: DetectRequest):
        """Run drift detection on an episode and return signals."""
        from engine.drift_detector import DriftDetector

        detector = DriftDetector()
        signals = detector.detect_from_episode(body.episode)
        return DetectResponse(
            episode_id=body.episode.get("episode_id", ""),
            signals=[s.model_dump() for s in signals],
            signal_count=len(signals),
        )

    @router.get("/drift/signals")
    def query_drift_signals(
        severity: Optional[str] = Query(None),
        drift_type: Optional[str] = Query(None),
        episode_id: Optional[str] = Query(None),
        limit: int = Query(100, ge=1, le=1000),
    ):
        """Query stored drift signals with filtering."""
        _ensure_dirs()
        signals = _read_jsonl(DRIFT_FILE)
        if severity:
            signals = [s for s in signals if s.get("severity") == severity]
        if drift_type:
            signals = [s for s in signals if s.get("drift_type") == drift_type]
        if episode_id:
            signals = [s for s in signals if s.get("episode_id") == episode_id]
        limited = signals[:limit]
        return {"count": len(limited), "signals": limited}

    @router.post("/drift/ingest")
    def ingest_external_signals(body: IngestRequest):
        """Accept external drift signals and store them."""
        _ensure_dirs()
        for signal in body.signals:
            _append_jsonl(DRIFT_FILE, signal)
        return {"ingested": len(body.signals)}
