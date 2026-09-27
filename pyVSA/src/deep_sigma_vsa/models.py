from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4


def _id(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:12]}"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class AuthorityStatus(str, Enum):
    CANDIDATE = "candidate"
    REVIEWED = "reviewed"
    AUTHORITATIVE = "authoritative"
    REJECTED = "rejected"


class Modality(str, Enum):
    ASSERTED = "asserted"
    PROBABLE = "probable"
    POSSIBLE = "possible"
    REQUIRED = "required"
    PROHIBITED = "prohibited"
    QUESTION = "question"
    UNKNOWN = "unknown"


@dataclass(slots=True, frozen=True)
class Confidence:
    value: float
    rationale: str | None = None

    def __post_init__(self) -> None:
        if not 0.0 <= self.value <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0")


@dataclass(slots=True, frozen=True)
class ProvenanceRef:
    source_id: str
    source_type: str
    source_uri: str | None = None
    source_sha256: str | None = None
    speaker_id: str | None = None
    start_ms: int | None = None
    end_ms: int | None = None
    observed_at: datetime | None = None
    transform_chain: tuple[str, ...] = ()


@dataclass(slots=True, frozen=True)
class TranscriptSegment:
    text: str
    speaker_id: str | None = None
    start_ms: int | None = None
    end_ms: int | None = None
    confidence: Confidence = field(default_factory=lambda: Confidence(1.0, "supplied transcript"))


@dataclass(slots=True, frozen=True)
class Transcript:
    text: str
    source_id: str
    segments: tuple[TranscriptSegment, ...] = ()
    language: str = "en"
    created_at: datetime = field(default_factory=utc_now)


@dataclass(slots=True, frozen=True)
class Evidence:
    text: str
    provenance: ProvenanceRef
    confidence: Confidence
    evidence_type: str = "utterance"
    id: str = field(default_factory=lambda: _id("evidence"))


@dataclass(slots=True, frozen=True)
class Entity:
    name: str
    entity_type: str = "unknown"
    aliases: tuple[str, ...] = ()
    confidence: Confidence = field(default_factory=lambda: Confidence(0.5))
    evidence_ids: tuple[str, ...] = ()
    id: str = field(default_factory=lambda: _id("entity"))


@dataclass(slots=True, frozen=True)
class Claim:
    text: str
    confidence: Confidence
    modality: Modality = Modality.ASSERTED
    negated: bool = False
    subject: str | None = None
    predicate: str = "asserts"
    object: str | None = None
    evidence_ids: tuple[str, ...] = ()
    assumption_ids: tuple[str, ...] = ()
    authority_status: AuthorityStatus = AuthorityStatus.CANDIDATE
    id: str = field(default_factory=lambda: _id("claim"))


@dataclass(slots=True, frozen=True)
class Assumption:
    statement: str
    confidence: Confidence
    evidence_ids: tuple[str, ...] = ()
    review_at: datetime | None = None
    authority_status: AuthorityStatus = AuthorityStatus.CANDIDATE
    id: str = field(default_factory=lambda: _id("assumption"))


@dataclass(slots=True, frozen=True)
class Event:
    description: str
    confidence: Confidence
    actor_ids: tuple[str, ...] = ()
    entity_ids: tuple[str, ...] = ()
    evidence_ids: tuple[str, ...] = ()
    occurred_at: datetime | None = None
    location: str | None = None
    event_type: str = "utterance_event"
    authority_status: AuthorityStatus = AuthorityStatus.CANDIDATE
    id: str = field(default_factory=lambda: _id("event"))


@dataclass(slots=True, frozen=True)
class Relationship:
    source_id: str
    predicate: str
    target_id: str
    confidence: Confidence
    evidence_ids: tuple[str, ...] = ()
    authority_status: AuthorityStatus = AuthorityStatus.CANDIDATE
    id: str = field(default_factory=lambda: _id("rel"))


@dataclass(slots=True, frozen=True)
class Intent:
    goal: str
    confidence: Confidence
    actor_id: str | None = None
    evidence_ids: tuple[str, ...] = ()
    authority_status: AuthorityStatus = AuthorityStatus.CANDIDATE
    id: str = field(default_factory=lambda: _id("intent"))


@dataclass(slots=True, frozen=True)
class GovernanceEnvelope:
    authority_status: AuthorityStatus = AuthorityStatus.CANDIDATE
    provenance_required: bool = True
    human_review_required: bool = True
    policy_tags: tuple[str, ...] = ()
    classification: str = "UNSPECIFIED"
    notes: tuple[str, ...] = (
        "Voice-derived semantics are candidate objects until governed downstream.",
    )


@dataclass(slots=True)
class SemanticPacket:
    transcript: Transcript
    evidence: list[Evidence] = field(default_factory=list)
    claims: list[Claim] = field(default_factory=list)
    entities: list[Entity] = field(default_factory=list)
    events: list[Event] = field(default_factory=list)
    relationships: list[Relationship] = field(default_factory=list)
    intents: list[Intent] = field(default_factory=list)
    assumptions: list[Assumption] = field(default_factory=list)
    governance: GovernanceEnvelope = field(default_factory=GovernanceEnvelope)
    packet_id: str = field(default_factory=lambda: _id("vsa"))
    created_at: datetime = field(default_factory=utc_now)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from .serialization import to_primitive

        return to_primitive(asdict(self))

    def to_json(self, *, indent: int | None = None) -> str:
        from .serialization import dumps

        return dumps(self.to_dict(), indent=indent)

    def to_rdf_triples(self) -> list[tuple[str, str, str]]:
        from .graph import to_rdf_triples

        return to_rdf_triples(self)

    def to_turtle(self) -> str:
        from .graph import triples_to_turtle

        return triples_to_turtle(self.to_rdf_triples())

    def to_resonator_payload(self) -> dict[str, Any]:
        from .graph import to_resonator_payload

        return to_resonator_payload(self)

    def to_pathfinder_payload(self) -> dict[str, Any]:
        from .graph import to_pathfinder_payload

        return to_pathfinder_payload(self)

    def to_composer_candidates(self) -> list[dict[str, Any]]:
        from .graph import to_composer_candidates

        return to_composer_candidates(self)

    def to_cerpa_candidates(self) -> list[dict[str, Any]]:
        from .graph import to_cerpa_candidates

        return to_cerpa_candidates(self)
