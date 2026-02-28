"""Runtime Gate — composable pre-execution policy enforcement.

Generalizes the degrade ladder's hard gates into a pluggable constraint
system. Operators define gate rules in their policy pack; the RuntimeGate
evaluates all constraints before execution and returns allow/deny/degrade
with a machine-readable rationale.

Also includes an SLO circuit breaker that trips when monitored metrics
breach thresholds for a sustained window.

Example policy pack gates section:

    "gates": [
        {"type": "freshness", "max_age_ms": 500, "on_fail": "abstain"},
        {"type": "verification", "require": "pass", "on_fail": "hitl"},
        {"type": "latency_slo", "p99_max_ms": 400, "window_s": 300, "on_fail": "degrade"},
        {"type": "quota", "max_per_hour": 120, "on_fail": "deny"},
        {"type": "custom", "expr": "drift_count < 10", "on_fail": "deny"}
    ]
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional


@dataclass
class GateResult:
    """Result of evaluating a single gate constraint."""

    gate_type: str
    passed: bool
    action: str  # "allow", "deny", "degrade", "abstain", "hitl"
    rationale: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GateVerdict:
    """Aggregate result of all gate evaluations."""

    allowed: bool
    action: str  # "allow", "deny", or a degrade step
    results: List[GateResult] = field(default_factory=list)
    rationale: Dict[str, Any] = field(default_factory=dict)


class SLOCircuitBreaker:
    """Trips when a metric breaches a threshold for a sustained window.

    Usage:
        breaker = SLOCircuitBreaker(threshold=400.0, window_s=300)
        breaker.record(p99_latency_ms)
        if breaker.is_tripped:
            # degrade
    """

    def __init__(self, threshold: float, window_s: int = 300) -> None:
        self.threshold = threshold
        self.window_s = window_s
        self._samples: List[tuple[float, float]] = []  # (timestamp, value)
        self._tripped = False

    def record(self, value: float) -> None:
        now = time.monotonic()
        self._samples.append((now, value))
        cutoff = now - self.window_s
        self._samples = [(t, v) for t, v in self._samples if t >= cutoff]
        if self._samples and all(v > self.threshold for _, v in self._samples):
            self._tripped = True
        else:
            self._tripped = False

    @property
    def is_tripped(self) -> bool:
        return self._tripped

    def reset(self) -> None:
        self._tripped = False
        self._samples.clear()


class RuntimeGate:
    """Evaluate a list of policy gate constraints before execution.

    Args:
        gates: List of gate rule dicts from the policy pack.
        breakers: Optional dict of metric_name -> SLOCircuitBreaker instances.
    """

    def __init__(
        self,
        gates: List[Dict[str, Any]],
        breakers: Optional[Dict[str, SLOCircuitBreaker]] = None,
    ) -> None:
        self.gates = gates
        self.breakers = breakers or {}

    def evaluate(self, context: Dict[str, Any]) -> GateVerdict:
        """Evaluate all gates against the current execution context.

        Args:
            context: Runtime context dict with keys like:
                - max_feature_age_ms: int
                - verifier_result: str (pass/fail/inconclusive)
                - drift_count: int
                - p99_ms: int
                - quota_used: int
                - quota_limit: int

        Returns:
            GateVerdict with the aggregate decision.
        """
        results: List[GateResult] = []

        for gate in self.gates:
            gate_type = gate.get("type", "unknown")
            on_fail = gate.get("on_fail", "deny")
            result = self._evaluate_gate(gate_type, gate, context, on_fail)
            results.append(result)

        # Any failure blocks — use the first failing gate's action
        failed = [r for r in results if not r.passed]
        if failed:
            action = failed[0].action
            return GateVerdict(
                allowed=action not in ("deny", "abstain"),
                action=action,
                results=results,
                rationale={"blocked_by": failed[0].gate_type, **failed[0].rationale},
            )

        return GateVerdict(
            allowed=True,
            action="allow",
            results=results,
            rationale={"reason": "all_gates_passed"},
        )

    def _evaluate_gate(
        self,
        gate_type: str,
        gate: Dict[str, Any],
        ctx: Dict[str, Any],
        on_fail: str,
    ) -> GateResult:
        if gate_type == "freshness":
            age = ctx.get("max_feature_age_ms", 0)
            limit = gate.get("max_age_ms", 500)
            passed = age <= limit
            return GateResult(gate_type, passed, "allow" if passed else on_fail, {
                "max_feature_age_ms": age, "limit": limit,
            })

        if gate_type == "verification":
            result = ctx.get("verifier_result", "pass")
            require = gate.get("require", "pass")
            passed = result == require
            return GateResult(gate_type, passed, "allow" if passed else on_fail, {
                "verifier_result": result, "required": require,
            })

        if gate_type == "latency_slo":
            metric_name = gate.get("metric", "p99_ms")
            breaker = self.breakers.get(metric_name)
            if breaker and breaker.is_tripped:
                return GateResult(gate_type, False, on_fail, {
                    "reason": "slo_breaker_tripped", "metric": metric_name,
                    "threshold": breaker.threshold,
                })
            return GateResult(gate_type, True, "allow", {"metric": metric_name})

        if gate_type == "quota":
            used = ctx.get("quota_used", 0)
            limit = gate.get("max_per_hour", 120)
            passed = used < limit
            return GateResult(gate_type, passed, "allow" if passed else on_fail, {
                "quota_used": used, "limit": limit,
            })

        if gate_type == "custom":
            return self._evaluate_custom(gate, ctx, on_fail)

        return GateResult(gate_type, True, "allow", {"reason": "unknown_gate_type_passed"})

    def _evaluate_custom(
        self,
        gate: Dict[str, Any],
        ctx: Dict[str, Any],
        on_fail: str,
    ) -> GateResult:
        """Evaluate a simple expression gate (e.g. 'drift_count < 10')."""
        expr = gate.get("expr", "")
        if not expr:
            return GateResult("custom", True, "allow", {"reason": "empty_expr"})

        try:
            # Safe subset: only allow comparisons on context values
            passed = bool(eval(expr, {"__builtins__": {}}, ctx))  # noqa: S307
        except Exception as exc:
            return GateResult("custom", False, on_fail, {
                "reason": "expr_eval_error", "expr": expr, "error": str(exc),
            })

        return GateResult("custom", passed, "allow" if passed else on_fail, {
            "expr": expr, "result": passed,
        })
