"""Standalone Exhaust Inbox service entrypoint.

Runs the Exhaust Inbox API as an independent FastAPI service,
decoupled from the main dashboard server.

Usage:
    uvicorn dashboard.server.exhaust_main:app --host 0.0.0.0 --port 8001

Environment variables:
    EXHAUST_USE_LLM     Set to "1" to enable Anthropic-backed extraction (default: "0")
    ANTHROPIC_API_KEY   Required when EXHAUST_USE_LLM=1
"""
from __future__ import annotations

try:
    from fastapi import FastAPI
    from dashboard.server.exhaust_api import router as exhaust_router

    app = FastAPI(
        title="Σ OVERWATCH Exhaust Inbox",
        version="0.3.0",
        description="Standalone ingestion service for AI interaction exhaust",
    )

    app.include_router(exhaust_router, prefix="/api/exhaust")

    try:
        from dashboard.server.drift_api import router as drift_router
        app.include_router(drift_router, prefix="/api")
    except ImportError:
        pass

    @app.get("/healthz", tags=["health"])
    def health() -> dict:
        return {"status": "ok", "service": "exhaust"}

except ImportError as exc:  # pragma: no cover
    raise RuntimeError(
        "FastAPI is required for exhaust_main. "
        "Install with: pip install 'fastapi>=0.104.0' 'uvicorn[standard]>=0.24.0'"
    ) from exc
