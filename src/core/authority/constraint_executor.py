"""Constraint Executor — evaluate compiled policy constraints at runtime.

Bridges the gap between CompiledPolicy.rules (extracted by the compiler)
and the 11-step evaluation pipeline. Each constraint type has a dedicated
evaluator function that returns the standard (bool, detail, verdict) tuple.
"""

from __future__ import annotations

import logging
import re
import uuid
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple

from .models import (
    ApprovalPath,
    AuthorityVerdict,
    ConstraintResult,
    ExpiryCondition,
    ExpiryConditionType,
    PolicyConstraint,
)

logger = logging.getLogger(__name__)

# ── ISO 8601 Duration Parser ─────────────────────────────────────

_DURATION_RE = re.compile(
    r"^P(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+(?:\.\d+)?)S)?)?$"
)


def _parse_iso_duration(s: str) -> timedelta:
    """Parse a subset of ISO 8601 durations: P<n>DT<n>H<n>M<n>S.

    Raises ValueError on unrecognized formats.
    """
    m = _DURATION_RE.match(s.strip())
    if not m or s.strip() == "P":
        raise ValueError(f"unsupported ISO 8601 duration: {s!r}")
    days = int(m.group(1) or 0)
    hours = int(m.group(2) or 0)
    minutes = int(m.group(3) or 0)
    seconds = float(m.group(4) or 0)
    return timedelta(days=days, hours=hours, minutes=minutes, seconds=seconds)


# ── Rate Limiter State ────────────────────────────────────────────

_rate_counters: Dict[str, deque] = defaultdict(deque)


def reset_rate_counters() -> None:
    """Clear all in-memory rate counters. Call from test teardown."""
    _rate_counters.clear()


# ── Per-Constraint Evaluators ─────────────────────────────────────


def _eval_time_window(
    constraint: PolicyConstraint,
    request: Dict[str, Any],
    context: Dict[str, Any],
    now: datetime,
) -> Tuple[bool, str, Optional[AuthorityVerdict]]:
    """Check if the current time falls within an allowed window.

    Parameters:
        allowed_hours: {"start": int, "end": int}  (0-23, UTC)
        allowed_days: list of weekday ints (0=Monday .. 6=Sunday)
    """
    params = constraint.parameters
    allowed_hours = params.get("allowed_hours")
    allowed_days = params.get("allowed_days")

    if not allowed_hours and not allowed_days:
        return True, "time_window:no_restrictions", None

    if allowed_days is not None:
        weekday = now.weekday()
        if weekday not in allowed_days:
            return (
                False,
                f"time_window_violation:day={weekday},allowed={allowed_days}",
                AuthorityVerdict.BLOCK,
            )

    if allowed_hours is not None:
        start = allowed_hours.get("start", 0)
        end = allowed_hours.get("end", 23)
        hour = now.hour
        if not (start <= hour <= end):
            return (
                False,
                f"time_window_violation:hour={hour},allowed={start}-{end}",
                AuthorityVerdict.BLOCK,
            )

    return True, "time_window:within_allowed_window", None


def _eval_requires_approval(
    constraint: PolicyConstraint,
    request: Dict[str, Any],
    context: Dict[str, Any],
    now: datetime,
) -> Tuple[bool, str, Optional[AuthorityVerdict]]:
    """Check that required approvals are present.

    Parameters:
        required_approvers: list of approver IDs
        deadline: optional ISO 8601 timestamp
    """
    params = constraint.parameters
    required = set(params.get("required_approvers", []))
    if not required:
        return True, "approval:no_approvers_required", None

    current = set(context.get("approvals", []))
    missing = required - current

    # Build ApprovalPath and store in context
    path = ApprovalPath(
        path_id=f"AP-{uuid.uuid4().hex[:8]}",
        required_approvers=sorted(required),
        current_approvals=sorted(current & required),
        status="pending" if missing else "approved",
    )

    # Check deadline
    deadline_str = params.get("deadline")
    if deadline_str and missing:
        try:
            deadline = datetime.fromisoformat(deadline_str.replace("Z", "+00:00"))
            if now >= deadline:
                path.status = "expired"
                context["_approval_path"] = path
                return (
                    False,
                    f"approval_expired:deadline={deadline_str}",
                    AuthorityVerdict.BLOCK,
                )
        except (ValueError, TypeError):
            pass

    path.deadline = deadline_str
    context["_approval_path"] = path

    if missing:
        return (
            False,
            f"approval_required:missing={sorted(missing)}",
            AuthorityVerdict.ESCALATE,
        )

    return True, "approval:all_approvers_present", None


