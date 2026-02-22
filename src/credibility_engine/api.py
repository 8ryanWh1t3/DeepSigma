"""Credibility Engine — API Routes.

FastAPI router providing tenant-scoped credibility engine endpoints.
Backward-compatible alias routes at /api/credibility/* serve DEFAULT_TENANT_ID.

v0.9.0: Added /policy and /audit endpoints. Existing v0.8.0 endpoints unchanged.
Quota enforcement on packet generation/sealing.

Abstract institutional credibility architecture.
No real-world system modeled.
"""

from __future__ import annotations

import time
from typing import Any, Callable

from fastapi import APIRouter, HTTPException, Query, Request

from credibility_engine.constants import DEFAULT_TENANT_ID
from credibility_engine.engine import CredibilityEngine
from credibility_engine.packet import (
    generate_credibility_packet,
    seal_credibility_packet,
)
from credibility_engine.store import CredibilityStore
from governance.audit import audit_action, load_recent_audit
from governance.telemetry import check_quota, record_metric
from tenancy.policies import (
    load_policy,
    save_policy,
)
from tenancy.rbac import get_role, get_user, require_role
from tenancy.tenants import assert_tenant_exists, list_tenants

router = APIRouter(tags=["credibility"])

StoreFactory = Callable[[str], CredibilityStore]

# Stateless runtime default: construct store/engine per request.
_store_factory: StoreFactory = lambda tenant_id: CredibilityStore(tenant_id=tenant_id)


def _get_engine(tenant_id: str) -> CredibilityEngine:
    """Build a request-scoped engine for the given tenant."""
    assert_tenant_exists(tenant_id)
    store = _store_factory(tenant_id)
    engine = CredibilityEngine(store=store, tenant_id=tenant_id)
    if not engine.load_from_store():
        engine.initialize_default_state()
    return engine


def set_store_factory(factory: StoreFactory) -> None:
    """Override store construction (used by tests/deploy wiring)."""
    global _store_factory
    _store_factory = factory


def reset_engine(
    tenant_id: str | None = None,
    store: CredibilityStore | None = None,
) -> CredibilityEngine:
    """Reset persisted state for a tenant (for testing or re-initialization)."""
    tid = tenant_id or DEFAULT_TENANT_ID
    s = store or _store_factory(tid)
    engine = CredibilityEngine(store=s, tenant_id=tid)
    engine.initialize_default_state()
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
    """Generate a credibility packet for the given tenant.

    Enforces quota limits. Emits audit event.
    """
    engine = _get_engine(tenant_id)
    role = get_role(request)
    user = get_user(request)

    # Quota check
    policy = load_policy(tenant_id)
    if not check_quota(tenant_id, "packet_generate", policy):
        audit_action(
            tenant_id=tenant_id,
            actor_user=user,
            actor_role=role,
            action="PACKET_GENERATE",
            target_type="PACKET",
            target_id="QUOTA_EXCEEDED",
            outcome="DENIED",
            metadata={"reason": "quota_exceeded"},
        )
        raise HTTPException(
            status_code=429,
            detail="Packet generation quota exceeded. Try again later.",
        )

    start = time.monotonic()
    engine.recalculate_index()
    packet = generate_credibility_packet(engine, role=role, user=user)
    elapsed_ms = round((time.monotonic() - start) * 1000, 1)

    record_metric(tenant_id, "packet_generate_latency_ms", elapsed_ms, actor=user)
    return packet


