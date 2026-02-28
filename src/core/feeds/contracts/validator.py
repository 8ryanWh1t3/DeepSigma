"""FEEDS contract validator — verify events match their declared contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .loader import RoutingTable


@dataclass
class ContractViolation:
    """A single contract validation violation."""

    function_id: str
    field: str
    message: str


@dataclass
class ContractResult:
    """Result of contract validation."""

    valid: bool
    violations: List[ContractViolation] = field(default_factory=list)


def validate_event_contract(
    event: Dict[str, Any],
    function_id: str,
    table: RoutingTable,
) -> ContractResult:
    """Validate that a FEEDS event conforms to its function contract.

    Checks:
    1. Function ID exists in routing table
    2. Event topic matches the function's input topic
    3. Event subtype matches the function's input subtype
    4. Required payload fields are present

    Args:
        event: A FEEDS envelope dict.
        function_id: The function ID processing this event.
        table: The loaded routing table.

    Returns:
        ContractResult with valid=True if all checks pass.
    """
    violations: List[ContractViolation] = []

    contract = table.get_function(function_id)
    if contract is None:
        violations.append(ContractViolation(
            function_id=function_id,
            field="function_id",
            message=f"Function {function_id} not found in routing table",
        ))
        return ContractResult(valid=False, violations=violations)

    # Check topic
    event_topic = event.get("topic", "")
    if event_topic != contract.input_topic:
        violations.append(ContractViolation(
            function_id=function_id,
            field="topic",
            message=f"Expected topic '{contract.input_topic}', got '{event_topic}'",
        ))

    # Check subtype
    event_subtype = event.get("subtype", "")
    if event_subtype != contract.input_subtype:
        violations.append(ContractViolation(
            function_id=function_id,
            field="subtype",
            message=f"Expected subtype '{contract.input_subtype}', got '{event_subtype}'",
        ))

    # Check required payload fields
    payload = event.get("payload", {})
    for req_field in contract.required_payload_fields:
        if req_field not in payload:
            violations.append(ContractViolation(
                function_id=function_id,
                field=f"payload.{req_field}",
                message=f"Required payload field '{req_field}' is missing",
            ))

    return ContractResult(valid=len(violations) == 0, violations=violations)


def validate_output_event(
    event: Dict[str, Any],
    function_id: str,
    table: RoutingTable,
) -> ContractResult:
    """Validate that an output event matches the producing function's declared outputs.

    Checks:
    1. Function ID exists in routing table
    2. Event topic is in the function's output topics
    3. Event subtype is in the function's output subtypes

    Args:
        event: A FEEDS envelope dict being emitted.
        function_id: The function ID producing this event.
        table: The loaded routing table.

    Returns:
        ContractResult with valid=True if all checks pass.
    """
    violations: List[ContractViolation] = []

    contract = table.get_function(function_id)
    if contract is None:
        violations.append(ContractViolation(
            function_id=function_id,
            field="function_id",
            message=f"Function {function_id} not found in routing table",
        ))
        return ContractResult(valid=False, violations=violations)

    event_topic = event.get("topic", "")
    if event_topic and event_topic not in contract.output_topics:
        violations.append(ContractViolation(
            function_id=function_id,
            field="topic",
            message=f"Output topic '{event_topic}' not in declared outputs {list(contract.output_topics)}",
        ))

    event_subtype = event.get("subtype", "")
    if event_subtype and event_subtype not in contract.output_subtypes:
        violations.append(ContractViolation(
            function_id=function_id,
            field="subtype",
            message=f"Output subtype '{event_subtype}' not in declared outputs {list(contract.output_subtypes)}",
        ))

    return ContractResult(valid=len(violations) == 0, violations=violations)


def validate_routing_table_integrity(table: RoutingTable) -> ContractResult:
    """Validate internal consistency of the routing table.

    Checks:
    1. Every emitted event ID exists in the events registry
    2. Every consumed event references a valid function
    3. Every event's producedBy references a valid function
    4. No orphaned events (at least one producer)

    Returns:
        ContractResult with any integrity violations found.
    """
    violations: List[ContractViolation] = []

    # Check function -> event references
    for fid, fn in table.functions.items():
        for eid in fn.emits_events:
            if eid not in table.events:
                violations.append(ContractViolation(
                    function_id=fid,
                    field="emitsEvents",
                    message=f"Function {fid} emits event {eid} which is not declared in events registry",
                ))

    # Check event -> function references
    for eid, ev in table.events.items():
        for fid in ev.produced_by:
            if fid not in table.functions:
                violations.append(ContractViolation(
                    function_id=fid,
                    field="producedBy",
                    message=f"Event {eid} declares producer {fid} which is not in functions registry",
                ))
        for fid in ev.consumed_by:
            if fid not in table.functions:
                violations.append(ContractViolation(
                    function_id=fid,
                    field="consumedBy",
                    message=f"Event {eid} declares consumer {fid} which is not in functions registry",
                ))

    # Check no orphaned events
    for eid, ev in table.events.items():
        if not ev.produced_by:
            violations.append(ContractViolation(
                function_id="",
                field="producedBy",
                message=f"Event {eid} has no producers",
            ))

    return ContractResult(valid=len(violations) == 0, violations=violations)
