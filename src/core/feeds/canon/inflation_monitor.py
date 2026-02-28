"""Canon inflation monitor — threshold engine for canon health.

Monitors per-domain metrics:
- claim_count: claims per canon entry (threshold > 50)
- contradiction_density: fraction of claims with contradictions (threshold > 10%)
- avg_claim_age_days: average age in days (threshold > 30)
- supersedes_depth: max supersedes chain length (threshold > 5)
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


# Default thresholds
DEFAULT_THRESHOLDS = {
    "claim_count": 50,
    "contradiction_density": 0.10,
    "avg_claim_age_days": 30,
    "supersedes_depth": 5,
}


class InflationMetrics:
    """Computed inflation metrics for a domain or canon entry."""

    def __init__(
        self,
        domain: str = "",
        claim_count: int = 0,
        contradiction_density: float = 0.0,
        avg_claim_age_days: float = 0.0,
        supersedes_depth: int = 0,
    ) -> None:
        self.domain = domain
        self.claim_count = claim_count
        self.contradiction_density = contradiction_density
        self.avg_claim_age_days = avg_claim_age_days
        self.supersedes_depth = supersedes_depth

    def to_dict(self) -> Dict[str, Any]:
        return {
            "domain": self.domain,
            "claimCount": self.claim_count,
            "contradictionDensity": self.contradiction_density,
            "avgClaimAgeDays": self.avg_claim_age_days,
            "supersedesDepth": self.supersedes_depth,
        }


def check_inflation(
    metrics: InflationMetrics,
    thresholds: Optional[Dict[str, float]] = None,
) -> List[Dict[str, Any]]:
    """Check inflation metrics against thresholds.

    Returns a list of drift signals for each breached threshold.
    """
    t = {**DEFAULT_THRESHOLDS, **(thresholds or {})}
    breaches: List[Dict[str, Any]] = []

    if metrics.claim_count > t["claim_count"]:
        breaches.append(_make_signal(
            metrics.domain, "claim_count",
            f"Claim count {metrics.claim_count} exceeds threshold {t['claim_count']}",
        ))

    if metrics.contradiction_density > t["contradiction_density"]:
        breaches.append(_make_signal(
            metrics.domain, "contradiction_density",
            f"Contradiction density {metrics.contradiction_density:.1%} "
            f"exceeds threshold {t['contradiction_density']:.0%}",
        ))

    if metrics.avg_claim_age_days > t["avg_claim_age_days"]:
        breaches.append(_make_signal(
            metrics.domain, "avg_claim_age",
            f"Avg claim age {metrics.avg_claim_age_days:.0f}d "
            f"exceeds threshold {t['avg_claim_age_days']}d",
        ))

    if metrics.supersedes_depth > t["supersedes_depth"]:
        breaches.append(_make_signal(
            metrics.domain, "supersedes_depth",
            f"Supersedes depth {metrics.supersedes_depth} "
            f"exceeds threshold {t['supersedes_depth']}",
        ))

    return breaches


def _make_signal(domain: str, metric: str, detail: str) -> Dict[str, Any]:
    return {
        "driftId": f"DS-inflation-{uuid.uuid4().hex[:8]}",
        "driftType": "canon_inflation",
        "severity": "yellow",
        "detectedAt": datetime.now(timezone.utc).isoformat(),
        "evidenceRefs": [f"domain:{domain}", f"metric:{metric}"],
        "fingerprint": {"key": f"inflation:{domain}:{metric}", "version": "1"},
        "notes": detail,
    }
