"""In-memory commitment registry."""

from __future__ import annotations

from typing import Dict, List, Optional

from .models import Commitment, CommitmentState


class CommitmentRegistry:
    """In-memory store of active commitments."""

    def __init__(self) -> None:
        self._commitments: Dict[str, Commitment] = {}

    def add(self, commitment: Commitment) -> str:
        """Add a commitment. Returns the commitment_id."""
        self._commitments[commitment.commitment_id] = commitment
        return commitment.commitment_id

    def get(self, commitment_id: str) -> Optional[Commitment]:
        """Retrieve a commitment by ID, or None if not found."""
        return self._commitments.get(commitment_id)

    def update(self, commitment: Commitment) -> None:
        """Update an existing commitment in the registry."""
        self._commitments[commitment.commitment_id] = commitment

    def remove(self, commitment_id: str) -> bool:
        """Remove a commitment. Returns True if it existed."""
        return self._commitments.pop(commitment_id, None) is not None

    def list_active(self) -> List[Commitment]:
        """Return all non-archived commitments."""
        return [
            c for c in self._commitments.values()
            if c.lifecycle_state != CommitmentState.ARCHIVED
        ]

    def list_by_state(self, state: str) -> List[Commitment]:
        """Return all commitments in a given lifecycle state."""
        return [
            c for c in self._commitments.values()
            if c.lifecycle_state == state
        ]

    def list_by_domain(self, domain: str) -> List[Commitment]:
        """Return all commitments for a given domain."""
        return [
            c for c in self._commitments.values()
            if c.domain == domain
        ]
