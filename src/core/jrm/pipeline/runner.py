"""Pipeline runner — orchestrate JRM stages in sequence."""

from __future__ import annotations

from typing import List, Optional

from ..types import JRMEvent, PipelineResult
from .truth import TruthStage
from .reasoning import ReasoningStage
from .drift import DriftDetectorBase, DriftStage
from .patch import PatchStage
from .memory_graph import MemoryGraphStage


class PipelineRunner:
    """Run JRM events through the full coherence pipeline.

    Stage chain: Truth → Reasoning → Drift → Patch → MemoryGraph
    """

    def __init__(
        self,
        environment_id: str = "default",
        drift_detectors: Optional[List[DriftDetectorBase]] = None,
        fp_spike_threshold: int = 5,
    ) -> None:
        self._env_id = environment_id
        self._truth = TruthStage()
        self._reasoning = ReasoningStage()
        self._drift = DriftStage(
            fp_spike_threshold=fp_spike_threshold,
            extra_detectors=drift_detectors,
        )
        self._patch = PatchStage()
        self._mg = MemoryGraphStage()

    def run(self, events: List[JRMEvent]) -> PipelineResult:
        """Process a batch of events through all 5 stages."""
        if not events:
            return PipelineResult(
                environment_id=self._env_id,
                events_processed=0,
                window_start="",
                window_end="",
            )

        # Determine window bounds
        timestamps = sorted(e.timestamp for e in events if e.timestamp)
        window_start = timestamps[0] if timestamps else ""
        window_end = timestamps[-1] if timestamps else ""

        errors: List[str] = []

        # Stage 1: Truth
        try:
            truth_out = self._truth.process(events)
        except Exception as exc:
            errors.append(f"Truth stage error: {exc}")
            truth_out = None

        claims = truth_out.claims if truth_out else []

        # Stage 2: Reasoning
        try:
            reasoning_out = self._reasoning.process(events, claims)
        except Exception as exc:
            errors.append(f"Reasoning stage error: {exc}")
            reasoning_out = None

        reasoning_results = reasoning_out.results if reasoning_out else []

        # Stage 3: Drift
        try:
            drift_out = self._drift.process(events, claims, reasoning_results)
        except Exception as exc:
            errors.append(f"Drift stage error: {exc}")
            drift_out = None

        drift_detections = drift_out.detections if drift_out else []

        # Stage 4: Patch
        try:
            patch_out = self._patch.process(drift_detections)
        except Exception as exc:
            errors.append(f"Patch stage error: {exc}")
            patch_out = None

        patches = patch_out.patches if patch_out else []

        # Stage 5: Memory Graph
        try:
            mg_out = self._mg.process(events, claims, drift_detections, patches)
        except Exception as exc:
            errors.append(f"MemoryGraph stage error: {exc}")
            mg_out = None

        return PipelineResult(
            environment_id=self._env_id,
            events_processed=len(events),
            window_start=window_start,
            window_end=window_end,
            claims=claims,
            reasoning_results=reasoning_results,
            drift_detections=drift_detections,
            patches=patches,
            mg_deltas=mg_out.mg_delta if mg_out else {},
            canon_postures=mg_out.canon_postures if mg_out else {},
            errors=errors,
        )
