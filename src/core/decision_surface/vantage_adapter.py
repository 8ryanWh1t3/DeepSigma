"""VantageAdapter — honest stub for Army Vantage / Foundry integration.

All methods raise NotImplementedError with descriptive messages pointing
to docs/decision_surface.md for the integration roadmap.
"""

from __future__ import annotations

from typing import List

from .models import (
    Claim,
    DriftSignal,
    EvaluationResult,
    Event,
    Evidence,
    PatchRecommendation,
)
from .surface_adapter import SurfaceAdapter

_MSG = (
    "VantageAdapter requires Foundry SDK integration — "
    "see docs/decision_surface.md for roadmap"
)


class VantageAdapter(SurfaceAdapter):
    """Stub adapter for Army Vantage / Palantir Foundry.

    Every method raises NotImplementedError until the Foundry SDK
    integration is implemented.
    """

    surface_name = "vantage"

    def ingest_claims(self, claims: List[Claim]) -> None:
        raise NotImplementedError(_MSG)

    def ingest_events(self, events: List[Event]) -> None:
        raise NotImplementedError(_MSG)

    def get_claims(self) -> List[Claim]:
        raise NotImplementedError(_MSG)

    def get_events(self) -> List[Event]:
        raise NotImplementedError(_MSG)

    def get_evidence(self) -> List[Evidence]:
        raise NotImplementedError(_MSG)

    def store_drift_signals(self, signals: List[DriftSignal]) -> None:
        raise NotImplementedError(_MSG)

    def store_patches(self, patches: List[PatchRecommendation]) -> None:
        raise NotImplementedError(_MSG)

    def store_evaluation_result(self, result: EvaluationResult) -> None:
        raise NotImplementedError(_MSG)
