"""Tenancy — Multi-tenant support for Credibility Engine.

Tenant registry, path management, and header-based RBAC.

Abstract institutional credibility architecture.
No real-world system modeled.
"""

from tenancy.paths import ensure_tenant_dirs, tenant_file, tenant_root
from tenancy.policies import evaluate_policy, load_policy, save_policy
from tenancy.rbac import get_role, require_role
from tenancy.tenants import (
    assert_tenant_exists,
    ensure_registry,
    get_tenant,
    list_tenants,
)

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
