"""Governed orchestration for Deep Sigma ↔ OpenShell."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from .compiler import OpenShellPolicyCompiler, diff_policies
from .models import (
    AgentMissionContract,
    GovernedPlan,
    PlanStatus,
)
from .semantic import OpenShellSemanticValidator


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class GovernanceError(RuntimeError):
    pass


class GovernedOpenShellController:
    """Coordinate semantic, authority, human and runtime boundaries.

    Important invariant: the controller never treats an OpenShell technical
    policy proof as mission authorization.  Semantic/authority/human gates must
    pass independently before an access expansion is applied.
    """

    def __init__(
        self,
        runtime: Any,
        authority_adapter: Any,
        *,
        compiler: Optional[OpenShellPolicyCompiler] = None,
        semantic_validator: Optional[OpenShellSemanticValidator] = None,
    ) -> None:
        self.runtime = runtime
        self.authority_adapter = authority_adapter
        self.compiler = compiler or OpenShellPolicyCompiler()
        self.semantic_validator = semantic_validator or OpenShellSemanticValidator()

    def plan(
        self,
        contract: AgentMissionContract,
        *,
        sandbox_name: str,
        current_policy: Optional[Dict[str, Any]] = None,
    ) -> GovernedPlan:
        projection = self.compiler.compile(contract)
        semantic = self.semantic_validator.assess(contract, projection)
        authority = self.authority_adapter.evaluate(
            contract,
            sandbox_name=sandbox_name,
            action_type="openshell_policy_change",
        )

        if current_policy is None and self.runtime.sandbox_exists(sandbox_name):
            current_policy = self.runtime.get_base_policy(sandbox_name)
        delta = diff_policies(current_policy, projection.policy)

        reasons = list(delta.reasons)
        blocked = not semantic.passed or authority.verdict in {
            "BLOCK",
            "EXPIRED",
            "MISSING_REASONING",
            "KILL_SWITCH_ACTIVE",
        }
        if not semantic.passed:
            reasons.extend(f"semantic:{f.code}" for f in semantic.findings if f.severity == "critical")
        if authority.verdict != "ALLOW":
            reasons.append(f"authority:{authority.verdict}")

        requires_human = bool(
            contract.human_approval_required
            or delta.expands_access
            or authority.verdict == "ESCALATE"
        )

        if blocked:
            status = PlanStatus.BLOCKED.value
        elif delta.requires_recreate and self.runtime.sandbox_exists(sandbox_name):
            # Still may require approval; caller gets an explicit structural state.
            status = PlanStatus.REQUIRES_RECREATE.value
        elif requires_human:
            status = PlanStatus.PENDING_APPROVAL.value
        else:
            status = PlanStatus.READY.value

        return GovernedPlan(
            plan_id=f"OSPLAN-{uuid.uuid4().hex[:12]}",
            sandbox_name=sandbox_name,
            contract=contract,
            projection=projection,
            semantic=semantic,
            authority=authority,
            delta=delta,
            status=status,
            requires_human_approval=requires_human,
            created_at=_now(),
            reasons=reasons,
        )

    def apply(
        self,
        plan: GovernedPlan,
        *,
        approved_by: Optional[str] = None,
        recreate: bool = False,
    ) -> GovernedPlan:
        if plan.status == PlanStatus.BLOCKED.value:
            raise GovernanceError("plan is blocked and cannot be applied")
        if plan.requires_human_approval and not approved_by:
            raise GovernanceError("human approval is required before this access change can be applied")
        if approved_by:
            plan.approved_by = approved_by

        exists = self.runtime.sandbox_exists(plan.sandbox_name)
        if exists and plan.delta.requires_recreate:
            if not recreate:
                plan.status = PlanStatus.REQUIRES_RECREATE.value
                return plan
            self.runtime.delete(plan.sandbox_name)
            exists = False

        if exists:
            receipt = self.runtime.apply_policy(
                plan.sandbox_name,
                plan.projection.yaml_text,
                wait=True,
            )
        else:
            receipt = self.runtime.create_sandbox(
                plan.sandbox_name,
                plan.projection.yaml_text,
                plan.contract.command,
                image=plan.contract.sandbox_image,
            )

        plan.runtime_receipt = receipt
        plan.applied_at = _now()
        plan.status = PlanStatus.APPLIED.value
        return plan


__all__ = ["GovernanceError", "GovernedOpenShellController"]
