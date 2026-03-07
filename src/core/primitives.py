"""Canonical core primitives — five-primitive enforcement model.

Defines PrimitiveType (the five canonical types: CLAIM, EVENT, REVIEW, PATCH,
APPLY) and the domain-specific reference dataclasses (AtomicClaim,
DecisionEpisode, DriftSignal, Patch) that implement the archival layer.
These are additive — they do not replace existing domain-specific models
in decision_surface, JRM, or paradox_ops.

Usage:
    from core.primitives import PrimitiveType, ALLOWED_PRIMITIVE_TYPES
    from core.primitives import AtomicClaim, DecisionEpisode, DriftSignal, Patch
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from .normalize import normalize_keys


# ── Five Primitive Types ────────────────────────────────────────


class PrimitiveType(str, Enum):
    """The five — and only five — canonical primitive types.

    Every object in the system is one of these five types, a subtype,
    metadata, a derived view, or orchestration.  No sixth primitive
    may be introduced.
    """

    CLAIM = "claim"
    EVENT = "event"
    REVIEW = "review"
    PATCH = "patch"
    APPLY = "apply"


ALLOWED_PRIMITIVE_TYPES: frozenset = frozenset(p.value for p in PrimitiveType)


# ── Status / severity enums ─────────────────────────────────────


class ClaimLifecycle(str, Enum):
    """Lifecycle states for an AtomicClaim."""

    ACTIVE = "active"
    EXPIRED = "expired"
    SUPERSEDED = "superseded"
    DISPUTED = "disputed"
    RETRACTED = "retracted"


class EpisodeStatus(str, Enum):
    """Lifecycle states for a DecisionEpisode.

    Matches the existing EpisodeState values in episode_state.py.
    """

    PENDING = "pending"
    ACTIVE = "active"
    SEALED = "sealed"
    ARCHIVED = "archived"
    FROZEN = "frozen"


class DriftSeverity(str, Enum):
    """Traffic-light severity for drift signals.

    Matches the green/yellow/red model in drift.schema.json.
    """

    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"


class DriftStatus(str, Enum):
    """Lifecycle states for a DriftSignal."""

    DETECTED = "detected"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    ESCALATED = "escalated"
    SUPPRESSED = "suppressed"


class PatchStatus(str, Enum):
    """Lifecycle states for a Patch."""

    PROPOSED = "proposed"
    APPROVED = "approved"
    APPLIED = "applied"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"


# ── Helpers ──────────────────────────────────────────────────────


def _seal_hash(content: Dict[str, Any]) -> str:
    """Deterministic SHA-256 hash of a dict, prefixed with ``sha256:``.

    Uses the repo-wide canonical serialisation:
    ``json.dumps(content, sort_keys=True, separators=(",", ":"))``
    """
    canonical = json.dumps(content, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def _snake_to_camel(key: str) -> str:
    """Convert ``snake_case`` to ``camelCase``."""
    parts = key.split("_")
    return parts[0] + "".join(p.capitalize() for p in parts[1:])


# ── AtomicClaim ──────────────────────────────────────────────────


@dataclass
class AtomicClaim:
    """The universal lowest-level primitive.

    Every higher-order structure (DecisionEpisode, DriftSignal, Patch)
    is composed of or references AtomicClaims.
    """

    claim_id: str
    claim_type: str
    statement: str
    source: str
    confidence: float
    created_at: str
    provenance: List[Dict[str, Any]] = field(default_factory=list)
    expires_at: Optional[str] = None
    status: str = ClaimLifecycle.ACTIVE.value
    supports: List[str] = field(default_factory=list)
    contradicts: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    # -- serialisation ------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        """Serialise to camelCase dict matching ``atomic_claim.schema.json``."""
        d: Dict[str, Any] = {
            "claimId": self.claim_id,
            "claimType": self.claim_type,
            "statement": self.statement,
            "source": self.source,
            "confidence": self.confidence,
            "createdAt": self.created_at,
            "status": self.status,
        }
        if self.provenance:
            d["provenance"] = self.provenance
        if self.expires_at is not None:
            d["expiresAt"] = self.expires_at
        if self.supports:
            d["supports"] = self.supports
        if self.contradicts:
            d["contradicts"] = self.contradicts
        if self.tags:
            d["tags"] = self.tags
        if self.metadata:
            d["metadata"] = self.metadata
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> AtomicClaim:
        """Construct from a camelCase or snake_case dict."""
        d = normalize_keys(data, style="snake")
        return cls(
            claim_id=d["claim_id"],
            claim_type=d["claim_type"],
            statement=d["statement"],
            source=d["source"],
            confidence=d["confidence"],
            created_at=d["created_at"],
            provenance=d.get("provenance", []),
            expires_at=d.get("expires_at"),
            status=d.get("status", ClaimLifecycle.ACTIVE.value),
            supports=d.get("supports", []),
            contradicts=d.get("contradicts", []),
            tags=d.get("tags", []),
            metadata=d.get("metadata", {}),
        )

    # -- domain helpers -----------------------------------------------

    def seal_hash(self) -> str:
        """Return a deterministic SHA-256 hash of this claim's content."""
        return _seal_hash(self.to_dict())

    def is_expired(self) -> bool:
        """Return ``True`` if *expires_at* is set and in the past."""
        if self.expires_at is None:
            return False
        try:
            exp = datetime.fromisoformat(self.expires_at.replace("Z", "+00:00"))
            return datetime.now(timezone.utc) >= exp
        except (ValueError, TypeError):
            return False


