"""Retcon executor — assess, execute, and propagate retroactive corrections.

A retcon replaces an existing canon claim with a corrected one, updates the
supersedes chain, and flags dependent claims for review.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


class RetconAssessment:
    """Result of assessing a proposed retcon's impact."""

    def __init__(
        self,
        retcon_id: str,
        original_claim_id: str,
        affected_claim_ids: List[str],
        affected_canon_ids: List[str],
        impact_severity: str,
    ) -> None:
        self.retcon_id = retcon_id
        self.original_claim_id = original_claim_id
        self.affected_claim_ids = affected_claim_ids
        self.affected_canon_ids = affected_canon_ids
        self.impact_severity = impact_severity

    def to_dict(self) -> Dict[str, Any]:
        return {
            "retconId": self.retcon_id,
            "originalClaimId": self.original_claim_id,
            "affectedClaimIds": self.affected_claim_ids,
            "affectedCanonIds": self.affected_canon_ids,
            "impactSeverity": self.impact_severity,
            "assessedAt": datetime.now(timezone.utc).isoformat(),
        }


def assess_retcon(
    original_claim_id: str,
    dependents: List[str],
    canon_entries: Optional[List[Dict[str, Any]]] = None,
) -> RetconAssessment:
    """Assess the impact of retconning a claim.

    Args:
        original_claim_id: The claim being corrected.
        dependents: Claim IDs that depend on the original.
        canon_entries: Canon entries referencing the original claim.

    Returns:
        A RetconAssessment with impact details.
    """
    affected_canon = []
    for entry in (canon_entries or []):
        claim_ids = entry.get("claimIds", []) or entry.get("data", {}).get("claimIds", [])
        if original_claim_id in claim_ids:
            cid = entry.get("canonId", "")
            if cid:
                affected_canon.append(cid)

    severity = "red" if len(dependents) > 5 else "yellow" if dependents else "green"

    return RetconAssessment(
        retcon_id=f"RETCON-{uuid.uuid4().hex[:8]}",
        original_claim_id=original_claim_id,
        affected_claim_ids=dependents,
        affected_canon_ids=affected_canon,
        impact_severity=severity,
    )


def execute_retcon(
    assessment: RetconAssessment,
    new_claim_id: str,
    reason: str = "",
) -> Dict[str, Any]:
    """Execute a retcon: produce a sealed retcon record.

    Args:
        assessment: The impact assessment.
        new_claim_id: The replacement claim ID.
        reason: Human-readable reason for the retcon.

    Returns:
        A retcon record dict suitable for FEEDS emission.
    """
    return {
        "retconId": assessment.retcon_id,
        "originalClaimId": assessment.original_claim_id,
        "newClaimId": new_claim_id,
        "affectedClaimIds": assessment.affected_claim_ids,
        "affectedCanonIds": assessment.affected_canon_ids,
        "reason": reason,
        "executedAt": datetime.now(timezone.utc).isoformat(),
        "sealed": True,
    }


def compute_propagation_targets(
    assessment: RetconAssessment,
) -> List[Dict[str, Any]]:
    """Compute which claims and canon entries need downstream updates.

    Returns a list of action dicts describing what to flag/review.
    """
    targets: List[Dict[str, Any]] = []

    for cid in assessment.affected_claim_ids:
        targets.append({
            "type": "claim_review",
            "claimId": cid,
            "reason": f"Depends on retconned claim {assessment.original_claim_id}",
        })

    for canon_id in assessment.affected_canon_ids:
        targets.append({
            "type": "canon_review",
            "canonId": canon_id,
            "reason": f"Contains retconned claim {assessment.original_claim_id}",
        })

    return targets
