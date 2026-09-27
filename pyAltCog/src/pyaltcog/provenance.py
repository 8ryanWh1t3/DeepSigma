from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

from .ids import stable_hash, stable_id
from .models import AuditEvent


@dataclass
class AuditLedger:
    events: List[AuditEvent] = field(default_factory=list)

    @property
    def head_hash(self) -> str:
        return self.events[-1].event_hash if self.events else "GENESIS"

    def append(
        self,
        *,
        event_type: str,
        occurred_at: str,
        subject_id: str,
        payload: Dict[str, Any],
    ) -> AuditEvent:
        previous = self.head_hash
        material = {
            "event_type": event_type,
            "occurred_at": occurred_at,
            "subject_id": subject_id,
            "payload": payload,
            "previous_hash": previous,
        }
        event_hash = stable_hash(material)
        event = AuditEvent(
            id=stable_id("AUD", material),
            event_type=event_type,
            occurred_at=occurred_at,
            subject_id=subject_id,
            payload=payload,
            previous_hash=previous,
            event_hash=event_hash,
        )
        self.events.append(event)
        return event

    def verify(self) -> bool:
        previous = "GENESIS"
        for event in self.events:
            material = {
                "event_type": event.event_type,
                "occurred_at": event.occurred_at,
                "subject_id": event.subject_id,
                "payload": event.payload,
                "previous_hash": previous,
            }
            if event.previous_hash != previous:
                return False
            if stable_hash(material) != event.event_hash:
                return False
            previous = event.event_hash
        return True