def _eval_rate_limit(
    constraint: PolicyConstraint,
    request: Dict[str, Any],
    context: Dict[str, Any],
    now: datetime,
) -> Tuple[bool, str, Optional[AuthorityVerdict]]:
    """Enforce rate limiting with an in-memory sliding window.

    Parameters:
        max_count: int (maximum actions in window)
        window_seconds: int (default 3600)
        key: optional string key (default: actorId)

    Note: Not thread-safe. In-memory only — resets on process restart.
    """
    params = constraint.parameters
    max_count = params.get("max_count", 10)
    window_seconds = params.get("window_seconds", 3600)
    key = params.get("key", request.get("actorId", "unknown"))

    cutoff = now - timedelta(seconds=window_seconds)
    counter = _rate_counters[key]

    # Evict expired entries
    while counter and counter[0] < cutoff:
        counter.popleft()

    if len(counter) >= max_count:
        return (
            False,
            f"rate_limit_exceeded:key={key},count={len(counter)},max={max_count}",
            AuthorityVerdict.BLOCK,
        )

    # Record this action
    counter.append(now)
    return True, f"rate_limit_ok:key={key},count={len(counter)},max={max_count}", None


def _eval_scope_limit(
    constraint: PolicyConstraint,
    request: Dict[str, Any],
    context: Dict[str, Any],
    now: datetime,
) -> Tuple[bool, str, Optional[AuthorityVerdict]]:
    """Check that the actor's scope covers the required scope.

    Parameters:
        scope: required scope string
    """
    required_scope = constraint.parameters.get("scope", "")
    if not required_scope:
        return True, "scope_limit:no_scope_required", None

    actor = context.get("_resolved_actor")
    if actor is None:
        # No resolved actor — graceful pass (actor_resolve step handles this)
        return True, "scope_limit:no_resolved_actor", None

    # Collect scopes from actor roles
    actor_scopes: List[str] = []
    if hasattr(actor, "roles"):
        for role in actor.roles:
            scope = role.scope if hasattr(role, "scope") else role.get("scope", "")
            if scope:
                actor_scopes.append(scope)
    elif isinstance(actor, dict):
        for role in actor.get("roles", []):
            scope = role.get("scope", "")
            if scope:
                actor_scopes.append(scope)

    # Check overlap: exact match or prefix match
    for scope in actor_scopes:
        if scope == required_scope or required_scope.startswith(scope):
            return True, f"scope_limit_ok:actor={scope},required={required_scope}", None

    return (
        False,
        f"scope_limit_violation:actor_scopes={actor_scopes},required={required_scope}",
        AuthorityVerdict.BLOCK,
    )


def _eval_requires_reasoning(
    constraint: PolicyConstraint,
    request: Dict[str, Any],
    context: Dict[str, Any],
    now: datetime,
) -> Tuple[bool, str, Optional[AuthorityVerdict]]:
    """Check reasoning sufficiency (confidence + truth types).

    Parameters:
        minimum_confidence: float (default 0.7)
        required_truth_types: list of strings
    """
    from .reasoning_gate import check_minimum_confidence, check_required_truth_types

    params = constraint.parameters
    claims = context.get("claims", [])

    min_conf = params.get("minimum_confidence", 0.7)
    met, avg = check_minimum_confidence(claims, threshold=min_conf)
    if not met:
        return (
            False,
            f"reasoning_insufficient:confidence={avg:.2f},required={min_conf}",
            AuthorityVerdict.MISSING_REASONING,
        )

    required_types = params.get("required_truth_types", [])
    if required_types:
        types_met, missing = check_required_truth_types(claims, required_types)
        if not types_met:
            return (
                False,
                f"reasoning_insufficient:missing_types={missing}",
                AuthorityVerdict.MISSING_REASONING,
            )

    return True, "reasoning_sufficient", None


def _eval_blast_radius_max(
    constraint: PolicyConstraint,
    request: Dict[str, Any],
    context: Dict[str, Any],
    now: datetime,
) -> Tuple[bool, str, Optional[AuthorityVerdict]]:
    """Skip — already handled by _step_blast_radius_threshold."""
    return True, "handled_by_pipeline_step", None


