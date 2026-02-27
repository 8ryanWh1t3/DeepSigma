"""Authority Gate consumer — validates DLR action claims against ALS blessed claims.

Compares the ``action`` claims in a Decision Lineage Record against the
``claimsBlessed`` list in one or more Authority Slices.  Unblessed action
claims emit an ``AUTHORITY_MISMATCH`` drift signal.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def _extract_action_claim_ids(dlr_payload: Dict[str, Any]) -> List[str]:
    """Extract claim IDs from the DLR ``claims.action`` list."""
    claims = dlr_payload.get("claims", {})
    action_claims = claims.get("action", [])
    return [c["claimId"] for c in action_claims if "claimId" in c]


def _collect_blessed_claim_ids(als_payloads: List[Dict[str, Any]]) -> set:
    """Gather all blessed claim IDs across multiple ALS payloads."""
    blessed: set = set()
    for als in als_payloads:
        for cid in als.get("claimsBlessed", []):
            blessed.add(cid)
    return blessed


class AuthorityGateConsumer:
    """Check DLR action claims against ALS blessed claims.

    Returns an ``AUTHORITY_MISMATCH`` drift signal payload when
    unblessed action claims are found, or ``None`` if all claims
    are authorized.
    """

    def check(
        self,
        dlr_payload: Dict[str, Any],
        als_payloads: List[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        """Compare DLR action claims to ALS blessed claims.

        Args:
            dlr_payload: The decision lineage payload.
            als_payloads: One or more authority slice payloads.

        Returns:
            A drift signal payload dict if unblessed claims found, else None.
        """
        action_ids = _extract_action_claim_ids(dlr_payload)
        if not action_ids:
            return None

        blessed = _collect_blessed_claim_ids(als_payloads)
        unblessed = [cid for cid in action_ids if cid not in blessed]

        if not unblessed:
            return None

        dlr_id = dlr_payload.get("dlrId", "unknown")
        return {
            "driftId": f"DS-auth-{uuid.uuid4().hex[:12]}",
            "driftType": "authority_mismatch",
            "severity": "red",
            "detectedAt": datetime.now(timezone.utc).isoformat(),
            "evidenceRefs": [f"dlr:{dlr_id}"] + [f"claim:{c}" for c in unblessed],
            "recommendedPatchType": "authority_update",
            "fingerprint": {"key": f"auth-gate:{dlr_id}", "version": "1"},
            "notes": f"Unblessed action claims: {', '.join(unblessed)}",
        }

    def check_refusals(
        self,
        dlr_payload: Dict[str, Any],
        refusal_entries: List[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        """Check if any DLR action claims have been explicitly refused.

        Args:
            dlr_payload: The decision lineage payload.
            refusal_entries: Authority ledger entries with entry_type AUTHORITY_REFUSAL.

        Returns:
            A drift signal payload if refused claims found, else None.
        """
        action_ids = _extract_action_claim_ids(dlr_payload)
        if not action_ids:
            return None

        refused_types = {
            e.get("refused_action_type")
            for e in refusal_entries
            if e.get("entry_type") == "AUTHORITY_REFUSAL"
        }
        if not refused_types:
            return None

        # Check if any action claim type matches a refused action type
        refused_claims = [cid for cid in action_ids if cid in refused_types]
        if not refused_claims:
            return None

        dlr_id = dlr_payload.get("dlrId", "unknown")
        return {
            "driftId": f"DS-refused-{uuid.uuid4().hex[:12]}",
            "driftType": "authority_refused",
            "severity": "red",
            "detectedAt": datetime.now(timezone.utc).isoformat(),
            "evidenceRefs": [f"dlr:{dlr_id}"] + [f"refused:{c}" for c in refused_claims],
            "recommendedPatchType": "authority_review",
            "fingerprint": {"key": f"auth-refused:{dlr_id}", "version": "1"},
            "notes": f"Explicitly refused action types: {', '.join(refused_claims)}",
        }
