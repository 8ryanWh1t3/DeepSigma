"""JRM core types — enums and dataclasses for the Judgment Refinement Module."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class EventType(str, Enum):
    """Source event types JRM can process."""

    SURICATA_ALERT = "suricata_alert"
    SURICATA_DNS = "suricata_dns"
    SURICATA_HTTP = "suricata_http"
    SURICATA_FLOW = "suricata_flow"
    SNORT_ALERT = "snort_alert"
    AGENT_PROMPT = "agent_prompt"
    AGENT_TOOL_CALL = "agent_tool_call"
    AGENT_RESPONSE = "agent_response"
    AGENT_GUARDRAIL = "agent_guardrail"
    MALFORMED = "malformed"
    GENERIC = "generic"


class Severity(str, Enum):
    """Severity levels for JRM events."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class DecisionLane(str, Enum):
    """Pipeline decision lanes for reasoning stage."""

    LOG_ONLY = "LOG_ONLY"
    NOTIFY = "NOTIFY"
    QUEUE_PATCH = "QUEUE_PATCH"
    REQUIRE_REVIEW = "REQUIRE_REVIEW"


class JRMDriftType(str, Enum):
    """JRM-specific drift types (local coherence)."""

    FP_SPIKE = "FP_SPIKE"
    MISSING_MAPPING = "MISSING_MAPPING"
    STALE_LOGIC = "STALE_LOGIC"
    ASSUMPTION_EXPIRED = "ASSUMPTION_EXPIRED"


# ── Dataclasses ──────────────────────────────────────────────────


@dataclass
class JRMEvent:
    """Normalized JRM event — output of an adapter."""

    event_id: str
    source_system: str
    event_type: EventType
    timestamp: str
    severity: Severity
    actor: Dict[str, Any]
    object: Dict[str, Any]
    action: str
    confidence: float
    evidence_hash: str
    raw_pointer: str
    environment_id: str
    assumptions: List[str] = field(default_factory=list)
    raw_bytes: bytes = field(default=b"", repr=False)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to camelCase dict suitable for JSON output."""
        return {
            "eventId": self.event_id,
            "sourceSystem": self.source_system,
            "eventType": self.event_type.value,
            "timestamp": self.timestamp,
            "severity": self.severity.value,
            "actor": self.actor,
            "object": self.object,
            "action": self.action,
            "confidence": self.confidence,
            "evidenceHash": self.evidence_hash,
            "rawPointer": self.raw_pointer,
            "environmentId": self.environment_id,
            "assumptions": self.assumptions,
            "metadata": self.metadata,
        }


@dataclass
class Claim:
    """A truth claim extracted from JRM events."""

    claim_id: str
    statement: str
    confidence: float
    evidence_refs: List[str]
    source_events: List[str]
    timestamp: str
    assumptions: List[str] = field(default_factory=list)


@dataclass
class WhyBullet:
    """A single reasoning bullet for DLR output."""

    text: str
    evidence_ref: str
    confidence: float


@dataclass
class ReasoningResult:
    """Output of the reasoning stage for one event."""

    event_id: str
    lane: DecisionLane
    why_bullets: List[WhyBullet]
    claims: List[Claim] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DriftDetection:
    """Output of the drift detection stage."""

    drift_id: str
    drift_type: JRMDriftType
    severity: Severity
    detected_at: str
    evidence_refs: List[str]
    fingerprint: Dict[str, str]
    notes: str = ""
    recommended_action: str = ""


@dataclass
class PatchRecord:
    """Output of the patch stage — versioned, never-overwrite."""

    patch_id: str
    drift_id: str
    rev: int
    previous_rev: int
    changes: List[Dict[str, Any]]
    applied_at: str
    supersedes: Optional[str] = None
    lineage: List[str] = field(default_factory=list)


@dataclass
class PipelineResult:
    """Complete result of processing a batch of events through the pipeline."""

    environment_id: str
    events_processed: int
    window_start: str
    window_end: str
    claims: List[Claim] = field(default_factory=list)
    reasoning_results: List[ReasoningResult] = field(default_factory=list)
    drift_detections: List[DriftDetection] = field(default_factory=list)
    patches: List[PatchRecord] = field(default_factory=list)
    mg_deltas: Dict[str, Any] = field(default_factory=dict)
    canon_postures: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)


@dataclass
class PacketManifest:
    """Manifest for a JRM-X packet."""

    packet_name: str
    environment_id: str
    window_start: str
    window_end: str
    part: int
    files: Dict[str, str]
    event_count: int
    size_bytes: int
    created_at: str