# ── DecisionEpisode ──────────────────────────────────────────────


@dataclass
class DecisionEpisode:
    """The orchestration container.

    Composed from claims and decision metadata, capturing the full
    lifecycle from goal through outcome.
    """

    decision_id: str
    title: str
    owner: str
    created_at: str
    goal: str
    claims_used: List[str] = field(default_factory=list)
    options: List[Dict[str, Any]] = field(default_factory=list)
    selected_option: str = ""
    rejected_options: List[str] = field(default_factory=list)
    assumptions: List[str] = field(default_factory=list)
    evidence: List[str] = field(default_factory=list)
    blast_radius: str = ""
    kill_switches: List[str] = field(default_factory=list)
    outcome: Optional[Dict[str, Any]] = None
    status: str = EpisodeStatus.PENDING.value
    lineage: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialise to camelCase dict matching ``decision_episode.schema.json``."""
        d: Dict[str, Any] = {
            "decisionId": self.decision_id,
            "title": self.title,
            "owner": self.owner,
            "createdAt": self.created_at,
            "goal": self.goal,
            "status": self.status,
        }
        if self.claims_used:
            d["claimsUsed"] = self.claims_used
        if self.options:
            d["options"] = self.options
        if self.selected_option:
            d["selectedOption"] = self.selected_option
        if self.rejected_options:
            d["rejectedOptions"] = self.rejected_options
        if self.assumptions:
            d["assumptions"] = self.assumptions
        if self.evidence:
            d["evidence"] = self.evidence
        if self.blast_radius:
            d["blastRadius"] = self.blast_radius
        if self.kill_switches:
            d["killSwitches"] = self.kill_switches
        if self.outcome is not None:
            d["outcome"] = self.outcome
        if self.lineage:
            d["lineage"] = self.lineage
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> DecisionEpisode:
        """Construct from a camelCase or snake_case dict."""
        d = normalize_keys(data, style="snake")
        return cls(
            decision_id=d["decision_id"],
            title=d["title"],
            owner=d["owner"],
            created_at=d["created_at"],
            goal=d["goal"],
            claims_used=d.get("claims_used", []),
            options=d.get("options", []),
            selected_option=d.get("selected_option", ""),
            rejected_options=d.get("rejected_options", []),
            assumptions=d.get("assumptions", []),
            evidence=d.get("evidence", []),
            blast_radius=d.get("blast_radius", ""),
            kill_switches=d.get("kill_switches", []),
            outcome=d.get("outcome"),
            status=d.get("status", EpisodeStatus.PENDING.value),
            lineage=d.get("lineage", {}),
        )

    def seal_hash(self) -> str:
        """Return a deterministic SHA-256 hash of this episode's content."""
        return _seal_hash(self.to_dict())


# ── DriftSignal ──────────────────────────────────────────────────


