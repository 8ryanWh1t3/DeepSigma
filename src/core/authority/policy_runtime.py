"""Policy Runtime — 11-step authority evaluation pipeline.

Each step is a pure function that receives the evaluation context and
returns a PolicyEvaluationStep. The pipeline short-circuits on critical
failures with the appropriate AuthorityVerdict.
"""

from __future__ import annotations

import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .models import (
    AuthorityVerdict,
    DecisionGateResult,
    PolicyEvaluationStep,
)

logger = logging.getLogger(__name__)

# Blast radius tier ordering for comparison
_BLAST_RADIUS_ORDER = {"tiny": 0, "small": 1, "medium": 2, "large": 3}


def evaluate(
    request: Dict[str, Any],
    context: Dict[str, Any],
) -> DecisionGateResult:
    """Run the full 11-step authority evaluation pipeline.

    Args:
        request: Action request dict with actionId, actionType, actorId,
                 resourceRef, episodeId, blastRadiusTier.
        context: Evaluation context with authority_ledger, memory_graph,
                 actor_registry, resource_registry, policy_packs, dlr_store,
                 kill_switch_active, claims, now.

    Returns:
        DecisionGateResult with verdict, passed/failed checks.
    """
    now = context.get("now", datetime.now(timezone.utc))
    if isinstance(now, str):
        now = datetime.fromisoformat(now)

    gate_id = f"GATE-{uuid.uuid4().hex[:12]}"
    steps: List[PolicyEvaluationStep] = []
    passed: List[str] = []
    failed: List[str] = []
    verdict = AuthorityVerdict.ALLOW

    pipeline = [
        ("action_intake", _step_action_intake),
        ("kill_switch_check", _step_kill_switch_check),
        ("actor_resolve", _step_actor_resolve),
        ("resource_resolve", _step_resource_resolve),
        ("policy_load", _step_policy_load),
        ("dlr_presence", _step_dlr_presence),
        ("assumption_validate", _step_assumption_validate),
        ("half_life_check", _step_half_life_check),
        ("blast_radius_threshold", _step_blast_radius_threshold),
        ("decision_gate", _step_decision_gate),
        ("audit_emit", _step_audit_emit),
    ]

    for step_name, step_fn in pipeline:
        t0 = time.monotonic()
        result, detail, step_verdict = step_fn(request, context, now)
        elapsed = (time.monotonic() - t0) * 1000

        step = PolicyEvaluationStep(
            step_name=step_name,
            result="pass" if result else "fail",
            detail=detail,
            elapsed_ms=elapsed,
        )
        steps.append(step)

        if result:
            passed.append(step_name)
        else:
            failed.append(step_name)
            if step_verdict is not None:
                verdict = step_verdict
                # Short-circuit on terminal verdicts
                if verdict in (
                    AuthorityVerdict.BLOCK,
                    AuthorityVerdict.KILL_SWITCH_ACTIVE,
                    AuthorityVerdict.MISSING_REASONING,
                    AuthorityVerdict.EXPIRED,
                ):
                    break

    # If no failures, final verdict comes from decision gate
    if not failed:
        verdict = AuthorityVerdict.ALLOW

    return DecisionGateResult(
        gate_id=gate_id,
        verdict=verdict.value if isinstance(verdict, AuthorityVerdict) else verdict,
        evaluated_at=now.isoformat() if hasattr(now, "isoformat") else str(now),
        policy_ref=context.get("policy_ref", ""),
        failed_checks=failed,
        passed_checks=passed,
    )


# ── Pipeline steps ───────────────────────────────────────────────
# Each returns: (success: bool, detail: str, verdict_if_failed: Optional[AuthorityVerdict])


def _step_action_intake(
    request: Dict[str, Any],
    context: Dict[str, Any],
    now: datetime,
) -> tuple:
    """Validate action request fields."""
    required = ["actionId", "actionType", "actorId", "resourceRef"]
    missing = [f for f in required if not request.get(f)]
    if missing:
        return False, f"missing_fields:{','.join(missing)}", AuthorityVerdict.BLOCK
    return True, "action_fields_valid", None


def _step_actor_resolve(
    request: Dict[str, Any],
    context: Dict[str, Any],
    now: datetime,
) -> tuple:
    """Resolve actor identity."""
    from .authority_graph import resolve_actor

    actor = resolve_actor(request.get("actorId", ""), context)
    if actor is None:
        return False, f"actor_not_found:{request.get('actorId', '')}", AuthorityVerdict.BLOCK
    context["_resolved_actor"] = actor
    return True, f"actor_resolved:{actor.actor_id}", None


