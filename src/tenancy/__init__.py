"""Tenancy — Multi-tenant support for Credibility Engine.

Tenant registry, path management, and header-based RBAC.

Abstract institutional credibility architecture.
No real-world system modeled.
"""

from tenancy.paths import ensure_tenant_dirs, tenant_file, tenant_root
from tenancy.policies import evaluate_policy, load_policy, save_policy


def ensure_registry(*args, **kwargs):
    from tenancy.tenants import ensure_registry as _ensure_registry

    return _ensure_registry(*args, **kwargs)


def list_tenants(*args, **kwargs):
    from tenancy.tenants import list_tenants as _list_tenants

    return _list_tenants(*args, **kwargs)


def get_tenant(*args, **kwargs):
    from tenancy.tenants import get_tenant as _get_tenant

    return _get_tenant(*args, **kwargs)


def assert_tenant_exists(*args, **kwargs):
    from tenancy.tenants import assert_tenant_exists as _assert_tenant_exists

    return _assert_tenant_exists(*args, **kwargs)


def get_role(*args, **kwargs):
    from tenancy.rbac import get_role as _get_role

    return _get_role(*args, **kwargs)


def require_role(*args, **kwargs):
    from tenancy.rbac import require_role as _require_role

    return _require_role(*args, **kwargs)


__all__ = [
    "ensure_registry",
    "list_tenants",
    "get_tenant",
    "assert_tenant_exists",
    "tenant_root",
    "ensure_tenant_dirs",
    "tenant_file",
    "get_role",
    "require_role",
    "load_policy",
    "save_policy",
    "evaluate_policy",
]
