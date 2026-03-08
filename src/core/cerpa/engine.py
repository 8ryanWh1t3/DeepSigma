"""CERPA engine — orchestrates the adaptation loop.

Claim -> Event -> Review -> Patch -> Apply

The engine provides deterministic review logic and cycle orchestration.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from .models import ApplyResult, CerpaCycle, Claim, Event, Patch, Review
from .types import CerpaStatus, PatchAction, ReviewVerdict


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _uid(prefix: str = "CERPA") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


# ── Review ──────────────────────────────────────────────────────


def review_claim_against_event(claim: Claim, event: Event) -> Review:
    """Compare a Claim against an Event and produce a Review.

    Deterministic logic:
    - If event.metadata contains ``violation=True`` -> violation
    - If event.observed_state contradicts any claim assumption -> mismatch
    - If claim.metadata contains ``expired=True`` -> expired
    - Otherwise -> aligned
    """
    verdict = ReviewVerdict.ALIGNED
    rationale = "Claim and event are aligned; no drift detected"
    severity = None
    drift_detected = False

    # Check for explicit policy violation
    if event.metadata.get("violation"):
        verdict = ReviewVerdict.VIOLATION
        rationale = event.metadata.get(
            "violation_detail",
            "Policy violation detected in event",
        )
        severity = "red"
        drift_detected = True

    # Check observed_state against assumptions
    elif event.observed_state and claim.assumptions:
        observed_status = event.observed_state.get("status", "")
        for assumption in claim.assumptions:
            assumption_lower = assumption.lower()
            observed_lower = str(observed_status).lower()
            # Mismatch when observed state explicitly contradicts
            if observed_lower and observed_lower in ("failed", "violated", "breached"):
                verdict = ReviewVerdict.MISMATCH
                rationale = (
                    f"Observed state '{observed_status}' "
                    f"contradicts assumption: {assumption}"
                )
                severity = "yellow"
                drift_detected = True
                break
            # Mismatch when observed state negates the assumption text
            if (
                "not" in event.text.lower()
                or "failed" in event.text.lower()
                or "violated" in event.text.lower()
            ):
                verdict = ReviewVerdict.MISMATCH
                rationale = f"Event indicates failure: {event.text}"
                severity = "yellow"
                drift_detected = True
                break

    # Check for expired claim
    elif claim.metadata.get("expired"):
        verdict = ReviewVerdict.EXPIRED
        rationale = "Claim has expired; assumptions may be stale"
        severity = "yellow"
        drift_detected = True

    return Review(
        id=_uid("REV"),
        claim_id=claim.id,
        event_id=event.id,
        domain=claim.domain,
        timestamp=_now_iso(),
        verdict=verdict,
        rationale=rationale,
        drift_detected=drift_detected,
        severity=severity,
        source="cerpa-engine",
        related_ids=[claim.id, event.id],
    )


# ── Patch Generation ────────────────────────────────────────────


_VERDICT_ACTION_MAP: Dict[str, str] = {
    ReviewVerdict.MISMATCH: PatchAction.ADJUST,
    ReviewVerdict.VIOLATION: PatchAction.STRENGTHEN,
    ReviewVerdict.EXPIRED: PatchAction.EXPIRE,
}

_VERDICT_DESC_MAP: Dict[str, str] = {
    ReviewVerdict.MISMATCH: "Adjust plan to resolve observed mismatch",
    ReviewVerdict.VIOLATION: "Strengthen controls to prevent recurrence",
    ReviewVerdict.EXPIRED: "Expire stale claim and refresh observation",
}


def generate_patch_from_review(review: Review) -> Optional[Patch]:
    """Generate a Patch from a Review. Returns None if aligned."""
    if not review.drift_detected:
        return None

    action = _VERDICT_ACTION_MAP.get(review.verdict, PatchAction.ADJUST)
    description = _VERDICT_DESC_MAP.get(
        review.verdict,
        f"Corrective action for {review.verdict}",
    )

    return Patch(
        id=_uid("PATCH"),
        review_id=review.id,
        domain=review.domain,
        timestamp=_now_iso(),
        action=action,
        target=review.claim_id,
        description=description,
        source="cerpa-engine",
        related_ids=[review.id, review.claim_id],
    )


# ── Apply ───────────────────────────────────────────────────────


def apply_patch(patch: Patch, claim: Claim) -> ApplyResult:
    """Apply a Patch and return the result."""
    new_state: Dict[str, Any] = {
        "previous_claim": claim.text,
        "action_taken": patch.action,
        "target": patch.target,
    }

    return ApplyResult(
        id=_uid("APPLY"),
        patch_id=patch.id,
        domain=patch.domain,
        timestamp=_now_iso(),
        success=True,
        new_state=new_state,
        updated_claims=[claim.id],
        source="cerpa-engine",
        related_ids=[patch.id, claim.id],
    )


# ── Full Cycle ──────────────────────────────────────────────────


def run_cerpa_cycle(
    claim: Claim,
    event: Event,
    context: Optional[Any] = None,
) -> CerpaCycle:
    """Run a complete CERPA cycle: Claim + Event -> Review -> Patch -> Apply.

    Args:
        claim: The claim to evaluate.
        event: The event to compare against.
        context: Optional ContextEnvelope to attach to the cycle.
    """
    started_at = _now_iso()

    review = review_claim_against_event(claim, event)
    if context is not None:
        review.metadata["context_ref"] = getattr(context, "context_id", None)

    patch = generate_patch_from_review(review)
    if patch is not None and context is not None:
        patch.metadata["context_ref"] = getattr(context, "context_id", None)

    apply_result = None
    if patch is not None:
        apply_result = apply_patch(patch, claim)
        if apply_result is not None and context is not None:
            apply_result.metadata["context_ref"] = getattr(context, "context_id", None)

    if apply_result is not None:
        status = CerpaStatus.APPLIED
    elif patch is not None:
        status = CerpaStatus.PATCHED
    elif review.drift_detected:
        status = CerpaStatus.MISMATCHED
    else:
        status = CerpaStatus.ALIGNED

    return CerpaCycle(
        cycle_id=_uid("CYCLE"),
        domain=claim.domain,
        claim=claim,
        event=event,
        review=review,
        patch=patch,
        apply_result=apply_result,
        status=status,
        started_at=started_at,
        completed_at=_now_iso(),
        context=context,
    )


# ── Serialization ───────────────────────────────────────────────


def cycle_to_dict(cycle: CerpaCycle) -> Dict[str, Any]:
    """Serialize a CerpaCycle to a plain dict."""
    return cycle.to_dict()
