"""JRM Advisory Engine — publish and track patch advisories."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List

from ..types import Advisory, CrossEnvDrift


class AdvisoryEngine:
    """Create and track patch advisories from cross-env drift detections."""

    def __init__(self) -> None:
        self._advisories: Dict[str, Advisory] = {}

    def publish(self, drifts: List[CrossEnvDrift]) -> List[Advisory]:
        """Create PATCH_ADVISORY_PUBLISHED payloads from drift detections."""
        advisories: List[Advisory] = []
        for drift in drifts:
            adv = Advisory(
                advisory_id=f"ADV-{uuid.uuid4().hex[:12]}",
                drift_type=drift.drift_type.value,
                source_env=drift.environments[0] if drift.environments else "",
                target_envs=drift.environments[1:] if len(drift.environments) > 1 else [],
                recommendation=self._recommend(drift),
                status="published",
                detail={
                    "driftId": drift.drift_id,
                    "signatureId": drift.signature_id,
                    "detail": drift.detail,
                },
            )
            self._advisories[adv.advisory_id] = adv
            advisories.append(adv)
        return advisories

    def accept(self, advisory_id: str) -> bool:
        """Accept an advisory."""
        if advisory_id in self._advisories:
            self._advisories[advisory_id].status = "accepted"
            return True
        return False

    def decline(self, advisory_id: str) -> bool:
        """Decline an advisory."""
        if advisory_id in self._advisories:
            self._advisories[advisory_id].status = "declined"
            return True
        return False

    def list_advisories(self) -> List[Advisory]:
        return list(self._advisories.values())

    @staticmethod
    def _recommend(drift: CrossEnvDrift) -> str:
        if drift.drift_type.value == "VERSION_SKEW":
            return "Reconcile signature revisions across environments to latest rev"
        if drift.drift_type.value == "POSTURE_DIVERGENCE":
            return "Review and align posture/confidence for divergent entries"
        if drift.drift_type.value == "REFINEMENT_CONFLICT":
            return "Resolve conflicting patches — manual review required"
        return "Review cross-environment drift and apply appropriate corrections"
