"""Context envelope validation."""

from __future__ import annotations

from typing import List

from .models import ContextEnvelope

_VALID_BLAST_RADIUS = {"tiny", "small", "medium", "large"}
_VALID_ACTOR_TYPES = {"agent", "human", "system", "service", ""}


def validate_context_envelope(envelope: ContextEnvelope) -> List[str]:
    """Validate a ContextEnvelope, returning a list of error strings.

    An empty list means the envelope is valid.
    """
    errors: List[str] = []

    if not envelope.context_id or not envelope.context_id.startswith("CTX-"):
        errors.append(
            f"context_id must start with 'CTX-', got '{envelope.context_id}'"
        )

    if envelope.blast_radius_tier not in _VALID_BLAST_RADIUS:
        errors.append(
            f"blast_radius_tier must be one of {_VALID_BLAST_RADIUS}, "
            f"got '{envelope.blast_radius_tier}'"
        )

    if envelope.actor_type not in _VALID_ACTOR_TYPES:
        errors.append(
            f"actor_type must be one of {_VALID_ACTOR_TYPES}, "
            f"got '{envelope.actor_type}'"
        )

    if envelope.deadline_ms is not None and envelope.deadline_ms <= 0:
        errors.append(
            f"deadline_ms must be positive, got {envelope.deadline_ms}"
        )

    if envelope.freshness_ttl_ms is not None and envelope.freshness_ttl_ms <= 0:
        errors.append(
            f"freshness_ttl_ms must be positive, got {envelope.freshness_ttl_ms}"
        )

    if envelope.max_hops is not None and envelope.max_hops <= 0:
        errors.append(
            f"max_hops must be positive, got {envelope.max_hops}"
        )

    if envelope.max_chain_depth is not None and envelope.max_chain_depth <= 0:
        errors.append(
            f"max_chain_depth must be positive, got {envelope.max_chain_depth}"
        )

    return errors
