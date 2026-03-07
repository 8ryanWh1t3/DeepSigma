"""NotebookAdapter — in-memory reference implementation.

MVP adapter demonstrating the full DecisionSurface lifecycle.
All data is held in-memory; suitable for notebooks and testing.
"""

from __future__ import annotations

from typing import List, Optional

from .models import (
    Claim,
    DriftSignal,
    EvaluationResult,
    Event,
    Evidence,
    PatchRecommendation,
)
from .surface_adapter import SurfaceAdapter


class NotebookAdapter(SurfaceAdapter):
    """In-memory surface adapter for notebooks and interactive use."""

    surface_name = "notebook"

    def __init__(self) -> None:
        self._claims: List[Claim] = []
        self._events: List[Event] = []
        self._evidence: List[Evidence] = []
        self._drift_signals: List[DriftSignal] = []
        self._patches: List[PatchRecommendation] = []
        self._evaluation_result: Optional[EvaluationResult] = None

    def ingest_claims(self, claims: List[Claim]) -> None:
        self._claims.extend(claims)

    def ingest_events(self, events: List[Event]) -> None:
        self._events.extend(events)

    def get_claims(self) -> List[Claim]:
        return list(self._claims)

    def get_events(self) -> List[Event]:
        return list(self._events)

    def get_evidence(self) -> List[Evidence]:
        return list(self._evidence)

    def store_drift_signals(self, signals: List[DriftSignal]) -> None:
        self._drift_signals.extend(signals)

    def store_patches(self, patches: List[PatchRecommendation]) -> None:
        self._patches.extend(patches)

    def store_evaluation_result(self, result: EvaluationResult) -> None:
        self._evaluation_result = result
