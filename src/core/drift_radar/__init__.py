"""Drift Radar -- cross-domain drift intelligence surface.

Aggregates drift signals from all 6 domain modes, computes correlations,
trends, forecasts, and remediation priorities. Architecturally mirrors
DecisionSurface: sits above domains, uses an adapter ABC.
"""

from __future__ import annotations

from .correlation import amplify_severity_score, find_correlations
from .forecasting import project_drift
from .inmemory_adapter import InMemoryRadarAdapter
from .models import (
    DomainDriftView,
    DriftCorrelation,
    DriftForecast,
    DriftTrend,
    RadarSnapshot,
    RemediationPriority,
)
from .prioritization import rank_remediations
from .radar_adapter import RadarAdapter
from .runtime import DriftRadar
from .trending import compute_trends

__all__ = [
    # models
    "DomainDriftView",
    "DriftCorrelation",
    "DriftForecast",
    "DriftTrend",
    "RadarSnapshot",
    "RemediationPriority",
    # adapters
    "InMemoryRadarAdapter",
    "RadarAdapter",
    # engine
    "amplify_severity_score",
    "compute_trends",
    "find_correlations",
    "project_drift",
    "rank_remediations",
    # runtime
    "DriftRadar",
]
