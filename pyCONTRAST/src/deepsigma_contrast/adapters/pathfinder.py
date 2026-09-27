from __future__ import annotations

from dataclasses import dataclass

from ..memory import EpisodeStore, find_comparable
from ..models import Episode


@dataclass
class PathfinderAdapter:
    """Retrieves comparable historical episodes; does not decide authority."""

    store: EpisodeStore

    def comparable_episodes(self, current: Episode, *, top_k: int = 5) -> list[tuple[Episode, float]]:
        return find_comparable(current, self.store.all(), top_k=top_k)
