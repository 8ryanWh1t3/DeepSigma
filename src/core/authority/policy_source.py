"""Policy Source — Primitive 1: Formal Input Format.

Wraps a ReOps DLR + PolicyPack into a validated, hashable object that
serves as the single input to the OpenPQL compilation pipeline.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from .seal_and_hash import compute_hash


@dataclass
class PolicySource:
    """Validated, hashable input to the OpenPQL pipeline."""

    source_id: str
    dlr: Dict[str, Any]
    policy_pack: Dict[str, Any]
    claims: List[Dict[str, Any]] = field(default_factory=list)
    created_at: str = ""
    version: str = "1.0.0"
    source_hash: str = ""


def build_policy_source(
    dlr: Dict[str, Any],
    policy_pack: Dict[str, Any],
    claims: Optional[List[Dict[str, Any]]] = None,
) -> PolicySource:
    """Construct a PolicySource from a ReOps DLR and policy pack.

    Args:
        dlr: Decision Log Record with dlrId, episodeId, claims, etc.
        policy_pack: Policy configuration with constraints, requirements.
        claims: Optional explicit claims list (extracted from DLR if omitted).

    Returns:
        PolicySource with computed source_hash.

    Raises:
        ValueError: If dlr has no dlrId.
    """
    dlr_id = dlr.get("dlrId", dlr.get("dlr_id", ""))
    if not dlr_id:
        raise ValueError("DLR must have a dlrId")

    if claims is None:
        raw_claims = dlr.get("claims", {})
        if isinstance(raw_claims, dict):
            # Flatten action-keyed claims into a list
            claims = []
            for v in raw_claims.values():
                if isinstance(v, list):
                    claims.extend(v)
        elif isinstance(raw_claims, list):
            claims = raw_claims
        else:
            claims = []

    now = datetime.now(timezone.utc).isoformat()
    source_id = f"PSRC-{uuid.uuid4().hex[:12]}"

    source_hash = compute_hash({
        "dlr_id": dlr_id,
        "policy_pack_id": policy_pack.get("policyPackId", policy_pack.get("policy_pack_id", "")),
        "claim_count": len(claims),
    })

    return PolicySource(
        source_id=source_id,
        dlr=dlr,
        policy_pack=policy_pack,
        claims=claims,
        created_at=now,
        source_hash=source_hash,
    )


def validate_policy_source(source: PolicySource) -> Tuple[bool, List[str]]:
    """Validate a PolicySource for completeness.

    Returns:
        (valid, errors) tuple.
    """
    errors: List[str] = []
    if not source.dlr:
        errors.append("dlr is empty")
    elif not source.dlr.get("dlrId", source.dlr.get("dlr_id", "")):
        errors.append("dlr has no dlrId")
    if not source.policy_pack:
        errors.append("policy_pack is empty")
    if not source.source_hash:
        errors.append("source_hash is missing")
    return (len(errors) == 0, errors)
