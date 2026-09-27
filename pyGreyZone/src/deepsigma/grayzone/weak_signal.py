"""Surface partial links and recurrence even when campaign gates are unmet."""

from __future__ import annotations

from collections import defaultdict

from .correlate import components
from .provenance import digest
from .schema import Event, EventLink, WeakSignal


def find_weak_signals(events: tuple[Event, ...], links: tuple[EventLink, ...]) -> tuple[WeakSignal, ...]:
    signals: list[WeakSignal] = []
    for ids in components(events, links):
        if len(ids) > 1:
            signals.append(WeakSignal("weak-" + digest(ids)[:12], ids,
                "Linked observations require source and benign-explanation review."))
    by_tag: dict[str, set[str]] = defaultdict(set)
    for event in events:
        for tag in event.tags:
            by_tag[tag].add(event.id)
    for tag, ids in sorted(by_tag.items()):
        if len(ids) >= 3:
            ordered = tuple(sorted(ids))
            signals.append(WeakSignal("repeat-" + digest((tag, ordered))[:12], ordered,
                f"Repeated tag {tag!r}; frequency is uncalibrated without a baseline."))
    return tuple(signals)
