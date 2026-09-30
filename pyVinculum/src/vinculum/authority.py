from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from fnmatch import fnmatchcase
from typing import Any, Iterable, Mapping

from .exceptions import DuplicateRecordError, GovernanceError


class AuthorityStatus(str, Enum):
    ACTIVE = "ACTIVE"
    REVOKED = "REVOKED"
    SUSPENDED = "SUSPENDED"
    EXPIRED = "EXPIRED"


@dataclass(frozen=True)
class AuthorityGrant:
    """A deterministic authority assertion.

    This object is a deterministic authority assertion. Cryptographic authenticity is
    established only when its containing GovernanceContext is accepted through the
    v0.3 trusted-governance layer.
    """

    id: str
    principal_id: str
    role: str
    actions: tuple[str, ...] | list[str]
    scopes: tuple[str, ...] | list[str] = ("*",)
    status: AuthorityStatus | str = AuthorityStatus.ACTIVE
    provenance_ref: str | None = None
    evidence_refs: tuple[str, ...] | list[str] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.id.strip():
            raise GovernanceError("authority grant id cannot be empty")
        if not self.principal_id.strip():
            raise GovernanceError("authority principal_id cannot be empty")
        if not self.role.strip():
            raise GovernanceError("authority role cannot be empty")
        actions = tuple(str(v).strip() for v in self.actions if str(v).strip())
        scopes = tuple(str(v).strip() for v in self.scopes if str(v).strip())
        if not actions:
            raise GovernanceError("authority grant requires at least one action")
        if not scopes:
            raise GovernanceError("authority grant requires at least one scope")
        status = self.status if isinstance(self.status, AuthorityStatus) else AuthorityStatus(str(self.status))
        object.__setattr__(self, "actions", actions)
        object.__setattr__(self, "scopes", scopes)
        object.__setattr__(self, "status", status)
        object.__setattr__(self, "evidence_refs", tuple(str(v) for v in self.evidence_refs))

    def allows(self, *, action: str, scope: str) -> bool:
        if self.status is not AuthorityStatus.ACTIVE:
            return False
        if action not in self.actions and "*" not in self.actions:
            return False
        return any(fnmatchcase(scope, pattern) for pattern in self.scopes)

    def receipt_view(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "principal_id": self.principal_id,
            "role": self.role,
            "actions": list(self.actions),
            "scopes": list(self.scopes),
            "status": self.status.value,
            "provenance_ref": self.provenance_ref,
            "evidence_refs": list(self.evidence_refs),
            "metadata": dict(self.metadata),
        }


class AuthorityRegistry:
    def __init__(self, grants: Iterable[AuthorityGrant] = ()) -> None:
        self._grants: dict[str, AuthorityGrant] = {}
        for grant in grants:
            if grant.id in self._grants:
                raise DuplicateRecordError(f"duplicate authority grant id: {grant.id}")
            self._grants[grant.id] = grant

    def get(self, grant_id: str) -> AuthorityGrant | None:
        return self._grants.get(grant_id)

    def receipt_view(self) -> list[dict[str, Any]]:
        return [self._grants[k].receipt_view() for k in sorted(self._grants)]
