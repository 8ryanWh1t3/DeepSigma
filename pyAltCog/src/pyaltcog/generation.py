from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Protocol

from .models import AlternativeKind, ExceptionClusterCard


@dataclass(frozen=True)
class HypothesisDraft:
    kind: AlternativeKind
    hypothesis: str
    rationale: str


class HypothesisProvider(Protocol):
    """Optional generation seam. Providers generate drafts, never maturity promotion."""

    def generate(self, cluster: ExceptionClusterCard, dominant_model: str) -> list[HypothesisDraft]: ...


class TemplateHypothesisGenerator:
    """Offline deterministic generator for structured alternative categories.

    These are prompts-to-investigate, not evidence and not validated AltCogs.
    """

    _LABELS = {
        AlternativeKind.BENIGN: "A benign environmental or contextual condition explains the observed friction",
        AlternativeKind.STRUCTURAL: "A recurring structural mechanism explains the observed friction",
        AlternativeKind.ADVERSARIAL: "An intentional adversarial mechanism could explain the observed friction",
        AlternativeKind.INSTRUMENTATION_ERROR: "Instrumentation, measurement, or data-pipeline error explains the observed friction",
        AlternativeKind.TIMING: "Timing, ordering, or latency explains the observed friction",
        AlternativeKind.CROSS_DOMAIN: "A mechanism analogous to another domain explains the observed friction",
        AlternativeKind.UNKNOWN_MODEL: "The current model class is incomplete; preserve an unknown-model placeholder",
    }

    def __init__(self, kinds: Iterable[AlternativeKind] | None = None) -> None:
        self.kinds = list(kinds) if kinds is not None else list(AlternativeKind)

    def generate(self, cluster: ExceptionClusterCard, dominant_model: str) -> list[HypothesisDraft]:
        context = ", ".join(cluster.centroid_terms[:8]) or "clustered friction"
        return [
            HypothesisDraft(
                kind=kind,
                hypothesis=f"{self._LABELS[kind]} [{context}].",
                rationale=f"Candidate category '{kind.value}' generated to challenge dominant model: {dominant_model}",
            )
            for kind in self.kinds
        ]
