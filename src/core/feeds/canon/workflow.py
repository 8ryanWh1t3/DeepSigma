"""Canon state machine — lifecycle states for canon entries.

States: PROPOSED -> BLESSED -> ACTIVE -> UNDER_REVIEW -> SUPERSEDED / RETCONNED / EXPIRED
Also: PROPOSED -> REJECTED, ACTIVE -> FROZEN (killswitch)

Follows the TriageState pattern from FEEDS consumers.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional


class CanonState(str, Enum):
    """Lifecycle states for a canon entry."""

    PROPOSED = "proposed"
    BLESSED = "blessed"
    ACTIVE = "active"
    UNDER_REVIEW = "under_review"
    SUPERSEDED = "superseded"
    RETCONNED = "retconned"
    EXPIRED = "expired"
    REJECTED = "rejected"
    FROZEN = "frozen"


# Valid transitions: source -> set of allowed target states
_TRANSITIONS: Dict[CanonState, set] = {
    CanonState.PROPOSED: {CanonState.BLESSED, CanonState.REJECTED},
    CanonState.BLESSED: {CanonState.ACTIVE},
    CanonState.ACTIVE: {
        CanonState.UNDER_REVIEW,
        CanonState.SUPERSEDED,
        CanonState.RETCONNED,
        CanonState.EXPIRED,
        CanonState.FROZEN,
    },
    CanonState.UNDER_REVIEW: {CanonState.ACTIVE, CanonState.SUPERSEDED},
    CanonState.SUPERSEDED: set(),
    CanonState.RETCONNED: set(),
    CanonState.EXPIRED: set(),
    CanonState.REJECTED: set(),
    CanonState.FROZEN: {CanonState.ACTIVE},  # resume requires explicit authority
}


class CanonWorkflow:
    """In-memory canon state tracker with transition validation."""

    def __init__(self) -> None:
        self._states: Dict[str, CanonState] = {}

    def set_state(self, canon_id: str, state: CanonState) -> None:
        """Set state without transition validation (for initial load)."""
        self._states[canon_id] = state

    def get_state(self, canon_id: str) -> Optional[CanonState]:
        """Get current state of a canon entry."""
        return self._states.get(canon_id)

    def transition(self, canon_id: str, target: CanonState) -> bool:
        """Attempt a state transition. Returns True if valid.

        If the canon_id is unknown, the transition is allowed (first-time set).
        """
        current = self._states.get(canon_id)
        if current is None:
            self._states[canon_id] = target
            return True

        allowed = _TRANSITIONS.get(current, set())
        if target not in allowed:
            return False

        self._states[canon_id] = target
        return True

    def is_terminal(self, canon_id: str) -> bool:
        """Check if a canon entry is in a terminal state."""
        state = self._states.get(canon_id)
        if state is None:
            return False
        return len(_TRANSITIONS.get(state, set())) == 0

    def active_entries(self) -> List[str]:
        """Return canon IDs in ACTIVE state."""
        return [cid for cid, s in self._states.items() if s == CanonState.ACTIVE]

    def all_states(self) -> Dict[str, str]:
        """Return all tracked states as a plain dict."""
        return {cid: s.value for cid, s in self._states.items()}
