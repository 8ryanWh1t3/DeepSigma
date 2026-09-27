"""Deep Sigma Voice Semantic Adapter (VSA)."""

from .models import (
    Assumption,
    AuthorityStatus,
    Claim,
    Confidence,
    Entity,
    Event,
    Evidence,
    GovernanceEnvelope,
    Intent,
    Modality,
    ProvenanceRef,
    Relationship,
    SemanticPacket,
    Transcript,
    TranscriptSegment,
)
from .pipeline import VoiceSemanticAdapter

__all__ = [
    "Assumption",
    "AuthorityStatus",
    "Claim",
    "Confidence",
    "Entity",
    "Event",
    "Evidence",
    "GovernanceEnvelope",
    "Intent",
    "Modality",
    "ProvenanceRef",
    "Relationship",
    "SemanticPacket",
    "Transcript",
    "TranscriptSegment",
    "VoiceSemanticAdapter",
]

__version__ = "0.1.0"
