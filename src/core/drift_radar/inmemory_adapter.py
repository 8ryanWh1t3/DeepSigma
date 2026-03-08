"""In-memory RadarAdapter — default implementation for testing and local use."""

from __future__ import annotations

from typing import Dict, List

from .models import DriftCorrelation, DomainDriftView, RadarSnapshot
from .radar_adapter import RadarAdapter


class InMemoryRadarAdapter(RadarAdapter):
    """In-memory store for drift radar data."""

    adapter_name = "inmemory"

    def __init__(self) -> None:
        self._domain_views: List[DomainDriftView] = []
        self._correlations: List[DriftCorrelation] = []
        self._snapshots: List[RadarSnapshot] = []
        self._raw_signals: Dict[str, List[Dict]] = {}

    def store_domain_view(self, view: DomainDriftView) -> None:
        # Replace existing view for same domain
        self._domain_views = [v for v in self._domain_views if v.domain != view.domain]
        self._domain_views.append(view)

    def get_domain_views(self) -> List[DomainDriftView]:
        return list(self._domain_views)

    def store_correlations(self, correlations: List[DriftCorrelation]) -> None:
        self._correlations.extend(correlations)

    def get_correlations(self) -> List[DriftCorrelation]:
        return list(self._correlations)

    def store_snapshot(self, snapshot: RadarSnapshot) -> None:
        self._snapshots.append(snapshot)

    def get_snapshots(self) -> List[RadarSnapshot]:
        return list(self._snapshots)

    def get_raw_signals(self, domain: str) -> List[Dict]:
        return list(self._raw_signals.get(domain, []))

    def store_raw_signals(self, domain: str, signals: List[Dict]) -> None:
        existing = self._raw_signals.get(domain, [])
        existing.extend(signals)
        self._raw_signals[domain] = existing
