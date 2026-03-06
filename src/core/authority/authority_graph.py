"""Authority Graph — actor/resource resolution and authority lookup.

Uses the AuthorityLedger for ledger-based lookups and MemoryGraph
for graph-based authority traversal.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .models import Actor, AuthorityGrant, Delegation, Resource, Role

logger = logging.getLogger(__name__)


def resolve_actor(
    actor_id: str,
    context: Dict[str, Any],
) -> Optional[Actor]:
    """Resolve an actor's identity, roles, and delegation source.

    Args:
        actor_id: The identifier to resolve.
        context: Must contain 'actor_registry' (dict mapping actorId -> actor data)
                 or 'authority_ledger' for ledger-based lookups.

    Returns:
        Resolved Actor or None if not found.
    """
    registry = context.get("actor_registry", {})
    actor_data = registry.get(actor_id)
    if actor_data is None:
        logger.debug("Actor %s not found in registry", actor_id)
        return None

    roles = [
        Role(
            role_id=r.get("roleId", r.get("role_id", "")),
            role_name=r.get("roleName", r.get("role_name", "")),
            scope=r.get("scope", ""),
            granted_at=r.get("grantedAt", r.get("granted_at", "")),
            expires_at=r.get("expiresAt", r.get("expires_at")),
        )
        for r in actor_data.get("roles", [])
    ]

    return Actor(
        actor_id=actor_id,
        actor_type=actor_data.get("actorType", actor_data.get("actor_type", "agent")),
        roles=roles,
        delegated_from=actor_data.get("delegatedFrom", actor_data.get("delegated_from")),
        resolved_at=datetime.now(timezone.utc).isoformat(),
    )


def resolve_resource(
    resource_ref: str,
    context: Dict[str, Any],
) -> Optional[Resource]:
    """Resolve a resource's classification, owner, and constraints.

    Args:
        resource_ref: The resource identifier to resolve.
        context: Must contain 'resource_registry' (dict mapping resourceId -> data).

    Returns:
        Resolved Resource or None if not found.
    """
    registry = context.get("resource_registry", {})
    res_data = registry.get(resource_ref)
    if res_data is None:
        logger.debug("Resource %s not found in registry", resource_ref)
        return None

    return Resource(
        resource_id=resource_ref,
        resource_type=res_data.get("resourceType", res_data.get("resource_type", "")),
        owner=res_data.get("owner", ""),
        classification=res_data.get("classification", ""),
    )


def find_authority(
    actor: Actor,
    resource: Resource,
    context: Dict[str, Any],
) -> Optional[AuthorityGrant]:
    """Find an authority grant for an actor acting on a resource.

    Checks the authority ledger for grants matching actor roles and resource scope.

    Returns:
        AuthorityGrant if found, None otherwise.
    """
    ledger = context.get("authority_ledger")
    if ledger is None:
        return None

    # Check each role's scope against resource
    for role in actor.roles:
        proof = None
        # Walk ledger entries for grants matching role scope
        for entry in reversed(ledger.entries):
            if entry.entry_type == "revocation" and role.scope in entry.scope:
                break
            if entry.entry_type == "grant" and role.scope in entry.scope:
                proof = entry
                break

        if proof is not None:
            return AuthorityGrant(
                authority_id=proof.entry_id,
                source_type="role_binding",
                scope=proof.scope,
                effective_at=proof.effective_at,
                expires_at=proof.expires_at,
            )

    return None
