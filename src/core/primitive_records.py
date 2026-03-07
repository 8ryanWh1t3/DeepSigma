"""Primitive Records — typed payload contracts for PrimitiveEnvelope.

Each record type corresponds to exactly one PrimitiveType and defines the
explicit field contract for that primitive's payload.  Use ``from_cerpa()``
to bridge from CERPA operational models to governance-grade records.

Usage:
    from core.primitive_records import ClaimRecord, wrap_record
    record = ClaimRecord.from_cerpa(cerpa_claim)
    envelope = wrap_record(record, source="my-module")
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .cerpa.models import ApplyResult, Claim, Event, Patch, Review
from .primitives import PrimitiveType


# ── ClaimRecord ────────────────────────────────────────────────


@dataclass
class ClaimRecord:
    """Typed payload for CLAIM envelopes."""

    PRIMITIVE_TYPE = PrimitiveType.CLAIM

    claim_id: str
    text: str
    domain: str
    source: str
    timestamp: str
    assumptions: List[str] = field(default_factory=list)
    confidence: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "claimId": self.claim_id,
            "text": self.text,
            "domain": self.domain,
            "source": self.source,
            "timestamp": self.timestamp,
        }
        if self.assumptions:
            d["assumptions"] = self.assumptions
        if self.confidence is not None:
            d["confidence"] = self.confidence
        if self.metadata:
            d["metadata"] = self.metadata
        return d

    @classmethod
    def from_cerpa(cls, claim: Claim) -> ClaimRecord:
        return cls(
            claim_id=claim.id,
            text=claim.text,
            domain=claim.domain,
            source=claim.source,
            timestamp=claim.timestamp,
            assumptions=claim.assumptions,
            metadata=claim.metadata,
        )


# ── EventRecord ────────────────────────────────────────────────


@dataclass
class EventRecord:
    """Typed payload for EVENT envelopes."""

    PRIMITIVE_TYPE = PrimitiveType.EVENT

    event_id: str
    text: str
    domain: str
    source: str
    timestamp: str
    observed_state: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "eventId": self.event_id,
            "text": self.text,
            "domain": self.domain,
            "source": self.source,
            "timestamp": self.timestamp,
        }
        if self.observed_state:
            d["observedState"] = self.observed_state
        if self.metadata:
            d["metadata"] = self.metadata
        return d

    @classmethod
    def from_cerpa(cls, event: Event) -> EventRecord:
        return cls(
            event_id=event.id,
            text=event.text,
            domain=event.domain,
            source=event.source,
            timestamp=event.timestamp,
            observed_state=event.observed_state,
            metadata=event.metadata,
        )


# ── ReviewRecord ───────────────────────────────────────────────


@dataclass
class ReviewRecord:
    """Typed payload for REVIEW envelopes."""

    PRIMITIVE_TYPE = PrimitiveType.REVIEW

    review_id: str
    claim_id: str
    event_id: str
    domain: str
    timestamp: str
    verdict: str
    rationale: str
    drift_detected: bool
    severity: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "reviewId": self.review_id,
            "claimId": self.claim_id,
            "eventId": self.event_id,
            "domain": self.domain,
            "timestamp": self.timestamp,
            "verdict": self.verdict,
            "rationale": self.rationale,
            "driftDetected": self.drift_detected,
        }
        if self.severity is not None:
            d["severity"] = self.severity
        if self.metadata:
            d["metadata"] = self.metadata
        return d

    @classmethod
    def from_cerpa(cls, review: Review) -> ReviewRecord:
        return cls(
            review_id=review.id,
            claim_id=review.claim_id,
            event_id=review.event_id,
            domain=review.domain,
            timestamp=review.timestamp,
            verdict=review.verdict,
            rationale=review.rationale,
            drift_detected=review.drift_detected,
            severity=review.severity,
            metadata=review.metadata,
        )


# ── PatchRecord ────────────────────────────────────────────────


@dataclass
class PatchRecord:
    """Typed payload for PATCH envelopes."""

    PRIMITIVE_TYPE = PrimitiveType.PATCH

    patch_id: str
    review_id: str
    domain: str
    timestamp: str
    action: str
    target: str
    description: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "patchId": self.patch_id,
            "reviewId": self.review_id,
            "domain": self.domain,
            "timestamp": self.timestamp,
            "action": self.action,
            "target": self.target,
            "description": self.description,
        }
        if self.metadata:
            d["metadata"] = self.metadata
        return d

    @classmethod
    def from_cerpa(cls, patch: Patch) -> PatchRecord:
        return cls(
            patch_id=patch.id,
            review_id=patch.review_id,
            domain=patch.domain,
            timestamp=patch.timestamp,
            action=patch.action,
            target=patch.target,
            description=patch.description,
            metadata=patch.metadata,
        )


# ── ApplyRecord ────────────────────────────────────────────────


@dataclass
class ApplyRecord:
    """Typed payload for APPLY envelopes."""

    PRIMITIVE_TYPE = PrimitiveType.APPLY

    apply_id: str
    patch_id: str
    domain: str
    timestamp: str
    success: bool
    new_state: Dict[str, Any] = field(default_factory=dict)
    updated_claims: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "applyId": self.apply_id,
            "patchId": self.patch_id,
            "domain": self.domain,
            "timestamp": self.timestamp,
            "success": self.success,
        }
        if self.new_state:
            d["newState"] = self.new_state
        if self.updated_claims:
            d["updatedClaims"] = self.updated_claims
        if self.metadata:
            d["metadata"] = self.metadata
        return d

    @classmethod
    def from_cerpa(cls, apply_result: ApplyResult) -> ApplyRecord:
        return cls(
            apply_id=apply_result.id,
            patch_id=apply_result.patch_id,
            domain=apply_result.domain,
            timestamp=apply_result.timestamp,
            success=apply_result.success,
            new_state=apply_result.new_state,
            updated_claims=apply_result.updated_claims,
            metadata=apply_result.metadata,
        )


# ── Registry ──────────────────────────────────────────────────


RECORD_TYPE_MAP: Dict[PrimitiveType, type] = {
    PrimitiveType.CLAIM: ClaimRecord,
    PrimitiveType.EVENT: EventRecord,
    PrimitiveType.REVIEW: ReviewRecord,
    PrimitiveType.PATCH: PatchRecord,
    PrimitiveType.APPLY: ApplyRecord,
}


def record_from_cerpa(primitive_type: PrimitiveType, cerpa_obj: Any) -> Any:
    """Create a record from a CERPA model object.

    Raises ``KeyError`` if *primitive_type* has no registered record class.
    """
    cls = RECORD_TYPE_MAP[primitive_type]
    return cls.from_cerpa(cerpa_obj)
