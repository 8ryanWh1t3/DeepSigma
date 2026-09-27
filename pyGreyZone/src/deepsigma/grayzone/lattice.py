"""Configurable adapter for Lattice-like JSONL exports, not an official schema."""

from __future__ import annotations

from pathlib import Path

from .ingest import load_events
from .schema import Event, FieldMap


LATTICE_EXAMPLE_MAP = FieldMap(
    event_id="id", occurred_at="timestamp", kind="type", channel="channel",
    summary="summary", source_id="source.system", record_id="source.record_id",
    lineage_group="source.lineage_group", entities="entities", assets="assets",
    location="location.id", tags="labels",
)


def load_lattice_jsonl(path: str | Path, mapping: FieldMap = LATTICE_EXAMPLE_MAP) -> list[Event]:
    """Map an approved export using known local paths; customize FieldMap for real feeds."""
    return load_events(path, mapping, default_source="lattice-export")