@router.post("/api/{tenant_id}/credibility/packet/seal")
def tenant_seal_packet(tenant_id: str, request: Request) -> dict[str, Any]:
    """Seal the latest credibility packet. Requires coherence_steward role.

    Enforces quota limits. Emits audit events including denied attempts.
    """
    user = get_user(request)
    role_header = get_role(request)

    # Check role — audit denied attempts
    if role_header not in {"coherence_steward"}:
        audit_action(
            tenant_id=tenant_id,
            actor_user=user,
            actor_role=role_header,
            action="PACKET_SEAL",
            target_type="PACKET",
            target_id="DENIED",
            outcome="DENIED",
            metadata={"reason": f"role '{role_header}' not authorized"},
        )
        raise HTTPException(
            status_code=403,
            detail=(
                f"Role '{role_header}' is not authorized for this action. "
                f"Required: coherence_steward"
            ),
        )

    # Quota check
    policy = load_policy(tenant_id)
    if not check_quota(tenant_id, "packet_seal", policy):
        audit_action(
            tenant_id=tenant_id,
            actor_user=user,
            actor_role=role_header,
            action="PACKET_SEAL",
            target_type="PACKET",
            target_id="QUOTA_EXCEEDED",
            outcome="DENIED",
            metadata={"reason": "quota_exceeded"},
        )
        raise HTTPException(
            status_code=429,
            detail="Packet seal quota exceeded. Try again later.",
        )

    engine = _get_engine(tenant_id)
    start = time.monotonic()
    engine.recalculate_index()
    result = seal_credibility_packet(engine, role=role_header, user=user)
    elapsed_ms = round((time.monotonic() - start) * 1000, 1)

    record_metric(tenant_id, "packet_seal_latency_ms", elapsed_ms, actor=user)
    return result


# -- Policy endpoints (v0.9.0) ------------------------------------------------

@router.get("/api/{tenant_id}/policy")
def tenant_get_policy(tenant_id: str) -> dict[str, Any]:
    """Return the current policy for the given tenant."""
    assert_tenant_exists(tenant_id)
    return load_policy(tenant_id)


@router.post("/api/{tenant_id}/policy")
async def tenant_update_policy(
    tenant_id: str,
    request: Request,
) -> dict[str, Any]:
    """Update the policy for the given tenant.

    Requires truth_owner or coherence_steward role.
    Emits audit event for POLICY_UPDATE.
    """
    assert_tenant_exists(tenant_id)
    role = require_role(request, {"truth_owner", "coherence_steward"})
    user = get_user(request)

    body = await request.json()

    current_policy = load_policy(tenant_id)

    # Validate: only allow known top-level keys
    valid_keys = {
        "ttl_policy", "quorum_policy", "correlation_policy",
        "silence_policy", "slo_policy", "quota_policy",
    }
    for key in body:
        if key in valid_keys:
            current_policy[key] = body[key]

    saved = save_policy(tenant_id, current_policy, actor=user)

    audit_action(
        tenant_id=tenant_id,
        actor_user=user,
        actor_role=role,
        action="POLICY_UPDATE",
        target_type="POLICY",
        target_id=tenant_id,
        outcome="SUCCESS",
        metadata={"updated_keys": [k for k in body if k in valid_keys]},
    )

    return saved


# -- Audit endpoints (v0.9.0, read-only) --------------------------------------

@router.get("/api/{tenant_id}/audit/recent")
def tenant_audit_recent(
    tenant_id: str,
    limit: int = Query(default=50, le=200),
) -> dict[str, Any]:
    """Return the most recent audit events for the given tenant."""
    assert_tenant_exists(tenant_id)
    events = load_recent_audit(tenant_id, limit=limit)
    return {
        "tenant_id": tenant_id,
        "count": len(events),
        "events": events,
    }


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


# -- Evidence tiering ---------------------------------------------------------

@router.get("/api/{tenant_id}/credibility/tiers")
def tenant_tier_summary(tenant_id: str) -> dict[str, Any]:
    """Return evidence tier summary for the given tenant."""
    engine = _get_engine(tenant_id)
    if engine.tier_manager is None:
        engine.enable_tiering()
    return engine.tier_manager.tier_summary()


@router.post("/api/{tenant_id}/credibility/tiers/sweep")
def tenant_tier_sweep(tenant_id: str) -> dict[str, Any]:
    """Trigger a tier demotion sweep for the given tenant."""
    engine = _get_engine(tenant_id)
    if engine.tier_manager is None:
        engine.enable_tiering()
    return engine.run_tier_sweep()
