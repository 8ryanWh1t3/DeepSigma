"""Evidence Completeness consumer — validates DLR evidence refs against packet manifest.

Cross-references the evidence references in a Decision Lineage Record
against the artifact manifest of the coherence packet.  Missing evidence
emits a ``PROCESS_GAP`` drift signal.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def _extract_evidence_refs(dlr_payload: Dict[str, Any]) -> List[str]:
    """Extract evidence reference IDs from the DLR claims.context list."""
    claims = dlr_payload.get("claims", {})
    context_claims = claims.get("context", [])
    return [c["claimId"] for c in context_claims if "claimId" in c]


def _collect_manifest_ids(manifest_payload: Dict[str, Any]) -> set:
    """Collect all event IDs from a packet_index artifactManifest."""
    artifacts = manifest_payload.get("artifactManifest", [])
    ids: set = set()
    for entry in artifacts:
        eid = entry.get("eventId", "")
        if eid:
            ids.add(eid)
        # Also collect payload hashes for broader matching
        ph = entry.get("payloadHash", "")
        if ph:
            ids.add(ph)
    return ids


class EvidenceCheckConsumer:
    """Check DLR evidence references against packet manifest.

    Returns a ``PROCESS_GAP`` drift signal payload when evidence
    references are missing from the manifest, or ``None`` if complete.
    """

    def check(
        self,
        dlr_payload: Dict[str, Any],
        manifest_payload: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """Compare DLR evidence refs to manifest artifacts.

        Args:
            dlr_payload: The decision lineage payload.
            manifest_payload: The packet_index payload.

        Returns:
            A drift signal payload dict if missing refs found, else None.
        """
        evidence_refs = _extract_evidence_refs(dlr_payload)
        if not evidence_refs:
            return None

        manifest_ids = _collect_manifest_ids(manifest_payload)
        missing = [ref for ref in evidence_refs if ref not in manifest_ids]

        if not missing:
            return None

        dlr_id = dlr_payload.get("dlrId", "unknown")
        return {
            "driftId": f"DS-evid-{uuid.uuid4().hex[:12]}",
            "driftType": "process_gap",
            "severity": "yellow",
            "detectedAt": datetime.now(timezone.utc).isoformat(),
            "evidenceRefs": [f"dlr:{dlr_id}"] + [f"missing:{r}" for r in missing],
            "recommendedPatchType": "process_fix",
            "fingerprint": {"key": f"evidence-check:{dlr_id}", "version": "1"},
            "notes": f"Missing evidence refs: {', '.join(missing)}",
        }
