"""Credibility Engine — Index Calculation.

Computes the Credibility Index (0-100) from current engine state.
Uses v0.6.4 calibration bands and penalty formulas.

Abstract institutional credibility architecture.
No real-world system modeled.
"""

from __future__ import annotations

from typing import Any


# -- Band thresholds -----------------------------------------------------------

BANDS = [
    (90, "Stable"),
    (75, "Minor Drift"),
    (60, "Elevated"),
    (40, "Degraded"),
    (0, "Compromised"),
]


def score_to_band(score: int) -> str:
    """Map a 0-100 score to its interpretation band."""
    for threshold, label in BANDS:
        if score >= threshold:
            return label
    return "Compromised"


# -- Penalty calculations -----------------------------------------------------

def drift_penalty(drift_events: list[dict[str, Any]]) -> int:
    """Calculate drift penalty from recent events.

    Severity weights: critical=6, high=2, medium=0.3, low=0.
    Capped at -15.
    """
    weights = {"critical": 6, "high": 2, "medium": 0.3, "low": 0}
    total = sum(weights.get(e.get("severity", "low"), 0) for e in drift_events)
    # Scale by event count — penalty based on rate, not raw accumulation
    rate_factor = min(len(drift_events) / 50, 1.0) if drift_events else 0
    penalty = -int(total * rate_factor)
    return max(-15, penalty)


def correlation_penalty(clusters: list[dict[str, Any]]) -> int:
    """Calculate correlation risk penalty.

    Critical (>0.9): -3 each. Review (>0.7): -1 each.
    Plus coefficient-based continuous penalty.
    Capped at -12.
    """
    if not clusters:
        return 0
    max_coeff = max(c.get("coefficient", 0) for c in clusters)
    critical = sum(1 for c in clusters if c.get("coefficient", 0) > 0.9)
    review = sum(1 for c in clusters if c.get("coefficient", 0) > 0.7)
    penalty = -(critical * 3 + review * 1 + int(max(0, max_coeff - 0.6) * 5))
    return max(-12, penalty)


def quorum_penalty(claims: list[dict[str, Any]]) -> int:
    """Calculate quorum margin penalty.

    UNKNOWN claims: -2 each. Margin=1 claims: -1 each.
    Capped at -10.
    """
    unknown = sum(1 for c in claims if c.get("state", "") == "UNKNOWN")
    margin_1 = sum(
        1 for c in claims
        if c.get("margin", 2) == 1 and c.get("state", "") != "UNKNOWN"
    )
    penalty = -(unknown * 2 + margin_1 * 1)
    return max(-10, penalty)


def ttl_penalty(claims: list[dict[str, Any]]) -> int:
    """Calculate TTL expiration penalty.

    Expired claims: -2 each. Near-expired (<=30min): -1 each.
    Capped at -6.
    """
    expired = sum(1 for c in claims if c.get("ttl_remaining", 240) <= 0)
    near_expired = sum(
        1 for c in claims if 0 < c.get("ttl_remaining", 240) <= 30
    )
    penalty = -(expired * 2 + near_expired * 1)
    return max(-6, penalty)


def sync_penalty(sync_regions: list[dict[str, Any]]) -> int:
    """Calculate sync plane penalty.

    CRITICAL regions: -3 each. WARN regions: -1 each.
    Capped at -9.
    """
    critical = sum(1 for r in sync_regions if r.get("status", "OK") == "CRITICAL")
    warn = sum(1 for r in sync_regions if r.get("status", "OK") == "WARN")
    penalty = -(critical * 3 + warn * 1)
    return max(-9, penalty)


# -- Main calculation ----------------------------------------------------------

def calculate_index(
    drift_events: list[dict[str, Any]],
    correlation_clusters: list[dict[str, Any]],
    claims: list[dict[str, Any]],
    sync_regions: list[dict[str, Any]],
) -> tuple[int, str]:
    """Calculate the Credibility Index and band.

    Start at 100, subtract penalties, clamp 0-100.

    Returns:
        (score, band) tuple.
    """
    score = 100

    d_pen = drift_penalty(drift_events)
    c_pen = correlation_penalty(correlation_clusters)
    q_pen = quorum_penalty(claims)
    t_pen = ttl_penalty(claims)
    s_pen = sync_penalty(sync_regions)

    score += d_pen + c_pen + q_pen + t_pen + s_pen
    score = max(0, min(100, score))

    return score, score_to_band(score)


def calculate_index_detailed(
    drift_events: list[dict[str, Any]],
    correlation_clusters: list[dict[str, Any]],
    claims: list[dict[str, Any]],
    sync_regions: list[dict[str, Any]],
) -> dict[str, Any]:
    """Calculate index with full component breakdown."""
    d_pen = drift_penalty(drift_events)
    c_pen = correlation_penalty(correlation_clusters)
    q_pen = quorum_penalty(claims)
    t_pen = ttl_penalty(claims)
    s_pen = sync_penalty(sync_regions)

    score = 100 + d_pen + c_pen + q_pen + t_pen + s_pen
    score = max(0, min(100, score))

    return {
        "score": score,
        "band": score_to_band(score),
        "components": {
            "base": 100,
            "drift_penalty": d_pen,
            "correlation_penalty": c_pen,
            "quorum_penalty": q_pen,
            "ttl_penalty": t_pen,
            "sync_penalty": s_pen,
        },
    }
