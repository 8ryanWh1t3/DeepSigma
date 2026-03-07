"""In-memory Paradox Tension Set registry."""

from __future__ import annotations

from typing import Dict, List, Optional

from .models import ParadoxTensionSet, TensionLifecycleState


class ParadoxRegistry:
    """In-memory store of active tension sets."""

    def __init__(self) -> None:
        self._tensions: Dict[str, ParadoxTensionSet] = {}

    def add(self, pts: ParadoxTensionSet) -> str:
        """Add a PTS to the registry. Returns the tension_id."""
        self._tensions[pts.tension_id] = pts
        return pts.tension_id

    def get(self, tension_id: str) -> Optional[ParadoxTensionSet]:
        """Retrieve a PTS by ID, or None if not found."""
        return self._tensions.get(tension_id)

    def update(self, pts: ParadoxTensionSet) -> None:
        """Update an existing PTS in the registry."""
        self._tensions[pts.tension_id] = pts

    def remove(self, tension_id: str) -> bool:
        """Remove a PTS. Returns True if it existed."""
        return self._tensions.pop(tension_id, None) is not None

    def list_active(self) -> List[ParadoxTensionSet]:
        """Return all non-archived tension sets."""
        return [
            pts for pts in self._tensions.values()
            if pts.lifecycle_state != TensionLifecycleState.ARCHIVED
        ]

    def list_by_state(self, state: str) -> List[ParadoxTensionSet]:
        """Return all tension sets in a given lifecycle state."""
        return [
            pts for pts in self._tensions.values()
            if pts.lifecycle_state == state
        ]
