"""Tenancy — Tenant Registry.

Manages tenant registration and lookup via a JSON file.

Abstract institutional credibility architecture.
No real-world system modeled.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import HTTPException

_REGISTRY_PATH = Path(__file__).parent.parent / "data" / "tenants.json"

_DEFAULT_TENANTS = [
    {
        "tenant_id": "tenant-alpha",
        "display_name": "Tenant Alpha",
        "status": "ACTIVE",
        "profile": "Stable baseline — low drift, correlation OK",
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    },
    {
        "tenant_id": "tenant-bravo",
        "display_name": "Tenant Bravo",
        "status": "ACTIVE",
        "profile": "Entropy — elevated drift, quorum margin warning",
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    },
    {
        "tenant_id": "tenant-charlie",
        "display_name": "Tenant Charlie",
        "status": "ACTIVE",
        "profile": "Correlation pressure — cluster CRITICAL, claim UNKNOWN",
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    },
]


def ensure_registry() -> list[dict[str, Any]]:
    """Ensure the tenant registry file exists. Create with defaults if missing."""
    _REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not _REGISTRY_PATH.exists():
        with open(_REGISTRY_PATH, "w", encoding="utf-8") as f:
            json.dump(_DEFAULT_TENANTS, f, indent=2)
            f.write("\n")
    return _load_registry()


def list_tenants() -> list[dict[str, Any]]:
    """Return all registered tenants."""
    return ensure_registry()


def get_tenant(tenant_id: str) -> dict[str, Any] | None:
    """Look up a single tenant by ID."""
    for t in ensure_registry():
        if t["tenant_id"] == tenant_id:
            return t
    return None


def assert_tenant_exists(tenant_id: str) -> dict[str, Any]:
    """Raise HTTP 404 if tenant does not exist. Returns tenant dict."""
    tenant = get_tenant(tenant_id)
    if tenant is None:
        raise HTTPException(status_code=404, detail=f"Tenant not found: {tenant_id}")
    return tenant


# -- Internal ------------------------------------------------------------------

def _load_registry() -> list[dict[str, Any]]:
    """Load the registry file."""
    with open(_REGISTRY_PATH, encoding="utf-8") as f:
        return json.load(f)
