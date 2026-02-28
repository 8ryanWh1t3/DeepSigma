"""Patch stage — create versioned patch records from drift detections."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ..types import DriftDetection, JRMDriftType, PatchRecord


@dataclass
class PatchOutput:
    """Output of the patch stage."""

    patches: List[PatchRecord]


class PatchStage:
    """Create patch proposals from drift detections.

    Never overwrites — always rev++ with lineage preserved.
    """

    def __init__(self) -> None:
        # Track rev per fingerprint key (signature_id or drift fingerprint)
        self._rev_tracker: Dict[str, int] = {}
        # Track patch lineage per fingerprint key
        self._lineage_tracker: Dict[str, List[str]] = {}

    def process(self, drift_detections: List[DriftDetection]) -> PatchOutput:
        patches: List[PatchRecord] = []
        for dd in drift_detections:
            patch = self._create_patch(dd)
            if patch is not None:
                patches.append(patch)
        return PatchOutput(patches=patches)

    def _create_patch(self, dd: DriftDetection) -> PatchRecord | None:
        """Create a patch record for a drift detection."""
        fp_key = self._fingerprint_key(dd)

        prev_rev = self._rev_tracker.get(fp_key, 0)
        new_rev = prev_rev + 1
        self._rev_tracker[fp_key] = new_rev

        prev_lineage = self._lineage_tracker.get(fp_key, [])
        patch_id = f"PATCH-{uuid.uuid4().hex[:12]}"

        supersedes = prev_lineage[-1] if prev_lineage else None

        new_lineage = prev_lineage + [patch_id]
        self._lineage_tracker[fp_key] = new_lineage

        changes = self._derive_changes(dd)

        return PatchRecord(
            patch_id=patch_id,
            drift_id=dd.drift_id,
            rev=new_rev,
            previous_rev=prev_rev,
            changes=changes,
            applied_at=datetime.now(timezone.utc).isoformat(),
            supersedes=supersedes,
            lineage=prev_lineage.copy(),
        )

    @staticmethod
    def _fingerprint_key(dd: DriftDetection) -> str:
        sig = dd.fingerprint.get("signature_id", "")
        if sig:
            return f"sig:{sig}"
        et = dd.fingerprint.get("event_type", "")
        if et:
            return f"type:{et}"
        return f"drift:{dd.drift_id}"

    @staticmethod
    def _derive_changes(dd: DriftDetection) -> List[Dict[str, Any]]:
        """Derive recommended changes from a drift detection."""
        if dd.drift_type == JRMDriftType.FP_SPIKE:
            return [{"action": "adjust_threshold", "drift_type": "FP_SPIKE",
                      "detail": dd.notes}]
        if dd.drift_type == JRMDriftType.MISSING_MAPPING:
            return [{"action": "add_mapping", "drift_type": "MISSING_MAPPING",
                      "detail": dd.notes}]
        if dd.drift_type == JRMDriftType.STALE_LOGIC:
            return [{"action": "reconcile_rev", "drift_type": "STALE_LOGIC",
                      "detail": dd.notes}]
        if dd.drift_type == JRMDriftType.ASSUMPTION_EXPIRED:
            return [{"action": "revalidate_assumption", "drift_type": "ASSUMPTION_EXPIRED",
                      "detail": dd.notes}]
        return [{"action": "review", "drift_type": dd.drift_type.value, "detail": dd.notes}]
