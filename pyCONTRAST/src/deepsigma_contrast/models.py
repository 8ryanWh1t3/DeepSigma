from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Mapping


@dataclass(frozen=True)
class EvidenceRef:
    id: str
    uri: str | None = None
    weight: float = 1.0
    supports: bool = True
    note: str | None = None

    def __post_init__(self) -> None:
        if not 0.0 <= self.weight <= 1.0:
            raise ValueError("Evidence weight must be between 0.0 and 1.0.")


@dataclass(frozen=True)
class Assumption:
    id: str
    statement: str
    confidence: float = 0.5
    status: str = "ACTIVE"
    expires_at: str | None = None
    evidence_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("Assumption confidence must be between 0.0 and 1.0.")


@dataclass(frozen=True)
class Outcome:
    status: str
    summary: str = ""
    metrics: Mapping[str, float | int | str | bool] = field(default_factory=dict)


@dataclass(frozen=True)
class Episode:
    id: str
    title: str
    claim: str
    decision: str = ""
    rationale: str = ""
    assumptions: tuple[Assumption, ...] | list[Assumption] = ()
    outcome: Outcome | None = None
    evidence: tuple[EvidenceRef, ...] | list[EvidenceRef] = ()
    tags: set[str] | frozenset[str] = field(default_factory=set)
    entities: tuple[str, ...] | list[str] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)
    occurred_at: str | None = None
    version: str = "1"

    def __post_init__(self) -> None:
        object.__setattr__(self, "assumptions", tuple(self.assumptions))
        object.__setattr__(self, "evidence", tuple(self.evidence))
        object.__setattr__(self, "tags", frozenset(self.tags))
        object.__setattr__(self, "entities", tuple(self.entities))

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["tags"] = sorted(self.tags)
        return data


@dataclass(frozen=True)
class Delta:
    kind: str
    key: str
    prior: Any
    current: Any
    materiality: float
    rationale: str


@dataclass(frozen=True)
class DiscriminatingFactor:
    key: str
    description: str
    weight: float
    evidence_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class ContrastResult:
    current_episode_id: str
    prior_episode_id: str
    similarity: float
    structural_similarity: float
    lexical_similarity: float
    assumption_deltas: tuple[Delta, ...]
    outcome_deltas: tuple[Delta, ...]
    evidence_deltas: tuple[Delta, ...]
    metadata_deltas: tuple[Delta, ...]
    material_differences: tuple[str, ...]
    discriminating_factors: tuple[DiscriminatingFactor, ...]
    confidence: float
    advisory_only: bool = True
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
