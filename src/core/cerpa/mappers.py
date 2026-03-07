"""CERPA mappers — bidirectional adapters to existing DeepSigma structures.

Bridges between CERPA cycle primitives and the canonical/domain-specific
models already in the repo.  Prefer reuse over duplication.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict

from .models import ApplyResult, Claim, Event, Patch, Review


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── AtomicClaim <-> CERPA Claim ─────────────────────────────────


def claim_from_atomic(
    atomic: Any,
    domain: str,
) -> Claim:
    """Map a ``core.primitives.AtomicClaim`` to a CERPA Claim.

    Parameters:
        atomic: An AtomicClaim instance from ``core.primitives``.
        domain: The CERPA domain (intelops, reops, etc.).
    """
    return Claim(
        id=atomic.claim_id,
        text=atomic.statement,
        domain=domain,
        source=atomic.source,
        timestamp=atomic.created_at,
        assumptions=[],
        authority=None,
        provenance=list(atomic.provenance),
        related_ids=list(atomic.supports) + list(atomic.contradicts),
        metadata={
            "claim_type": atomic.claim_type,
            "confidence": atomic.confidence,
            "status": atomic.status,
            "expires_at": atomic.expires_at,
            "tags": list(atomic.tags),
        },
    )


def claim_to_atomic(claim: Claim) -> Any:
    """Map a CERPA Claim to a ``core.primitives.AtomicClaim``.

    Returns:
        An AtomicClaim instance.  Imports lazily to avoid circular deps.
    """
    from core.primitives import AtomicClaim

    meta = claim.metadata
    return AtomicClaim(
        claim_id=claim.id,
        claim_type=meta.get("claim_type", "observation"),
        statement=claim.text,
        source=claim.source,
        confidence=meta.get("confidence", 1.0),
        created_at=claim.timestamp,
        provenance=list(claim.provenance),
        expires_at=meta.get("expires_at"),
        status=meta.get("status", "active"),
        supports=[],
        contradicts=[],
        tags=meta.get("tags", []),
        metadata={},
    )


# ── decision_surface.Event -> CERPA Event ───────────────────────


def event_from_surface(
    surface_event: Any,
    domain: str,
) -> Event:
    """Map a ``decision_surface.models.Event`` to a CERPA Event.

    Parameters:
        surface_event: An Event instance from ``decision_surface.models``.
        domain: The CERPA domain.
    """
    return Event(
        id=surface_event.event_id,
        text=f"{surface_event.event_type}: {surface_event.source}",
        domain=domain,
        source=surface_event.source,
        timestamp=surface_event.timestamp,
        observed_state=dict(surface_event.payload),
        related_ids=list(surface_event.claim_refs),
    )


# ── primitives.DriftSignal -> CERPA Review ──────────────────────


def review_from_drift(
    drift: Any,
    claim_id: str = "",
    event_id: str = "",
) -> Review:
    """Map a ``core.primitives.DriftSignal`` to a CERPA Review.

    Parameters:
        drift: A DriftSignal instance from ``core.primitives``.
        claim_id: Optional claim reference (uses first related_claim if empty).
        event_id: Optional event reference.
    """
    resolved_claim_id = claim_id
    if not resolved_claim_id and drift.related_claims:
        resolved_claim_id = drift.related_claims[0]

    return Review(
        id=drift.drift_id,
        claim_id=resolved_claim_id,
        event_id=event_id,
        domain="",
        timestamp=drift.detected_at,
        verdict="mismatch",
        rationale=drift.description or f"Drift triggered by {drift.trigger}",
        drift_detected=True,
        severity=drift.severity,
        source="drift-mapper",
        related_ids=list(drift.related_claims),
        metadata={
            "trigger": drift.trigger,
            "expected_state": drift.expected_state,
            "observed_state": drift.observed_state,
            "drift_status": drift.status,
        },
    )


# ── primitives.Patch <-> CERPA Patch ───────────────────────────


def patch_from_canonical(
    canonical: Any,
    review_id: str = "",
) -> Patch:
    """Map a ``core.primitives.Patch`` to a CERPA Patch.

    Parameters:
        canonical: A Patch instance from ``core.primitives``.
        review_id: Optional review reference.
    """
    return Patch(
        id=canonical.patch_id,
        review_id=review_id or canonical.drift_id,
        domain="",
        timestamp=canonical.issued_at,
        action="adjust",
        target=canonical.decision_id,
        description=canonical.description,
        source="patch-mapper",
        related_ids=list(canonical.claims_updated) + list(canonical.supersedes),
        metadata={
            "status": canonical.status,
            "rationale": canonical.rationale,
            "lineage": dict(canonical.lineage),
        },
    )


def patch_to_canonical(patch: Patch, decision_id: str = "", drift_id: str = "") -> Any:
    """Map a CERPA Patch to a ``core.primitives.Patch``.

    Returns:
        A Patch instance from ``core.primitives``.
    """
    from core.primitives import Patch as CanonicalPatch

    return CanonicalPatch(
        patch_id=patch.id,
        decision_id=decision_id or patch.target,
        drift_id=drift_id or patch.review_id,
        issued_at=patch.timestamp,
        description=patch.description,
        claims_updated=list(patch.related_ids),
        supersedes=[],
        status="proposed",
        rationale=patch.metadata.get("rationale", ""),
        lineage=patch.metadata.get("lineage", {}),
    )


# ── DLREntry -> CERPA Review ───────────────────────────────────


def review_from_dlr(dlr: Any) -> Review:
    """Map a ``core.decision_log.DLREntry`` to a CERPA Review.

    DLR entries are post-seal records; mapped as aligned reviews.
    """
    return Review(
        id=dlr.dlr_id,
        claim_id="",
        event_id=dlr.episode_id,
        domain="",
        timestamp=dlr.recorded_at,
        verdict="aligned",
        rationale=f"Decision logged: {dlr.decision_type}",
        drift_detected=False,
        source="dlr-mapper",
        related_ids=[dlr.episode_id],
        metadata={
            "decision_type": dlr.decision_type,
            "outcome_code": dlr.outcome_code,
        },
    )
