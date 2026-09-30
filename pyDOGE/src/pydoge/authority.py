from __future__ import annotations

from typing import Any


def trace_authority(work_item: Any, policies: dict[str, Any], authorities: dict[str, Any]) -> list[dict]:
    chain: list[dict] = []
    for pid in work_item.policy_ids:
        policy = policies.get(pid)
        if not policy:
            chain.append({"policy_id": pid, "status": "MISSING_POLICY"})
            continue
        authority = authorities.get(policy.authority_id) if policy.authority_id else None
        chain.append({
            "policy_id": policy.id,
            "policy": policy.title,
            "authority_id": getattr(authority, "id", None),
            "authority": getattr(authority, "name", None),
            "authority_level": getattr(authority, "level", None),
            "source": getattr(authority, "source", None),
            "status": "BOUND" if authority else "NO_AUTHORITY_BINDING",
        })
    return chain
