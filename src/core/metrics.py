"""Coherence metrics — 4 composable metric points for observability.

Collects: coherence_score, drift_density, authority_coverage, memory_coverage.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .decision_log import DLRBuilder
from .drift_signal import DriftSignalCollector
from .memory_graph import MemoryGraph, NodeKind
from .reflection import ReflectionSession
from .scoring import CoherenceScorer


@dataclass
class MetricPoint:
    """A single metric measurement."""

    name: str
    value: float
    unit: str  # "score" | "ratio" | "count"
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MetricsReport:
    """Collection of metric points with metadata."""

    computed_at: str
    metrics: List[MetricPoint]
    summary: Dict[str, Any] = field(default_factory=dict)

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(asdict(self), indent=indent, default=str)


class MetricsCollector:
    """Collect coherence metrics from the pipeline.

    Produces 4 metrics:
    1. ``coherence_score`` (0-100): overall coherence score
    2. ``drift_density`` (ratio): drift_count / episode_count
    3. ``authority_coverage`` (ratio): authorized claims / total claims
    4. ``memory_coverage`` (ratio): episode nodes / expected episodes

    Usage::

        collector = MetricsCollector(
            dlr_builder=dlr, rs=rs, ds=ds, mg=mg,
        )
        report = collector.collect()
    """

    def __init__(
        self,
        dlr_builder: Optional[DLRBuilder] = None,
        rs: Optional[ReflectionSession] = None,
        ds: Optional[DriftSignalCollector] = None,
        mg: Optional[MemoryGraph] = None,
        authority_ledger: Optional[Any] = None,
    ) -> None:
        self._dlr = dlr_builder
        self._rs = rs
        self._ds = ds
        self._mg = mg
        self._authority_ledger = authority_ledger

    def collect(self) -> MetricsReport:
        """Compute all metrics and return a report."""
        metrics: List[MetricPoint] = [
            self._coherence_score(),
            self._drift_density(),
            self._authority_coverage(),
            self._memory_coverage(),
        ]
        return MetricsReport(
            computed_at=datetime.now(timezone.utc).isoformat(),
            metrics=metrics,
            summary={m.name: m.value for m in metrics},
        )

    def _coherence_score(self) -> MetricPoint:
        """Overall coherence score (0-100)."""
        try:
            scorer = CoherenceScorer(
                dlr_builder=self._dlr,
                rs=self._rs,
                ds=self._ds,
                mg=self._mg,
            )
            report = scorer.score()
            return MetricPoint(
                name="coherence_score",
                value=report.overall_score,
                unit="score",
                details={"grade": report.grade},
            )
        except Exception:
            return MetricPoint(
                name="coherence_score", value=0.0, unit="score",
                details={"error": "scoring_failed"},
            )

    def _drift_density(self) -> MetricPoint:
        """Ratio of drift signals to episodes."""
        drift_count = self._ds.event_count if self._ds else 0
        episode_count = len(self._dlr.entries) if self._dlr else 0

        ratio = 0.0
        if episode_count > 0:
            ratio = round(drift_count / episode_count, 4)

        return MetricPoint(
            name="drift_density",
            value=ratio,
            unit="ratio",
            details={
                "drift_count": drift_count,
                "episode_count": episode_count,
            },
        )

    def _authority_coverage(self) -> MetricPoint:
        """Ratio of authorized claims to total claims in MG."""
        if self._mg is None:
            return MetricPoint(
                name="authority_coverage", value=0.0, unit="ratio",
                details={"total_claims": 0, "authorized": 0},
            )

        claim_nodes = [
            n for n in self._mg._nodes.values()
            if n.kind == NodeKind.CLAIM
        ]
        total = len(claim_nodes)

        if total == 0 or self._authority_ledger is None:
            coverage = 1.0 if total == 0 else 0.0
            return MetricPoint(
                name="authority_coverage",
                value=coverage,
                unit="ratio",
                details={"total_claims": total, "authorized": 0},
            )

        authorized = 0
        for node in claim_nodes:
            proof = self._authority_ledger.prove_authority(node.node_id)
            if proof is not None:
                authorized += 1

        ratio = round(authorized / total, 4) if total > 0 else 0.0
        return MetricPoint(
            name="authority_coverage",
            value=ratio,
            unit="ratio",
            details={"total_claims": total, "authorized": authorized},
        )

    def _memory_coverage(self) -> MetricPoint:
        """Ratio of episode nodes in MG to expected episodes from DLR."""
        expected = len(self._dlr.entries) if self._dlr else 0
        if self._mg is None or expected == 0:
            return MetricPoint(
                name="memory_coverage", value=0.0, unit="ratio",
                details={"expected": expected, "actual": 0},
            )

        episode_nodes = [
            n for n in self._mg._nodes.values()
            if n.kind == NodeKind.EPISODE
        ]
        actual = len(episode_nodes)

        ratio = round(min(actual / expected, 1.0), 4) if expected > 0 else 0.0
        return MetricPoint(
            name="memory_coverage",
            value=ratio,
            unit="ratio",
            details={"expected": expected, "actual": actual},
        )
