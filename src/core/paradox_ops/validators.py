"""Validation rules for Paradox Tension Sets.

Returns lists of error messages (empty list = valid).
"""

from __future__ import annotations

from typing import Any, Dict, List

from .dimensions import COMMON_DIMENSION_NAMES
from .models import PatchAction, ParadoxTensionSet, TensionSubtype


def validate_tension_set(data: Dict[str, Any]) -> List[str]:
    """Validate a PTS creation payload."""
    errors: List[str] = []

    poles = data.get("poles", [])
    if len(poles) < 2:
        errors.append("A tension set requires at least 2 poles.")

    subtype = data.get("subtype", "")
    pole_count = len(poles)
    if subtype == TensionSubtype.TENSION_PAIR and pole_count != 2:
        errors.append(f"tension_pair requires exactly 2 poles, got {pole_count}.")
    elif subtype == TensionSubtype.TENSION_TRIPLE and pole_count != 3:
        errors.append(f"tension_triple requires exactly 3 poles, got {pole_count}.")
    elif subtype == TensionSubtype.HIGHER_ORDER and pole_count < 4:
        errors.append(f"higher_order requires 4+ poles, got {pole_count}.")

    pole_ids = [p.get("poleId", p.get("pole_id", "")) for p in poles]
    if len(pole_ids) != len(set(pole_ids)):
        errors.append("Pole IDs must be unique within a tension set.")

    for p in poles:
        w = p.get("weight", 1.0)
        if not isinstance(w, (int, float)) or w <= 0:
            errors.append(f"Pole weight must be > 0, got {w}.")

    dimensions = data.get("dimensions", [])
    if dimensions:
        dim_names = [d.get("name", "") for d in dimensions]
        has_common = any(n in COMMON_DIMENSION_NAMES for n in dim_names)
        if not has_common:
            errors.append("At least one common dimension is required.")
        if len(dim_names) != len(set(dim_names)):
            errors.append("Dimension names must be unique within a tension set.")

    pressure = data.get("pressureScore", data.get("pressure_score", 0.0))
    if not isinstance(pressure, (int, float)) or pressure < 0.0 or pressure > 1.0:
        errors.append(f"Pressure score must be 0.0-1.0, got {pressure}.")

    return errors


def validate_dimension_shift(
    data: Dict[str, Any],
    pts: ParadoxTensionSet,
) -> List[str]:
    """Validate a dimension shift payload against an existing PTS."""
    errors: List[str] = []

    dim_id = data.get("dimensionId", data.get("dimension_id", ""))
    known_ids = {d.dimension_id for d in pts.dimensions}
    if dim_id not in known_ids:
        errors.append(f"Unknown dimension ID: {dim_id!r}.")

    new_value = data.get("newValue", data.get("new_value"))
    if not isinstance(new_value, (int, float)):
        errors.append(f"New value must be numeric, got {type(new_value).__name__}.")

    return errors


def validate_patch(data: Dict[str, Any]) -> List[str]:
    """Validate a tension patch payload."""
    errors: List[str] = []

    if not data.get("tensionId", data.get("tension_id")):
        errors.append("Tension ID is required.")

    actions = data.get("recommendedActions", data.get("recommended_actions", []))
    valid_actions = {a.value for a in PatchAction}
    for a in actions:
        if a not in valid_actions:
            errors.append(f"Unknown patch action: {a!r}.")

    return errors
