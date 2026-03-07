"""CLIAdapter — in-memory adapter with JSON serialization for CLI output.

Stores data in memory like NotebookAdapter, adds ``to_json()`` for
structured output suitable for command-line tooling.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any, List, Optional

from .models import (
    Claim,
    DriftSignal,
    EvaluationResult,
    Event,
    Evidence,
    PatchRecommendation,
)
from .surface_adapter import SurfaceAdapter


class CLIAdapter(SurfaceAdapter):
    """In-memory surface adapter with JSON serialization for CLI use."""

    surface_name = "cli"

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

    def to_json(self) -> str:
        """Serialize current state to JSON for CLI output."""
        data: dict[str, Any] = {
            "claims": [asdict(c) for c in self._claims],
            "events": [asdict(e) for e in self._events],
            "evidence": [asdict(e) for e in self._evidence],
            "driftSignals": [asdict(s) for s in self._drift_signals],
            "patches": [asdict(p) for p in self._patches],
        }
        if self._evaluation_result:
            data["evaluationResult"] = {
                "claimsEvaluated": self._evaluation_result.claims_evaluated,
                "satisfied": self._evaluation_result.satisfied,
                "atRisk": self._evaluation_result.at_risk,
                "drifted": self._evaluation_result.drifted,
                "pending": self._evaluation_result.pending,
            }
        return json.dumps(data, indent=2, default=str)
