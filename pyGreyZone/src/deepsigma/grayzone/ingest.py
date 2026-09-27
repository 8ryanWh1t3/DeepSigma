"""Explicit JSON, JSONL and CSV normalization with line-specific errors."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Iterable, Mapping

from .provenance import digest
from .schema import Event, FieldMap, SourceRef, parse_time


def _get(record: Mapping[str, Any], path: str, default: Any = "") -> Any:
    if not path:
        return default
    value: Any = record
    for key in path.split("."):
        if not isinstance(value, Mapping) or key not in value:
            return default
        value = value[key]
    return default if value is None else value


def _ids(value: Any) -> tuple[str, ...]:
    if value is None or value == "":
        return ()
    if isinstance(value, list):
        items = value
    elif isinstance(value, str):
        items = value.split("|")
    else:
        items = [value]
    result: list[str] = []
    for item in items:
        if isinstance(item, Mapping):
            item = item.get("id", "")
        token = str(item).strip()
        if token and token not in result:
            result.append(token)
    return tuple(result)


def normalize(record: Mapping[str, Any], mapping: FieldMap = FieldMap(), *,
              default_source: str = "unknown", locator: str = "") -> Event:
    if not isinstance(record, Mapping):
        raise ValueError("event must be a JSON object")
    raw_hash = digest(record)
    event_id = str(_get(record, mapping.event_id) or "evt-" + raw_hash[:16])
    source_id = str(_get(record, mapping.source_id) or default_source)
    record_id = str(_get(record, mapping.record_id) or event_id)
    lineage_group = str(_get(record, mapping.lineage_group) or source_id)
    try:
        return Event(
            id=event_id,
            occurred_at=parse_time(_get(record, mapping.occurred_at)),
            kind=str(_get(record, mapping.kind)),
            channel=str(_get(record, mapping.channel)),
            summary=str(_get(record, mapping.summary)),
            sources=(SourceRef(source_id, record_id, raw_hash, lineage_group, locator),),
            entities=_ids(_get(record, mapping.entities)),
            assets=_ids(_get(record, mapping.assets)),
            location=str(_get(record, mapping.location)),
            tags=_ids(_get(record, mapping.tags)),
        )
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{locator or event_id}: {exc}") from exc


def _records(path: Path) -> Iterable[tuple[str, Mapping[str, Any]]]:
    name = path.name.lower()
    if name.endswith((".jsonl", ".ndjson")):
        with path.open(encoding="utf-8-sig") as handle:
            for line_number, line in enumerate(handle, 1):
                if line.strip():
                    try:
                        yield f"{path.name}:{line_number}", json.loads(line)
                    except json.JSONDecodeError as exc:
                        raise ValueError(f"{path.name}:{line_number}: {exc.msg}") from exc
    elif name.endswith(".json"):
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        items = data.get("events", []) if isinstance(data, dict) else data
        if not isinstance(items, list):
            raise ValueError("JSON input must be a list or an object with an events list")
        for i, item in enumerate(items, 1):
            yield f"{path.name}:{i}", item
    elif name.endswith(".csv"):
        with path.open(encoding="utf-8-sig", newline="") as handle:
            for i, item in enumerate(csv.DictReader(handle), 2):
                yield f"{path.name}:{i}", item
    else:
        raise ValueError("input must end in .json, .jsonl, .ndjson or .csv")


def load_events(path: str | Path, mapping: FieldMap = FieldMap(), *,
                default_source: str = "unknown") -> list[Event]:
    source = Path(path)
    events: list[Event] = []
    seen: dict[str, Event] = {}
    for locator, record in _records(source):
        event = normalize(record, mapping, default_source=default_source, locator=locator)
        previous = seen.get(event.id)
        if previous:
            if previous.sources[0].sha256 != event.sources[0].sha256:
                raise ValueError(f"{locator}: duplicate event id with different data: {event.id}")
            continue
        seen[event.id] = event
        events.append(event)
    return events
