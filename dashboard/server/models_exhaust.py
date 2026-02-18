"""Pydantic models for the Exhaust Inbox system.

Defines EpisodeEvent, DecisionEpisode, RefinedEpisode, and all
sub-models for Truth/Reasoning/Memory buckets, drift signals,
and coherence scoring.
"""
from __future__ import annotations

import hashlib
from enum import Enum
from typing import Any, Dict, List, Optional

try:
    from pydantic import BaseModel, Field
except ImportError:
    raise ImportError("pydantic is required: pip install pydantic>=2.0")


# ── Enums ────────────────────────────────────────────────────────

class EventType(str, Enum):
    prompt = "prompt"
    completion = "completion"
    tool = "tool"
    metric = "metric"
    error = "error"


class Source(str, Enum):
    langchain = "langchain"
    openai = "openai"
    azure = "azure"
    anthropic = "anthropic"
    manual = "manual"


class DriftSeverity(str, Enum):
    green = "green"
    yellow = "yellow"
    red = "red"


class DriftType(str, Enum):
    contradiction = "contradiction"
    missing_policy = "missing_policy"
    low_claim_coverage = "low_claim_coverage"


class ItemStatus(str, Enum):
    pending = "pending"
    accepted = "accepted"
    rejected = "rejected"
    edited = "edited"


class ConfidenceTier(str, Enum):
    auto_commit = "auto_commit"
    review_required = "review_required"
    hold = "hold"


class Grade(str, Enum):
    A = "A"
    B = "B"
    C = "C"
    D = "D"


# ── Helpers ──────────────────────────────────────────────────────

def _stable_id(*parts: str) -> str:
    """Deterministic SHA-256 based ID from string parts."""
    raw = "|".join(str(p) for p in parts)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _now_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


# ── Episode Event (raw ingest) ───────────────────────────────────

class EpisodeEvent(BaseModel):
    """A single raw event from an AI interaction."""
    event_id: str = Field(default="", description="Deterministic ID; computed if blank")
    episode_id: str = Field(..., description="Groups events into an episode")
    event_type: EventType
    timestamp: str = Field(default="", description="ISO 8601; auto-filled if blank")
    source: Source = Source.manual
    user_hash: str = Field(default="anon", description="Hashed user ID, no PII")
    session_id: str = Field(default="")
    project: str = Field(default="default")
    team: str = Field(default="default")
    payload: Dict[str, Any] = Field(default_factory=dict)

    def model_post_init(self, __context: Any) -> None:
        if not self.timestamp:
            self.timestamp = _now_iso()
        if not self.event_id:
            self.event_id = _stable_id(
                self.episode_id, self.event_type.value, self.timestamp
            )


# ── Decision Episode (assembled) ─────────────────────────────────

class DecisionEpisode(BaseModel):
    """Assembled episode from grouped events."""
    episode_id: str
    events: List[EpisodeEvent] = Field(default_factory=list)
    source: Source = Source.manual
    user_hash: str = "anon"
    session_id: str = ""
    project: str = "default"
    team: str = "default"
    started_at: str = ""
    ended_at: str = ""
    status: str = "assembled"
    coherence_score: Optional[float] = None
    grade: Optional[Grade] = None
    refined: bool = False


# ── Truth / Reasoning / Memory items ─────────────────────────────

class TruthItem(BaseModel):
    """Atomic claim extracted from exhaust."""
    item_id: str = ""
    claim: str
    evidence: str = ""
    confidence: float = Field(0.5, ge=0.0, le=1.0)
    truth_type: str = "empirical"
    entity: str = ""
    property_name: str = ""
    value: str = ""
    unit: str = ""
    support_count: int = 1
    provenance: List[str] = Field(default_factory=list)
    status: ItemStatus = ItemStatus.pending

    def model_post_init(self, __context: Any) -> None:
        if not self.item_id:
            self.item_id = _stable_id("truth", self.claim)


class ReasoningItem(BaseModel):
    """Decision/assumption/rationale extracted from exhaust."""
    item_id: str = ""
    decision: str
    rationale: str = ""
    assumptions: List[str] = Field(default_factory=list)
    alternatives: List[str] = Field(default_factory=list)
    confidence: float = Field(0.5, ge=0.0, le=1.0)
    provenance: List[str] = Field(default_factory=list)
    status: ItemStatus = ItemStatus.pending

    def model_post_init(self, __context: Any) -> None:
        if not self.item_id:
            self.item_id = _stable_id("reasoning", self.decision)


