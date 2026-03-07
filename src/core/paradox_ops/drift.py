"""Inter-dimensional drift detection and patch recommendation.

Inter-dimensional drift triggers when 2+ dimensions shift materially
while 1+ governance-relevant dimensions remain stale.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .models import PatchAction, ParadoxTensionSet


def detect_interdimensional_drift(
    pts: ParadoxTensionSet,
) -> Optional[Dict[str, Any]]:
    """Detect inter-dimensional drift in a PTS.

    Trigger condition:
        1. 2+ dimensions shifted beyond their threshold
        2. 1+ governance-relevant dimensions remain stale
           (shift < 10% of threshold or no shift at all)

    Returns a drift signal dict, or None if no drift detected.
    """
    if not pts.dimensions:
        return None

    shifted: List[str] = []
    stale_governance: List[str] = []

    for d in pts.dimensions:
        shift = abs(d.current_value - d.previous_value)
        stale_cutoff = d.threshold * 0.1

        if shift > d.threshold:
            shifted.append(d.name)
        elif d.is_governance_relevant and shift <= stale_cutoff:
            stale_governance.append(d.name)

    if len(shifted) >= 2 and len(stale_governance) >= 1:
        return {
            "driftId": f"DS-pdx-{uuid.uuid4().hex[:8]}",
            "driftType": "interdimensional_drift",
            "severity": "red",
            "detectedAt": datetime.now(timezone.utc).isoformat(),
            "evidenceRefs": [f"tension:{pts.tension_id}"],
            "fingerprint": {
                "key": f"{pts.tension_id}:idd",
                "version": "1",
            },
            "targetType": "tension_set",
            "targetId": pts.tension_id,
            "shiftedDimensions": shifted,
            "staleDimensions": stale_governance,
            "notes": (
                f"Inter-dimensional drift: {', '.join(shifted)} shifted "
                f"while {', '.join(stale_governance)} remained stale."
            ),
        }

    return None


def build_patch_recommendations(
    pts: ParadoxTensionSet,
    breaches: List[Dict[str, Any]],
) -> List[str]:
    """Generate patch action recommendations based on dimension state.

    Maps governance-relevant dimension conditions to recommended actions.
    """
    actions: List[str] = []

    governance_dims = {d.name: d for d in pts.dimensions if d.is_governance_relevant}
    breach_names = {b.get("dimensionName", "") for b in breaches}

    for name, dim in governance_dims.items():
        shift = abs(dim.current_value - dim.previous_value)
        stale = shift <= dim.threshold * 0.1

        if name == "authority" and stale:
            actions.append(PatchAction.CLARIFY_AUTHORITY.value)
        elif name == "risk" and name in breach_names:
            actions.append(PatchAction.INCREASE_CONTROL_FRICTION.value)
            actions.append(PatchAction.ADD_REVIEW_GATE.value)

    non_gov_breached = [b for b in breaches if not b.get("isGovernanceRelevant")]
    for b in non_gov_breached:
        dim_name = b.get("dimensionName", "")
        if dim_name == "visibility":
            actions.append(PatchAction.ELEVATE_VISIBILITY.value)
        elif dim_name == "time":
            risk_dim = governance_dims.get("risk")
            if risk_dim and abs(risk_dim.current_value - risk_dim.previous_value) > risk_dim.threshold:
                actions.append(PatchAction.REDUCE_IRREVERSIBILITY.value)

    if not actions:
        actions.append(PatchAction.PROMOTE_TO_POLICY_BAND.value)

    return list(dict.fromkeys(actions))
