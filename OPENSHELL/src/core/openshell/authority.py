"""PATHFINDER/AuthorityOps bridge for OpenShell actions."""

from __future__ import annotations

import uuid
from typing import Any, Dict, Optional

from core.authority.models import CompiledPolicy
from core.authority.runtime_gate import RuntimeGate

from .models import AgentMissionContract, AuthorityDecision


class DeepSigmaAuthorityAdapter:
    """Evaluate OpenShell changes with the existing Deep Sigma RuntimeGate."""

    def __init__(
        self,
        context: Dict[str, Any],
        compiled_policy: Optional[CompiledPolicy] = None,
        runtime_gate: Optional[RuntimeGate] = None,
    ) -> None:
        self.context = context
        self.compiled_policy = compiled_policy
        self.runtime_gate = runtime_gate or RuntimeGate()

    def evaluate(
        self,
        contract: AgentMissionContract,
        *,
        sandbox_name: str,
        action_type: str = "openshell_policy_change",
    ) -> AuthorityDecision:
        request = {
            "actionId": f"OSACT-{uuid.uuid4().hex[:12]}",
            "actionType": action_type,
            "actorId": contract.actor_id,
            "resourceRef": f"openshell:{sandbox_name}",
            "episodeId": contract.episode_id,
            "blastRadiusTier": contract.blast_radius_tier,
            "authorityScope": contract.authority_scope,
            "contractId": contract.contract_id,
        }
        # RuntimeGate mutates context by attaching _compiled, so isolate callers.
        context = dict(self.context)
        if self.compiled_policy is not None:
            result = self.runtime_gate.evaluate(self.compiled_policy, request, context)
        else:
            result = self.runtime_gate.evaluate_raw(request, context)

        reason = result.failed_reason or (
            "authority allowed" if result.verdict == "ALLOW" else "authority gate denied or escalated"
        )
        return AuthorityDecision(
            verdict=result.verdict,
            gate_id=result.gate_id,
            reason=reason,
            passed_checks=list(result.passed_checks),
            failed_checks=list(result.failed_checks),
            escalation_target=result.escalation_target,
        )


class AllowAuthorityAdapter:
    """Explicit development adapter; never use as a hidden production default."""

    def evaluate(self, contract: AgentMissionContract, *, sandbox_name: str, action_type: str = "openshell_policy_change") -> AuthorityDecision:
        return AuthorityDecision(
            verdict="ALLOW",
            gate_id="DEV-ALLOW",
            reason="explicit AllowAuthorityAdapter",
        )


__all__ = ["AllowAuthorityAdapter", "DeepSigmaAuthorityAdapter"]
