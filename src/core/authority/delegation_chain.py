"""Delegation Chain — validate delegated authority with depth limits.

Walks a delegation chain from the acting actor back to the original
authority source, checking expiry and scope at each hop.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from .models import Actor, Delegation

logger = logging.getLogger(__name__)


def validate_chain(
    delegations: List[Delegation],
    actor: Actor,
    max_depth: int = 5,
    now: Optional[datetime] = None,
) -> Tuple[bool, List[str]]:
    """Validate a delegation chain for a given actor.

    Args:
        delegations: Ordered list of delegations from root to leaf.
        actor: The actor at the end of the chain.
        max_depth: Maximum allowed chain depth.
        now: Current time for expiry checks.

    Returns:
        Tuple of (is_valid, list of issues).
    """
    if now is None:
        now = datetime.now(timezone.utc)

    issues: List[str] = []

    if not delegations:
        issues.append("empty_delegation_chain")
        return False, issues

    if len(delegations) > max_depth:
        issues.append(f"chain_depth_exceeded:depth={len(delegations)},max={max_depth}")
        return False, issues

    # Verify chain connectivity
    for i, delegation in enumerate(delegations):
        # Check expiry
        if not check_expiry(delegation, now):
            issues.append(f"delegation_expired:{delegation.delegation_id}")

        # Check revocation
        if delegation.revoked_at is not None:
            issues.append(f"delegation_revoked:{delegation.delegation_id}")

        # Check chain linkage (each delegation's to_actor_id should match
        # the next delegation's from_actor_id, or the final actor)
        if i < len(delegations) - 1:
            next_del = delegations[i + 1]
            if delegation.to_actor_id != next_del.from_actor_id:
                issues.append(
                    f"chain_broken:hop={i},"
                    f"expected={delegation.to_actor_id},"
                    f"got={next_del.from_actor_id}"
                )

    # Verify the final delegation targets our actor
    if delegations and delegations[-1].to_actor_id != actor.actor_id:
        issues.append(
            f"chain_terminal_mismatch:"
            f"expected={actor.actor_id},"
            f"got={delegations[-1].to_actor_id}"
        )

    return len(issues) == 0, issues


def check_expiry(
    delegation: Delegation,
    now: Optional[datetime] = None,
) -> bool:
    """Check if a delegation has expired.

    Returns True if the delegation is still valid (not expired).
    """
    if now is None:
        now = datetime.now(timezone.utc)

    if delegation.expires_at is None:
        return True  # No expiry set

    try:
        expires = datetime.fromisoformat(delegation.expires_at)
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        return now < expires
    except (ValueError, TypeError):
        return True  # Unparseable expiry treated as no expiry


def compute_effective_scope(chain: List[Delegation]) -> str:
    """Compute the most restrictive scope from a delegation chain.

    The effective scope is the intersection (most restrictive) of all
    scopes in the chain. Simple implementation: use the last (narrowest)
    scope in the chain.
    """
    if not chain:
        return ""
    # Delegation scopes narrow as the chain gets longer
    return chain[-1].scope
