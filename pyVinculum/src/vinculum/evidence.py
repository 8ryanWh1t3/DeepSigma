from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping

from .exceptions import EvidenceIntegrityError, GovernanceError
from .receipts import sha256_receipt


class EvidenceKind(str, Enum):
    DOCUMENT = "DOCUMENT"
    DATASET = "DATASET"
    OBSERVATION = "OBSERVATION"
    SENSOR = "SENSOR"
    COMPUTATION = "COMPUTATION"
    TESTIMONY = "TESTIMONY"
    OTHER = "OTHER"


class EvidenceStatus(str, Enum):
    ACTIVE = "ACTIVE"
    WITHDRAWN = "WITHDRAWN"
    SUPERSEDED = "SUPERSEDED"


@dataclass(frozen=True)
class EvidenceRecord:
    """A stable evidentiary artifact referenced by a hypothesis or authority assertion.

    ``payload`` is optional. When it is present, the library verifies or derives the
    SHA-256 digest deterministically. When it is absent, ``sha256`` is treated as an
    externally supplied content fingerprint and strict callers may elect to require
    materialized payloads before accepting evidence.
    """

    id: str
    kind: EvidenceKind | str
    source: str
    sha256: str | None = None
    payload: Any | None = None
    status: EvidenceStatus | str = EvidenceStatus.ACTIVE
    observed_at: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.id.strip():
            raise GovernanceError("evidence id cannot be empty")
        if not self.source.strip():
            raise GovernanceError("evidence source cannot be empty")

        kind = self.kind if isinstance(self.kind, EvidenceKind) else EvidenceKind(str(self.kind))
        status = self.status if isinstance(self.status, EvidenceStatus) else EvidenceStatus(str(self.status))
        object.__setattr__(self, "kind", kind)
        object.__setattr__(self, "status", status)

        digest = self.sha256.lower() if self.sha256 else None
        if self.payload is not None:
            computed = sha256_receipt(self.payload)
            if digest is not None and digest != computed:
                raise EvidenceIntegrityError(
                    f"evidence {self.id!r} digest mismatch: declared {digest}, computed {computed}"
                )
            digest = computed

        if digest is None:
            raise GovernanceError("evidence requires payload or sha256")
        if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            raise GovernanceError(f"evidence {self.id!r} has invalid sha256")
        object.__setattr__(self, "sha256", digest)

    @classmethod
    def from_payload(
        cls,
        *,
        id: str,
        kind: EvidenceKind | str,
        source: str,
        payload: Any,
        status: EvidenceStatus | str = EvidenceStatus.ACTIVE,
        observed_at: str = "",
        metadata: Mapping[str, Any] | None = None,
    ) -> "EvidenceRecord":
        return cls(
            id=id,
            kind=kind,
            source=source,
            payload=payload,
            status=status,
            observed_at=observed_at,
            metadata=metadata or {},
        )

    @property
    def materialized(self) -> bool:
        return self.payload is not None

    def receipt_view(self) -> dict[str, Any]:
        """Canonical context view that binds identity to content without embedding content."""
        return {
            "id": self.id,
            "kind": self.kind.value,
            "source": self.source,
            "sha256": self.sha256,
            "status": self.status.value,
            "observed_at": self.observed_at,
            "metadata": dict(self.metadata),
        }
