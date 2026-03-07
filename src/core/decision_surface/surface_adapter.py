"""SurfaceAdapter — abstract base class for DecisionSurface adapters.

Every execution environment (notebook, CLI, Vantage/Foundry) implements
this ABC. Adapters handle storage and retrieval only; evaluation logic
lives in claim_event_engine.py.
"""

from __future__ import annotations

import abc
from typing import List

from .models import (
    Claim,
    DriftSignal,
    EvaluationResult,
    Event,
    Evidence,
    PatchRecommendation,
)


class SurfaceAdapter(abc.ABC):
    """Abstract base for DecisionSurface environment adapters."""

    surface_name: str = "unknown"

    @abc.abstractmethod
    def ingest_claims(self, claims: List[Claim]) -> None:
        """Store incoming claims."""

    @abc.abstractmethod
    def ingest_events(self, events: List[Event]) -> None:
        """Store incoming events."""

    @abc.abstractmethod
    def get_claims(self) -> List[Claim]:
        """Retrieve all stored claims."""

    @abc.abstractmethod
    def get_events(self) -> List[Event]:
        """Retrieve all stored events."""

    @abc.abstractmethod
    def get_evidence(self) -> List[Evidence]:
        """Retrieve all stored evidence links."""

    @abc.abstractmethod
    def store_drift_signals(self, signals: List[DriftSignal]) -> None:
        """Persist drift signals from evaluation."""

    @abc.abstractmethod
    def store_patches(self, patches: List[PatchRecommendation]) -> None:
        """Persist patch recommendations from evaluation."""

    @abc.abstractmethod
    def store_evaluation_result(self, result: EvaluationResult) -> None:
        """Persist the overall evaluation result."""