@dataclass
class DriftSignal:
    """Divergence between expected and observed state.

    Links a DecisionEpisode to the corrective action that follows.
    """

    drift_id: str
    decision_id: str
    trigger: str
    detected_at: str
    severity: str = DriftSeverity.YELLOW.value
    related_claims: List[str] = field(default_factory=list)
    description: str = ""
    status: str = DriftStatus.DETECTED.value
    telemetry_refs: List[str] = field(default_factory=list)
    expected_state: str = ""
    observed_state: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Serialise to camelCase dict matching ``drift_signal_primitive.schema.json``."""
        d: Dict[str, Any] = {
            "driftId": self.drift_id,
            "decisionId": self.decision_id,
            "trigger": self.trigger,
            "detectedAt": self.detected_at,
            "severity": self.severity,
            "status": self.status,
        }
        if self.related_claims:
            d["relatedClaims"] = self.related_claims
        if self.description:
            d["description"] = self.description
        if self.telemetry_refs:
            d["telemetryRefs"] = self.telemetry_refs
        if self.expected_state:
            d["expectedState"] = self.expected_state
        if self.observed_state:
            d["observedState"] = self.observed_state
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> DriftSignal:
        """Construct from a camelCase or snake_case dict."""
        d = normalize_keys(data, style="snake")
        return cls(
            drift_id=d["drift_id"],
            decision_id=d["decision_id"],
            trigger=d["trigger"],
            detected_at=d["detected_at"],
            severity=d.get("severity", DriftSeverity.YELLOW.value),
            related_claims=d.get("related_claims", []),
            description=d.get("description", ""),
            status=d.get("status", DriftStatus.DETECTED.value),
            telemetry_refs=d.get("telemetry_refs", []),
            expected_state=d.get("expected_state", ""),
            observed_state=d.get("observed_state", ""),
        )


# ── Patch ────────────────────────────────────────────────────────


@dataclass
class Patch:
    """Append-only correction resolving a drift signal.

    Patches never overwrite prior state — they supersede, creating
    an immutable lineage chain.
    """

    patch_id: str
    decision_id: str
    drift_id: str
    issued_at: str
    description: str
    claims_updated: List[str] = field(default_factory=list)
    supersedes: List[str] = field(default_factory=list)
    status: str = PatchStatus.PROPOSED.value
    rationale: str = ""
    lineage: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialise to camelCase dict matching ``patch.schema.json``."""
        d: Dict[str, Any] = {
            "patchId": self.patch_id,
            "decisionId": self.decision_id,
            "driftId": self.drift_id,
            "issuedAt": self.issued_at,
            "description": self.description,
            "status": self.status,
        }
        if self.claims_updated:
            d["claimsUpdated"] = self.claims_updated
        if self.supersedes:
            d["supersedes"] = self.supersedes
        if self.rationale:
            d["rationale"] = self.rationale
        if self.lineage:
            d["lineage"] = self.lineage
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Patch:
        """Construct from a camelCase or snake_case dict."""
        d = normalize_keys(data, style="snake")
        return cls(
            patch_id=d["patch_id"],
            decision_id=d["decision_id"],
            drift_id=d["drift_id"],
            issued_at=d["issued_at"],
            description=d["description"],
            claims_updated=d.get("claims_updated", []),
            supersedes=d.get("supersedes", []),
            status=d.get("status", PatchStatus.PROPOSED.value),
            rationale=d.get("rationale", ""),
            lineage=d.get("lineage", {}),
        )


# ── Validation wrappers ─────────────────────────────────────────


def validate_claim(data: Dict[str, Any]) -> Any:
    """Validate *data* against ``atomic_claim.schema.json``."""
    from .schema_validator import validate
    return validate(data, "atomic_claim")


def validate_episode(data: Dict[str, Any]) -> Any:
    """Validate *data* against ``decision_episode.schema.json``."""
    from .schema_validator import validate
    return validate(data, "decision_episode")


def validate_drift(data: Dict[str, Any]) -> Any:
    """Validate *data* against ``drift_signal_primitive.schema.json``."""
    from .schema_validator import validate
    return validate(data, "drift_signal_primitive")


def validate_patch(data: Dict[str, Any]) -> Any:
    """Validate *data* against ``patch.schema.json``."""
    from .schema_validator import validate
    return validate(data, "patch")
