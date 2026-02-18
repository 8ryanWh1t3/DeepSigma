"""Standalone Drift Detector — decoupled from Exhaust Inbox.

Provides a DriftDetector class that can be called independently of the
exhaust refine workflow. Reuses the same detection logic from exhaust_refiner.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from dashboard.server.models_exhaust import (
    DecisionEpisode,
    DriftSignal,
    MemoryItem,
    TruthItem,
)
from engine.exhaust_refiner import detect_drift, extract_memory, extract_truth


class DriftDetector:
    """Standalone drift detection service.

    Usage:
        detector = DriftDetector(canon_path=Path("/app/data/mg/memory_graph.jsonl"))
        signals = detector.detect_from_episode(episode_dict)
    """

    def __init__(self, canon_path: Optional[Path] = None) -> None:
        self.canon_path = canon_path or Path(
            os.environ.get("DATA_DIR", "/app/data")
        ) / "mg" / "memory_graph.jsonl"

    def detect_from_episode(self, episode_dict: Dict[str, Any]) -> List[DriftSignal]:
        """Full pipeline: extract truth/memory, then detect drift."""
        if isinstance(episode_dict, DecisionEpisode):
            episode = episode_dict
        else:
            episode = DecisionEpisode(**episode_dict)
        truth = extract_truth(episode)
        memory = extract_memory(episode)
        return detect_drift(episode, truth, memory, canon_path=self.canon_path)

    def detect_from_claims(
        self,
        truth: List[TruthItem],
        memory: List[MemoryItem],
        episode_id: str = "",
    ) -> List[DriftSignal]:
        """Detect drift from pre-extracted claims."""
        episode = DecisionEpisode(episode_id=episode_id, events=[])
        return detect_drift(episode, truth, memory, canon_path=self.canon_path)
