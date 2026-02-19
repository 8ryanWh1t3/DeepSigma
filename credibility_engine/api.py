"""Credibility Engine — API Routes.

FastAPI router providing credibility engine endpoints.
Integrates into the existing dashboard API server.

Abstract institutional credibility architecture.
No real-world system modeled.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from credibility_engine.engine import CredibilityEngine
from credibility_engine.packet import generate_credibility_packet
from credibility_engine.store import CredibilityStore

router = APIRouter(prefix="/api/credibility", tags=["credibility"])

# Singleton engine instance — initialized on first request
_engine: CredibilityEngine | None = None
_store: CredibilityStore | None = None


def _get_engine() -> CredibilityEngine:
    """Lazy-initialize the engine singleton."""
    global _engine, _store
    if _engine is None:
        _store = CredibilityStore()
        _engine = CredibilityEngine(store=_store)
        if not _engine.load_from_store():
            _engine.initialize_default_state()
    return _engine


def reset_engine(store: CredibilityStore | None = None) -> CredibilityEngine:
    """Reset the engine (for testing or re-initialization)."""
    global _engine, _store
    _store = store or CredibilityStore()
    _engine = CredibilityEngine(store=_store)
    _engine.initialize_default_state()
    return _engine


# -- Endpoints -----------------------------------------------------------------

@router.get("/snapshot")
def get_snapshot() -> dict[str, Any]:
    """Return current credibility snapshot for the dashboard."""
    engine = _get_engine()
    engine.recalculate_index()
    return engine.snapshot_credibility()


@router.get("/claims/tier0")
def get_claims_tier0() -> dict[str, Any]:
    """Return current Tier 0 claim state."""
    engine = _get_engine()
    return engine.snapshot_claims()


@router.get("/drift/24h")
def get_drift_24h() -> dict[str, Any]:
    """Return drift events for the last 24 hours."""
    engine = _get_engine()
    return engine.snapshot_drift()


@router.get("/correlation")
def get_correlation() -> dict[str, Any]:
    """Return correlation cluster map."""
    engine = _get_engine()
    return engine.snapshot_correlation()


@router.get("/sync")
def get_sync() -> dict[str, Any]:
    """Return sync plane integrity."""
    engine = _get_engine()
    return engine.snapshot_sync()


@router.get("/packet")
def get_packet() -> dict[str, Any]:
    """Generate and return a credibility packet."""
    engine = _get_engine()
    engine.recalculate_index()
    return generate_credibility_packet(engine)
