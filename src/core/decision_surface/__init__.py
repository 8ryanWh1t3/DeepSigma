"""DecisionSurface — portable Coherence Ops runtime.

Provides a generic adapter/runtime layer for executing claim-event
evaluation, drift detection, and patching across external environments
(notebook, CLI, Vantage/Foundry).
"""

from __future__ import annotations

from .claim_event_engine import (
    build_memory_graph_update,
    build_patch_recommendation,
    compute_blast_radius,
    detect_contradictions,
    detect_expired_assumptions,
    evaluate,
    match_events_to_claims,
)
from .cli_adapter import CLIAdapter
from .models import (
    Assumption,
    Claim,
    ClaimStatus,
    DecisionArtifact,
    DriftSignal,
    EvaluationResult,
    Event,
    Evidence,
    MemoryGraphUpdate,
    PatchRecommendation,
)
from .notebook_adapter import NotebookAdapter
from .runtime import DecisionSurface
from .surface_adapter import SurfaceAdapter
from .vantage_adapter import VantageAdapter

__all__ = [
    # models
    "Assumption",
    "Claim",
    "ClaimStatus",
    "DecisionArtifact",
    "DriftSignal",
    "EvaluationResult",
    "Event",
    "Evidence",
    "MemoryGraphUpdate",
    "PatchRecommendation",
    # adapters
    "CLIAdapter",
    "NotebookAdapter",
    "SurfaceAdapter",
    "VantageAdapter",
    # engine
    "build_memory_graph_update",
    "build_patch_recommendation",
    "compute_blast_radius",
    "detect_contradictions",
    "detect_expired_assumptions",
    "evaluate",
    "match_events_to_claims",
    # runtime
    "DecisionSurface",
]
