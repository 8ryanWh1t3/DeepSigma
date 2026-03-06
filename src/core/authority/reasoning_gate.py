"""Reasoning Gate — DLR presence, assumption freshness, confidence checks.

Validates that sufficient reasoning exists before authorizing an action.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


def check_dlr_presence(
    dlr_ref: Optional[str],
    context: Dict[str, Any],
) -> Tuple[bool, str]:
    """Verify a DLR exists for this decision.

    Args:
        dlr_ref: Reference to the expected DLR.
        context: Must contain 'dlr_store' or DLR data.

    Returns:
        Tuple of (present, detail_message).
    """
    if not dlr_ref:
        return False, "no_dlr_reference_provided"

    dlr_store = context.get("dlr_store", {})
    if dlr_ref in dlr_store:
        return True, f"dlr_found:{dlr_ref}"

    # Also accept if DLR data is passed directly in context
    if context.get("dlr_data") is not None:
        return True, f"dlr_data_present:{dlr_ref}"

    return False, f"dlr_not_found:{dlr_ref}"


def check_assumption_freshness(
    claims: List[Dict[str, Any]],
    now: Optional[datetime] = None,
) -> Tuple[bool, List[str]]:
    """Check all assumption-type claims for freshness.

    Args:
        claims: List of claim dicts with truthType, halfLife, etc.
        now: Current time for freshness checks.

    Returns:
        Tuple of (all_fresh, list of stale claim IDs).
    """
    if now is None:
        now = datetime.now(timezone.utc)

    stale: List[str] = []
    for claim in claims:
        truth_type = claim.get("truthType", claim.get("truth_type", ""))
        if truth_type != "assumption":
            continue

        claim_id = claim.get("claimId", claim.get("claim_id", "unknown"))
        half_life = claim.get("halfLife", claim.get("half_life", {}))
        expires_at = half_life.get("expiresAt", half_life.get("expires_at"))

        if expires_at:
            try:
                exp = datetime.fromisoformat(expires_at)
                if exp.tzinfo is None:
                    exp = exp.replace(tzinfo=timezone.utc)
                if now >= exp:
                    stale.append(claim_id)
            except (ValueError, TypeError):
                pass  # Unparseable treated as fresh

    return len(stale) == 0, stale


def check_minimum_confidence(
    claims: List[Dict[str, Any]],
    threshold: float = 0.7,
) -> Tuple[bool, float]:
    """Check that average claim confidence meets threshold.

    Args:
        claims: List of claim dicts with confidence scores.
        threshold: Minimum acceptable average confidence.

    Returns:
        Tuple of (meets_threshold, average_confidence).
    """
    if not claims:
        return True, 1.0

    scores = []
    for claim in claims:
        confidence = claim.get("confidence", {})
        if isinstance(confidence, dict):
            score = confidence.get("score", 0.0)
        elif isinstance(confidence, (int, float)):
            score = float(confidence)
        else:
            score = 0.0
        scores.append(score)

    avg = sum(scores) / len(scores) if scores else 0.0
    return avg >= threshold, avg


def check_required_truth_types(
    claims: List[Dict[str, Any]],
    required: List[str],
) -> Tuple[bool, List[str]]:
    """Check that claims include all required truth types.

    Args:
        claims: List of claim dicts.
        required: List of required truth type strings.

    Returns:
        Tuple of (all_present, list of missing truth types).
    """
    if not required:
        return True, []

    present = {
        claim.get("truthType", claim.get("truth_type", ""))
        for claim in claims
    }
    missing = [t for t in required if t not in present]
    return len(missing) == 0, missing
