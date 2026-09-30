from __future__ import annotations

from typing import Any

from .authority import trace_authority


def explain_work(work: Any, missions: dict[str, Any], policies: dict[str, Any], authorities: dict[str, Any], systems: dict[str, Any]) -> dict:
    mission = missions.get(work.mission_id) if work.mission_id else None
    policy_chain = trace_authority(work, policies, authorities)
    return {
        "work_id": work.id,
        "work": work.name,
        "why_it_exists": {
            "mission": getattr(mission, "name", None),
            "mission_outcome": getattr(mission, "outcome", None),
            "policy_authority_chain": policy_chain,
        },
        "how_it_operates": {
            "steps": work.steps,
            "dependencies": work.depends_on,
            "systems": [systems[s].name for s in work.system_ids if s in systems],
            "approvals": work.approval_steps,
            "volume_per_month": work.volume_per_month,
            "touch_time_hours": work.touch_time_hours,
            "cycle_time_hours": work.cycle_time_hours,
        },
        "what_it_produces": work.outputs,
        "question": "If this work changed or disappeared, what mission, authority, policy, dependency, system, or outcome would be affected?",
    }
