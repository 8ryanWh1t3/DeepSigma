"""Tenancy — Header-Based RBAC.

Minimal role-based access control via X-Role and X-User headers.
Intended for demo/development use, not production security.

Abstract institutional credibility architecture.
No real-world system modeled.
"""

from __future__ import annotations

from fastapi import HTTPException, Request

VALID_ROLES = {"truth_owner", "coherence_steward", "dri", "exec"}
DEFAULT_ROLE = "exec"


def get_role(request: Request) -> str:
    """Extract the role from X-Role header. Defaults to 'exec'."""
    role = request.headers.get("X-Role", DEFAULT_ROLE).lower()
    if role not in VALID_ROLES:
        return DEFAULT_ROLE
    return role


def get_user(request: Request) -> str:
    """Extract the user from X-User header. Defaults to 'anonymous'."""
    return request.headers.get("X-User", "anonymous")


def require_role(request: Request, allowed: set[str]) -> str:
    """Enforce that the caller has one of the allowed roles.

    Returns the role if authorized, raises HTTP 403 otherwise.
    """
    role = get_role(request)
    if role not in allowed:
        raise HTTPException(
            status_code=403,
            detail=(
                f"Role '{role}' is not authorized for this action. "
                f"Required: {', '.join(sorted(allowed))}"
            ),
        )
    return role
