"""Tenancy — Per-Tenant Policy Engine.

Manages policy files that define thresholds, quotas, and SLO targets
per tenant. Policies are stored as JSON under data/policies/{tenant_id}.json.

If no policy file exists for a tenant, a default policy is generated.

Abstract institutional credibility architecture.
No real-world system modeled.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_BASE_POLICY_DIR = Path(__file__).parent.parent / "data" / "policies"
_SAFE_ID_RE = re.compile(r"^[A-Za-z0-9_.-]{1,64}$")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _validated_tenant_id(tenant_id: str) -> str:
    if not _SAFE_ID_RE.fullmatch(tenant_id):
        raise ValueError("Invalid tenant_id")
    return tenant_id


def default_policy(tenant_id: str) -> dict[str, Any]:
    """Return the default policy for a tenant."""
    tenant_id = _validated_tenant_id(tenant_id)
    return {
        "tenant_id": tenant_id,
        "updated_at": _now_iso(),
        "ttl_policy": {
            "tier0_seconds": 900,
            "tier1_seconds": 3600,
            "tier2_seconds": 21600,
        },
        "quorum_policy": {
            "tier0": {
                "k_required": 3,
                "n_total": 5,
                "min_correlation_groups": 2,
                "out_of_band_required": True,
            },
            "tier1": {
                "k_required": 2,
                "n_total": 4,
                "min_correlation_groups": 2,
                "out_of_band_required": False,
            },
        },
        "correlation_policy": {
            "review_threshold": 0.7,
            "invalid_threshold": 0.9,
        },
        "silence_policy": {
            "healthy_pct": 0.1,
            "elevated_pct": 1.0,
            "degraded_pct": 2.0,
        },
        "slo_policy": {
            "why_retrieval_target_seconds": 60,
            "packet_generate_target_ms": 500,
        },
        "quota_policy": {
            "packets_per_hour": 120,
            "exports_per_day": 500,
        },
    }


def _policy_path(tenant_id: str) -> Path:
    """Return the policy file path for a tenant."""
    _BASE_POLICY_DIR.mkdir(parents=True, exist_ok=True)
    safe_tenant_id = _validated_tenant_id(tenant_id)
    base = _BASE_POLICY_DIR.resolve()
    path = (base / f"{safe_tenant_id}.json").resolve()
    if os.path.commonpath([str(base), str(path)]) != str(base):
        raise ValueError("Invalid tenant_id path")
    if path.parent != base:
        raise ValueError("Invalid tenant_id path")
    return path


def load_policy(tenant_id: str) -> dict[str, Any]:
    """Load the policy for a tenant. Creates default if missing."""
    path = _policy_path(tenant_id)
    if not path.exists():
        policy = default_policy(tenant_id)
        save_policy(tenant_id, policy)
        return policy
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_policy(
    tenant_id: str,
    policy_dict: dict[str, Any],
    actor: str | None = None,
) -> dict[str, Any]:
    """Save a policy for a tenant. Returns the saved policy."""
    policy_dict["tenant_id"] = tenant_id
    policy_dict["updated_at"] = _now_iso()
    if actor:
        policy_dict["updated_by"] = actor
    path = _policy_path(tenant_id)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(policy_dict, f, indent=2, default=str)
        f.write("\n")
    return policy_dict


def get_policy_hash(policy_dict: dict[str, Any]) -> str:
    """Compute a SHA-256 hash of the canonical policy JSON.

    Excludes transient fields (updated_at, updated_by) from the hash
    so the hash reflects the policy content, not metadata.
    """
    stable = {
        k: v for k, v in sorted(policy_dict.items())
        if k not in ("updated_at", "updated_by")
    }
    canonical = json.dumps(stable, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode()).hexdigest()[:40]


def evaluate_policy(
    tenant_id: str,
    state: dict[str, Any],
) -> dict[str, Any]:
    """Evaluate policy against current engine state.

    Args:
        tenant_id: Tenant to evaluate.
        state: Dict with keys: claims, clusters, sync_regions, drift_events.

    Returns:
        Dict with applied_thresholds, violations, computed_penalties,
        and policy_hash.
    """
    policy = load_policy(tenant_id)
    policy_hash = get_policy_hash(policy)

    violations: list[dict[str, Any]] = []

    # -- TTL violations --
    ttl_policy = policy.get("ttl_policy", {})
    tier0_ttl_s = ttl_policy.get("tier0_seconds", 900)
    expired_claims = [
        c for c in state.get("claims", [])
        if c.get("ttl_remaining", 240) <= 0
    ]
    if expired_claims:
        violations.append({
            "type": "ttl_expired",
            "severity": "high",
            "detail": f"{len(expired_claims)} claim(s) with expired TTL",
            "threshold": f"tier0_seconds={tier0_ttl_s}",
        })

    # -- Correlation violations --
    corr_policy = policy.get("correlation_policy", {})
    review_threshold = corr_policy.get("review_threshold", 0.7)
    invalid_threshold = corr_policy.get("invalid_threshold", 0.9)
    for cluster in state.get("clusters", []):
        coeff = cluster.get("coefficient", 0)
        if coeff > invalid_threshold:
            violations.append({
                "type": "correlation_critical",
                "severity": "critical",
                "detail": f"Cluster {cluster.get('id')} at {coeff:.2f} exceeds invalid threshold {invalid_threshold}",
            })
        elif coeff > review_threshold:
            violations.append({
                "type": "correlation_review",
                "severity": "medium",
                "detail": f"Cluster {cluster.get('id')} at {coeff:.2f} exceeds review threshold {review_threshold}",
            })

    # -- Quorum violations --
    quorum_policy = policy.get("quorum_policy", {}).get("tier0", {})
    min_k = quorum_policy.get("k_required", 3)
    for claim in state.get("claims", []):
        if claim.get("state") == "UNKNOWN":
            violations.append({
                "type": "quorum_broken",
                "severity": "high",
                "detail": f"Claim {claim.get('id')} in UNKNOWN state (quorum broken, min k={min_k})",
            })

    # -- Silence violations --
    silence_policy = policy.get("silence_policy", {})
    sync_regions = state.get("sync_regions", [])
    total_nodes = sum(r.get("sync_nodes", 0) for r in sync_regions)
    silent_nodes = total_nodes - sum(
        r.get("sync_nodes_healthy", 0) for r in sync_regions
    )
    if total_nodes > 0:
        silent_pct = (silent_nodes / total_nodes) * 100
        degraded_threshold = silence_policy.get("degraded_pct", 2.0)
        if silent_pct > degraded_threshold:
            violations.append({
                "type": "silence_degraded",
                "severity": "high",
                "detail": f"Silent nodes at {silent_pct:.1f}% exceeds degraded threshold {degraded_threshold}%",
            })

    return {
        "tenant_id": tenant_id,
        "policy_hash": policy_hash,
        "applied_thresholds": {
            "ttl_tier0_seconds": tier0_ttl_s,
            "correlation_review": review_threshold,
            "correlation_invalid": invalid_threshold,
            "quorum_tier0_k": min_k,
        },
        "violations": violations,
        "violation_count": len(violations),
        "evaluated_at": _now_iso(),
    }
