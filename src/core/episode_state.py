"""Episode state machine — lifecycle states for decision episodes.

States: PENDING -> ACTIVE -> SEALED -> ARCHIVED
Also: ACTIVE -> FROZEN (killswitch), FROZEN -> ACTIVE (resume)

Follows the CanonWorkflow/TriageState pattern.
"""

from __future__ import annotations

from enum import Enum
from typing import Dict, List, Optional


class EpisodeState(str, Enum):
    """Lifecycle states for a decision episode."""

    PENDING = "pending"
    ACTIVE = "active"
    SEALED = "sealed"
    ARCHIVED = "archived"
    FROZEN = "frozen"


# Valid transitions: source -> set of allowed target states
_TRANSITIONS: Dict[EpisodeState, set] = {
    EpisodeState.PENDING: {EpisodeState.ACTIVE},
    EpisodeState.ACTIVE: {EpisodeState.SEALED, EpisodeState.FROZEN},
    EpisodeState.SEALED: {EpisodeState.ARCHIVED},
    EpisodeState.ARCHIVED: set(),
    EpisodeState.FROZEN: {EpisodeState.ACTIVE},
}


class EpisodeTracker:
    """In-memory episode state tracker with transition validation."""

    def __init__(self) -> None:
        self._states: Dict[str, EpisodeState] = {}

    def set_state(self, episode_id: str, state: EpisodeState) -> None:
        """Set state without transition validation (for initial load)."""
        self._states[episode_id] = state

    def get_state(self, episode_id: str) -> Optional[EpisodeState]:
        """Get current state of an episode."""
        return self._states.get(episode_id)

    def transition(self, episode_id: str, target: EpisodeState) -> bool:
        """Attempt a state transition. Returns True if valid."""
        current = self._states.get(episode_id)
        if current is None:
            self._states[episode_id] = target
            return True

        allowed = _TRANSITIONS.get(current, set())
        if target not in allowed:
            return False

        self._states[episode_id] = target
        return True

    def freeze_all(self) -> List[str]:
        """Freeze all ACTIVE episodes. Returns list of frozen episode IDs."""
        frozen: List[str] = []
        for eid, state in list(self._states.items()):
            if state == EpisodeState.ACTIVE:
                self._states[eid] = EpisodeState.FROZEN
                frozen.append(eid)
        return frozen

    def active_episodes(self) -> List[str]:
        """Return episode IDs in ACTIVE state."""
        return [eid for eid, s in self._states.items() if s == EpisodeState.ACTIVE]

    def all_states(self) -> Dict[str, str]:
        """Return all tracked states as a plain dict."""
        return {eid: s.value for eid, s in self._states.items()}
