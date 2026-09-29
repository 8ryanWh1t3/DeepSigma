"""CERPA integration for OpenShell policy/runtime changes."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from core.cerpa.engine import run_cerpa_cycle
from core.cerpa.models import CerpaCycle, Claim, Event

from .models import AgentMissionContract, GovernedPlan, OpenShellAuditEvent
from .audit import to_cerpa_event


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def contract_claim(contract: AgentMissionContract) -> Claim:
    """Represent the governing mission contract as a CERPA claim."""
    return Claim(
        id=f"OSCLAIM-{contract.contract_id}",
        text=(
            f"Agent {contract.agent_id} is authorized only within mission "
            f"{contract.mission!r} and authority scope {contract.authority_scope!r}."
        ),
        domain="authorityops",
        source="deepsigma.openshell",
        timestamp=_now(),
        assumptions=list(contract.assumptions),
        authority=contract.authority_scope,
        provenance=[{"type": "mission_contract", "ref": contract.contract_id, "hash": contract.canonical_hash()}],
        related_ids=[contract.episode_id],
        metadata={
            "blast_radius_tier": contract.blast_radius_tier,
            "kill_conditions": list(contract.kill_conditions),
        },
    )


def policy_plan_event(plan: GovernedPlan) -> Event:
    """Create a CERPA event for a proposed/applied OpenShell policy state."""
    violation = plan.status == "blocked"
    return Event(
        id=f"OSEVT-PLAN-{uuid.uuid4().hex[:10]}",
        text=f"OpenShell policy plan {plan.plan_id} status={plan.status}",
        domain="authorityops",
        source="deepsigma.openshell",
        timestamp=_now(),
        observed_state={
            "status": "violated" if violation else "observed",
            "plan_status": plan.status,
            "policy_hash": plan.projection.policy_hash,
            "expands_access": plan.delta.expands_access,
            "static_changed": plan.delta.static_changed,
            "dynamic_changed": plan.delta.dynamic_changed,
        },
        provenance=[
            {"type": "mission_contract", "hash": plan.projection.contract_hash},
            {"type": "openshell_policy", "hash": plan.projection.policy_hash},
        ],
        related_ids=[plan.contract.contract_id, plan.contract.episode_id],
        metadata={
            "violation": violation,
            "violation_detail": "; ".join(plan.reasons) if violation else "",
            "authority_verdict": plan.authority.verdict,
        },
    )


def run_plan_cycle(plan: GovernedPlan) -> CerpaCycle:
    return run_cerpa_cycle(contract_claim(plan.contract), policy_plan_event(plan))


def run_runtime_event_cycle(
    contract: AgentMissionContract,
    runtime_event: OpenShellAuditEvent,
) -> CerpaCycle:
    event = to_cerpa_event(
        runtime_event,
        contract_id=contract.contract_id,
        episode_id=contract.episode_id,
    )
    return run_cerpa_cycle(contract_claim(contract), event)


__all__ = [
    "contract_claim",
    "policy_plan_event",
    "run_plan_cycle",
    "run_runtime_event_cycle",
]
