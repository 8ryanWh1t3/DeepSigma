from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class MaturityState(str, Enum):
    AC0_NOISE = "AC0"
    AC1_ANOMALY = "AC1"
    AC2_WEAK_SIGNAL = "AC2"
    AC3_CANDIDATE_PATTERN = "AC3"
    AC4_ALTERNATIVE_HYPOTHESIS = "AC4"
    AC5_SCORED_ALTERNATIVE = "AC5"
    AC6_OPERATIONAL_ALTERNATIVE = "AC6"
    AC7_PROMOTED_MODEL = "AC7"
    AC8_ARCHIVED_WITH_TRIGGER = "AC8"


class DiscoverySurface(str, Enum):
    OUTCOME_MISMATCH = "outcome_mismatch"
    RESIDUAL_EVIDENCE = "residual_evidence"
    REPEATED_EXCEPTION = "repeated_exception"
    CROSS_SOURCE_CONTRADICTION = "cross_source_contradiction"
    ASSUMPTION_DEPENDENCE = "assumption_dependence"
    EDGE_CASE_ACCUMULATION = "edge_case_accumulation"
    CROSS_DOMAIN_ANALOGY = "cross_domain_analogy"


class AlternativeKind(str, Enum):
    BENIGN = "benign"
    STRUCTURAL = "structural"
    ADVERSARIAL = "adversarial"
    INSTRUMENTATION_ERROR = "instrumentation_error"
    TIMING = "timing"
    CROSS_DOMAIN = "cross_domain"
    UNKNOWN_MODEL = "unknown_model"


class DiscoveryFunction(str, Enum):
    F13_FRICTION_SIGNAL_CAPTURE = "ALT-F13"
    F14_RESIDUAL_DETECTION = "ALT-F14"
    F15_EXCEPTION_CLUSTERING = "ALT-F15"
    F16_ALTERNATIVE_CANDIDATE_PROMOTION = "ALT-F16"
    F17_DISCRIMINATING_EVIDENCE_PLANNER = "ALT-F17"
    F18_DORMANT_ALTERNATIVE_MONITORING = "ALT-F18"


class DiscoveryEvent(str, Enum):
    E13_OUTCOME_MISMATCH_DETECTED = "ALT-E13"
    E14_RESIDUAL_EVIDENCE_IDENTIFIED = "ALT-E14"
    E15_EXCEPTION_PATTERN_FORMED = "ALT-E15"
    E16_ALTCOG_CANDIDATE_CREATED = "ALT-E16"
    E17_CANDIDATE_PROMOTED_OPERATIONAL = "ALT-E17"
    E18_DORMANT_ALTERNATIVE_REACTIVATED = "ALT-E18"


@dataclass(frozen=True)
class ProvenanceRef:
    source: str
    locator: str = ""
    sha256: str = ""
    observed_at: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class EvidenceItem:
    id: str
    statement: str
    source: str
    supports_alternative: bool = True
    confidence: float = 1.0
    provenance: List[ProvenanceRef] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Prediction:
    variable: str
    dominant_expected: str
    alternative_expected: str
    observation_window: str = ""
    success_condition: str = ""


@dataclass
class FrictionSignalRecord:
    id: str
    stream_id: str
    surface: DiscoverySurface
    statement: str
    source: str
    detected_at: str
    maturity: MaturityState = MaturityState.AC1_ANOMALY
    strength: float = 0.5
    tags: List[str] = field(default_factory=list)
    domain: str = ""
    provenance: List[ProvenanceRef] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ResidualEvidenceRecord:
    id: str
    stream_id: str
    dominant_model: str
    observed: str
    explained: str
    residual: str
    detected_at: str
    signal_id: str = ""
    provenance: List[ProvenanceRef] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExceptionClusterCard:
    id: str
    stream_id: str
    signal_ids: List[str]
    created_at: str
    centroid_terms: List[str] = field(default_factory=list)
    surfaces: List[DiscoverySurface] = field(default_factory=list)
    domains: List[str] = field(default_factory=list)
    strength: float = 0.0
    maturity: MaturityState = MaturityState.AC3_CANDIDATE_PATTERN
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CandidateScore:
    evidence: float
    distinct_prediction: float
    falsifiability: float
    mission_relevance: float
    contradiction_resilience: float
    ownership: float
    revisitability: float
    total: float
    rationale: List[str] = field(default_factory=list)


@dataclass
class AltCogCandidatePacket:
    id: str
    stream_id: str
    cluster_id: str
    dominant_model: str
    hypothesis: str
    created_at: str
    kind: AlternativeKind = AlternativeKind.STRUCTURAL
    maturity: MaturityState = MaturityState.AC4_ALTERNATIVE_HYPOTHESIS
    signal_ids: List[str] = field(default_factory=list)
    evidence: List[EvidenceItem] = field(default_factory=list)
    predictions: List[Prediction] = field(default_factory=list)
    falsification_conditions: List[str] = field(default_factory=list)
    mission_relevance: float = 0.0
    owner: str = ""
    revisit_trigger: str = ""
    score: Optional[CandidateScore] = None
    validation: Optional["ValidationResult"] = None
    archived_reason: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class EvidenceRequest:
    id: str
    variable: str
    request: str
    dominant_prediction: str
    alternative_prediction: str
    decision_rule: str
    priority: int = 1


@dataclass
class DiscriminatingEvidencePlan:
    id: str
    candidate_id: str
    created_at: str
    requests: List[EvidenceRequest]
    falsification_condition: str
    owner: str = ""
    due_at: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DormantAlternativeMonitor:
    id: str
    candidate_id: str
    archived_at: str
    trigger_terms: List[str]
    revisit_trigger: str
    active: bool = True
    last_checked_at: str = ""
    reactivated_at: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ValidationResult:
    candidate_id: str
    observed_at: str
    verdict: str  # alternative_supported | dominant_supported | inconclusive
    rationale: str
    evidence_ids: List[str] = field(default_factory=list)
    confidence: float = 0.0


@dataclass(frozen=True)
class AuditEvent:
    id: str
    event_type: str
    occurred_at: str
    subject_id: str
    payload: Dict[str, Any]
    previous_hash: str
    event_hash: str
