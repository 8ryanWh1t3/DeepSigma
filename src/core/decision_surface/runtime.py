"""DecisionSurface runtime — orchestration layer wiring adapter + engine.

The DecisionSurface class provides a high-level API for ingesting
claims/events, running evaluation, and sealing decision artifacts.
"""

from __future__ import annotations

import uuid
from dataclasses import asdict
from datetime import datetime, timezone
from typing import List, Optional

from . import claim_event_engine
from .models import (
    Assumption,
    Claim,
    DecisionArtifact,
    EvaluationResult,
    Event,
)
from .surface_adapter import SurfaceAdapter


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class DecisionSurface:
    """Orchestration class wiring a SurfaceAdapter to the claim-event engine."""

    def __init__(self, adapter: SurfaceAdapter) -> None:
        self._adapter = adapter

    @classmethod
    def from_surface(cls, name: str) -> DecisionSurface:
        """Factory method — create a DecisionSurface for a named adapter.

        Supported names: ``notebook``, ``cli``, ``vantage``.
        Raises ValueError for unknown surface names.
        """
        if name == "notebook":
            from .notebook_adapter import NotebookAdapter
            return cls(NotebookAdapter())
        elif name == "cli":
            from .cli_adapter import CLIAdapter
            return cls(CLIAdapter())
        elif name == "vantage":
            from .vantage_adapter import VantageAdapter
            return cls(VantageAdapter())
        else:
            raise ValueError(f"Unknown surface: {name!r}")

    @property
    def surface_name(self) -> str:
        """The name of the underlying adapter."""
        return self._adapter.surface_name

    def ingest(
        self,
        claims: Optional[List[Claim]] = None,
        events: Optional[List[Event]] = None,
    ) -> None:
        """Ingest claims and/or events into the adapter."""
        if claims:
            self._adapter.ingest_claims(claims)
        if events:
            self._adapter.ingest_events(events)

    def evaluate(
        self,
        assumptions: Optional[List[Assumption]] = None,
    ) -> EvaluationResult:
        """Run the full evaluation pipeline.

        1. Retrieve claims + events from the adapter.
        2. Delegate to ``claim_event_engine.evaluate``.
        3. Store drift signals, patches, and result via adapter.
        4. Return the EvaluationResult.
        """
        claims = self._adapter.get_claims()
        events = self._adapter.get_events()

        result = claim_event_engine.evaluate(claims, events, assumptions)

        if result.drift_signals:
            self._adapter.store_drift_signals(result.drift_signals)
        if result.patches:
            self._adapter.store_patches(result.patches)
        self._adapter.store_evaluation_result(result)

        return result

    def seal(self) -> DecisionArtifact:
        """Seal the current surface state into a DecisionArtifact.

        Uses ``core.authority.seal_and_hash.seal`` for cryptographic
        immutability.
        """
        from core.authority.seal_and_hash import seal as seal_fn

        artifact = DecisionArtifact(
            artifact_id=f"ART-{uuid.uuid4().hex[:8]}",
            claims=self._adapter.get_claims(),
            events=self._adapter.get_events(),
            evidence=self._adapter.get_evidence(),
        )

        # Build hashable payload
        payload = {
            "artifactId": artifact.artifact_id,
            "claims": [asdict(c) for c in artifact.claims],
            "events": [asdict(e) for e in artifact.events],
            "evidence": [asdict(e) for e in artifact.evidence],
        }

        seal_result = seal_fn(payload)
        artifact.sealed_at = seal_result["sealedAt"]
        artifact.seal_hash = seal_result["hash"]

        return artifact

    def get_adapter(self) -> SurfaceAdapter:
        """Return the underlying adapter instance."""
        return self._adapter
