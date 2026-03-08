"""RadarAdapter — abstract base class for Drift Radar storage.

Mirrors the SurfaceAdapter pattern from DecisionSurface.
Adapters handle persistence of radar data; analysis logic lives in runtime.py.
"""

from __future__ import annotations

import abc
from typing import Dict, List

from .models import DriftCorrelation, DomainDriftView, RadarSnapshot


class RadarAdapter(abc.ABC):
    """Abstract base for Drift Radar environment adapters."""

    adapter_name: str = "unknown"

    @abc.abstractmethod
    def store_domain_view(self, view: DomainDriftView) -> None:
        """Persist a domain drift view."""

    @abc.abstractmethod
    def get_domain_views(self) -> List[DomainDriftView]:
        """Retrieve all stored domain views."""

    @abc.abstractmethod
    def store_correlations(self, correlations: List[DriftCorrelation]) -> None:
        """Persist drift correlations."""

    @abc.abstractmethod
    def get_correlations(self) -> List[DriftCorrelation]:
        """Retrieve all stored correlations."""

    @abc.abstractmethod
    def store_snapshot(self, snapshot: RadarSnapshot) -> None:
        """Persist a radar snapshot."""

    @abc.abstractmethod
    def get_snapshots(self) -> List[RadarSnapshot]:
        """Retrieve all stored snapshots."""

    @abc.abstractmethod
    def get_raw_signals(self, domain: str) -> List[Dict]:
        """Retrieve raw drift signals for a domain."""

    @abc.abstractmethod
    def store_raw_signals(self, domain: str, signals: List[Dict]) -> None:
        """Persist raw drift signals for a domain."""
