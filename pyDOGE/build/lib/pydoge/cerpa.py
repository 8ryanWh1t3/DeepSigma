from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class CERPARecord:
    kind: str
    id: str
    subject_id: str
    statement: str
    evidence: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=_now)
    metadata: dict[str, Any] = field(default_factory=dict)


class CERPALedger:
    """Minimal append-only Claim → Event → Review → Patch → Apply ledger."""

    ORDER = ("CLAIM", "EVENT", "REVIEW", "PATCH", "APPLY")

    def __init__(self) -> None:
        self._records: list[CERPARecord] = []

    def append(self, kind: str, id: str, subject_id: str, statement: str, evidence: list[str] | None = None, **metadata: Any) -> CERPARecord:
        kind = kind.upper()
        if kind not in self.ORDER:
            raise ValueError(f"kind must be one of {self.ORDER}")
        rec = CERPARecord(kind, id, subject_id, statement, evidence or [], metadata=metadata)
        self._records.append(rec)
        return rec

    def records(self) -> list[dict[str, Any]]:
        return [asdict(r) for r in self._records]

    def subject_history(self, subject_id: str) -> list[dict[str, Any]]:
        return [asdict(r) for r in self._records if r.subject_id == subject_id]
