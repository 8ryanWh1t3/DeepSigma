"""Tension lifecycle state machine.

Manages lifecycle transitions for Paradox Tension Sets following the
detect -> monitor -> threshold -> promote to drift -> seal/version/patch pattern.
"""

from __future__ import annotations

from typing import Dict, Optional, Set

from .models import TensionLifecycleState

_S = TensionLifecycleState

_TRANSITIONS: Dict[TensionLifecycleState, Set[TensionLifecycleState]] = {
    _S.DETECTED: {_S.ACTIVE},
    _S.ACTIVE: {_S.ELEVATED, _S.SEALED, _S.ARCHIVED},
    _S.ELEVATED: {_S.PROMOTED_TO_DRIFT, _S.SEALED, _S.ACTIVE},
    _S.PROMOTED_TO_DRIFT: {_S.SEALED},
    _S.SEALED: {_S.PATCHED, _S.ARCHIVED},
    _S.PATCHED: {_S.REBALANCED, _S.ARCHIVED},
    _S.REBALANCED: {_S.ARCHIVED},
    _S.ARCHIVED: set(),
}


class TensionLifecycle:
    """In-memory tension lifecycle tracker with transition validation."""

    def __init__(self) -> None:
        self._states: Dict[str, TensionLifecycleState] = {}

    def set_state(self, tension_id: str, state: TensionLifecycleState) -> None:
        """Set state directly (for initial load, no validation)."""
        self._states[tension_id] = state

    def get_state(self, tension_id: str) -> Optional[TensionLifecycleState]:
        """Get current state, or None if not tracked."""
        return self._states.get(tension_id)

    def transition(self, tension_id: str, target: TensionLifecycleState) -> bool:
        """Attempt a state transition. Returns True if valid and applied."""
        current = self._states.get(tension_id)
        if current is None:
            return False
        allowed = _TRANSITIONS.get(current, set())
        if target not in allowed:
            return False
        self._states[tension_id] = target
        return True

    def is_terminal(self, tension_id: str) -> bool:
        """Check if the tension is in a terminal state."""
        current = self._states.get(tension_id)
        if current is None:
            return False
        return len(_TRANSITIONS.get(current, set())) == 0

    def valid_transitions(self, tension_id: str) -> Set[TensionLifecycleState]:
        """Return the set of valid next states."""
        current = self._states.get(tension_id)
        if current is None:
            return set()
        return _TRANSITIONS.get(current, set())
