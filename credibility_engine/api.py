"""Credibility Engine — API Routes.

FastAPI router providing tenant-scoped credibility engine endpoints.
Backward-compatible alias routes at /api/credibility/* serve DEFAULT_TENANT_ID.

Abstract institutional credibility architecture.
No real-world system modeled.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request

from credibility_engine.constants import DEFAULT_TENANT_ID
from credibility_engine.engine import CredibilityEngine
from credibility_engine.packet import (
    generate_credibility_packet,
    seal_credibility_packet,
)
from credibility_engine.store import CredibilityStore
from tenancy.rbac import get_role, get_user, require_role
from tenancy.tenants import assert_tenant_exists, list_tenants

router = APIRouter(tags=["credibility"])

# Engine cache — one engine per tenant, lazily initialized
_engines: dict[str, CredibilityEngine] = {}


def _get_engine(tenant_id: str) -> CredibilityEngine:
    """Get or create an engine instance for the given tenant."""
    if tenant_id not in _engines:
        assert_tenant_exists(tenant_id)
        store = CredibilityStore(tenant_id=tenant_id)
        engine = CredibilityEngine(store=store, tenant_id=tenant_id)
        if not engine.load_from_store():
            engine.initialize_default_state()
        _engines[tenant_id] = engine
    return _engines[tenant_id]


def reset_engine(
    tenant_id: str | None = None,
    store: CredibilityStore | None = None,
) -> CredibilityEngine:
    """Reset the engine for a tenant (for testing or re-initialization)."""
    tid = tenant_id or DEFAULT_TENANT_ID
    s = store or CredibilityStore(tenant_id=tid)
    engine = CredibilityEngine(store=s, tenant_id=tid)
    engine.initialize_default_state()
    _engines[tid] = engine
    return engine


# -- Tenant registry -----------------------------------------------------------

@router.get("/api/tenants")
def api_list_tenants() -> list[dict[str, Any]]:
    """Return all registered tenants."""
    return list_tenants()


# -- Tenant-scoped canonical routes -------------------------------------------

@router.get("/api/{tenant_id}/credibility/snapshot")
def tenant_snapshot(tenant_id: str) -> dict[str, Any]:
    """Return current credibility snapshot for the given tenant."""
    engine = _get_engine(tenant_id)
    engine.recalculate_index()
    return engine.snapshot_credibility()


@router.get("/api/{tenant_id}/credibility/claims/tier0")
def tenant_claims_tier0(tenant_id: str) -> dict[str, Any]:
    """Return current Tier 0 claim state for the given tenant."""
    return _get_engine(tenant_id).snapshot_claims()


@router.get("/api/{tenant_id}/credibility/drift/24h")
def tenant_drift_24h(tenant_id: str) -> dict[str, Any]:
    """Return drift events for the last 24 hours for the given tenant."""
    return _get_engine(tenant_id).snapshot_drift()


@router.get("/api/{tenant_id}/credibility/correlation")
def tenant_correlation(tenant_id: str) -> dict[str, Any]:
    """Return correlation cluster map for the given tenant."""
    return _get_engine(tenant_id).snapshot_correlation()


@router.get("/api/{tenant_id}/credibility/sync")
def tenant_sync(tenant_id: str) -> dict[str, Any]:
    """Return sync plane integrity for the given tenant."""
    return _get_engine(tenant_id).snapshot_sync()


@router.post("/api/{tenant_id}/credibility/packet/generate")
def tenant_generate_packet(tenant_id: str, request: Request) -> dict[str, Any]:
    """Generate a credibility packet for the given tenant."""
    engine = _get_engine(tenant_id)
    engine.recalculate_index()
    role = get_role(request)
    user = get_user(request)
    return generate_credibility_packet(engine, role=role, user=user)


@router.post("/api/{tenant_id}/credibility/packet/seal")
def tenant_seal_packet(tenant_id: str, request: Request) -> dict[str, Any]:
    """Seal the latest credibility packet. Requires coherence_steward role."""
    role = require_role(request, {"coherence_steward"})
    user = get_user(request)
    engine = _get_engine(tenant_id)
    engine.recalculate_index()
    return seal_credibility_packet(engine, role=role, user=user)


# -- Backward-compatible alias routes (default tenant) -------------------------

@router.get("/api/credibility/snapshot")
def get_snapshot() -> dict[str, Any]:
    """Alias: credibility snapshot for default tenant."""
    engine = _get_engine(DEFAULT_TENANT_ID)
    engine.recalculate_index()
    return engine.snapshot_credibility()


@router.get("/api/credibility/claims/tier0")
def get_claims_tier0() -> dict[str, Any]:
    """Alias: Tier 0 claims for default tenant."""
    return _get_engine(DEFAULT_TENANT_ID).snapshot_claims()


@router.get("/api/credibility/drift/24h")
def get_drift_24h() -> dict[str, Any]:
    """Alias: drift events for default tenant."""
    return _get_engine(DEFAULT_TENANT_ID).snapshot_drift()


@router.get("/api/credibility/correlation")
def get_correlation() -> dict[str, Any]:
    """Alias: correlation clusters for default tenant."""
    return _get_engine(DEFAULT_TENANT_ID).snapshot_correlation()


@router.get("/api/credibility/sync")
def get_sync() -> dict[str, Any]:
    """Alias: sync plane integrity for default tenant."""
    return _get_engine(DEFAULT_TENANT_ID).snapshot_sync()


@router.get("/api/credibility/packet")
def get_packet() -> dict[str, Any]:
    """Alias: generate packet for default tenant."""
    engine = _get_engine(DEFAULT_TENANT_ID)
    engine.recalculate_index()
    return generate_credibility_packet(engine)
