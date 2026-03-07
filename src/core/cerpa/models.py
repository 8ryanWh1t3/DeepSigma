"""CERPA models — cycle-focused primitives for the adaptation loop.

Claim -> Event -> Review -> Patch -> Apply

These are lighter than the archival canonical primitives in core.primitives.
Use cerpa.mappers to bridge between CERPA and existing structures.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Claim:
    """An asserted truth or commitment to be monitored."""

    id: str
    text: str
    domain: str
    source: str
    timestamp: str
    assumptions: List[str] = field(default_factory=list)
    authority: Optional[str] = None
    provenance: List[Dict[str, Any]] = field(default_factory=list)
    related_ids: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "id": self.id,
            "text": self.text,
            "domain": self.domain,
            "source": self.source,
            "timestamp": self.timestamp,
        }
        if self.assumptions:
            d["assumptions"] = self.assumptions
        if self.authority is not None:
            d["authority"] = self.authority
        if self.provenance:
            d["provenance"] = self.provenance
        if self.related_ids:
            d["related_ids"] = self.related_ids
        if self.metadata:
            d["metadata"] = self.metadata
        return d


@dataclass
class Event:
    """An observable occurrence that may affect a Claim."""

    id: str
    text: str
    domain: str
    source: str
    timestamp: str
    observed_state: Dict[str, Any] = field(default_factory=dict)
    provenance: List[Dict[str, Any]] = field(default_factory=list)
    related_ids: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "id": self.id,
            "text": self.text,
            "domain": self.domain,
            "source": self.source,
            "timestamp": self.timestamp,
        }
        if self.observed_state:
            d["observed_state"] = self.observed_state
        if self.provenance:
            d["provenance"] = self.provenance
        if self.related_ids:
            d["related_ids"] = self.related_ids
        if self.metadata:
            d["metadata"] = self.metadata
        return d


@dataclass
class Review:
    """Evaluation of a Claim against an Event."""

    id: str
    claim_id: str
    event_id: str
    domain: str
    timestamp: str
    verdict: str
    rationale: str
    drift_detected: bool
    severity: Optional[str] = None
    source: str = ""
    provenance: List[Dict[str, Any]] = field(default_factory=list)
    related_ids: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "id": self.id,
            "claim_id": self.claim_id,
            "event_id": self.event_id,
            "domain": self.domain,
            "timestamp": self.timestamp,
            "verdict": self.verdict,
            "rationale": self.rationale,
            "drift_detected": self.drift_detected,
        }
        if self.severity is not None:
            d["severity"] = self.severity
        if self.source:
            d["source"] = self.source
        if self.provenance:
            d["provenance"] = self.provenance
        if self.related_ids:
            d["related_ids"] = self.related_ids
        if self.metadata:
            d["metadata"] = self.metadata
        return d


@dataclass
class Patch:
    """Corrective action generated from a Review."""

    id: str
    review_id: str
    domain: str
    timestamp: str
    action: str
    target: str
    description: str
    source: str = ""
    provenance: List[Dict[str, Any]] = field(default_factory=list)
    related_ids: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "id": self.id,
            "review_id": self.review_id,
            "domain": self.domain,
            "timestamp": self.timestamp,
            "action": self.action,
            "target": self.target,
            "description": self.description,
        }
        if self.source:
            d["source"] = self.source
        if self.provenance:
            d["provenance"] = self.provenance
        if self.related_ids:
            d["related_ids"] = self.related_ids
        if self.metadata:
            d["metadata"] = self.metadata
        return d


@dataclass
class ApplyResult:
    """Outcome of applying a Patch."""

    id: str
    patch_id: str
    domain: str
    timestamp: str
    success: bool
    new_state: Dict[str, Any] = field(default_factory=dict)
    updated_claims: List[str] = field(default_factory=list)
    source: str = ""
    provenance: List[Dict[str, Any]] = field(default_factory=list)
    related_ids: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "id": self.id,
            "patch_id": self.patch_id,
            "domain": self.domain,
            "timestamp": self.timestamp,
            "success": self.success,
        }
        if self.new_state:
            d["new_state"] = self.new_state
        if self.updated_claims:
            d["updated_claims"] = self.updated_claims
        if self.source:
            d["source"] = self.source
        if self.provenance:
            d["provenance"] = self.provenance
        if self.related_ids:
            d["related_ids"] = self.related_ids
        if self.metadata:
            d["metadata"] = self.metadata
        return d


@dataclass
class CerpaCycle:
    """A complete CERPA adaptation cycle."""

    cycle_id: str
    domain: str
    claim: Claim
    event: Event
    review: Review
    patch: Optional[Patch] = None
    apply_result: Optional[ApplyResult] = None
    status: str = "aligned"
    started_at: str = ""
    completed_at: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "cycle_id": self.cycle_id,
            "domain": self.domain,
            "status": self.status,
            "claim": self.claim.to_dict(),
            "event": self.event.to_dict(),
            "review": self.review.to_dict(),
        }
        if self.patch is not None:
            d["patch"] = self.patch.to_dict()
        if self.apply_result is not None:
            d["apply_result"] = self.apply_result.to_dict()
        if self.started_at:
            d["started_at"] = self.started_at
        if self.completed_at:
            d["completed_at"] = self.completed_at
        if self.metadata:
            d["metadata"] = self.metadata
        return d
