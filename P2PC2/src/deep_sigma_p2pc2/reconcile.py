from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from .models import MissionObject
from .world import WorldModel


@dataclass(frozen=True, slots=True)
class Conflict:
    conflict_id: str
    entity_id: str
    field: str
    candidates: tuple[MissionObject, ...]
    reason: str


class Reconciler:
    """Finds semantic conflicts without silently deleting alternatives."""

    def detect(self, world: WorldModel) -> tuple[Conflict, ...]:
        conflicts: list[Conflict] = []
        for entity_id, field in world.all_keys():
            state = world.state(entity_id, field)
            live = [o for o in state.candidates if not o.is_expired()]
            distinct_values = {repr(o.value) for o in live}
            if len(distinct_values) > 1:
                conflicts.append(
                    Conflict(
                        conflict_id=str(uuid4()),
                        entity_id=entity_id,
                        field=field,
                        candidates=tuple(sorted(live, key=lambda o: (o.observed_at, o.object_id))),
                        reason="multiple live peer assertions disagree",
                    )
                )
        return tuple(conflicts)

    def rank_candidates(self, conflict: Conflict) -> tuple[MissionObject, ...]:
        """Deterministic suggestion only; does not convert ranking into authority.

        Confidence is used only when present, then recency. The caller still must
        perform an authority-backed review before APPLY.
        """
        return tuple(
            sorted(
                conflict.candidates,
                key=lambda o: (
                    o.confidence if o.confidence is not None else -1.0,
                    o.observed_at,
                    o.object_id,
                ),
                reverse=True,
            )
        )
