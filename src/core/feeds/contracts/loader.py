"""FEEDS routing table loader — load, query, and fingerprint the contract manifest."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

_TABLE_PATH = Path(__file__).resolve().parent / "routing_table.json"


@dataclass(frozen=True)
class FunctionContract:
    """A single domain function contract."""

    function_id: str
    name: str
    domain: str
    input_topic: str
    input_subtype: str
    handler: str
    emits_events: tuple[str, ...]
    output_topics: tuple[str, ...] = ()
    output_subtypes: tuple[str, ...] = ()
    required_payload_fields: tuple[str, ...] = ()
    state_writes: tuple[str, ...] = ()
    description: str = ""


@dataclass(frozen=True)
class EventDeclaration:
    """A single event declaration."""

    event_id: str
    name: str
    domain: str
    topic: str
    subtype: str
    produced_by: tuple[str, ...]
    consumed_by: tuple[str, ...] = ()
    severity: Optional[str] = None
    description: str = ""


@dataclass
class RoutingTable:
    """In-memory representation of the FEEDS routing table."""

    schema_version: str
    generated_at: str
    contract_fingerprint: str
    functions: Dict[str, FunctionContract] = field(default_factory=dict)
    events: Dict[str, EventDeclaration] = field(default_factory=dict)

    # ── Queries ──────────────────────────────────────────────────

    def get_function(self, function_id: str) -> Optional[FunctionContract]:
        """Look up a function contract by ID (e.g. INTEL-F01)."""
        return self.functions.get(function_id)

    def get_event(self, event_id: str) -> Optional[EventDeclaration]:
        """Look up an event declaration by ID (e.g. INTEL-E01)."""
        return self.events.get(event_id)

    def get_handler(self, function_id: str) -> Optional[str]:
        """Return the handler dotted path for a function ID."""
        fn = self.functions.get(function_id)
        return fn.handler if fn else None

    def get_consumers(self, event_id: str) -> List[str]:
        """Return function IDs that consume a given event."""
        ev = self.events.get(event_id)
        return list(ev.consumed_by) if ev else []

    def get_producers(self, event_id: str) -> List[str]:
        """Return function IDs that produce a given event."""
        ev = self.events.get(event_id)
        return list(ev.produced_by) if ev else []

    def functions_by_domain(self, domain: str) -> List[FunctionContract]:
        """Return all functions belonging to a domain."""
        return [f for f in self.functions.values() if f.domain == domain]

    def events_by_domain(self, domain: str) -> List[EventDeclaration]:
        """Return all events belonging to a domain."""
        return [e for e in self.events.values() if e.domain == domain]

    def functions_for_topic(self, topic: str, subtype: Optional[str] = None) -> List[FunctionContract]:
        """Return functions that subscribe to a given topic (and optionally subtype)."""
        results = []
        for fn in self.functions.values():
            if fn.input_topic == topic:
                if subtype is None or fn.input_subtype == subtype:
                    results.append(fn)
        return results

    @property
    def function_ids(self) -> List[str]:
        """All registered function IDs."""
        return sorted(self.functions.keys())

    @property
    def event_ids(self) -> List[str]:
        """All registered event IDs."""
        return sorted(self.events.keys())


def _parse_function(fid: str, raw: Dict[str, Any]) -> FunctionContract:
    """Parse a raw JSON function entry into a FunctionContract."""
    return FunctionContract(
        function_id=fid,
        name=raw["name"],
        domain=raw["domain"],
        input_topic=raw["inputTopic"],
        input_subtype=raw["inputSubtype"],
        handler=raw["handler"],
        emits_events=tuple(raw.get("emitsEvents", [])),
        output_topics=tuple(raw.get("outputTopics", [])),
        output_subtypes=tuple(raw.get("outputSubtypes", [])),
        required_payload_fields=tuple(raw.get("requiredPayloadFields", [])),
        state_writes=tuple(raw.get("stateWrites", [])),
        description=raw.get("description", ""),
    )


def _parse_event(eid: str, raw: Dict[str, Any]) -> EventDeclaration:
    """Parse a raw JSON event entry into an EventDeclaration."""
    return EventDeclaration(
        event_id=eid,
        name=raw["name"],
        domain=raw["domain"],
        topic=raw["topic"],
        subtype=raw["subtype"],
        produced_by=tuple(raw.get("producedBy", [])),
        consumed_by=tuple(raw.get("consumedBy", [])),
        severity=raw.get("severity"),
        description=raw.get("description", ""),
    )


def compute_table_fingerprint(raw: Dict[str, Any]) -> str:
    """Compute SHA-256 fingerprint of the routing table content (functions + events only)."""
    content = {
        "functions": raw.get("functions", {}),
        "events": raw.get("events", {}),
    }
    canonical = json.dumps(content, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def load_routing_table(path: Optional[Path] = None) -> RoutingTable:
    """Load the routing table from disk.

    Args:
        path: Override path to routing_table.json. Defaults to the
              bundled file next to this module.

    Returns:
        Parsed RoutingTable instance.

    Raises:
        FileNotFoundError: If the routing table file does not exist.
        json.JSONDecodeError: If the file is not valid JSON.
    """
    table_path = path or _TABLE_PATH
    raw = json.loads(table_path.read_text(encoding="utf-8"))

    functions = {}
    for fid, fdata in raw.get("functions", {}).items():
        functions[fid] = _parse_function(fid, fdata)

    events = {}
    for eid, edata in raw.get("events", {}).items():
        events[eid] = _parse_event(eid, edata)

    return RoutingTable(
        schema_version=raw.get("schemaVersion", "0.0.0"),
        generated_at=raw.get("generatedAt", ""),
        contract_fingerprint=raw.get("contractFingerprint", ""),
        functions=functions,
        events=events,
    )
