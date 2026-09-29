from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Iterable

from .models import MissionObject


@dataclass(frozen=True, slots=True)
class FieldState:
    winner: MissionObject | None
    candidates: tuple[MissionObject, ...]


class WorldModel:
    """Materialized local world model derived from immutable mission objects.

    It intentionally retains competing candidates. The default projection favors
    non-expired, higher-version, newer observations, but reconciliation logic may
    override that projection through a patch object.
    """

    def __init__(self) -> None:
        self._by_key: dict[tuple[str, str], list[MissionObject]] = defaultdict(list)

    def ingest(self, obj: MissionObject) -> None:
        key = (obj.entity_id, obj.field)
        if any(existing.object_id == obj.object_id for existing in self._by_key[key]):
            return
        self._by_key[key].append(obj)

    def ingest_many(self, objects: Iterable[MissionObject]) -> None:
        for obj in objects:
            self.ingest(obj)

    def state(self, entity_id: str, field: str = "status") -> FieldState:
        candidates = tuple(self._by_key.get((entity_id, field), ()))
        live = [o for o in candidates if not o.is_expired()]
        if not live:
            return FieldState(None, candidates)
        winner = max(live, key=lambda o: (o.version, o.observed_at, o.created_at, o.object_id))
        return FieldState(winner, candidates)

    def current(self, entity_id: str, field: str = "status"):
        s = self.state(entity_id, field)
        return s.winner.value if s.winner else None

    def all_keys(self) -> tuple[tuple[str, str], ...]:
        return tuple(sorted(self._by_key))
