from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .codec import sha256_hex
from .models import MissionObject


@dataclass(frozen=True, slots=True)
class LedgerEntry:
    sequence: int
    object: MissionObject
    prior_hash: str
    entry_hash: str


class EventLedger:
    """Append-only, hash-chained local event ledger."""

    def __init__(self) -> None:
        self._entries: list[LedgerEntry] = []
        self._seen: set[str] = set()

    def append(self, obj: MissionObject) -> LedgerEntry:
        if obj.object_id in self._seen:
            return next(e for e in self._entries if e.object.object_id == obj.object_id)
        prior_hash = self._entries[-1].entry_hash if self._entries else "GENESIS"
        sequence = len(self._entries) + 1
        entry_hash = sha256_hex({"sequence": sequence, "prior_hash": prior_hash, "object": obj})
        entry = LedgerEntry(sequence, obj, prior_hash, entry_hash)
        self._entries.append(entry)
        self._seen.add(obj.object_id)
        return entry

    def extend(self, objects: Iterable[MissionObject]) -> list[LedgerEntry]:
        return [self.append(obj) for obj in objects]

    def contains(self, object_id: str) -> bool:
        return object_id in self._seen

    def objects(self) -> tuple[MissionObject, ...]:
        return tuple(e.object for e in self._entries)

    def after(self, sequence: int) -> tuple[MissionObject, ...]:
        return tuple(e.object for e in self._entries if e.sequence > sequence)

    @property
    def head_sequence(self) -> int:
        return len(self._entries)

    @property
    def head_hash(self) -> str:
        return self._entries[-1].entry_hash if self._entries else "GENESIS"
