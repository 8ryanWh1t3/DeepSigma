from __future__ import annotations

from typing import Any


def estimate_monthly_workload(work: list[Any]) -> dict:
    base_hours = 0.0
    rework_hours = 0.0
    waiting_hours = 0.0
    for w in work:
        if not w.active:
            continue
        base = w.volume_per_month * w.touch_time_hours
        base_hours += base
        rework_hours += base * max(0.0, w.rework_rate)
        waiting_hours += w.volume_per_month * max(0.0, w.cycle_time_hours - w.touch_time_hours)
    return {
        "touch_hours_per_month": round(base_hours, 2),
        "rework_hours_per_month": round(rework_hours, 2),
        "calendar_wait_hours_per_month": round(waiting_hours, 2),
    }


def estimate_labor_cost(work: list[Any], roles: dict[str, Any]) -> dict:
    total = 0.0
    unresolved_hours = 0.0
    for w in work:
        if not w.active:
            continue
        hours = w.volume_per_month * w.touch_time_hours * (1.0 + max(0.0, w.rework_rate))
        costs = [roles[r].loaded_hourly_cost for r in w.role_ids if r in roles and roles[r].loaded_hourly_cost > 0]
        if costs:
            total += hours * (sum(costs) / len(costs))
        else:
            unresolved_hours += hours
    return {
        "estimated_monthly_labor_cost": round(total, 2),
        "hours_without_cost_binding": round(unresolved_hours, 2),
        "note": "Architecture-level estimate; not an employee performance score.",
    }
