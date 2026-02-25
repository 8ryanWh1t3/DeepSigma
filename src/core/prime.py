"""
PRIME Threshold Gate - Phase 1 Core Implementation
===================================================
Converts LLM probability gradients into decision-grade actions
using Truth-Reasoning-Memory invariants.

Part of the Coherence Ops framework under Deep Sigma.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any


class Verdict(str, Enum):
    """PRIME gate output verdicts."""
    APPROVE = "APPROVE"
    DEFER = "DEFER"
    ESCALATE = "ESCALATE"


class ConfidenceBand(str, Enum):
    """Confidence classification for claims."""
    HIGH = "HIGH"
    MODERATE = "MODERATE"
    LOW = "LOW"
    CONTESTED = "CONTESTED"


@dataclass
class TruthInvariant:
    """Truth facet: claim-evidence-source chain."""
    claim: str = ""
    evidence: list[str] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)
    confidence: ConfidenceBand = ConfidenceBand.MODERATE
    disconfirmers: list[str] = field(default_factory=list)

    @property
    def is_contested(self) -> bool:
        return len(self.disconfirmers) > 0

    @property
    def evidence_ratio(self) -> float:
        total = len(self.evidence) + len(self.disconfirmers)
        return len(self.evidence) / total if total > 0 else 0.0


@dataclass
class ReasoningInvariant:
    """Reasoning facet: facts vs interpretation with assumption tracking."""
    facts: list[str] = field(default_factory=list)
    interpretations: list[str] = field(default_factory=list)
    assumptions: list[dict[str, Any]] = field(default_factory=list)

    def active_assumptions(self, now: float | None = None) -> list[dict]:
        """Return assumptions that haven't expired."""
        ts = now or time.time()
        return [
            a for a in self.assumptions
            if a.get("expires_at", float("inf")) > ts
        ]

    @property
    def fact_ratio(self) -> float:
        total = len(self.facts) + len(self.interpretations)
        return len(self.facts) / total if total > 0 else 0.0


@dataclass
class MemoryInvariant:
    """Memory facet: seal-version-patch lineage."""
    seal_id: str = ""
    version: int = 1
    patches: list[dict[str, Any]] = field(default_factory=list)
    lineage: list[str] = field(default_factory=list)

    def apply_patch(self, patch: dict) -> None:
        """Record a patch and increment version."""
        patch["applied_at"] = time.time()
        patch["version"] = self.version + 1
        self.patches.append(patch)
        self.version += 1
        self.lineage.append(
            hashlib.sha256(
                json.dumps(patch, sort_keys=True, default=str).encode()
            ).hexdigest()[:12]
        )


@dataclass
class PRIMEContext:
    """Input context for the PRIME threshold gate."""
    truth: TruthInvariant = field(default_factory=TruthInvariant)
    reasoning: ReasoningInvariant = field(default_factory=ReasoningInvariant)
    memory: MemoryInvariant = field(default_factory=MemoryInvariant)
    raw_output: str = ""
    coherence_score: float = 0.0
    temperature: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class PRIMEVerdict:
    """Output from the PRIME threshold gate."""
    verdict: Verdict
    confidence: float
    reasoning: str
    truth_score: float
    reasoning_score: float
    memory_score: float
    composite_score: float
    escalation_factors: list[str] = field(default_factory=list)
    lineage: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["verdict"] = self.verdict.value
        return d


@dataclass
class PRIMEConfig:
    """Configuration for PRIME gate thresholds."""
    approve_threshold: float = 0.7
    defer_threshold: float = 0.4
    min_evidence_ratio: float = 0.5
    min_fact_ratio: float = 0.3
    max_expired_assumptions: int = 2
    temperature_ceiling: float = 0.8
    require_seal: bool = False
    contested_claim_policy: str = "defer"
    tool_allowlist: list[str] = field(default_factory=list)
    cost_cap_usd: float = 0.0
    offline_lane: bool = False

    def validate(self) -> list[str]:
        issues = []
        if self.approve_threshold <= self.defer_threshold:
            issues.append("approve_threshold must exceed defer_threshold")
        if not 0 <= self.min_evidence_ratio <= 1:
            issues.append("min_evidence_ratio must be in [0, 1]")
        if not 0 <= self.min_fact_ratio <= 1:
            issues.append("min_fact_ratio must be in [0, 1]")
        return issues


