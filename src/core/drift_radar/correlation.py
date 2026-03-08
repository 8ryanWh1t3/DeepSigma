"""Cross-domain drift correlation engine."""

from __future__ import annotations

import uuid
from typing import Dict, List, Optional

from .models import DomainDriftView, DriftCorrelation

# Severity rank for amplification
_SEVERITY_RANK = {"green": 0, "yellow": 1, "red": 2}
_SEVERITY_NAMES = ["green", "yellow", "red"]


def find_correlations(
    domain_views: List[DomainDriftView],
    temporal_window_ms: float = 60_000,
) -> List[DriftCorrelation]:
    """Find cross-domain drift correlations.

    Correlates drift types that appear across multiple domains.
    """
    correlations: List[DriftCorrelation] = []

    for i, view_a in enumerate(domain_views):
        for j in range(i + 1, len(domain_views)):
            view_b = domain_views[j]

            # Find shared drift types
            shared_types = set(view_a.by_type) & set(view_b.by_type)
            for dtype in shared_types:
                count_a = view_a.by_type[dtype]
                count_b = view_b.by_type[dtype]
                total = count_a + count_b
                if total == 0:
                    continue

                # Correlation strength: min/max ratio (closer to 1.0 = stronger)
                strength = min(count_a, count_b) / max(count_a, count_b)

                correlations.append(DriftCorrelation(
                    correlation_id=f"DC-{uuid.uuid4().hex[:8]}",
                    domain_a=view_a.domain,
                    domain_b=view_b.domain,
                    drift_type_a=dtype,
                    drift_type_b=dtype,
                    correlation_strength=round(strength, 4),
                    temporal_proximity_ms=temporal_window_ms,
                ))

    return correlations


def amplify_severity_score(
    base_severity: str,
    correlations: List[DriftCorrelation],
    threshold: float = 0.5,
) -> str:
    """Amplify severity when correlated drift exceeds threshold.

    If any correlation strength exceeds threshold, severity escalates one level.
    """
    rank = _SEVERITY_RANK.get(base_severity, 0)
    for corr in correlations:
        if corr.correlation_strength >= threshold and rank < 2:
            rank += 1
            break
    return _SEVERITY_NAMES[rank]
