"""DriftRadar — cross-domain drift intelligence runtime.

Aggregates drift signals from all domains, computes correlations,
trends, forecasts, and remediation priorities. Architecturally mirrors
DecisionSurface: sits above domain modes, uses an adapter ABC.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .correlation import amplify_severity_score, find_correlations
from .forecasting import project_drift
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
from .trending import compute_trends


class DriftRadar:
    """Cross-domain drift intelligence orchestrator.

    Usage:
        from core.drift_radar import DriftRadar, InMemoryRadarAdapter
        radar = DriftRadar(InMemoryRadarAdapter())
        radar.ingest_domain_signals("intelops", signals)
        snapshot = radar.snapshot()
    """

    def __init__(self, adapter: RadarAdapter) -> None:
        self._adapter = adapter

    @property
    def adapter_name(self) -> str:
        return self._adapter.adapter_name

    def ingest_domain_signals(self, domain: str, signals: List[Dict]) -> None:
        """Ingest raw drift signals for a single domain."""
        self._adapter.store_raw_signals(domain, signals)

        # Build domain view from raw signals
        by_type: Dict[str, int] = {}
        by_severity: Dict[str, int] = {}
        worst = "green"
        severity_rank = {"green": 0, "yellow": 1, "red": 2}
        fingerprints: List[str] = []

        for sig in signals:
            dtype = sig.get("driftType", sig.get("drift_type", "unknown"))
            severity = sig.get("severity", "green")
            by_type[dtype] = by_type.get(dtype, 0) + 1
            by_severity[severity] = by_severity.get(severity, 0) + 1
            if severity_rank.get(severity, 0) > severity_rank.get(worst, 0):
                worst = severity

            fp = sig.get("fingerprint", {})
            if isinstance(fp, dict) and fp.get("key"):
                fingerprints.append(fp["key"])

        view = DomainDriftView(
            domain=domain,
            total_signals=len(signals),
            by_type=by_type,
            by_severity=by_severity,
            worst_severity=worst,
            top_fingerprints=fingerprints[:10],
        )
        self._adapter.store_domain_view(view)

    def ingest_all_domains(
        self, collectors: Dict[str, Any],
    ) -> None:
        """Ingest signals from multiple DriftSignalCollectors.

        Args:
            collectors: Dict mapping domain name to DriftSignalCollector instances.
        """
        for domain, collector in collectors.items():
            summary = collector.summarise()
            signals = []
            for bucket in summary.buckets:
                signals.append({
                    "driftType": bucket.drift_type,
                    "severity": bucket.worst_severity,
                    "count": bucket.count,
                    "fingerprint": {"key": bucket.fingerprint_key},
                })
            self.ingest_domain_signals(domain, signals)

    def correlate(self) -> List[DriftCorrelation]:
        """Find cross-domain drift correlations."""
        views = self._adapter.get_domain_views()
        correlations = find_correlations(views)
        if correlations:
            self._adapter.store_correlations(correlations)
        return correlations

    def compute_trends(self, window_hours: int = 24) -> List[DriftTrend]:
        """Compute trends from current domain views."""
        views = self._adapter.get_domain_views()
        return compute_trends(views, window_hours)

    def forecast(self, horizon_hours: int = 12) -> List[DriftForecast]:
        """Project drift forward based on trends."""
        trends = self.compute_trends()
        return project_drift(trends, horizon_hours)

    def prioritize(self) -> List[RemediationPriority]:
        """Rank remediation priorities."""
        trends = self.compute_trends()
        forecasts = project_drift(trends)
        return rank_remediations(trends, forecasts)

    def amplify_severity(
        self,
        base_severity: str,
        correlations: Optional[List[DriftCorrelation]] = None,
    ) -> str:
        """Amplify severity based on cross-domain correlations."""
        if correlations is None:
            correlations = self._adapter.get_correlations()
        return amplify_severity_score(base_severity, correlations)

    def snapshot(self) -> RadarSnapshot:
        """Capture a point-in-time radar snapshot."""
        views = self._adapter.get_domain_views()
        correlations = self.correlate()
        trends = self.compute_trends()
        forecasts = project_drift(trends)
        priorities = rank_remediations(trends, forecasts)

        # Determine overall health
        overall = "green"
        for view in views:
            if view.worst_severity == "red":
                overall = "red"
                break
            if view.worst_severity == "yellow":
                overall = "yellow"

        now = datetime.now(timezone.utc).isoformat()
        snap = RadarSnapshot(
            snapshot_id=f"SNAP-{uuid.uuid4().hex[:8]}",
            captured_at=now,
            domain_views=views,
            correlations=correlations,
            trends=trends,
            forecasts=forecasts,
            priorities=priorities,
            overall_health=overall,
        )
        self._adapter.store_snapshot(snap)
        return snap
