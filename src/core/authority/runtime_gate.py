"""Runtime Gate — Primitive 4: Runtime Enforcement Gateway.

Thin facade over ``policy_runtime.evaluate()`` that adds artifact
awareness, clear API naming, and structured gate decisions.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .models import AuthorityVerdict, CompiledPolicy, DecisionGateResult


@dataclass
class GateDecision:
    """Structured result of a runtime gate evaluation."""

    gate_id: str
    verdict: str  # AuthorityVerdict value
    evaluated_at: str
    artifact_id: str = ""
    policy_hash: str = ""
    passed_checks: List[str] = field(default_factory=list)
    failed_checks: List[str] = field(default_factory=list)
    failed_reason: str = ""
    escalation_target: Optional[str] = None


class RuntimeGate:
    """Artifact-aware authority evaluation gateway.

    Wraps ``policy_runtime.evaluate()`` with artifact reference tracking
    and a structured ``GateDecision`` return type.
    """

    def evaluate(
        self,
        compiled: Optional[CompiledPolicy],
        request: Dict[str, Any],
        context: Dict[str, Any],
    ) -> GateDecision:
        """Evaluate an action request against a compiled policy artifact.

        If ``compiled`` is None, returns BLOCK with ``no_artifact`` reason.
        Otherwise delegates to the existing 11-step pipeline and wraps
        the result with artifact metadata.
        """
        now = datetime.now(timezone.utc).isoformat()
        gate_id = f"RGATE-{uuid.uuid4().hex[:12]}"

        if compiled is None:
            return GateDecision(
                gate_id=gate_id,
                verdict=AuthorityVerdict.BLOCK.value,
                evaluated_at=now,
                failed_checks=["artifact_exists"],
                failed_reason="no_artifact",
            )

        from .policy_runtime import evaluate

        result = evaluate(request, context)

        return GateDecision(
            gate_id=gate_id,
            verdict=result.verdict,
            evaluated_at=result.evaluated_at,
            artifact_id=compiled.artifact_id,
            policy_hash=compiled.policy_hash,
            passed_checks=result.passed_checks,
            failed_checks=result.failed_checks,
            escalation_target=result.escalation_target,
        )

    def evaluate_raw(
        self,
        request: Dict[str, Any],
        context: Dict[str, Any],
    ) -> GateDecision:
        """Evaluate without an artifact (backward-compatible path)."""
        from .policy_runtime import evaluate

        now = datetime.now(timezone.utc).isoformat()
        gate_id = f"RGATE-{uuid.uuid4().hex[:12]}"

        result = evaluate(request, context)

        return GateDecision(
            gate_id=gate_id,
            verdict=result.verdict,
            evaluated_at=result.evaluated_at,
            passed_checks=result.passed_checks,
            failed_checks=result.failed_checks,
            escalation_target=result.escalation_target,
        )
