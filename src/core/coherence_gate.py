"""CoherenceGate — composable enforcement gate for agentic actions.

Combines CoherenceScorer (4-dimension score) with PRIMEGate (T-R-M invariants)
to produce a GREEN / YELLOW / RED signal with enforcement message.

Usage:
    gate = CoherenceGate(config=GateConfig(green_threshold=80))
    result = gate.evaluate(
        dlr_builder=dlr,
        rs=reflection_session,
        ds=drift_collector,
        mg=memory_graph,
    )
    if result.signal == Signal.RED:
        raise RuntimeError(result.enforcement)
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from .prime import PRIMEConfig, PRIMEContext, PRIMEGate, Verdict
from .scoring import CoherenceScorer

logger = logging.getLogger(__name__)


class Signal(str, Enum):
    """Traffic-light signal from the CoherenceGate."""

    GREEN = "GREEN"
    YELLOW = "YELLOW"
    RED = "RED"


@dataclass
class GateConfig:
    """Configuration for the CoherenceGate."""

    green_threshold: float = 80.0
    yellow_threshold: float = 60.0
    tool_allowlist: List[str] = field(default_factory=list)
    cost_cap_usd: float = 0.0
    offline_lane: bool = False


@dataclass
class GateResult:
    """Output of a CoherenceGate evaluation."""

    signal: Signal
    score: float
    grade: str
    violations: List[str] = field(default_factory=list)
    enforcement: str = ""
    details: Dict[str, Any] = field(default_factory=dict)


class CoherenceGate:
    """Composable enforcement gate combining scoring + PRIME.

    Usage:
        gate = CoherenceGate(config=GateConfig())
        result = gate.evaluate(dlr_builder=dlr, rs=rs, ds=ds, mg=mg)
    """

    def __init__(
        self,
        config: Optional[GateConfig] = None,
        prime_config: Optional[PRIMEConfig] = None,
    ) -> None:
        self.config = config or GateConfig()
        self.prime_config = prime_config

    def evaluate(
        self,
        dlr_builder=None,
        rs=None,
        ds=None,
        mg=None,
        tool_name: Optional[str] = None,
        cost_usd: float = 0.0,
        prime_context: Optional[PRIMEContext] = None,
    ) -> GateResult:
        """Run the full coherence gate.

        1. CoherenceScorer -> score + grade
        2. Classify: >= green_threshold GREEN, >= yellow_threshold YELLOW, else RED
        3. Check tool allowlist
        4. Check cost cap
        5. Optionally run PRIMEGate
        6. Return GateResult
        """
        violations: List[str] = []

        # 1. Score
        scorer = CoherenceScorer(
            dlr_builder=dlr_builder,
            rs=rs,
            ds=ds,
            mg=mg,
        )
        report = scorer.score()
        score = report.overall_score
        grade = report.grade

        # 2. Classify
        if score >= self.config.green_threshold:
            signal = Signal.GREEN
        elif score >= self.config.yellow_threshold:
            signal = Signal.YELLOW
        else:
            signal = Signal.RED
            violations.append(
                f"Coherence score {score:.1f} below yellow threshold "
                f"({self.config.yellow_threshold})"
            )

        # 3. Tool allowlist
        if (
            tool_name
            and self.config.tool_allowlist
            and tool_name not in self.config.tool_allowlist
        ):
            signal = Signal.RED
            violations.append(f"Tool {tool_name!r} not in allowlist")

        # 4. Cost cap
        if self.config.cost_cap_usd > 0 and cost_usd > self.config.cost_cap_usd:
            signal = Signal.RED
            violations.append(
                f"Cost ${cost_usd:.2f} exceeds cap ${self.config.cost_cap_usd:.2f}"
            )

        # 5. PRIME gate (optional)
        if prime_context is not None:
            prime_gate = PRIMEGate(self.prime_config)
            verdict = prime_gate.evaluate(prime_context)
            if verdict.verdict == Verdict.ESCALATE:
                signal = Signal.RED
                violations.append(
                    f"PRIME escalated: {verdict.reasoning}"
                )

        # 6. Build enforcement message
        if signal == Signal.RED:
            enforcement = (
                f"BLOCKED: {'; '.join(violations)}"
            )
        elif signal == Signal.YELLOW:
            enforcement = (
                f"CAUTION: coherence score {score:.1f}/100 (grade {grade}) "
                f"— proceed with monitoring"
            )
        else:
            enforcement = ""

        result = GateResult(
            signal=signal,
            score=score,
            grade=grade,
            violations=violations,
            enforcement=enforcement,
            details={
                "dimensions": [
                    {"name": d.name, "score": d.score, "weight": d.weight}
                    for d in report.dimensions
                ],
            },
        )
        logger.info("CoherenceGate: %s (score=%.1f, grade=%s)", signal.value, score, grade)
        return result
