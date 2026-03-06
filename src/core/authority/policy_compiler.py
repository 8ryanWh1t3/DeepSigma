"""Policy Compiler — DLR to governance artifact compilation.

Transforms a ReOps decision packet (DLR) into an AuthorityOps governance
artifact. This is the OpenPQL compilation step — deterministic, no side
effects, fully testable.
"""

from __future__ import annotations

import hashlib
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List

from .models import (
    CompiledPolicy,
    GovernanceArtifact,
    PolicyConstraint,
    PolicyEvaluation,
    PolicyEvaluationStep,
    ReasoningRequirement,
)
from .seal_and_hash import canonical_json as _canonical_json, compute_hash

logger = logging.getLogger(__name__)


def compile_policy(
    dlr: Dict[str, Any],
    policy_pack: Dict[str, Any],
) -> GovernanceArtifact:
    """Compile a DLR and policy pack into a governance artifact.

    Args:
        dlr: Decision Log Record dict with dlrId, episodeId, claims, etc.
        policy_pack: Policy configuration with constraints, requirements.

    Returns:
        GovernanceArtifact with compiled rules, sealed and hashed.
    """
    dlr_id = dlr.get("dlrId", dlr.get("dlr_id", ""))
    episode_id = dlr.get("episodeId", dlr.get("episode_id", ""))

    now = datetime.now(timezone.utc).isoformat()
    artifact_id = f"GOV-{uuid.uuid4().hex[:12]}"

    # Compile seal hash from DLR + policy inputs
    seal_input = {
        "dlr_id": dlr_id,
        "policy_pack_id": policy_pack.get("policyPackId", policy_pack.get("policy_pack_id", "")),
        "compiled_at": now,
    }
    seal_hash = "sha256:" + hashlib.sha256(
        _canonical_json(seal_input).encode("utf-8")
    ).hexdigest()

    return GovernanceArtifact(
        artifact_id=artifact_id,
        artifact_type="policy_evaluation",
        created_at=now,
        episode_id=episode_id,
        dlr_ref=dlr_id,
        seal_hash=seal_hash,
        seal_version=1,
    )


def extract_reasoning_requirements(
    dlr: Dict[str, Any],
    policy_pack: Dict[str, Any] | None = None,
) -> ReasoningRequirement:
    """Extract reasoning requirements from a DLR and optional policy pack.

    Args:
        dlr: Decision Log Record dict.
        policy_pack: Optional policy configuration.

    Returns:
        ReasoningRequirement with compiled thresholds.
    """
    if policy_pack is None:
        policy_pack = {}

    claims = dlr.get("claims", {})
    claim_count = sum(len(v) if isinstance(v, list) else 0 for v in claims.values())

    return ReasoningRequirement(
        requirement_id=f"RR-{uuid.uuid4().hex[:8]}",
        requires_dlr=policy_pack.get("requiresDlr", True),
        minimum_claims=policy_pack.get("minimumClaims", max(1, claim_count)),
        required_truth_types=policy_pack.get("requiredTruthTypes", []),
        minimum_confidence=policy_pack.get("minimumConfidence", 0.7),
        max_assumption_age=policy_pack.get("maxAssumptionAge", ""),
    )


def extract_constraints(
    policy_pack: Dict[str, Any],
    action_type: str,
) -> List[PolicyConstraint]:
    """Extract applicable constraints from a policy pack for a given action type.

    Args:
        policy_pack: Policy configuration dict.
        action_type: The type of action being evaluated.

    Returns:
        List of applicable PolicyConstraint objects.
    """
    raw_constraints = policy_pack.get("constraints", [])
    result: List[PolicyConstraint] = []

    for c in raw_constraints:
        # Filter by action type if specified in the constraint
        applies_to = c.get("appliesTo", [])
        if applies_to and action_type not in applies_to:
            continue

        result.append(PolicyConstraint(
            constraint_id=c.get("constraintId", c.get("constraint_id", f"C-{uuid.uuid4().hex[:8]}")),
            constraint_type=c.get("constraintType", c.get("constraint_type", "")),
            expression=c.get("expression", ""),
            parameters=c.get("parameters", {}),
        ))

    # Always add implicit DLR requirement if policy requires it
    if policy_pack.get("requiresDlr", True):
        result.append(PolicyConstraint(
            constraint_id="C-implicit-dlr",
            constraint_type="requires_dlr",
            expression="dlr_ref IS NOT NULL",
        ))

    # Add blast radius constraint if specified
    max_br = policy_pack.get("maxBlastRadius")
    if max_br:
        result.append(PolicyConstraint(
            constraint_id="C-implicit-blast-radius",
            constraint_type="blast_radius_max",
            expression=f"blast_radius_tier <= {max_br}",
            parameters={"maxBlastRadius": max_br},
        ))

    return result


def compile_from_source(source: "PolicySource") -> CompiledPolicy:
    """Compile a PolicySource into a CompiledPolicy (OpenPQL pipeline entry).

    Uses existing ``extract_constraints`` and ``extract_reasoning_requirements``
    to build rules, then seals the result.

    Args:
        source: A validated PolicySource object.

    Returns:
        CompiledPolicy with deterministic policy_hash and seal.
    """
    from .policy_source import PolicySource  # noqa: F811 (type hint)

    dlr = source.dlr
    policy_pack = source.policy_pack
    dlr_id = dlr.get("dlrId", dlr.get("dlr_id", ""))
    episode_id = dlr.get("episodeId", dlr.get("episode_id", ""))
    action_type = dlr.get("actionType", dlr.get("action_type", ""))
    policy_pack_id = policy_pack.get("policyPackId", policy_pack.get("policy_pack_id", ""))

    now = datetime.now(timezone.utc).isoformat()
    artifact_id = f"GOV-{uuid.uuid4().hex[:12]}"

    rules = extract_constraints(policy_pack, action_type)
    reasoning = extract_reasoning_requirements(dlr, policy_pack)

    # Deterministic policy hash over rules + reasoning
    rules_payload = [
        {"id": r.constraint_id, "type": r.constraint_type, "expr": r.expression}
        for r in rules
    ]
    reasoning_payload = {
        "requires_dlr": reasoning.requires_dlr,
        "minimum_claims": reasoning.minimum_claims,
        "minimum_confidence": reasoning.minimum_confidence,
    }
    policy_hash = compute_hash({"rules": rules_payload, "reasoning": reasoning_payload})

    seal_hash = compute_hash({
        "artifact_id": artifact_id,
        "source_id": source.source_id,
        "policy_hash": policy_hash,
        "compiled_at": now,
    })

    return CompiledPolicy(
        artifact_id=artifact_id,
        source_id=source.source_id,
        dlr_ref=dlr_id,
        episode_id=episode_id,
        policy_pack_id=policy_pack_id,
        rules=rules,
        reasoning_requirements=reasoning,
        created_at=now,
        policy_hash=policy_hash,
        seal_hash=seal_hash,
        seal_version=1,
    )
