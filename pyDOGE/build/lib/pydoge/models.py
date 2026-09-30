from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass(slots=True)
class Mission:
    id: str
    name: str
    outcome: str = ""


@dataclass(slots=True)
class Authority:
    id: str
    name: str
    level: str = ""
    source: str = ""


@dataclass(slots=True)
class Policy:
    id: str
    title: str
    authority_id: str | None = None
    requirements: list[str] = field(default_factory=list)


@dataclass(slots=True)
class SystemAsset:
    id: str
    name: str
    kind: str = "application"
    interface_count: int = 0


@dataclass(slots=True)
class RoleCapacity:
    id: str
    name: str
    fte: float = 0.0
    loaded_hourly_cost: float = 0.0


@dataclass(slots=True)
class WorkItem:
    id: str
    name: str
    mission_id: str | None = None
    policy_ids: list[str] = field(default_factory=list)
    system_ids: list[str] = field(default_factory=list)
    role_ids: list[str] = field(default_factory=list)
    depends_on: list[str] = field(default_factory=list)
    steps: list[str] = field(default_factory=list)
    outputs: list[str] = field(default_factory=list)
    volume_per_month: float = 0.0
    touch_time_hours: float = 0.0
    cycle_time_hours: float = 0.0
    rework_rate: float = 0.0
    approval_steps: int = 0
    rule_defined: bool = False
    mission_critical: bool = False
    active: bool = True
    notes: str = ""


@dataclass(slots=True)
class OutcomeObservation:
    work_id: str
    expected: str
    observed: str
    variance: float | None = None
    period: str = ""


def model_to_dict(obj: Any) -> dict[str, Any]:
    return asdict(obj)
