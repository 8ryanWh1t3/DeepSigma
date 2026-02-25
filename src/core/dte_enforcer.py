"""DTE Enforcer — active Decision Timing Envelope constraint validation.

Complements the degrade_ladder (which selects fallback steps) by
validating hard DTE constraints and returning typed violations.
The caller (supervisor, API) decides whether to abort, degrade, or log.

Usage:
    from core.dte_enforcer import DTEEnforcer
    enforcer = DTEEnforcer(dte_spec)
    violations = enforcer.enforce(
        elapsed_ms=95,
        stage_elapsed={"context": 40, "plan": 30, "act": 20, "verify": 5},
        feature_ages={"price_feed": 350, "user_profile": 100},
        counts={"hops": 3, "tool_calls": 12},
    )
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class DTEViolation:
    """A single DTE constraint violation."""

    gate: str       # "deadline", "stage_budget", "feature_ttl", "limits"
    field: str      # e.g. "deadlineMs", "stageBudgetsMs.plan", "featureTtls.price_feed"
    limit_value: Any
    actual_value: Any
    severity: str   # "hard" (must abort/abstain) or "soft" (should degrade)
    message: str


class DTEEnforcer:
    """Validate runtime signals against a DTE spec.

    Args:
        dte_spec: A dict matching the DTE schema (deadlineMs, stageBudgetsMs,
                  freshness, limits, etc.).
    """

    def __init__(self, dte_spec: Dict[str, Any]) -> None:
        self.spec = dte_spec

    def enforce(
        self,
        elapsed_ms: int,
        stage_elapsed: Optional[Dict[str, int]] = None,
        feature_ages: Optional[Dict[str, int]] = None,
        counts: Optional[Dict[str, int]] = None,
    ) -> List[DTEViolation]:
        """Check all DTE constraints. Returns empty list when within envelope."""
        violations: List[DTEViolation] = []
        violations.extend(self._check_deadline(elapsed_ms))
        if stage_elapsed:
            violations.extend(self._check_stage_budgets(stage_elapsed))
        if feature_ages:
            violations.extend(self._check_freshness(feature_ages))
        if counts:
            violations.extend(self._check_limits(counts))
        return violations

    # ── Deadline ────────────────────────────────────────────────

    def _check_deadline(self, elapsed_ms: int) -> List[DTEViolation]:
        deadline = self.spec.get("deadlineMs")
        if deadline is None:
            return []
        if elapsed_ms > deadline:
            return [DTEViolation(
                gate="deadline",
                field="deadlineMs",
                limit_value=deadline,
                actual_value=elapsed_ms,
                severity="hard",
                message=f"Deadline exceeded: {elapsed_ms}ms > {deadline}ms",
            )]
        return []

    # ── Stage Budgets ───────────────────────────────────────────

    def _check_stage_budgets(self, stage_elapsed: Dict[str, int]) -> List[DTEViolation]:
        budgets = self.spec.get("stageBudgetsMs", {})
        violations: List[DTEViolation] = []
        for stage in ("context", "plan", "act", "verify"):
            budget = budgets.get(stage)
            actual = stage_elapsed.get(stage)
            if budget is not None and actual is not None and actual > budget:
                violations.append(DTEViolation(
                    gate="stage_budget",
                    field=f"stageBudgetsMs.{stage}",
                    limit_value=budget,
                    actual_value=actual,
                    severity="soft",
                    message=f"Stage '{stage}' exceeded budget: {actual}ms > {budget}ms",
                ))
        return violations

    # ── Freshness / TTL ─────────────────────────────────────────

    def _check_freshness(self, feature_ages: Dict[str, int]) -> List[DTEViolation]:
        freshness = self.spec.get("freshness", {})
        default_ttl = freshness.get("defaultTtlMs")
        feature_ttls = freshness.get("featureTtls", {})
        allow_stale = freshness.get("allowStaleIfSafe", False)

        violations: List[DTEViolation] = []
        for feature, age_ms in feature_ages.items():
            ttl = feature_ttls.get(feature, default_ttl)
            if ttl is None:
                continue
            if age_ms > ttl:
                severity = "soft" if allow_stale else "hard"
                violations.append(DTEViolation(
                    gate="feature_ttl",
                    field=f"featureTtls.{feature}",
                    limit_value=ttl,
                    actual_value=age_ms,
                    severity=severity,
                    message=f"Feature '{feature}' stale: {age_ms}ms > TTL {ttl}ms",
                ))
        return violations

    # ── Limits ──────────────────────────────────────────────────

    def _check_limits(self, counts: Dict[str, int]) -> List[DTEViolation]:
        limits = self.spec.get("limits", {})
        violations: List[DTEViolation] = []
        limit_map = {
            "hops": "maxHops",
            "fanout": "maxFanout",
            "tool_calls": "maxToolCalls",
            "chain_depth": "maxChainDepth",
        }
        for count_key, spec_key in limit_map.items():
            max_val = limits.get(spec_key)
            actual = counts.get(count_key)
            if max_val is not None and actual is not None and actual > max_val:
                violations.append(DTEViolation(
                    gate="limits",
                    field=f"limits.{spec_key}",
                    limit_value=max_val,
                    actual_value=actual,
                    severity="hard",
                    message=f"Limit '{spec_key}' exceeded: {actual} > {max_val}",
                ))
        return violations
