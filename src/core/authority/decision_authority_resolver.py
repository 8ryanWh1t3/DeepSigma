"""Decision Authority Resolver — effective authority intersection.

Resolves the intersection of actor roles, resource constraints, and
policy to determine whether effective authority exists for an action.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from .models import ActionRequest, Actor, AuthorityGrant, PolicyConstraint, Resource

logger = logging.getLogger(__name__)


def resolve(
    actor: Actor,
    action: ActionRequest,
    resource: Resource,
    policies: List[Dict[str, Any]],
) -> Optional[AuthorityGrant]:
    """Determine if an actor has effective authority for an action on a resource.

    Args:
        actor: Resolved actor with roles.
        action: The action being evaluated.
        resource: The target resource.
        policies: List of applicable policy dicts.

    Returns:
        AuthorityGrant if authority found, None otherwise.
    """
    for role in actor.roles:
        # Check if role scope overlaps with resource scope/classification
        if not check_scope_overlap(role.scope, resource.resource_type):
            continue

        # Check constraints from policies
        blocked = False
        for policy in policies:
            constraints = policy.get("constraints", [])
            for c in constraints:
                c_type = c.get("constraintType", c.get("constraint_type", ""))
                if c_type == "scope_limit":
                    allowed_scope = c.get("parameters", {}).get("scope", "")
                    if allowed_scope and not check_scope_overlap(role.scope, allowed_scope):
                        blocked = True
                        break
            if blocked:
                break

        if not blocked:
            return AuthorityGrant(
                authority_id=f"RESOLVED-{role.role_id}",
                source_type="role_binding",
                scope=role.scope,
                effective_at=role.granted_at,
                expires_at=role.expires_at,
            )

    return None


def check_scope_overlap(authority_scope: str, resource_scope: str) -> bool:
    """Check if an authority scope overlaps with a resource scope.

    Simple prefix-based overlap: 'global' covers everything,
    otherwise check if one scope is a prefix of the other.
    """
    if not authority_scope or not resource_scope:
        return True  # Empty scope = universal

    if authority_scope == "global" or resource_scope == "global":
        return True

    # Prefix match in either direction
    return (
        authority_scope.startswith(resource_scope)
        or resource_scope.startswith(authority_scope)
    )
