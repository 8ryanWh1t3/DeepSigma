"""Remediation prioritization — urgency x impact ranking."""

from __future__ import annotations

from typing import List

from .models import DriftTrend, DriftForecast, RemediationPriority

_SEVERITY_URGENCY = {"green": 0.2, "yellow": 0.5, "red": 1.0}


def rank_remediations(
    trends: List[DriftTrend],
    forecasts: List[DriftForecast],
) -> List[RemediationPriority]:
    """Rank remediation priorities by urgency x impact.

    Urgency comes from current severity trajectory and forecast.
    Impact comes from rate of change and correlation breadth.
    """
    # Build forecast lookup
    forecast_map = {f.fingerprint_key: f for f in forecasts}
    priorities: List[RemediationPriority] = []

    for trend in trends:
        forecast = forecast_map.get(trend.fingerprint_key)

        # Urgency: based on trajectory and forecast severity
        urgency = 0.3  # baseline
        if trend.severity_trajectory == "escalating":
            urgency += 0.4
        if forecast and forecast.projected_severity == "red":
            urgency += 0.3
        elif forecast and forecast.projected_severity == "yellow":
            urgency += 0.1
        urgency = min(1.0, urgency)

        # Impact: based on rate of change
        impact = min(1.0, trend.rate_of_change / 5.0)

        # Priority score
        priority_score = round(urgency * impact, 4)

        # Recommended action
        if urgency >= 0.8:
            action = "immediate_investigation"
        elif urgency >= 0.5:
            action = "scheduled_review"
        else:
            action = "monitor"

        current_severity = "green"
        if trend.severity_trajectory == "escalating":
            current_severity = "yellow"
        if forecast and forecast.projected_severity == "red":
            current_severity = "red"

        priorities.append(RemediationPriority(
            fingerprint_key=trend.fingerprint_key,
            domain=trend.domain,
            urgency=round(urgency, 4),
            impact=round(impact, 4),
            priority_score=priority_score,
            recommended_action=action,
            current_severity=current_severity,
        ))

    # Sort by priority score descending
    priorities.sort(key=lambda p: p.priority_score, reverse=True)
    return priorities
