from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Mapping

from .exceptions import InvalidProbability
from .governance import GovernanceEvaluation, GovernanceStatus


class ConstraintStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    UNKNOWN = "UNKNOWN"


class BoundedState(str, Enum):
    ACCEPTED = "BOUNDED_ACCEPTED"
    REJECTED = "BOUNDED_REJECTED"
    UNRESOLVED = "BOUNDED_UNRESOLVED"


@dataclass(frozen=True)
class Hypothesis:
    id: str
    statement: str
    probability: float
    payload: Mapping[str, Any] = field(default_factory=dict)
    source: str = "unspecified"
    evidence_refs: tuple[str, ...] | list[str] = ()
    provenance_ref: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not 0.0 <= float(self.probability) <= 1.0:
            raise InvalidProbability(f"probability must be in [0,1], got {self.probability}")
        if not self.id.strip():
            raise ValueError("hypothesis id cannot be empty")
        if not self.statement.strip():
            raise ValueError("hypothesis statement cannot be empty")
        object.__setattr__(self, "evidence_refs", tuple(str(v) for v in self.evidence_refs))


@dataclass(frozen=True)
class ConstraintEvaluation:
    constraint_id: str
    status: ConstraintStatus
    hard: bool
    weight: float
    field: str
    op: str
    expected: Any
    actual: Any = None
    reason: str = ""
    description: str = ""


@dataclass(frozen=True)
class BindingResult:
    hypothesis: Hypothesis
    state: BoundedState
    evaluations: tuple[ConstraintEvaluation, ...]
    governance_evaluations: tuple[GovernanceEvaluation, ...]
    governance_status: GovernanceStatus
    constraint_coverage: float
    governance_coverage: float
    soft_compliance: float
    bounded_confidence: float
    coherence_score: float

    @property
    def hard_failures(self) -> tuple[ConstraintEvaluation, ...]:
        return tuple(e for e in self.evaluations if e.hard and e.status is ConstraintStatus.FAIL)

    @property
    def hard_unknowns(self) -> tuple[ConstraintEvaluation, ...]:
        return tuple(e for e in self.evaluations if e.hard and e.status is ConstraintStatus.UNKNOWN)

    @property
    def governance_failures(self) -> tuple[GovernanceEvaluation, ...]:
        return tuple(e for e in self.governance_evaluations if e.status is GovernanceStatus.FAIL)

    @property
    def governance_unknowns(self) -> tuple[GovernanceEvaluation, ...]:
        return tuple(e for e in self.governance_evaluations if e.status is GovernanceStatus.UNKNOWN)

    def to_dict(self) -> dict[str, Any]:
        return {
            "hypothesis": asdict(self.hypothesis),
            "state": self.state.value,
            "evaluations": [
                {
                    **asdict(e),
                    "status": e.status.value,
                }
                for e in self.evaluations
            ],
            "governance_evaluations": [
                {
                    **asdict(e),
                    "category": e.category.value,
                    "status": e.status.value,
                }
                for e in self.governance_evaluations
            ],
            "governance_status": self.governance_status.value,
            "constraint_coverage": self.constraint_coverage,
            "governance_coverage": self.governance_coverage,
            "soft_compliance": self.soft_compliance,
            "bounded_confidence": self.bounded_confidence,
            "coherence_score": self.coherence_score,
        }


@dataclass(frozen=True)
class BindingReport:
    results: tuple[BindingResult, ...]
    best_supported_id: str | None
    metrics: Mapping[str, float]
    governance_context_sha256: str | None = None
    governance_policy: Mapping[str, Any] = field(default_factory=dict)
    trust: Mapping[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "results": [r.to_dict() for r in self.results],
            "best_supported_id": self.best_supported_id,
            "metrics": dict(self.metrics),
            "governance_context_sha256": self.governance_context_sha256,
            "governance_policy": dict(self.governance_policy),
            "trust": dict(self.trust) if self.trust is not None else None,
        }

    def sha256(self) -> str:
        from .receipts import sha256_receipt

        return sha256_receipt(self.to_dict())
