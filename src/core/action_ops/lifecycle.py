"""Commitment lifecycle state machine.

Manages lifecycle transitions for commitments following the
propose -> activate -> track -> breach/complete -> remediate/archive pattern.
"""

from __future__ import annotations

from typing import Dict, Optional, Set

from .models import CommitmentState

_S = CommitmentState

_TRANSITIONS: Dict[CommitmentState, Set[CommitmentState]] = {
    _S.PROPOSED: {_S.ACTIVE},
    _S.ACTIVE: {_S.AT_RISK, _S.COMPLETED, _S.ARCHIVED},
    _S.AT_RISK: {_S.BREACHED, _S.REMEDIATED, _S.ACTIVE},
    _S.BREACHED: {_S.ESCALATED, _S.REMEDIATED},
    _S.REMEDIATED: {_S.ACTIVE, _S.COMPLETED},
    _S.ESCALATED: {_S.REMEDIATED, _S.ARCHIVED},
    _S.COMPLETED: {_S.ARCHIVED},
    _S.ARCHIVED: set(),
}


class CommitmentLifecycle:
    """In-memory commitment lifecycle tracker with transition validation."""

    def __init__(self) -> None:
        self._states: Dict[str, CommitmentState] = {}

    def set_state(self, commitment_id: str, state: CommitmentState) -> None:
        """Set state directly (for initial load, no validation)."""
        self._states[commitment_id] = state

    def get_state(self, commitment_id: str) -> Optional[CommitmentState]:
        """Get current state, or None if not tracked."""
        return self._states.get(commitment_id)

    def transition(self, commitment_id: str, target: CommitmentState) -> bool:
        """Attempt a state transition. Returns True if valid and applied."""
        current = self._states.get(commitment_id)
        if current is None:
            return False
        allowed = _TRANSITIONS.get(current, set())
        if target not in allowed:
            return False
        self._states[commitment_id] = target
        return True

    def is_terminal(self, commitment_id: str) -> bool:
        """Check if the commitment is in a terminal state."""
        current = self._states.get(commitment_id)
        if current is None:
            return False
        return len(_TRANSITIONS.get(current, set())) == 0

    def valid_transitions(self, commitment_id: str) -> Set[CommitmentState]:
        """Return the set of valid next states."""
        current = self._states.get(commitment_id)
        if current is None:
            return set()
        return _TRANSITIONS.get(current, set())
