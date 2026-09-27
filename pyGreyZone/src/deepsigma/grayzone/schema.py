"""Immutable event and assessment contracts. Times must include an offset."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Mapping


def utc(dt: datetime) -> datetime:
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError("timestamp must include a UTC offset")
    return dt.astimezone(timezone.utc)


def parse_time(value: str | datetime) -> datetime:
    if isinstance(value, datetime):
        return utc(value)
    if not isinstance(value, str):
        raise ValueError("timestamp must be an ISO 8601 string")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"invalid timestamp: {value!r}") from exc
    return utc(parsed)


@dataclass(frozen=True)
class SourceRef:
    source_id: str
    record_id: str
    sha256: str
    lineage_group: str = ""
    locator: str = ""

    @property
    def independent_group(self) -> str:
        """Declared upstream group; distinct values are not proof of independence."""
        return self.lineage_group or self.source_id


@dataclass(frozen=True)
class Event:
    id: str
    occurred_at: datetime
    kind: str
    channel: str
    summary: str
    sources: tuple[SourceRef, ...]
    entities: tuple[str, ...] = ()
    assets: tuple[str, ...] = ()
    location: str = ""
    tags: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.id or not self.kind or not self.channel or not self.sources:
            raise ValueError("event requires id, kind, channel and at least one source")
        object.__setattr__(self, "occurred_at", utc(self.occurred_at))


@dataclass(frozen=True)
class EventLink:
    left: str
    right: str
    score: float
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class WeakSignal:
    id: str
    event_ids: tuple[str, ...]
    observation: str


@dataclass(frozen=True)
class Alternative:
    explanation: str
    discriminating_check: str


@dataclass(frozen=True)
class Hypothesis:
    id: str
    event_ids: tuple[str, ...]
    link_ids: tuple[tuple[str, str], ...]
    source_groups: tuple[str, ...]
    channels: tuple[str, ...]
    priority_score: int
    statement: str
    alternatives: tuple[Alternative, ...]
    collection_gaps: tuple[str, ...]
    status: str = "unreviewed"


@dataclass(frozen=True)
class Assessment:
    id: str
    window_start: datetime | None
    window_end: datetime | None
    events: tuple[Event, ...]
    links: tuple[EventLink, ...]
    weak_signals: tuple[WeakSignal, ...]
    hypotheses: tuple[Hypothesis, ...]
    method: str = "rules-v0.1"
    limitations: tuple[str, ...] = (
        "Priority score is a deterministic review order, not a probability or intent assessment.",
        "A candidate pattern does not establish coordination, actor identity, or hostility.",
        "Completeness depends on the supplied feeds, source lineage, identifiers, and baseline.",
    )


@dataclass(frozen=True)
class AssessmentConfig:
    window: timedelta = timedelta(days=30)
    max_link_gap: timedelta = timedelta(hours=72)
    min_events: int = 3
    min_channels: int = 2
    min_source_groups: int = 2
    min_link_score: float = 0.50
    max_events: int = 5000

    def __post_init__(self) -> None:
        if self.window <= timedelta(0) or self.max_link_gap <= timedelta(0):
            raise ValueError("windows must be positive")
        if self.min_events < 2 or self.min_channels < 1 or self.min_source_groups < 1:
            raise ValueError("minimum counts must be positive")
        if not 0 <= self.min_link_score <= 1 or self.max_events < 1:
            raise ValueError("invalid score threshold or event cap")


@dataclass(frozen=True)
class FieldMap:
    """Dot paths into a site-specific export. Empty optional paths are allowed."""

    event_id: str = "id"
    occurred_at: str = "occurred_at"
    kind: str = "kind"
    channel: str = "channel"
    summary: str = "summary"
    source_id: str = "source_id"
    record_id: str = "record_id"
    lineage_group: str = "lineage_group"
    entities: str = "entities"
    assets: str = "assets"
    location: str = "location"
    tags: str = "tags"

    @classmethod
    def from_mapping(cls, values: Mapping[str, str]) -> "FieldMap":
        unknown = set(values) - set(cls.__dataclass_fields__)
        if unknown:
            raise ValueError(f"unknown field map keys: {sorted(unknown)}")
        if any(not isinstance(v, str) for v in values.values()):
            raise ValueError("field map values must be strings")
        return cls(**values)