def _eval_requires_dlr(
    constraint: PolicyConstraint,
    request: Dict[str, Any],
    context: Dict[str, Any],
    now: datetime,
) -> Tuple[bool, str, Optional[AuthorityVerdict]]:
    """Skip — already handled by _step_dlr_presence."""
    return True, "handled_by_pipeline_step", None


# ── Evaluator Registry ────────────────────────────────────────────

_EVALUATORS: Dict[str, Callable] = {
    "time_window": _eval_time_window,
    "blast_radius_max": _eval_blast_radius_max,
    "requires_approval": _eval_requires_approval,
    "requires_dlr": _eval_requires_dlr,
    "requires_reasoning": _eval_requires_reasoning,
    "scope_limit": _eval_scope_limit,
    "rate_limit": _eval_rate_limit,
}


# ── Top-Level Constraint Executor ─────────────────────────────────


def execute_constraints(
    constraints: List[PolicyConstraint],
    request: Dict[str, Any],
    context: Dict[str, Any],
    now: datetime,
) -> Tuple[bool, str, Optional[AuthorityVerdict]]:
    """Evaluate all compiled policy constraints against a request.

    Iterates through constraints, dispatching to the appropriate evaluator.
    Short-circuits on the first failure. Records individual results in
    ``context["_constraint_results"]``.

    Returns:
        Tuple of (all_passed, detail, verdict_if_failed).
    """
    if not constraints:
        return True, "no_constraints", None

    results: List[ConstraintResult] = []

    for constraint in constraints:
        evaluator = _EVALUATORS.get(constraint.constraint_type)
        if evaluator is None:
            # Unknown constraint type — skip with warning
            logger.warning("unknown constraint type: %s", constraint.constraint_type)
            results.append(ConstraintResult(
                constraint_id=constraint.constraint_id,
                constraint_type=constraint.constraint_type,
                passed=True,
                detail="unknown_type_skipped",
            ))
            continue

        passed, detail, verdict = evaluator(constraint, request, context, now)

        results.append(ConstraintResult(
            constraint_id=constraint.constraint_id,
            constraint_type=constraint.constraint_type,
            passed=passed,
            detail=detail,
            verdict=verdict.value if verdict else "",
        ))

        if not passed:
            context["_constraint_results"] = results
            return False, f"constraint_failed:{constraint.constraint_id}:{detail}", verdict

    context["_constraint_results"] = results
    return True, "all_constraints_satisfied", None


# ── Expiry Condition Evaluator ────────────────────────────────────


def evaluate_expiry_conditions(
    conditions: List[ExpiryCondition],
    context: Dict[str, Any],
    now: datetime,
) -> Tuple[bool, str]:
    """Evaluate a list of expiry conditions.

    Handles TIME_ABSOLUTE, TIME_RELATIVE, and EXTERNAL_EVENT.
    Skips CLAIM_HALF_LIFE and DELEGATION_EXPIRY (handled elsewhere).

    Returns:
        Tuple of (all_valid, detail).
    """
    if not conditions:
        return True, "no_expiry_conditions"

    for condition in conditions:
        ct = condition.condition_type

        if ct in (
            ExpiryConditionType.CLAIM_HALF_LIFE.value,
            ExpiryConditionType.DELEGATION_EXPIRY.value,
        ):
            continue  # Handled by pipeline steps

        if ct == ExpiryConditionType.TIME_ABSOLUTE.value:
            if condition.expires_at:
                try:
                    exp = datetime.fromisoformat(
                        condition.expires_at.replace("Z", "+00:00")
                    )
                    if now >= exp:
                        condition.is_expired = True
                        return False, f"expired:time_absolute:{condition.condition_id}"
                except (ValueError, TypeError):
                    pass

        elif ct == ExpiryConditionType.TIME_RELATIVE.value:
            ref = condition.half_life_ref
            effective_at = context.get("grant_effective_at")
            if ref and effective_at:
                try:
                    duration = _parse_iso_duration(ref)
                    if isinstance(effective_at, str):
                        effective_at = datetime.fromisoformat(
                            effective_at.replace("Z", "+00:00")
                        )
                    if now >= effective_at + duration:
                        condition.is_expired = True
                        return False, f"expired:time_relative:{condition.condition_id}"
                except (ValueError, TypeError):
                    pass

        elif ct == ExpiryConditionType.EXTERNAL_EVENT.value:
            events = context.get("external_events", {})
            if events.get(condition.condition_id, False):
                condition.is_expired = True
                return False, f"expired:external_event:{condition.condition_id}"

    return True, "all_conditions_valid"
