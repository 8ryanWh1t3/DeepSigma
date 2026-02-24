"""Reflection Session (RS) — aggregate episodes into learning summaries.

A ReflectionSession takes a batch of sealed DecisionEpisodes and
produces a structured summary: outcome distribution, degradation
frequency, verification pass rates, notable divergences, and
human-readable takeaways.

RS answers: "what happened, what degraded, what should we learn?"
"""

from __future__ import annotations

import json
import logging
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


@dataclass
class Divergence:
    """A notable divergence between expected and actual behaviour."""

    episode_id: str
    field: str
    expected: str
    actual: str
    severity: str = "info"  # info / warning / critical


@dataclass
class ReflectionSummary:
    """Output of a ReflectionSession."""

    session_id: str
    created_at: str
    episode_count: int
    outcome_distribution: Dict[str, int]
    degrade_distribution: Dict[str, int]
    verification_pass_rate: float
    divergences: List[Divergence]
    takeaways: List[str]
    metadata: Dict[str, Any] = field(default_factory=dict)


class ReflectionSession:
    """Aggregate episodes into a ReflectionSummary.

    Usage:
        rs = ReflectionSession("rs-001")
        rs.ingest(episodes)
        summary = rs.summarise()
    """

    def __init__(self, session_id: str) -> None:
        self.session_id = session_id
        self._episodes: List[Dict[str, Any]] = []

    def ingest(self, episodes: List[Dict[str, Any]]) -> None:
        """Add episodes to the session."""
        self._episodes.extend(episodes)
        logger.debug("Ingested %d episodes into RS %s", len(episodes), self.session_id)

    def summarise(self) -> ReflectionSummary:
        """Produce a ReflectionSummary from ingested episodes."""
        outcomes = Counter(
            ep.get("outcome", {}).get("code", "unknown")
            for ep in self._episodes
        )
        degrades = Counter(
            ep.get("degrade", {}).get("step", "none")
            for ep in self._episodes
        )
        verify_results = [
            ep.get("verification", {}).get("result", "na")
            for ep in self._episodes
        ]
        pass_count = sum(1 for v in verify_results if v == "pass")
        total_verified = sum(1 for v in verify_results if v != "na")
        pass_rate = pass_count / total_verified if total_verified else 1.0

        divergences = self._detect_divergences()
        takeaways = self._generate_takeaways(outcomes, degrades, pass_rate, divergences)

        summary = ReflectionSummary(
            session_id=self.session_id,
            created_at=datetime.now(timezone.utc).isoformat(),
            episode_count=len(self._episodes),
            outcome_distribution=dict(outcomes),
            degrade_distribution=dict(degrades),
            verification_pass_rate=round(pass_rate, 4),
            divergences=divergences,
            takeaways=takeaways,
        )
        logger.info("RS %s summarised %d episodes", self.session_id, len(self._episodes))
        return summary

    def to_json(self, indent: int = 2) -> str:
        """Summarise and serialise to JSON."""
        return json.dumps(asdict(self.summarise()), indent=indent)

    # ------------------------------------------------------------------
    # Divergence detection
    # ------------------------------------------------------------------

    def _detect_divergences(self) -> List[Divergence]:
        """Scan episodes for notable divergences."""
        divs: List[Divergence] = []
        for ep in self._episodes:
            outcome = ep.get("outcome", {}).get("code", "unknown")
            degrade = ep.get("degrade", {}).get("step", "none")
            verify = ep.get("verification", {}).get("result", "na")

            # Verification failed but action still succeeded — suspicious
            if verify == "fail" and outcome == "success":
                divs.append(Divergence(
                    episode_id=ep.get("episodeId", ""),
                    field="verification_vs_outcome",
                    expected="outcome should not be success when verification fails",
                    actual=f"verify={verify}, outcome={outcome}",
                    severity="critical",
                ))

            # Degrade triggered but outcome still success — may be masking
            if degrade not in ("none", None) and outcome == "success":
                divs.append(Divergence(
                    episode_id=ep.get("episodeId", ""),
                    field="degrade_vs_outcome",
                    expected="degraded episodes may not fully succeed",
                    actual=f"degrade={degrade}, outcome={outcome}",
                    severity="info",
                ))

        return divs

    # ------------------------------------------------------------------
    # Takeaway generation
    # ------------------------------------------------------------------

    @staticmethod
    def _generate_takeaways(
        outcomes: Counter,
        degrades: Counter,
        pass_rate: float,
        divergences: List[Divergence],
    ) -> List[str]:
        """Produce human-readable takeaway strings."""
        tips: List[str] = []
        total = sum(outcomes.values())
        if total == 0:
            return ["No episodes to reflect on."]

        fail_count = outcomes.get("fail", 0) + outcomes.get("partial", 0)
        fail_pct = fail_count / total * 100
        if fail_pct > 20:
            tips.append(f"High failure rate ({fail_pct:.0f}%) — review DTE budgets and degrade ladder.")

        abstain_count = outcomes.get("abstain", 0)
        if abstain_count > total * 0.1:
            tips.append(f"Abstain rate {abstain_count}/{total} — check freshness gates and TTL configuration.")

        if pass_rate < 0.9:
            tips.append(f"Verification pass rate {pass_rate:.0%} — investigate verifier configuration.")

        degrade_count = sum(v for k, v in degrades.items() if k not in ("none", None))
        if degrade_count > total * 0.3:
            tips.append(f"High degrade rate ({degrade_count}/{total}) — consider tuning thresholds.")

        critical = [d for d in divergences if d.severity == "critical"]
        if critical:
            tips.append(f"{len(critical)} critical divergence(s) detected — immediate review recommended.")

        if not tips:
            tips.append("All indicators within normal range.")

        return tips