class MemoryItem(BaseModel):
    """Entity/relation/artifact extracted from exhaust."""
    item_id: str = ""
    entity: str
    relation: str = ""
    target: str = ""
    context: str = ""
    artifact_type: str = ""
    confidence: float = Field(0.5, ge=0.0, le=1.0)
    provenance: List[str] = Field(default_factory=list)
    status: ItemStatus = ItemStatus.pending

    def model_post_init(self, __context: Any) -> None:
        if not self.item_id:
            self.item_id = _stable_id("memory", self.entity, self.relation, self.target)


# ── Drift Signal ─────────────────────────────────────────────────

class DriftSignal(BaseModel):
    """Detected drift from extraction/comparison."""
    drift_id: str = ""
    drift_type: DriftType
    severity: DriftSeverity = DriftSeverity.green
    fingerprint: str = ""
    description: str = ""
    entity: str = ""
    property_name: str = ""
    expected_value: str = ""
    actual_value: str = ""
    episode_id: str = ""
    recommended_patch: Dict[str, Any] = Field(default_factory=dict)
    timestamp: str = ""

    def model_post_init(self, __context: Any) -> None:
        if not self.timestamp:
            self.timestamp = _now_iso()
        if not self.fingerprint:
            self.fingerprint = _stable_id(
                self.drift_type.value, self.entity, self.property_name
            )
        if not self.drift_id:
            self.drift_id = _stable_id("drift", self.fingerprint, self.timestamp)


# ── Coherence Score ──────────────────────────────────────────────

class CoherenceBreakdown(BaseModel):
    """Dimensional breakdown of coherence scoring."""
    claim_coverage: float = Field(0.0, ge=0.0, le=1.0)
    evidence_quality: float = Field(0.0, ge=0.0, le=1.0)
    reasoning_completeness: float = Field(0.0, ge=0.0, le=1.0)
    memory_linkage: float = Field(0.0, ge=0.0, le=1.0)
    policy_adherence: float = Field(0.0, ge=0.0, le=1.0)


# ── Refined Episode ──────────────────────────────────────────────

class RefinedEpisode(BaseModel):
    """Result of running the refiner on a DecisionEpisode."""
    episode_id: str
    truth: List[TruthItem] = Field(default_factory=list)
    reasoning: List[ReasoningItem] = Field(default_factory=list)
    memory: List[MemoryItem] = Field(default_factory=list)
    drift_signals: List[DriftSignal] = Field(default_factory=list)
    coherence_score: float = 0.0
    grade: Grade = Grade.D
    breakdown: CoherenceBreakdown = Field(default_factory=CoherenceBreakdown)
    confidence_tier: ConfidenceTier = ConfidenceTier.hold
    refined_at: str = ""
    committed: bool = False

    def model_post_init(self, __context: Any) -> None:
        if not self.refined_at:
            self.refined_at = _now_iso()
        # Auto-compute tier from score
        if self.coherence_score >= 85:
            self.confidence_tier = ConfidenceTier.auto_commit
            self.grade = Grade.A
        elif self.coherence_score >= 75:
            self.confidence_tier = ConfidenceTier.review_required
            self.grade = Grade.B
        elif self.coherence_score >= 65:
            self.confidence_tier = ConfidenceTier.review_required
            self.grade = Grade.C
        else:
            self.confidence_tier = ConfidenceTier.hold
            self.grade = Grade.D


# ── API request/response models ──────────────────────────────────

class ItemAction(BaseModel):
    """Request body for accept/reject/edit a single item."""
    item_id: str
    bucket: str = Field(..., description="truth | reasoning | memory")
    action: str = Field(..., description="accept | reject | edit")
    edited_data: Optional[Dict[str, Any]] = None


class EpisodeListParams(BaseModel):
    """Query parameters for listing episodes."""
    project: Optional[str] = None
    team: Optional[str] = None
    source: Optional[Source] = None
    drift_only: bool = False
    low_confidence_only: bool = False
    min_score: Optional[float] = None
    max_score: Optional[float] = None
    limit: int = Field(50, ge=1, le=500)
    offset: int = Field(0, ge=0)


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = "ok"
    events_count: int = 0
    episodes_count: int = 0
    refined_count: int = 0
    drift_count: int = 0
