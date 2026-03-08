"""Drift Radar models -- dataclasses for cross-domain drift intelligence.

Defines the object model for domain views, correlations, trends,
forecasts, remediation priorities, and radar snapshots.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class DomainDriftView:
    """Aggregated drift view for a single domain."""

    domain: str
    total_signals: int = 0
    by_type: Dict[str, int] = field(default_factory=dict)
    by_severity: Dict[str, int] = field(default_factory=dict)
    worst_severity: str = "green"
    top_fingerprints: List[str] = field(default_factory=list)


@dataclass
class DriftCorrelation:
    """Cross-domain drift correlation."""

    correlation_id: str
    domain_a: str
    domain_b: str
    drift_type_a: str
    drift_type_b: str
    correlation_strength: float  # 0.0-1.0
    temporal_proximity_ms: float = 0.0
    amplified_severity: Optional[str] = None


@dataclass
class DriftTrend:
    """Trending analysis for a drift fingerprint."""

    fingerprint_key: str
    domain: str
    window_hours: int = 24
    rate_of_change: float = 0.0  # signals/hour
    direction: str = "stable"  # increasing, decreasing, stable
    severity_trajectory: str = "stable"  # escalating, de-escalating, stable


@dataclass
class DriftForecast:
    """Forward projection for a drift fingerprint."""

    fingerprint_key: str
    domain: str
    horizon_hours: int = 12
    projected_severity: str = "green"
    threshold_eta_hours: Optional[float] = None
    confidence: float = 0.0


@dataclass
class RemediationPriority:
    """Prioritized remediation recommendation."""

    fingerprint_key: str
    domain: str
    urgency: float = 0.0  # 0.0-1.0
    impact: float = 0.0  # 0.0-1.0
    priority_score: float = 0.0  # urgency * impact
    recommended_action: str = ""
    current_severity: str = "green"


@dataclass
class RadarSnapshot:
    """Point-in-time snapshot of cross-domain drift state."""

    snapshot_id: str
    captured_at: str
    domain_views: List[DomainDriftView] = field(default_factory=list)
    correlations: List[DriftCorrelation] = field(default_factory=list)
    trends: List[DriftTrend] = field(default_factory=list)
    forecasts: List[DriftForecast] = field(default_factory=list)
    priorities: List[RemediationPriority] = field(default_factory=list)
    overall_health: str = "green"  # green, yellow, red
