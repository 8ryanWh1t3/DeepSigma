"""Drift trending — rate-of-change and trajectory analysis."""

from __future__ import annotations

from typing import Dict, List

from .models import DomainDriftView, DriftTrend


def compute_trends(
    domain_views: List[DomainDriftView],
    window_hours: int = 24,
) -> List[DriftTrend]:
    """Compute drift trends for each domain's top fingerprints.

    Since we're working with aggregated bucket data, trends are estimated
    from signal counts and severity distribution within the window.
    """
    trends: List[DriftTrend] = []

    for view in domain_views:
        for dtype, count in view.by_type.items():
            if count == 0:
                continue

            rate = count / max(window_hours, 1)

            # Direction heuristic: higher rate → increasing
            if rate > 1.0:
                direction = "increasing"
            elif rate < 0.1:
                direction = "decreasing"
            else:
                direction = "stable"

            # Severity trajectory from distribution
            red = view.by_severity.get("red", 0)
            yellow = view.by_severity.get("yellow", 0)
            if red > 0 and red >= yellow:
                trajectory = "escalating"
            elif red == 0 and yellow == 0:
                trajectory = "stable"
            else:
                trajectory = "de-escalating" if red == 0 else "stable"

            trends.append(DriftTrend(
                fingerprint_key=f"{view.domain}:{dtype}",
                domain=view.domain,
                window_hours=window_hours,
                rate_of_change=round(rate, 4),
                direction=direction,
                severity_trajectory=trajectory,
            ))

    return trends
