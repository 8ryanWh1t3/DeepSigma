"""Typed representation contracts. Status and confidence are declarations, not truth."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping

from .util import Record, ValidationError, freeze, instant, strings, text, timestamp


class Status(str, Enum):
    OBSERVED = "observed"
    ASSERTED = "asserted"
    INFERRED = "inferred"
    UNKNOWN = "unknown"
    RETRACTED = "retracted"


def _attributes(obj: Any) -> None:
    if not isinstance(obj.attributes, Mapping):
        raise ValidationError("attributes must be a JSON object")
    object.__setattr__(obj, "attributes", freeze(obj.attributes))


def _temporal(obj: Any) -> None:
    for name in ("valid_from", "valid_to", "review_due"):
        if hasattr(obj, name) and getattr(obj, name) is not None:
            object.__setattr__(obj, name, timestamp(getattr(obj, name)))
    if obj.valid_from and obj.valid_to and instant(obj.valid_from) >= instant(obj.valid_to):
        raise ValidationError("valid_from must precede valid_to; intervals are [from,to)")


def _status(obj: Any) -> None:
    try:
        object.__setattr__(obj, "status", Status(obj.status))
    except (TypeError, ValueError) as exc:
        raise ValidationError("Unknown epistemic status") from exc
    value = obj.confidence
    if value is not None and (type(value) not in (float, int) or not 0 <= value <= 1):
        raise ValidationError("confidence must be null or a finite number in [0,1]")
    if value is not None:
        object.__setattr__(obj, "confidence", float(value))
    object.__setattr__(obj, "evidence_ids", strings(obj.evidence_ids, "evidence_ids"))


@dataclass(frozen=True)
class Node(Record):
    id: str
    label: str
    kind: str
    layer: str = "meaning"
    scope: str = "default"
    status: Status = Status.ASSERTED
    confidence: float | None = None
    evidence_ids: tuple[str, ...] = ()
    valid_from: str | None = None
    valid_to: str | None = None
    review_due: str | None = None
    attributes: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in ("id", "label", "kind", "layer", "scope"):
            text(getattr(self, name), name)
        _status(self)
        _temporal(self)
        _attributes(self)


@dataclass(frozen=True)
class Edge(Record):
    id: str
    source: str
    predicate: str
    target: str
    status: Status = Status.ASSERTED
    confidence: float | None = None
    evidence_ids: tuple[str, ...] = ()
    valid_from: str | None = None
    valid_to: str | None = None
    attributes: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in ("id", "source", "predicate", "target"):
            text(getattr(self, name), name)
        _status(self)
        _temporal(self)
        _attributes(self)


@dataclass(frozen=True)
class Evidence(Record):
    id: str
    source: str
    locator: str = ""
    sha256: str | None = None
    valid_from: str | None = None
    valid_to: str | None = None
    attributes: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        text(self.id, "id")
        text(self.source, "source")
        if not isinstance(self.locator, str):
            raise ValidationError("locator must be a string")
        if self.sha256 is not None and (not isinstance(self.sha256, str) or
                                        not re.fullmatch(r"[a-f0-9]{64}", self.sha256)):
            raise ValidationError("sha256 must contain exactly 64 lowercase hexadecimal digits")
        _temporal(self)
        _attributes(self)


@dataclass(frozen=True)
class Predicate(Record):
    id: str
    label: str
    description: str
    dependency: str = "none"
    source_kinds: tuple[str, ...] = ()
    target_kinds: tuple[str, ...] = ()
    evidence_relation: bool = False

    def __post_init__(self) -> None:
        for name in ("id", "label", "description"):
            text(getattr(self, name), name)
        if self.dependency not in ("forward", "reverse", "none"):
            raise ValidationError("dependency must be forward, reverse, or none")
        if type(self.evidence_relation) is not bool:
            raise ValidationError("evidence_relation must be a boolean")
        for name in ("source_kinds", "target_kinds"):
            object.__setattr__(self, name, strings(getattr(self, name), name))


DEFAULT_PREDICATES = (
    Predicate("depends_on", "Depends on", "Source depends on target.", "forward"),
    Predicate("requires", "Requires", "Source requires target.", "forward"),
    Predicate("supported_by", "Supported by", "Source cites target as support.", "forward", evidence_relation=True),
    Predicate("supports", "Supports", "Source supports target.", "reverse", evidence_relation=True),
    Predicate("derived_from", "Derived from", "Source representation derives from target.", "forward", evidence_relation=True),
    Predicate("authorized_by", "Authority reference", "Source records a reference to an authority; not a verified grant.", "forward", target_kinds=("authority", "authority_slice", "role")),
    Predicate("implements", "Implements", "Source records implementation of target.", "forward"),
    Predicate("part_of", "Part of", "Source is represented as a part of target."),
    Predicate("contradicts", "Recorded contradiction", "A contradiction has been recorded; this is not a text inference."),
    Predicate("supersedes", "Supersedes", "Source records succession of target; no automatic retraction."),
    Predicate("relates_to", "Related to", "A declared relationship without dependency semantics."),
    Predicate("produced", "Produced", "Source records production of target."),
    Predicate("informed_by", "Informed by", "Source records an informational input from target.", "forward", evidence_relation=True),
    Predicate("evidence_of", "Evidence of", "Source evidence relates to target.", "reverse", evidence_relation=True),
)


def active(record: Node | Edge | Evidence, as_of: str) -> bool:
    at = instant(as_of)
    if getattr(record, "status", None) == Status.RETRACTED:
        return False
    return ((record.valid_from is None or instant(record.valid_from) <= at) and
            (record.valid_to is None or at < instant(record.valid_to)))


@dataclass(frozen=True)
class CoverageRequirement(Record):
    """An explicit expected outgoing relationship, not inferred mission completeness."""
    subject_id: str
    predicate: str
    target_kind: str | None = None
    minimum: int = 1

    def __post_init__(self) -> None:
        text(self.subject_id, "subject_id")
        text(self.predicate, "predicate")
        if self.target_kind is not None:
            text(self.target_kind, "target_kind")
        if type(self.minimum) is not int or self.minimum < 1:
            raise ValidationError("minimum must be a positive integer")
