"""Model Exchange Engine — governed multi-model reasoning for Deep Sigma.

Deep Sigma is the reactor, boundary, and memory system.
Models are interchangeable cognitive thrusters.
Models produce exhaust. Deep Sigma produces judgment.
"""

from __future__ import annotations

from .base_adapter import BaseModelAdapter
from .confidence import (
    aggregate_confidence,
    downweight_for_contradictions,
    score_evidence_coverage,
)
from .consensus import agreement_score, claim_overlap_score, reasoning_overlap_score
from .contradiction import contradiction_score, detect_claim_contradictions
from .engine import ModelExchangeEngine
from .evaluator import evaluate_results
from .models import (
    CandidateClaim,
    ContradictionRecord,
    EvaluationResult,
    ModelMeta,
    ReasoningResult,
    ReasoningStep,
)
from .registry import AdapterRegistry
from .router import AdapterRouter
from .ttl import compute_claim_ttl_seconds, ttl_from_packet

__all__ = [
    "AdapterRegistry",
    "AdapterRouter",
    "BaseModelAdapter",
    "CandidateClaim",
    "ContradictionRecord",
    "EvaluationResult",
    "ModelExchangeEngine",
    "ModelMeta",
    "ReasoningResult",
    "ReasoningStep",
    "aggregate_confidence",
    "agreement_score",
    "claim_overlap_score",
    "compute_claim_ttl_seconds",
    "contradiction_score",
    "detect_claim_contradictions",
    "downweight_for_contradictions",
    "evaluate_results",
    "reasoning_overlap_score",
    "score_evidence_coverage",
    "ttl_from_packet",
]
