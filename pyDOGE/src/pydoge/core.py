from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

from .automation import automation_candidates
from .drift import detect_outcome_drift
from .explain import explain_work
from .graph import DependencyGraph
from .io import load_json, parse_dataset
from .metrics import estimate_labor_cost, estimate_monthly_workload
from .waste import duplicate_candidates, handoff_findings, orphan_findings, rework_findings


class WorkSystem:
    """Mission-first diagnostic surface.

    pyDOGE deliberately evaluates work architecture rather than ranking people.
    """

    PRINCIPLES = (
        "Diagnose work before workforce.",
        "Trace work to mission, authority, and policy.",
        "Score architecture, not employees.",
        "Automation candidates require human authority before implementation.",
        "Workforce implications are downstream of redesigned work.",
    )

    def __init__(self, *, missions=None, authorities=None, policies=None, systems=None, roles=None, work=None, outcomes=None) -> None:
        self.missions = {x.id: x for x in (missions or [])}
        self.authorities = {x.id: x for x in (authorities or [])}
        self.policies = {x.id: x for x in (policies or [])}
        self.systems = {x.id: x for x in (systems or [])}
        self.roles = {x.id: x for x in (roles or [])}
        self.work = {x.id: x for x in (work or [])}
        self.outcomes = list(outcomes or [])
        self.graph = DependencyGraph.from_dependencies({w.id: w.depends_on for w in self.work.values()})

    @classmethod
    def load(cls, path: str | Path) -> "WorkSystem":
        return cls(**parse_dataset(load_json(path)))

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "WorkSystem":
        return cls(**parse_dataset(data))

    def map_work(self) -> dict:
        return {
            "principles": list(self.PRINCIPLES),
            "counts": {
                "missions": len(self.missions),
                "authorities": len(self.authorities),
                "policies": len(self.policies),
                "systems": len(self.systems),
                "roles": len(self.roles),
                "work_items": len(self.work),
            },
            "work": [asdict(w) for w in self.work.values()],
            "dependency_cycles": self.graph.cycles(),
        }

    def trace_authority(self, work_id: str) -> list[dict]:
        from .authority import trace_authority
        return trace_authority(self.work[work_id], self.policies, self.authorities)

    def find_duplicate_work(self, threshold: float = 0.78) -> list[dict]:
        return duplicate_candidates(list(self.work.values()), threshold)

    def find_rework(self, threshold: float = 0.15) -> list[dict]:
        return rework_findings(list(self.work.values()), threshold)

    def find_policy_generated_work(self) -> list[dict]:
        out = []
        for w in self.work.values():
            if w.policy_ids:
                out.append({
                    "work_id": w.id,
                    "work": w.name,
                    "policy_ids": w.policy_ids,
                    "authority_trace": self.trace_authority(w.id),
                })
        return out

    def find_handoff_latency(self, min_wait_ratio: float = 0.50) -> list[dict]:
        return handoff_findings(list(self.work.values()), min_wait_ratio)

    def find_orphan_tasks(self) -> list[dict]:
        return orphan_findings(list(self.work.values()))

    def find_automation_candidates(self, min_volume: float = 20.0) -> list[dict]:
        return automation_candidates(list(self.work.values()), min_volume)

    def find_drift(self, variance_threshold: float = 0.20) -> list[dict]:
        return detect_outcome_drift(self.outcomes, variance_threshold)

    def calculate_blast_radius(self, work_id: str) -> dict:
        downstream = self.graph.downstream(work_id)
        return {
            "work_id": work_id,
            "downstream_work": downstream,
            "downstream_count": len(downstream),
            "mission_critical_downstream": [w for w in downstream if self.work.get(w) and self.work[w].mission_critical],
        }

    def explain(self, work_id: str) -> dict:
        return explain_work(self.work[work_id], self.missions, self.policies, self.authorities, self.systems)

    def metrics(self) -> dict:
        return {
            "workload": estimate_monthly_workload(list(self.work.values())),
            "labor_cost": estimate_labor_cost(list(self.work.values()), self.roles),
        }

    def optimize(self) -> dict:
        duplicates = self.find_duplicate_work()
        rework = self.find_rework()
        handoffs = self.find_handoff_latency()
        orphans = self.find_orphan_tasks()
        automation = self.find_automation_candidates()
        drift = self.find_drift()
        cycles = self.graph.cycles()

        actions = []
        if orphans:
            actions.append({"sequence": 1, "action": "VALIDATE", "target": "orphan work", "count": len(orphans), "why": "Prove mission/policy necessity before optimizing it."})
        if duplicates:
            actions.append({"sequence": 2, "action": "CONSOLIDATE", "target": "duplicate candidates", "count": len(duplicates), "why": "Remove redundant work only after human validation."})
        if handoffs:
            actions.append({"sequence": 3, "action": "REDESIGN", "target": "handoff/approval latency", "count": len(handoffs), "why": "Reduce waiting and routing before reducing capacity."})
        if rework:
            actions.append({"sequence": 4, "action": "PATCH", "target": "rework loops", "count": len(rework), "why": "Correct causes of repeated work."})
        if automation:
            actions.append({"sequence": 5, "action": "AUTOMATE", "target": "bounded work candidates", "count": len(automation), "why": "Automate only after authority, exceptions, and decision rights are understood."})
        actions.append({"sequence": 6, "action": "SIZE", "target": "workforce capacity", "count": None, "why": "Determine capacity requirements from the redesigned work, not as the opening assumption."})

        return {
            "thesis": "Make the system explainable before optimizing it.",
            "sequence": actions,
            "findings": {
                "orphan_work": orphans,
                "duplicate_work": duplicates,
                "handoff_latency": handoffs,
                "rework": rework,
                "automation_candidates": automation,
                "outcome_drift": drift,
                "dependency_cycles": cycles,
            },
            "metrics": self.metrics(),
            "guardrail": "pyDOGE does not rank or score individual employees.",
        }
