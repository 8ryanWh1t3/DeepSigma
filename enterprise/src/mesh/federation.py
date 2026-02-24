"""Mesh Federation — Federated quorum and correlation computation.

Policy-driven quorum across regions and correlation groups.
Claims cannot become VERIFIED without multi-region, multi-group consensus.
Partition → UNKNOWN (safe default). UNKNOWN beats false VERIFIED.

Abstract institutional credibility architecture.
No real-world system modeled.
"""

from __future__ import annotations

import math
from collections import defaultdict
from typing import Any


def compute_federated_state(
    policy: dict[str, Any],
    envelopes: list[dict],
    validations: list[dict],
    sync_regions: list[dict],
    prior_claims: list[dict] | None = None,
) -> dict[str, Any]:
    """Compute federated claim state from envelopes and validations.

    Returns dict with:
      - tier0_claims: list of claim summaries
      - correlation_clusters: list of cluster dicts
      - sync_regions: updated region list
      - component_metrics: dict of index-relevant penalties
    """
    quorum_policy = policy.get("quorum_policy", {})
    correlation_policy = policy.get("correlation_policy", {})
    tier0_qp = quorum_policy.get("tier0", {})
    k_required = tier0_qp.get("k_required", 3)
    n_total = tier0_qp.get("n_total", 5)
    min_corr_groups = tier0_qp.get("min_correlation_groups", 2)
    review_threshold = correlation_policy.get("review_threshold", 0.7)
    invalid_threshold = correlation_policy.get("invalid_threshold", 0.9)

    # --- Group envelopes by correlation_group and region ---
    env_by_group: dict[str, list[dict]] = defaultdict(list)
    env_by_region: dict[str, list[dict]] = defaultdict(list)
    for env in envelopes:
        grp = env.get("correlation_group", "unknown")
        rgn = env.get("region_id", "unknown")
        env_by_group[grp].append(env)
        env_by_region[rgn].append(env)

    # --- Build validation index ---
    val_by_envelope: dict[str, list[dict]] = defaultdict(list)
    for v in validations:
        val_by_envelope[v.get("envelope_id", "")].append(v)

    # --- Compute correlation coefficients per group ---
    clusters = _compute_correlation_clusters(
        env_by_group, review_threshold, invalid_threshold,
    )

    # --- Check for INVALID correlation in any region ---
    invalid_regions: set[str] = set()
    region_clusters: dict[str, list[dict]] = defaultdict(list)
    for env in envelopes:
        rgn = env.get("region_id", "unknown")
        grp = env.get("correlation_group", "unknown")
        region_clusters[rgn].append(env)

    for rgn, rgn_envs in region_clusters.items():
        rgn_by_group: dict[str, list[dict]] = defaultdict(list)
        for e in rgn_envs:
            rgn_by_group[e.get("correlation_group", "unknown")].append(e)
        for cluster in _compute_correlation_clusters(
            rgn_by_group, review_threshold, invalid_threshold
        ):
            if cluster["risk_level"] == "invalid":
                invalid_regions.add(rgn)

    # --- Count ACCEPT validations per group/region ---
    accept_count = 0
    accept_groups: set[str] = set()
    accept_regions: set[str] = set()
    for env in envelopes:
        env_id = env.get("envelope_id", "")
        grp = env.get("correlation_group", "unknown")
        rgn = env.get("region_id", "unknown")
        for v in val_by_envelope.get(env_id, []):
            if v.get("verdict") == "ACCEPT":
                accept_count += 1
                accept_groups.add(grp)
                accept_regions.add(rgn)

    # --- Determine online/offline regions ---
    all_known_regions: set[str] = set()
    online_regions: set[str] = set()
    offline_regions: set[str] = set()
    for sr in sync_regions:
        rgn = sr.get("region_id", "")
        all_known_regions.add(rgn)
        if sr.get("status") == "offline":
            offline_regions.add(rgn)
        else:
            online_regions.add(rgn)

    # High-assurance mesh: all known regions must participate
    min_regions = max(2, len(all_known_regions))

    # --- Compute claim state ---
    claim_state = "UNKNOWN"  # safe default
    margin = n_total - k_required

    # Region partition: any offline region → cannot reach VERIFIED
    if len(offline_regions) > 0:
        if accept_count > 0 and len(invalid_regions) == 0:
            claim_state = "UNKNOWN"  # honest: partial quorum from partition
        elif len(invalid_regions) > 0:
            claim_state = "DEGRADED"  # partition + correlation failure
        # else: UNKNOWN (no evidence at all)
    elif accept_count >= k_required and \
       len(accept_groups) >= min_corr_groups and \
       len(accept_regions) >= min_regions and \
       len(invalid_regions) == 0:
        claim_state = "VERIFIED"
    elif len(invalid_regions) > 0:
        # Correlated failure degrades trust
        if accept_count >= k_required:
            claim_state = "DEGRADED"
        else:
            claim_state = "UNKNOWN"
    elif accept_count > 0:
        # Partial evidence, not enough for quorum
        claim_state = "DEGRADED"
    # else: UNKNOWN (no evidence or no validations)

    # Effective margin
    effective_n = len(online_regions) * max(1, len(accept_groups))
    effective_margin = max(0, effective_n - k_required)

    claim = {
        "claim_id": "MESH-T0-001",
        "state": claim_state,
        "k_required": k_required,
        "n_total": n_total,
        "margin": min(margin, effective_margin),
        "correlation_groups_required": min_corr_groups,
        "correlation_group_actuals": sorted(accept_groups),
        "ttl_remaining_seconds": _min_ttl(envelopes, policy),
        "accept_count": accept_count,
        "accept_regions": sorted(accept_regions),
        "invalid_regions": sorted(invalid_regions),
    }

    # --- Update sync regions ---
    updated_sync = _update_sync_regions(sync_regions, env_by_region)

    # --- Component metrics for index ---
    corr_penalty = _correlation_penalty(clusters)
    quorum_penalty = _quorum_penalty(claim)
    ttl_penalty = _ttl_penalty(claim)

    metrics = {
        "quorum_margin": claim["margin"],
        "correlation_penalty": corr_penalty,
        "quorum_penalty": quorum_penalty,
        "ttl_penalty": ttl_penalty,
        "online_region_count": len(online_regions),
        "total_envelopes": len(envelopes),
        "total_validations": len(validations),
        "accept_count": accept_count,
    }

    return {
        "tier0_claims": [claim],
        "correlation_clusters": clusters,
        "sync_regions": updated_sync,
        "component_metrics": metrics,
    }


