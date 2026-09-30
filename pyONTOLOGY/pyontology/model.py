from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Iterable


@dataclass(slots=True)
class ModuleManifest:
    module_id: str
    name: str
    version: str = "0.0.0"
    namespace: str | None = None
    owner: str | None = None
    authority: int = 0
    role: str = "module"  # foundation | extension | module
    extension_of: str | None = None
    dependencies: list[str] = field(default_factory=list)
    description: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class TermRecord:
    uri: str
    module_id: str
    kinds: tuple[str, ...]
    label: str
    alt_labels: tuple[str, ...] = ()
    definition: str | None = None
    comment: str | None = None
    namespace: str | None = None
    local_name: str | None = None
    fingerprint: str | None = None

    def all_labels(self) -> tuple[str, ...]:
        seen: list[str] = []
        for value in (self.label, *self.alt_labels):
            if value and value not in seen:
                seen.append(value)
        return tuple(seen)


@dataclass(slots=True)
class SemanticCandidate:
    uri: str
    module_id: str
    label: str
    kinds: tuple[str, ...]
    score: float
    reason: str
    definition: str | None = None


@dataclass(slots=True)
class ConceptProposal:
    requested_label: str
    requested_kind: str
    target_module: str
    recommended_action: str  # REUSE | LINK | SPECIALIZE | CREATE | REVIEW
    candidates: list[SemanticCandidate] = field(default_factory=list)
    rationale: str = ""


@dataclass(slots=True)
class Collision:
    normalized_label: str
    terms: list[TermRecord]
    severity: str
    rationale: str


@dataclass(slots=True)
class BridgeSuggestion:
    source_uri: str
    target_uri: str
    source_module: str
    target_module: str
    relation: str
    score: float
    rationale: str
    status: str = "PROPOSED"


@dataclass(slots=True)
class ValidationFinding:
    severity: str
    code: str
    message: str
    module_id: str | None = None
    uri: str | None = None


@dataclass(slots=True)
class ValidationReport:
    findings: list[ValidationFinding] = field(default_factory=list)

    @property
    def errors(self) -> list[ValidationFinding]:
        return [f for f in self.findings if f.severity == "ERROR"]

    @property
    def warnings(self) -> list[ValidationFinding]:
        return [f for f in self.findings if f.severity == "WARNING"]

    @property
    def ok(self) -> bool:
        return not self.errors

    def extend(self, items: Iterable[ValidationFinding]) -> None:
        self.findings.extend(items)


@dataclass(slots=True)
class DiffReport:
    old_fingerprint: str
    new_fingerprint: str
    added_triples: int
    removed_triples: int
    added_terms: list[str]
    removed_terms: list[str]
    changed_terms: list[str]
