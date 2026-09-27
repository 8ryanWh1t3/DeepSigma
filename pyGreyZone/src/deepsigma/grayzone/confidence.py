"""Evidence-quality gaps; scores elsewhere are priority, never probability."""

from __future__ import annotations

from .schema import Event


def collection_gaps(events: tuple[Event, ...]) -> tuple[str, ...]:
    gaps = ["Establish an ordinary-rate baseline before interpreting recurrence.",
            "Validate source independence and original record lineage.",
            "Seek disconfirming observations for each competing explanation."]
    if any(not e.entities and not e.assets for e in events):
        gaps.append("Resolve entity or asset identity for observations linked only by context.")
    if any(s.source_id == "unknown" for e in events for s in e.sources):
        gaps.append("Identify unknown source systems before review.")
    return tuple(gaps)