class PRIMEGate:
    """
    PRIME Threshold Gate
    ====================
    Sits between context assembly and action execution in the
    Coherence Ops pipeline. Evaluates Truth-Reasoning-Memory
    invariants and emits APPROVE / DEFER / ESCALATE verdicts
    with full decision lineage.
    """

    def __init__(self, config: PRIMEConfig | None = None):
        self.config = config or PRIMEConfig()
        issues = self.config.validate()
        if issues:
            raise ValueError(f"Invalid PRIMEConfig: {'; '.join(issues)}")

    def evaluate(self, context: PRIMEContext) -> PRIMEVerdict:
        """Run the PRIME threshold gate on the given context."""
        truth_score = self._score_truth(context.truth)
        reasoning_score = self._score_reasoning(context.reasoning)
        memory_score = self._score_memory(context.memory)
        escalation_factors = []

        composite = (
            truth_score * 0.4
            + reasoning_score * 0.3
            + memory_score * 0.15
            + context.coherence_score * 0.15
        )

        if context.temperature > self.config.temperature_ceiling:
            escalation_factors.append(
                f"temperature={context.temperature:.2f} exceeds ceiling={self.config.temperature_ceiling}"
            )

        if context.truth.is_contested:
            if self.config.contested_claim_policy == "escalate":
                escalation_factors.append("contested_claim_escalate: active disconfirmers present")
            elif self.config.contested_claim_policy == "defer":
                escalation_factors.append("contested_claim_defer: deferred for review")

        if self.config.require_seal and not context.memory.seal_id:
            escalation_factors.append("missing_seal: memory seal required but absent")

        expired = [
            a for a in context.reasoning.assumptions
            if a.get("expires_at", float("inf")) <= time.time()
        ]
        if len(expired) > self.config.max_expired_assumptions:
            escalation_factors.append(
                f"expired_assumptions={len(expired)} exceeds max={self.config.max_expired_assumptions}"
            )

        if escalation_factors and any(
            "escalate" in f.lower() or "missing_seal" in f or "temperature" in f
            for f in escalation_factors
        ):
            verdict = Verdict.ESCALATE
        elif composite >= self.config.approve_threshold and not escalation_factors:
            verdict = Verdict.APPROVE
        elif composite >= self.config.defer_threshold:
            verdict = Verdict.DEFER
        else:
            verdict = Verdict.ESCALATE

        reasoning_text = self._build_reasoning(
            verdict, composite, truth_score, reasoning_score,
            memory_score, escalation_factors
        )

        return PRIMEVerdict(
            verdict=verdict,
            confidence=min(composite, 1.0),
            reasoning=reasoning_text,
            truth_score=truth_score,
            reasoning_score=reasoning_score,
            memory_score=memory_score,
            composite_score=composite,
            escalation_factors=escalation_factors,
            lineage={
                "gate_version": "1.0.0",
                "config": asdict(self.config),
                "context_hash": hashlib.sha256(
                    json.dumps({
                        "truth_claim": context.truth.claim,
                        "raw_output_len": len(context.raw_output),
                        "coherence_score": context.coherence_score,
                    }, default=str).encode()
                ).hexdigest()[:16],
                "memory_version": context.memory.version,
                "seal_id": context.memory.seal_id,
            },
        )

    def _score_truth(self, truth: TruthInvariant) -> float:
        if not truth.claim:
            return 0.0
        base = {
            ConfidenceBand.HIGH: 0.9,
            ConfidenceBand.MODERATE: 0.6,
            ConfidenceBand.LOW: 0.3,
            ConfidenceBand.CONTESTED: 0.2,
        }.get(truth.confidence, 0.5)
        evidence_bonus = min(truth.evidence_ratio * 0.1, 0.1)
        return min(base + evidence_bonus, 1.0)

    def _score_reasoning(self, reasoning: ReasoningInvariant) -> float:
        if not reasoning.facts and not reasoning.interpretations:
            return 0.0
        fact_score = reasoning.fact_ratio
        active = reasoning.active_assumptions()
        assumption_penalty = max(0, (len(active) - 3) * 0.1)
        return max(0.0, min(fact_score - assumption_penalty, 1.0))

    def _score_memory(self, memory: MemoryInvariant) -> float:
        base = 0.5
        if memory.seal_id:
            base += 0.2
        if memory.lineage:
            base += min(len(memory.lineage) * 0.05, 0.2)
        if memory.version > 1:
            base += 0.1
        return min(base, 1.0)

    def _build_reasoning(
        self, verdict, composite, truth_s, reasoning_s,
        memory_s, escalation_factors
    ) -> str:
        parts = [
            f"PRIME Gate -> {verdict.value}",
            f"Composite: {composite:.3f} (T:{truth_s:.2f} R:{reasoning_s:.2f} M:{memory_s:.2f})",
        ]
        if escalation_factors:
            parts.append(f"Escalation triggers: {'; '.join(escalation_factors)}")
        return " | ".join(parts)

