from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import Authority, Mission, OutcomeObservation, Policy, RoleCapacity, SystemAsset, WorkItem


def load_json(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as f:
        return json.load(f)


def dump_json(data: Any, path: str | Path) -> None:
    with Path(path).open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=True)
        f.write("\n")


def parse_dataset(data: dict[str, Any]) -> dict[str, list[Any]]:
    return {
        "missions": [Mission(**x) for x in data.get("missions", [])],
        "authorities": [Authority(**x) for x in data.get("authorities", [])],
        "policies": [Policy(**x) for x in data.get("policies", [])],
        "systems": [SystemAsset(**x) for x in data.get("systems", [])],
        "roles": [RoleCapacity(**x) for x in data.get("roles", [])],
        "work": [WorkItem(**x) for x in data.get("work", [])],
        "outcomes": [OutcomeObservation(**x) for x in data.get("outcomes", [])],
    }