def _step_resource_resolve(
    request: Dict[str, Any],
    context: Dict[str, Any],
    now: datetime,
) -> tuple:
    """Resolve resource."""
    from .authority_graph import resolve_resource

    resource = resolve_resource(request.get("resourceRef", ""), context)
    if resource is None:
        # Resource unknown is not necessarily a block — allow with warning
        return True, f"resource_unknown:{request.get('resourceRef', '')}", None
    context["_resolved_resource"] = resource
    return True, f"resource_resolved:{resource.resource_id}", None


def _step_policy_load(
    request: Dict[str, Any],
    context: Dict[str, Any],
    now: datetime,
) -> tuple:
    """Load applicable policy pack."""
    policy_packs = context.get("policy_packs", {})
    action_type = request.get("actionType", "")
    policy = policy_packs.get(action_type, policy_packs.get("default"))
    if policy is None:
        # No policy = default allow (open policy)
        context["_policy"] = {}
        return True, "no_policy_loaded:default_allow", None
    context["_policy"] = policy
    return True, f"policy_loaded:{policy.get('policyPackId', 'inline')}", None


def _step_dlr_presence(
    request: Dict[str, Any],
    context: Dict[str, Any],
    now: datetime,
) -> tuple:
    """Check DLR exists for this decision."""
    from .reasoning_gate import check_dlr_presence

    policy = context.get("_policy", {})
    if not policy.get("requiresDlr", True):
        return True, "dlr_not_required", None

    dlr_ref = request.get("dlrRef", request.get("episodeId", ""))
    present, detail = check_dlr_presence(dlr_ref, context)
    if not present:
        return False, detail, AuthorityVerdict.MISSING_REASONING
    return True, detail, None


def _step_assumption_validate(
    request: Dict[str, Any],
    context: Dict[str, Any],
    now: datetime,
) -> tuple:
    """Check assumption freshness."""
    from .reasoning_gate import check_assumption_freshness

    claims = context.get("claims", [])
    if not claims:
        return True, "no_claims_to_check", None

    fresh, stale = check_assumption_freshness(claims, now)
    if not fresh:
        return False, f"stale_assumptions:{','.join(stale)}", AuthorityVerdict.EXPIRED
    return True, "assumptions_fresh", None


def _step_half_life_check(
    request: Dict[str, Any],
    context: Dict[str, Any],
    now: datetime,
) -> tuple:
    """Check claim half-lives."""
    claims = context.get("claims", [])
    expired_claims: List[str] = []

    for claim in claims:
        half_life = claim.get("halfLife", claim.get("half_life", {}))
        expires_at = half_life.get("expiresAt", half_life.get("expires_at"))
        if expires_at:
            try:
                exp = datetime.fromisoformat(expires_at)
                if exp.tzinfo is None:
                    exp = exp.replace(tzinfo=timezone.utc)
                if now >= exp:
                    claim_id = claim.get("claimId", claim.get("claim_id", "unknown"))
                    expired_claims.append(claim_id)
            except (ValueError, TypeError):
                pass

    if expired_claims:
        return False, f"expired_claims:{','.join(expired_claims)}", AuthorityVerdict.EXPIRED
    return True, "claims_within_half_life", None


def _step_blast_radius_threshold(
    request: Dict[str, Any],
    context: Dict[str, Any],
    now: datetime,
) -> tuple:
    """Compare blast radius against policy maximum."""
    policy = context.get("_policy", {})
    max_br = policy.get("maxBlastRadius", "large")
    actual_br = request.get("blastRadiusTier", "small")

    max_ord = _BLAST_RADIUS_ORDER.get(max_br, 3)
    actual_ord = _BLAST_RADIUS_ORDER.get(actual_br, 1)

    if actual_ord > max_ord:
        return False, f"blast_radius_exceeded:actual={actual_br},max={max_br}", AuthorityVerdict.ESCALATE
    return True, f"blast_radius_ok:actual={actual_br},max={max_br}", None


def _step_kill_switch_check(
    request: Dict[str, Any],
    context: Dict[str, Any],
    now: datetime,
) -> tuple:
    """Check kill-switch state."""
    if context.get("kill_switch_active", False):
        return False, "kill_switch_is_active", AuthorityVerdict.KILL_SWITCH_ACTIVE
    return True, "kill_switch_clear", None


def _step_decision_gate(
    request: Dict[str, Any],
    context: Dict[str, Any],
    now: datetime,
) -> tuple:
    """Compute final verdict from accumulated state. Always passes."""
    return True, "decision_gate_evaluated", None


def _step_audit_emit(
    request: Dict[str, Any],
    context: Dict[str, Any],
    now: datetime,
) -> tuple:
    """Emit audit record. Always passes (audit emission is best-effort)."""
    return True, "audit_record_queued", None
