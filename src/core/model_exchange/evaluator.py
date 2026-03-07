"""Evaluator — aggregate multi-adapter results into an EvaluationResult."""

from __future__ import annotations

from typing import List

from .confidence import (
    aggregate_confidence,
    downweight_for_contradictions,
    score_evidence_coverage,
)
from .consensus import agreement_score as _agreement_score
from .contradiction import contradiction_score as _contradiction_score
from .models import EvaluationResult, ReasoningResult


def _novelty_score(results: List[ReasoningResult]) -> float:
    """Simple novelty heuristic — fraction of unique claim types present."""
    if not results:
        return 0.0
    all_types: set = set()
    total = 0
    for r in results:
        for c in r.claims:
            all_types.add(c.claim_type)
            total += 1
    if total == 0:
        return 0.0
    return min(1.0, len(all_types) / max(total, 1))


def _escalation(
    agreement: float,
    contradiction: float,
    evidence_coverage: float,
    results: List[ReasoningResult],
) -> str:
    """Determine recommended escalation level."""
    # malformed guard
    if not results or all(len(r.claims) == 0 for r in results):
        return "reject"
    # high contradiction or very low evidence
    if contradiction >= 0.5 or evidence_coverage < 0.3:
        return "authority-review"
    # medium disagreement
    if agreement < 0.5 or contradiction >= 0.2:
        return "human-review"
    # strong agreement — still model-produced, so draft only
    return "accept-for-drafting"


def evaluate_results(results: List[ReasoningResult]) -> EvaluationResult:
    """Evaluate a list of adapter ReasoningResults into a single summary."""
    if not results:
        return EvaluationResult(
            request_id="unknown",
            adapter_results=[],
            agreement_score=0.0,
            contradiction_score=0.0,
            novelty_score=0.0,
            evidence_coverage_score=0.0,
            drift_likelihood=1.0,
            recommended_escalation="reject",
            notes=["No adapter results to evaluate"],
        )

    request_id = results[0].request_id
    agree = _agreement_score(results)
    contra = _contradiction_score(results)
    novelty = _novelty_score(results)
    evidence = score_evidence_coverage(results)

    # drift likelihood: average of contradiction, (1 - agreement), (1 - evidence)
    drift = (contra + (1.0 - agree) + (1.0 - evidence)) / 3.0

    escalation = _escalation(agree, contra, evidence, results)

    notes: List[str] = []
    if contra >= 0.5:
        notes.append("High contradiction detected across adapters")
    if evidence < 0.5:
        notes.append("Low evidence coverage in model claims")

    return EvaluationResult(
        request_id=request_id,
        adapter_results=results,
        agreement_score=round(agree, 4),
        contradiction_score=round(contra, 4),
        novelty_score=round(novelty, 4),
        evidence_coverage_score=round(evidence, 4),
        drift_likelihood=round(drift, 4),
        recommended_escalation=escalation,
        notes=notes,
    )
