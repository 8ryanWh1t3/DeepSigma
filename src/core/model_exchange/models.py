"""Typed data contracts for the Model Exchange Engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


MODEL_EXCHANGE_BOUNDARY_NOTE = (
    "Models produce exhaust. Deep Sigma produces judgment."
)


@dataclass
class ModelMeta:
    """Metadata describing the model that produced a reasoning result."""

    provider: str
    model: str
    adapter_name: str
    version: Optional[str] = None
    runtime: Optional[str] = None
    created_at: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "provider": self.provider,
            "model": self.model,
            "adapterName": self.adapter_name,
        }
        if self.version is not None:
            d["version"] = self.version
        if self.runtime is not None:
            d["runtime"] = self.runtime
        if self.created_at is not None:
            d["createdAt"] = self.created_at
        if self.extra:
            d["extra"] = self.extra
        return d


@dataclass
class CandidateClaim:
    """A single claim produced by a model adapter."""

    claim_id: str
    text: str
    claim_type: str
    confidence: float
    citations: List[str] = field(default_factory=list)
    contradiction_ids: List[str] = field(default_factory=list)
    ttl_seconds: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "claimId": self.claim_id,
            "text": self.text,
            "claimType": self.claim_type,
            "confidence": self.confidence,
        }
        if self.citations:
            d["citations"] = self.citations
        if self.contradiction_ids:
            d["contradictionIds"] = self.contradiction_ids
        if self.ttl_seconds is not None:
            d["ttlSeconds"] = self.ttl_seconds
        return d


@dataclass
class ReasoningStep:
    """A single step in a model's reasoning chain."""

    step_id: str
    kind: str
    text: str
    evidence_refs: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "stepId": self.step_id,
            "kind": self.kind,
            "text": self.text,
        }
        if self.evidence_refs:
            d["evidenceRefs"] = self.evidence_refs
        return d


@dataclass
class ContradictionRecord:
    """A detected contradiction between two claims or reasoning steps."""

    contradiction_id: str
    severity: str
    left_ref: str
    right_ref: str
    note: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "contradictionId": self.contradiction_id,
            "severity": self.severity,
            "leftRef": self.left_ref,
            "rightRef": self.right_ref,
            "note": self.note,
        }


@dataclass
class ReasoningResult:
    """Complete output from a single model adapter invocation."""

    request_id: str
    adapter_name: str
    claims: List[CandidateClaim]
    reasoning: List[ReasoningStep]
    confidence: float
    citations: List[str]
    contradictions: List[ContradictionRecord]
    model_meta: ModelMeta
    ttl: Optional[str] = None
    warnings: List[str] = field(default_factory=list)
    raw_text: Optional[str] = None
    raw_json: Optional[Dict[str, Any]] = None

    # -- helpers --

    def normalized_confidence(self) -> float:
        """Return confidence clamped to [0.0, 1.0]."""
        return max(0.0, min(1.0, self.confidence))

    def has_high_severity_contradictions(self) -> bool:
        return any(c.severity == "high" for c in self.contradictions)

    def claims_by_type(self, claim_type: str) -> List[CandidateClaim]:
        return [c for c in self.claims if c.claim_type == claim_type]

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "requestId": self.request_id,
            "adapterName": self.adapter_name,
            "claims": [c.to_dict() for c in self.claims],
            "reasoning": [r.to_dict() for r in self.reasoning],
            "confidence": self.confidence,
            "citations": self.citations,
            "contradictions": [c.to_dict() for c in self.contradictions],
            "modelMeta": self.model_meta.to_dict(),
        }
        if self.ttl is not None:
            d["ttl"] = self.ttl
        if self.warnings:
            d["warnings"] = self.warnings
        if self.raw_text is not None:
            d["rawText"] = self.raw_text
        if self.raw_json is not None:
            d["rawJson"] = self.raw_json
        return d


@dataclass
class EvaluationResult:
    """Aggregated evaluation across one or more adapter results."""

    request_id: str
    adapter_results: List[ReasoningResult]
    agreement_score: float
    contradiction_score: float
    novelty_score: float
    evidence_coverage_score: float
    drift_likelihood: float
    recommended_escalation: str
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "requestId": self.request_id,
            "adapterResults": [r.to_dict() for r in self.adapter_results],
            "agreementScore": self.agreement_score,
            "contradictionScore": self.contradiction_score,
            "noveltyScore": self.novelty_score,
            "evidenceCoverageScore": self.evidence_coverage_score,
            "driftLikelihood": self.drift_likelihood,
            "recommendedEscalation": self.recommended_escalation,
            "notes": self.notes,
        }
