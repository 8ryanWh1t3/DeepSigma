"""Explicit, deterministic event windowing and sequence checks."""

from __future__ import annotations

from datetime import timedelta
from typing import Iterable

from .schema import Event


def in_window(events: Iterable[Event], window: timedelta) -> tuple[Event, ...]:
    ordered = tuple(sorted(events, key=lambda e: (e.occurred_at, e.id)))
    if not ordered:
        return ()
    start = ordered[-1].occurred_at - window
    return tuple(e for e in ordered if e.occurred_at >= start)


def span(events: Iterable[Event]) -> timedelta:
    stamps = [e.occurred_at for e in events]
    return max(stamps) - min(stamps) if stamps else timedelta(0)
