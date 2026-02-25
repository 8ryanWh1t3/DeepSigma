"""Coherence Scorer — compute a unified coherence score.

Takes inputs from all four artifact layers (DLR, RS, DS, MG) and
produces a single 0-100 coherence score plus per-dimension breakdown.

Dimensions:
    - Policy adherence  (DLR: episodes with valid policy stamps)
    - Outcome health     (RS: success rate, verification pass rate)
    - Drift control      (DS: recurring drift, unresolved red signals)
    - Memory completeness (MG: graph coverage, orphan ratio)
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .decision_log import DLRBuilder
from .drift_signal import DriftSignalCollector
from .memory_graph import MemoryGraph
from .reflection import ReflectionSession

logger = logging.getLogger(__name__)


@dataclass
class DimensionScore:
    """Score for a single coherence dimension."""

    name: str
    score: float  # 0.0 – 100.0
    weight: float  # 0.0 – 1.0
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CoherenceReport:
    """Full coherence score report."""

    computed_at: str
    overall_score: float
    grade: str  # A / B / C / D / F
    dimensions: List[DimensionScore]
    metadata: Dict[str, Any] = field(default_factory=dict)


GRADE_THRESHOLDS = [
    (90, "A"),
    (75, "B"),
    (60, "C"),
    (40, "D"),
    (0, "F"),
]


def _grade(score: float) -> str:
    """Map a 0-100 score to a letter grade."""
    for threshold, letter in GRADE_THRESHOLDS:
        if score >= threshold:
            return letter
    return "F"


class CoherenceScorer:
    """Compute coherence score from the four artifact layers.

    Usage:
        scorer = CoherenceScorer(
            dlr_builder=dlr,
            rs=reflection_session,
            ds=drift_collector,
            mg=memory_graph,
        )
        report = scorer.score()
    """

    DEFAULT_WEIGHTS = {
        "policy_adherence": 0.25,
        "outcome_health": 0.30,
        "drift_control": 0.25,
        "memory_completeness": 0.20,
    }

    def __init__(
        self,
        dlr_builder: Optional[DLRBuilder] = None,
        rs: Optional[ReflectionSession] = None,
        ds: Optional[DriftSignalCollector] = None,
        mg: Optional[MemoryGraph] = None,
        weights: Optional[Dict[str, float]] = None,
    ) -> None:
        self.dlr = dlr_builder
        self.rs = rs
        self.ds = ds
        self.mg = mg
        self.weights = weights or dict(self.DEFAULT_WEIGHTS)

    def score(self) -> CoherenceReport:
        """Compute the full coherence report."""
        dims = [
            self._score_policy_adherence(),
            self._score_outcome_health(),
            self._score_drift_control(),
            self._score_memory_completeness(),
        ]
        overall = sum(d.score * d.weight for d in dims)
        return CoherenceReport(
            computed_at=datetime.now(timezone.utc).isoformat(),
            overall_score=round(overall, 2),
            grade=_grade(overall),
            dimensions=dims,
        )

    def to_json(self, indent: int = 2) -> str:
        """Score and serialise to JSON."""
        return json.dumps(asdict(self.score()), indent=indent)

    # ------------------------------------------------------------------
    # Per-dimension scoring
    # ------------------------------------------------------------------

    def _score_policy_adherence(self) -> DimensionScore:
        """Score based on DLR policy stamp coverage."""
        weight = self.weights.get("policy_adherence", 0.25)
        if self.dlr is None or not self.dlr.entries:
            return DimensionScore("policy_adherence", 50.0, weight,
                                  details={"reason": "no DLR data"})
        entries = self.dlr.entries
        stamped = sum(1 for e in entries if e.policy_stamp)
        ratio = stamped / len(entries)
        return DimensionScore("policy_adherence", round(ratio * 100, 2), weight,
                              details={"stamped": stamped, "total": len(entries)})

    def _score_outcome_health(self) -> DimensionScore:
        """Score based on RS outcome distribution and verification."""
        weight = self.weights.get("outcome_health", 0.30)
        if self.rs is None:
            return DimensionScore("outcome_health", 50.0, weight,
                                  details={"reason": "no RS data"})
        summary = self.rs.summarise()
        total = summary.episode_count
        if total == 0:
            return DimensionScore("outcome_health", 50.0, weight,
                                  details={"reason": "no episodes"})

        success = summary.outcome_distribution.get("success", 0)
        success_rate = success / total
        verify_score = summary.verification_pass_rate
        combined = (success_rate * 0.6 + verify_score * 0.4) * 100
        return DimensionScore("outcome_health", round(combined, 2), weight,
                              details={
                                  "success_rate": round(success_rate, 4),
                                  "verification_pass_rate": verify_score,
                              })

    def _score_drift_control(self) -> DimensionScore:
        """Score based on DS drift volume and severity."""
        weight = self.weights.get("drift_control", 0.25)
        if self.ds is None or self.ds.event_count == 0:
            return DimensionScore("drift_control", 100.0, weight,
                                  details={"reason": "no drift signals"})
        summary = self.ds.summarise()
        red_count = summary.by_severity.get("red", 0)
        recurring = len(summary.top_recurring)
        total = summary.total_signals

        # Penalise red severity and recurring patterns
        penalty = min(100, (red_count * 15) + (recurring * 10) + (total * 2))
        score_val = max(0, 100 - penalty)
        return DimensionScore("drift_control", round(score_val, 2), weight,
                              details={
                                  "total_signals": total,
                                  "red_count": red_count,
                                  "recurring_patterns": recurring,
                              })

    def _score_memory_completeness(self) -> DimensionScore:
        """Score based on MG graph coverage."""
        weight = self.weights.get("memory_completeness", 0.20)
        if self.mg is None:
            return DimensionScore("memory_completeness", 0.0, weight,
                                  details={"reason": "no MG data"})
        stats = self.mg.query("stats")
        total_nodes = stats.get("total_nodes", 0)
        episode_nodes = stats.get("nodes_by_kind", {}).get("episode", 0)

        if self.dlr is None or not self.dlr.entries:
            # No baseline to compare against
            score_val = 50.0 if total_nodes > 0 else 0.0
            return DimensionScore("memory_completeness", score_val, weight,
                                  details={"reason": "no DLR baseline", "nodes": total_nodes})

        expected = len(self.dlr.entries)
        coverage = episode_nodes / expected if expected else 1.0
        score_val = min(100, coverage * 100)
        return DimensionScore("memory_completeness", round(score_val, 2), weight,
                              details={
                                  "episode_nodes": episode_nodes,
                                  "expected_episodes": expected,
                                  "total_nodes": total_nodes,
                              })
