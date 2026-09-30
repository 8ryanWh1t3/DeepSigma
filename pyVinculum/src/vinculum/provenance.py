from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Iterable, Mapping

from .exceptions import DuplicateRecordError, GovernanceError
from .receipts import sha256_receipt


class ProvenanceKind(str, Enum):
    SOURCE = "SOURCE"
    POLICY = "POLICY"
    DATASET = "DATASET"
    TRANSFORM = "TRANSFORM"
    MODEL_RUN = "MODEL_RUN"
    DECISION = "DECISION"
    OTHER = "OTHER"


class ProvenanceStatus(str, Enum):
    ACTIVE = "ACTIVE"
    SUPERSEDED = "SUPERSEDED"
    REVOKED = "REVOKED"


@dataclass(frozen=True)
class ProvenanceRecord:
    """A versioned node in an explicit lineage graph."""

    id: str
    kind: ProvenanceKind | str
    artifact_sha256: str
    source: str
    version: str = ""
    parent_ids: tuple[str, ...] | list[str] = ()
    status: ProvenanceStatus | str = ProvenanceStatus.ACTIVE
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.id.strip():
            raise GovernanceError("provenance id cannot be empty")
        if not self.source.strip():
            raise GovernanceError("provenance source cannot be empty")
        digest = self.artifact_sha256.lower()
        if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            raise GovernanceError(f"provenance {self.id!r} has invalid artifact_sha256")
        kind = self.kind if isinstance(self.kind, ProvenanceKind) else ProvenanceKind(str(self.kind))
        status = self.status if isinstance(self.status, ProvenanceStatus) else ProvenanceStatus(str(self.status))
        object.__setattr__(self, "kind", kind)
        object.__setattr__(self, "status", status)
        object.__setattr__(self, "artifact_sha256", digest)
        object.__setattr__(self, "parent_ids", tuple(str(v) for v in self.parent_ids))

    @classmethod
    def from_payload(
        cls,
        *,
        id: str,
        kind: ProvenanceKind | str,
        source: str,
        payload: Any,
        version: str = "",
        parent_ids: Iterable[str] = (),
        status: ProvenanceStatus | str = ProvenanceStatus.ACTIVE,
        metadata: Mapping[str, Any] | None = None,
    ) -> "ProvenanceRecord":
        return cls(
            id=id,
            kind=kind,
            artifact_sha256=sha256_receipt(payload),
            source=source,
            version=version,
            parent_ids=tuple(parent_ids),
            status=status,
            metadata=metadata or {},
        )

    def receipt_view(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind.value,
            "artifact_sha256": self.artifact_sha256,
            "source": self.source,
            "version": self.version,
            "parent_ids": list(self.parent_ids),
            "status": self.status.value,
            "metadata": dict(self.metadata),
        }


class ProvenanceLedger:
    """Deterministic resolver for lineage completeness, status, and cycle detection."""

    def __init__(self, records: Iterable[ProvenanceRecord] = ()) -> None:
        self._records: dict[str, ProvenanceRecord] = {}
        for record in records:
            if record.id in self._records:
                raise DuplicateRecordError(f"duplicate provenance id: {record.id}")
            self._records[record.id] = record

    def get(self, record_id: str) -> ProvenanceRecord | None:
        return self._records.get(record_id)

    def validate(self, record_id: str) -> tuple[str, str]:
        """Return ``(PASS|FAIL|UNKNOWN, reason)`` for a lineage root."""
        if record_id not in self._records:
            return "UNKNOWN", "provenance record not found"

        visiting: set[str] = set()
        visited: set[str] = set()

        def walk(node_id: str) -> tuple[bool, str]:
            if node_id in visited:
                return True, ""
            if node_id in visiting:
                return False, f"provenance cycle detected at {node_id}"
            node = self._records.get(node_id)
            if node is None:
                return False, f"provenance parent missing: {node_id}"
            if node.status is not ProvenanceStatus.ACTIVE:
                return False, f"provenance {node_id} status is {node.status.value}"
            visiting.add(node_id)
            for parent_id in sorted(node.parent_ids):
                ok, reason = walk(parent_id)
                if not ok:
                    return False, reason
            visiting.remove(node_id)
            visited.add(node_id)
            return True, ""

        ok, reason = walk(record_id)
        return ("PASS", "") if ok else ("FAIL", reason)

    def lineage(self, record_id: str) -> tuple[str, ...]:
        if record_id not in self._records:
            return ()
        collected: set[str] = set()

        def walk(node_id: str) -> None:
            if node_id in collected:
                return
            node = self._records.get(node_id)
            if node is None:
                return
            collected.add(node_id)
            for parent_id in sorted(node.parent_ids):
                walk(parent_id)

        walk(record_id)
        return tuple(sorted(collected))

    def receipt_view(self) -> list[dict[str, Any]]:
        return [self._records[k].receipt_view() for k in sorted(self._records)]
