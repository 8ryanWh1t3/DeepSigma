"""Tenancy — Path Management.

Resolves tenant-scoped data directories and file paths.

Abstract institutional credibility architecture.
No real-world system modeled.
"""

from __future__ import annotations

from pathlib import Path

_BASE_DATA_DIR = Path(__file__).parent.parent / "data" / "credibility"


def tenant_root(tenant_id: str) -> Path:
    """Return the data directory for a given tenant."""
    return _BASE_DATA_DIR / tenant_id


def ensure_tenant_dirs(tenant_id: str) -> Path:
    """Create the tenant data directory if it doesn't exist. Returns the path."""
    root = tenant_root(tenant_id)
    root.mkdir(parents=True, exist_ok=True)
    return root


def tenant_file(tenant_id: str, name: str) -> Path:
    """Return the full path for a named file within a tenant's data directory."""
    return tenant_root(tenant_id) / name
