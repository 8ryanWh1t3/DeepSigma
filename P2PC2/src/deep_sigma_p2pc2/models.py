from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Mapping
from uuid import uuid4

from .codec import sha256_hex


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Scope(str, Enum):
    OBSERVE = "observe"
    ASSESS = "assess"
    PROPOSE = "propose"
    PATCH = "patch"
    APPLY = "apply"
    DELEGATE = "delegate"


class MissionObjectKind(str, Enum):
    OBSERVATION = "observation"
    ASSESSMENT = "assessment"
    INTENT = "intent"
    TASK = "task"
    DECISION = "decision"
    PATCH = "patch"
    HEARTBEAT = "heartbeat"


@dataclass(frozen=True, slots=True)
class AuthorityEnvelope:
    authority_id: str
    issuer: str
    subject: str
    scopes: set[Scope]
    constraints: Mapping[str, Any] = field(default_factory=dict)
    valid_from: datetime = field(default_factory=utcnow)
    valid_until: datetime | None = None
    parent_authority_id: str | None = None
    version: int = 1

    def is_time_valid(self, at: datetime | None = None) -> bool:
        at = at or utcnow()
        if at < self.valid_from:
            return False
        if self.valid_until is not None and at > self.valid_until:
            return False
        return True

    @property
    def digest(self) -> str:
        return sha256_hex(self)


@dataclass(frozen=True, slots=True)
class MissionObject:
    object_id: str
    kind: MissionObjectKind
    entity_id: str
    field: str
    value: Any
    origin_peer: str
    observed_at: datetime
    created_at: datetime
    confidence: float | None = None
    authority_id: str | None = None
    evidence: tuple[str, ...] = ()
    dependencies: tuple[str, ...] = ()
    classification: str = "UNCLASSIFIED"
    releasability: tuple[str, ...] = ()
    expires_at: datetime | None = None
    version: int = 1
    supersedes: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def observation(
        cls,
        *,
        entity_id: str,
        value: Any,
        origin_peer: str,
        field: str = "status",
        confidence: float | None = None,
        authority_id: str | None = None,
        evidence: tuple[str, ...] = (),
        observed_at: datetime | None = None,
        expires_at: datetime | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> "MissionObject":
        now = utcnow()
        return cls(
            object_id=str(uuid4()),
            kind=MissionObjectKind.OBSERVATION,
            entity_id=entity_id,
            field=field,
            value=value,
            origin_peer=origin_peer,
            observed_at=observed_at or now,
            created_at=now,
            confidence=confidence,
            authority_id=authority_id,
            evidence=evidence,
            expires_at=expires_at,
            metadata=metadata or {},
        )

    def is_expired(self, at: datetime | None = None) -> bool:
        at = at or utcnow()
        return self.expires_at is not None and at > self.expires_at

    @property
    def digest(self) -> str:
        return sha256_hex(self)


@dataclass(frozen=True, slots=True)
class Review:
    review_id: str
    conflict_id: str
    reviewer: str
    rationale: str
    selected_object_id: str | None = None
    created_at: datetime = field(default_factory=utcnow)


@dataclass(frozen=True, slots=True)
class Patch:
    patch_id: str
    conflict_id: str
    author: str
    entity_id: str
    field: str
    value: Any
    authority_id: str
    rationale: str
    supersedes: tuple[str, ...]
    created_at: datetime = field(default_factory=utcnow)

    @classmethod
    def create(
        cls,
        *,
        conflict_id: str,
        author: str,
        entity_id: str,
        field: str,
        value: Any,
        authority_id: str,
        rationale: str,
        supersedes: tuple[str, ...],
    ) -> "Patch":
        return cls(
            patch_id=str(uuid4()),
            conflict_id=conflict_id,
            author=author,
            entity_id=entity_id,
            field=field,
            value=value,
            authority_id=authority_id,
            rationale=rationale,
            supersedes=supersedes,
        )
