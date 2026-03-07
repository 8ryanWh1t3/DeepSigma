"""Validation rules for ActionOps payloads.

Returns lists of error messages (empty list = valid).
"""

from __future__ import annotations

from typing import Any, Dict, List

from .models import CommitmentType, DeliverableStatus


def validate_commitment(data: Dict[str, Any]) -> List[str]:
    """Validate a commitment creation payload."""
    errors: List[str] = []

    if not data.get("text"):
        errors.append("Commitment text is required.")
    if not data.get("domain"):
        errors.append("Domain is required.")
    if not data.get("owner"):
        errors.append("Owner is required.")

    ctype = data.get("commitmentType", data.get("commitment_type", ""))
    valid_types = {t.value for t in CommitmentType}
    if ctype and ctype not in valid_types:
        errors.append(f"Unknown commitment type: {ctype!r}.")

    risk = data.get("riskScore", data.get("risk_score", 0.0))
    if not isinstance(risk, (int, float)) or risk < 0.0 or risk > 1.0:
        errors.append(f"Risk score must be 0.0-1.0, got {risk}.")

    deliverables = data.get("deliverables", [])
    for i, d in enumerate(deliverables):
        if not d.get("description"):
            errors.append(f"Deliverable [{i}] requires a description.")

    return errors


def validate_deliverable_update(data: Dict[str, Any]) -> List[str]:
    """Validate a deliverable status update payload."""
    errors: List[str] = []

    if not data.get("commitmentId", data.get("commitment_id")):
        errors.append("Commitment ID is required.")
    if not data.get("deliverableId", data.get("deliverable_id")):
        errors.append("Deliverable ID is required.")

    status = data.get("status", "")
    if status:
        valid = {s.value for s in DeliverableStatus}
        if status not in valid:
            errors.append(f"Unknown deliverable status: {status!r}.")

    return errors


def validate_compliance_check(data: Dict[str, Any]) -> List[str]:
    """Validate a compliance check payload."""
    errors: List[str] = []

    if not data.get("commitmentId", data.get("commitment_id")):
        errors.append("Commitment ID is required.")

    check_type = data.get("checkType", data.get("check_type", ""))
    valid_types = {"deadline", "quality", "resource_utilization"}
    if check_type and check_type not in valid_types:
        errors.append(f"Unknown check type: {check_type!r}.")

    return errors
