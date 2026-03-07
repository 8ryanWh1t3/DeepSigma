"""Authority Blast Radius -- simulate damage from authority changes.

Given a target authority entity (actor, delegation, grant, role, policy),
compute what breaks across claims, decisions, canon, patches, and
downstream trust.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .dependency_map import count_affected_by_kind, walk_authority_dependencies


def simulate_blast_radius(
    target_type: str,
    target_id: str,
    memory_graph: Any,
    context: Dict[str, Any],
) -> Dict[str, Any]:
    """Simulate blast radius for a target authority entity (AUTH-F17).

    Walks the memory graph to find all artifacts that depend on the
    target entity, directly or transitively.

    Args:
        target_type: "actor" | "delegation" | "role" | "authority" | "policy"
        target_id: Identifier of the target entity.
        memory_graph: MemoryGraph instance (or None).
        context: Evaluation context.

    Returns:
        Simulation result dict with impact counts, severity, and
        recommended action.
    """
    deps = walk_authority_dependencies(target_id, memory_graph)
    counts = count_affected_by_kind(deps)

    claims = counts.get("claims", 0)
    decisions = counts.get("episodes", 0)
    canon = counts.get("canon_entries", 0)
    patches = counts.get("patches", 0)
    agents = counts.get("actors", 0)

    severity = compute_impact_severity(claims, decisions, canon, patches, agents)
    recommended = build_recommended_action(severity, counts)

    # Build affected artifacts list (limit to 50 for payload size)
    affected: List[Dict[str, Any]] = []
    for kind, ids in deps.items():
        for nid in ids[:10]:  # Cap per-kind
            affected.append({"nodeId": nid, "nodeKind": kind, "label": ""})

    return {
        "simulationId": f"SIM-{uuid.uuid4().hex[:12]}",
        "targetType": target_type,
        "targetId": target_id,
        "affectedClaimsCount": claims,
        "affectedDecisionsCount": decisions,
        "affectedCanonArtifactsCount": canon,
        "affectedPatchObjectsCount": patches,
        "affectedAgentsCount": agents,
        "affectedArtifacts": affected,
        "severity": severity,
        "recommendedAction": recommended,
        "simulatedAt": datetime.now(timezone.utc).isoformat(),
    }


def compute_impact_severity(
    affected_claims: int = 0,
    affected_decisions: int = 0,
    affected_canon: int = 0,
    affected_patches: int = 0,
    affected_agents: int = 0,
) -> str:
    """Compute SEV-1/2/3 from impact counts (AUTH-F18).

    Severity:
        SEV-3 = local actor only (<=1 agent, 0 decisions, <=2 claims)
        SEV-2 = one decision lane or one artifact family
        SEV-1 = cross-domain trust break (multiple decisions, canon, agents)
    """
    total = affected_claims + affected_decisions + affected_canon + affected_patches

    # SEV-3: Local only
    if affected_agents <= 1 and affected_decisions == 0 and affected_claims <= 2:
        return "SEV-3"

    # SEV-1: Cross-domain trust break
    if affected_decisions > 1 and affected_agents > 1:
        return "SEV-1"
    if total > 10:
        return "SEV-1"

    # SEV-2: Single decision lane or artifact family
    return "SEV-2"


def build_recommended_action(severity: str, counts: Dict[str, int]) -> str:
    """Build human-readable recommended action from severity and counts."""
    total = sum(counts.values())

    if severity == "SEV-3":
        return "Monitor only -- local actor impact"
    elif severity == "SEV-2":
        return f"Review affected decision lane before proceeding ({total} artifacts affected)"
    else:
        return f"LOCKDOWN -- cross-domain trust break, halt all dependent operations ({total} artifacts affected)"
