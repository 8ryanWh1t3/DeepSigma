"""Drift forecasting — linear projection and threshold ETA."""

from __future__ import annotations

from typing import List

from .models import DriftForecast, DriftTrend

_SEVERITY_THRESHOLD = {"green": 5, "yellow": 10, "red": 20}


def project_drift(
    trends: List[DriftTrend],
    horizon_hours: int = 12,
) -> List[DriftForecast]:
    """Project drift severity forward based on current trends.

    Uses linear projection: projected_count = rate * horizon.
    Threshold ETA estimates when the next severity level will be reached.
    """
    forecasts: List[DriftForecast] = []

    for trend in trends:
        if trend.rate_of_change <= 0:
            forecasts.append(DriftForecast(
                fingerprint_key=trend.fingerprint_key,
                domain=trend.domain,
                horizon_hours=horizon_hours,
                projected_severity="green",
                confidence=0.8,
            ))
            continue

        projected_count = trend.rate_of_change * horizon_hours

        # Project severity
        if projected_count >= _SEVERITY_THRESHOLD["red"]:
            projected_severity = "red"
        elif projected_count >= _SEVERITY_THRESHOLD["yellow"]:
            projected_severity = "yellow"
        else:
            projected_severity = "green"

        # Threshold ETA: when will we hit the next severity level?
        threshold_eta: float | None = None
        if trend.severity_trajectory == "escalating" and trend.rate_of_change > 0:
            next_threshold = _SEVERITY_THRESHOLD.get(projected_severity, 20)
            threshold_eta = round(next_threshold / trend.rate_of_change, 2)

        # Confidence: higher rate + more data = higher confidence
        confidence = min(0.9, 0.3 + (trend.rate_of_change * 0.1))

        forecasts.append(DriftForecast(
            fingerprint_key=trend.fingerprint_key,
            domain=trend.domain,
            horizon_hours=horizon_hours,
            projected_severity=projected_severity,
            threshold_eta_hours=threshold_eta,
            confidence=round(confidence, 4),
        ))

    return forecasts
