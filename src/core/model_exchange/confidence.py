"""Confidence aggregation and evidence coverage scoring."""

from __future__ import annotations

from typing import List, Set

from .models import ReasoningResult


def aggregate_confidence(results: List[ReasoningResult]) -> float:
    """Average normalised confidence across all adapter results."""
    if not results:
        return 0.0
    total = sum(r.normalized_confidence() for r in results)
    return total / len(results)


def downweight_for_contradictions(
    base: float,
    contradiction_score: float,
) -> float:
    """Reduce *base* confidence proportionally to contradictions.

    A contradiction_score of 1.0 halves the base confidence.
    """
    penalty = contradiction_score * 0.5
    return max(0.0, min(1.0, base * (1.0 - penalty)))


def score_evidence_coverage(results: List[ReasoningResult]) -> float:
    """Fraction of claims that have at least one citation."""
    total_claims = 0
    cited_claims = 0
    for r in results:
        for c in r.claims:
            total_claims += 1
            if c.citations:
                cited_claims += 1
    if total_claims == 0:
        return 1.0
    return cited_claims / total_claims
