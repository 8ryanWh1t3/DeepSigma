"""Stable content hashes and source lineage summaries."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable

from .schema import Event


def digest(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def groups(events: Iterable[Event]) -> tuple[str, ...]:
    return tuple(sorted({s.independent_group for e in events for s in e.sources}))


def evidence_index(events: Iterable[Event]) -> dict[str, list[dict[str, str]]]:
    return {
        e.id: [
            {"source_id": s.source_id, "record_id": s.record_id,
             "lineage_group": s.independent_group, "sha256": s.sha256,
             "locator": s.locator}
            for s in e.sources
        ]
        for e in events
    }