def compute_credibility_index(
    claims: list[dict],
    clusters: list[dict],
    sync_regions: list[dict],
    metrics: dict[str, Any],
) -> dict[str, Any]:
    """Compute credibility index from federated state.

    Mirrors the 6-component index from credibility_engine/index.py
    but uses mesh-derived inputs.
    """
    base = 100.0

    # 1. Claim integrity (tier-weighted)
    claim_penalty = 0.0
    for c in claims:
        if c.get("state") == "UNKNOWN":
            claim_penalty += 25.0
        elif c.get("state") == "DEGRADED":
            claim_penalty += 15.0

    # 2. Correlation risk penalty
    corr_penalty = metrics.get("correlation_penalty", 0.0)

    # 3. Quorum margin compression
    quorum_penalty = metrics.get("quorum_penalty", 0.0)

    # 4. TTL penalty
    ttl_penalty = metrics.get("ttl_penalty", 0.0)

    # 5. Sync plane health
    sync_penalty = 0.0
    for sr in sync_regions:
        if sr.get("status") == "offline":
            sync_penalty += 8.0
        elif sr.get("status") == "degraded":
            sync_penalty += 3.0

    # 6. Independent confirmation bonus
    bonus = 0.0
    for c in claims:
        groups = c.get("correlation_group_actuals", [])
        if len(groups) >= 3:
            bonus += 3.0

    score = max(0.0, min(100.0,
        base - claim_penalty - corr_penalty - quorum_penalty
        - ttl_penalty - sync_penalty + bonus
    ))
    score = round(score, 1)

    if score >= 95:
        band = "Stable"
    elif score >= 85:
        band = "Minor drift"
    elif score >= 70:
        band = "Elevated risk"
    elif score >= 50:
        band = "Structural degradation"
    else:
        band = "Compromised"

    return {
        "score": score,
        "band": band,
        "components": {
            "claim_integrity": -claim_penalty,
            "correlation_risk": -corr_penalty,
            "quorum_margin": -quorum_penalty,
            "ttl_health": -ttl_penalty,
            "sync_plane": -sync_penalty,
            "confirmation_bonus": bonus,
        },
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _compute_correlation_clusters(
    env_by_group: dict[str, list[dict]],
    review_threshold: float,
    invalid_threshold: float,
) -> list[dict]:
    """Compute correlation coefficients per group.

    Uses deterministic demo math: coefficient derived from value variance
    within each group's envelope payloads.
    """
    clusters = []
    groups = sorted(env_by_group.keys())

    for i, grp in enumerate(groups):
        envs = env_by_group[grp]
        values = [
            e.get("payload", {}).get("value", 0)
            for e in envs
        ]
        coeff = _demo_correlation(values)

        if coeff >= invalid_threshold:
            risk = "invalid"
        elif coeff >= review_threshold:
            risk = "review"
        else:
            risk = "low"

        clusters.append({
            "cluster_id": f"CORR-{grp}",
            "region_id": envs[0].get("region_id", "unknown") if envs else "unknown",
            "coefficient": round(coeff, 4),
            "risk_level": risk,
            "members": [e.get("envelope_id", "") for e in envs[:10]],
        })

    return clusters


def _demo_correlation(values: list[float | int]) -> float:
    """Deterministic demo correlation coefficient.

    High similarity (low variance) → high correlation → higher risk.
    Returns value between 0.0 and 1.0.
    """
    if len(values) < 3:
        return 0.0  # insufficient sample for meaningful correlation

    mean = sum(values) / len(values)
    if mean == 0:
        return 0.0

    variance = sum((v - mean) ** 2 for v in values) / len(values)
    cv = math.sqrt(variance) / abs(mean) if mean != 0 else 0.0

    # Low CV → high correlation (values are similar → shared source risk)
    # Map CV to correlation: cv=0 → corr=1.0, cv≥1 → corr≈0.0
    corr = max(0.0, 1.0 - cv)
    return round(corr, 4)


def _correlation_penalty(clusters: list[dict]) -> float:
    """Non-linear penalty from correlation clusters."""
    penalty = 0.0
    for c in clusters:
        risk = c.get("risk_level", "low")
        coeff = c.get("coefficient", 0.0)
        if risk == "invalid":
            penalty += 15.0 * coeff
        elif risk == "review":
            penalty += 5.0 * coeff
    return round(penalty, 2)


def _quorum_penalty(claim: dict) -> float:
    """Penalty when quorum margin compresses."""
    margin = claim.get("margin", 2)
    if margin <= 0:
        return 20.0
    if margin == 1:
        return 10.0
    return 0.0


def _ttl_penalty(claim: dict) -> float:
    """Penalty for TTL proximity to expiration."""
    ttl = claim.get("ttl_remaining_seconds", 900)
    if ttl <= 0:
        return 15.0
    if ttl <= 120:
        return 8.0
    if ttl <= 300:
        return 3.0
    return 0.0


def _min_ttl(envelopes: list[dict], policy: dict) -> float:
    """Compute minimum TTL remaining from envelopes."""
    ttl_policy = policy.get("ttl_policy", {})
    tier0_ttl = ttl_policy.get("tier0_seconds", 900)

    if not envelopes:
        return 0.0

    # Find oldest envelope timestamp, compute remaining TTL
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    min_remaining = tier0_ttl

    for env in envelopes:
        ts_str = env.get("timestamp", "")
        if not ts_str:
            continue
        try:
            ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
            age = (now - ts).total_seconds()
            remaining = tier0_ttl - age
            min_remaining = min(min_remaining, remaining)
        except (ValueError, TypeError):
            continue

    return max(0.0, min_remaining)


def _update_sync_regions(
    sync_regions: list[dict],
    env_by_region: dict[str, list[dict]],
) -> list[dict]:
    """Update sync region status based on envelope activity."""
    updated = []
    for sr in sync_regions:
        rgn = sr.get("region_id", "")
        envs = env_by_region.get(rgn, [])
        status = sr.get("status", "healthy")

        if status != "offline":
            if envs:
                sr_copy = dict(sr)
                sr_copy["online_count"] = len(envs)
                sr_copy["last_heartbeat"] = envs[-1].get("timestamp", "")
                sr_copy["status"] = "healthy"
                updated.append(sr_copy)
            else:
                sr_copy = dict(sr)
                sr_copy["status"] = "degraded"
                updated.append(sr_copy)
        else:
            updated.append(dict(sr))

    return updated
