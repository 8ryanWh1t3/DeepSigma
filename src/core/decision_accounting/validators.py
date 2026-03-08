"""Validation functions for decision accounting objects."""

from __future__ import annotations

from typing import Any, Dict, List

from .models import CostCategory

VALID_COST_CATEGORIES = frozenset(c.value for c in CostCategory)
VALID_DEBT_TYPES = frozenset({"rework", "scope_reduction", "quality_shortfall"})


def validate_cost_record(data: Dict[str, Any]) -> List[str]:
    """Validate cost record input data. Returns list of error strings."""
    errors: List[str] = []
    if not data.get("commitmentId") and not data.get("commitment_id"):
        errors.append("commitmentId is required")
    category = data.get("category", "")
    if category and category not in VALID_COST_CATEGORIES:
        errors.append(f"category must be one of {sorted(VALID_COST_CATEGORIES)}")
    amount = data.get("amount", 0)
    if not isinstance(amount, (int, float)) or amount < 0:
        errors.append("amount must be a non-negative number")
    return errors


def validate_value_assessment(data: Dict[str, Any]) -> List[str]:
    """Validate value assessment input data. Returns list of error strings."""
    errors: List[str] = []
    if not data.get("commitmentId") and not data.get("commitment_id"):
        errors.append("commitmentId is required")
    for field_name in ("outcomeQuality", "outcome_quality"):
        val = data.get(field_name)
        if val is not None and (not isinstance(val, (int, float)) or val < 0 or val > 1):
            errors.append(f"{field_name} must be a number in [0, 1]")
    return errors
