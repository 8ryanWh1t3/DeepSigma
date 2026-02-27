"""Claim validator — contradiction detection and TTL expiry checks.

Validates claims from Truth Snapshots against canon and temporal rules.
Emits drift signals for contradictions and stale assumptions.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def _parse_iso(dt_str: str) -> Optional[datetime]:
    """Parse an ISO 8601 datetime string, returning None on failure."""
    try:
        return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def _half_life_expired(claim: Dict[str, Any], now: Optional[datetime] = None) -> bool:
    """Check if a claim has exceeded its half-life TTL."""
    half_life = claim.get("halfLife", {})
    value = half_life.get("value")
    unit = half_life.get("unit", "hours")
    created = claim.get("timestampCreated")

    if not value or not created:
        return False

    created_dt = _parse_iso(created)
    if created_dt is None:
        return False

    now = now or datetime.now(timezone.utc)
    if unit == "hours":
        from datetime import timedelta
        expiry = created_dt + timedelta(hours=value)
    elif unit == "days":
        from datetime import timedelta
        expiry = created_dt + timedelta(days=value)
    elif unit == "minutes":
        from datetime import timedelta
        expiry = created_dt + timedelta(minutes=value)
    else:
        return False

    return now > expiry


class ClaimValidator:
    """Validate claims for contradictions, TTL expiry, and consistency.

    Returns a list of issues, each a dict with ``type``, ``detail``,
    and ``severity`` keys.
    """

    def __init__(self, canon_claims: Optional[List[Dict[str, Any]]] = None) -> None:
        """Initialize with known canon claims for contradiction checking.

        Args:
            canon_claims: List of canonical claim dicts (must have ``claimId``
                and optionally ``graph.contradicts``).
        """
        self._canon: Dict[str, Dict[str, Any]] = {}
        for c in (canon_claims or []):
            cid = c.get("claimId", "")
            if cid:
                self._canon[cid] = c

    def validate_claim(
        self, claim: Dict[str, Any], now: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """Validate a single claim.

        Checks:
            1. Contradiction against canon claims (via ``graph.contradicts``)
            2. TTL expiry (via ``halfLife`` + ``timestampCreated``)
            3. Confidence/statusLight consistency

        Args:
            claim: An AtomicClaim-like dict.
            now: Override current time for testing.

        Returns:
            List of issue dicts. Empty list means the claim is valid.
        """
        issues: List[Dict[str, Any]] = []
        claim_id = claim.get("claimId", "unknown")

        # 1. Contradiction check
        graph = claim.get("graph", {})
        for contra_id in graph.get("contradicts", []):
            if contra_id in self._canon:
                issues.append({
                    "type": "contradiction",
                    "claimId": claim_id,
                    "detail": f"Claim {claim_id} contradicts canon claim {contra_id}",
                    "severity": "red",
                })

        # 2. TTL expiry check
        if _half_life_expired(claim, now=now):
            issues.append({
                "type": "expired",
                "claimId": claim_id,
                "detail": f"Claim {claim_id} has exceeded its half-life TTL",
                "severity": "yellow",
            })

        # 3. Confidence/statusLight consistency
        confidence = claim.get("confidence", {})
        score = confidence.get("score") if isinstance(confidence, dict) else confidence
        status_light = claim.get("statusLight")

        if score is not None and status_light is not None:
            if isinstance(score, (int, float)):
                if score >= 0.8 and status_light == "red":
                    issues.append({
                        "type": "inconsistent",
                        "claimId": claim_id,
                        "detail": f"Claim {claim_id} has high confidence ({score}) but red status",
                        "severity": "yellow",
                    })
                elif score < 0.3 and status_light == "green":
                    issues.append({
                        "type": "inconsistent",
                        "claimId": claim_id,
                        "detail": f"Claim {claim_id} has low confidence ({score}) but green status",
                        "severity": "yellow",
                    })

        return issues

    def build_drift_signal(
        self, issue: Dict[str, Any], packet_id: str = ""
    ) -> Dict[str, Any]:
        """Convert a validation issue into a drift signal payload."""
        drift_type_map = {
            "contradiction": "authority_mismatch",
            "expired": "freshness",
            "inconsistent": "process_gap",
        }
        patch_type_map = {
            "contradiction": "authority_update",
            "expired": "ttl_change",
            "inconsistent": "manual_review",
        }

        issue_type = issue.get("type", "")
        return {
            "driftId": f"DS-claim-{uuid.uuid4().hex[:12]}",
            "driftType": drift_type_map.get(issue_type, "process_gap"),
            "severity": issue.get("severity", "yellow"),
            "detectedAt": datetime.now(timezone.utc).isoformat(),
            "evidenceRefs": [f"claim:{issue.get('claimId', '')}"],
            "recommendedPatchType": patch_type_map.get(issue_type, "manual_review"),
            "fingerprint": {
                "key": f"claim-validator:{issue.get('claimId', '')}:{issue_type}",
                "version": "1",
            },
            "notes": issue.get("detail", ""),
        }
