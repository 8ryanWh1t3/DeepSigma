from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..models import ContrastResult


@dataclass(frozen=True)
class SemanticFinding:
    kind: str
    key: str
    severity: str
    explanation: str
    source: str = "deepsigma-contrast"


class ResonatorAdapter:
    """Projects contrast output into RESONATOR-style semantic findings."""

    def analyze(self, result: ContrastResult) -> list[SemanticFinding]:
        findings: list[SemanticFinding] = []

        for d in result.assumption_deltas:
            findings.append(SemanticFinding(
                kind="ASSUMPTION_DELTA",
                key=d.key,
                severity=self._severity(d.materiality),
                explanation=d.rationale,
            ))

        for d in result.outcome_deltas:
            findings.append(SemanticFinding(
                kind="OUTCOME_DELTA",
                key=d.key,
                severity=self._severity(d.materiality),
                explanation=d.rationale,
            ))

        for d in result.evidence_deltas:
            kind = "CONTRADICTION" if d.kind == "EVIDENCE_STANCE_CHANGED" else "EVIDENCE_DELTA"
            findings.append(SemanticFinding(
                kind=kind,
                key=d.key,
                severity=self._severity(d.materiality),
                explanation=d.rationale,
            ))

        for d in result.metadata_deltas:
            findings.append(SemanticFinding(
                kind="CONTEXT_GAP",
                key=d.key,
                severity=self._severity(d.materiality),
                explanation=d.rationale,
            ))

        return findings

    @staticmethod
    def _severity(materiality: float) -> str:
        if materiality >= 0.85:
            return "HIGH"
        if materiality >= 0.50:
            return "MEDIUM"
        return "LOW"
