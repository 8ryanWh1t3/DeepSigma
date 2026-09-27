"""pyAltCog — deterministic Alternative Cognition operations for Deep Sigma."""

from .engine import AltCogEngine
from .lifecycle import LifecycleError, transition
from .metrics import (
    altcog_discovery_rate,
    dormant_alternative_recall,
    residual_conversion_rate,
    time_to_alternative_formation,
    weak_signal_promotion_rate,
)
from .models import (
    AltCogCandidatePacket,
    AlternativeKind,
    AuditEvent,
    CandidateScore,
    DiscriminatingEvidencePlan,
    DiscoveryEvent,
    DiscoveryFunction,
    DiscoverySurface,
    DormantAlternativeMonitor,
    EvidenceItem,
    ExceptionClusterCard,
    FrictionSignalRecord,
    MaturityState,
    Prediction,
    ProvenanceRef,
    ResidualEvidenceRecord,
    ValidationResult,
)
from .scoring import PromotionPolicy, score_candidate

__all__ = [
    "AltCogEngine",
    "AltCogCandidatePacket",
    "AlternativeKind",
    "AuditEvent",
    "CandidateScore",
    "DiscriminatingEvidencePlan",
    "DiscoveryEvent",
    "DiscoveryFunction",
    "DiscoverySurface",
    "DormantAlternativeMonitor",
    "EvidenceItem",
    "ExceptionClusterCard",
    "FrictionSignalRecord",
    "LifecycleError",
    "MaturityState",
    "Prediction",
    "PromotionPolicy",
    "ProvenanceRef",
    "ResidualEvidenceRecord",
    "ValidationResult",
    "altcog_discovery_rate",
    "dormant_alternative_recall",
    "residual_conversion_rate",
    "score_candidate",
    "time_to_alternative_formation",
    "transition",
    "weak_signal_promotion_rate",
]

__version__ = "0.1.0"

from .discovery import (
    SignalDraft,
    assumption_dependence,
    cross_domain_analogy,
    cross_source_contradiction,
    edge_case_accumulation,
    outcome_mismatch,
    repeated_exception,
    residual_evidence,
)
from .generation import HypothesisDraft, HypothesisProvider, TemplateHypothesisGenerator

__all__ += [
    "SignalDraft",
    "HypothesisDraft",
    "HypothesisProvider",
    "TemplateHypothesisGenerator",
    "assumption_dependence",
    "cross_domain_analogy",
    "cross_source_contradiction",
    "edge_case_accumulation",
    "outcome_mismatch",
    "repeated_exception",
    "residual_evidence",
]
