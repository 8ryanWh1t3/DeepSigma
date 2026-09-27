"""Stable assessment entry point; no current-clock or random state."""

from __future__ import annotations

from datetime import timedelta
from typing import Iterable

from .campaign import hypotheses
from .correlate import link_events
from .provenance import digest
from .schema import Assessment, AssessmentConfig, Event
from .temporal import in_window
from .weak_signal import find_weak_signals


def assess(events: Iterable[Event], config: AssessmentConfig = AssessmentConfig()) -> Assessment:
    supplied = tuple(events)
    if len(supplied) > config.max_events:
        raise ValueError(f"too many events for local pairwise assessment (max {config.max_events})")
    ids: dict[str, Event] = {}
    records: dict[tuple[str, str], str] = {}
    for event in supplied:
        if event.id in ids and ids[event.id] != event:
            raise ValueError(f"duplicate event id with different content: {event.id}")
        ids[event.id] = event
        for source in event.sources:
            key = (source.source_id, source.record_id)
            if key in records and records[key] != source.sha256:
                raise ValueError(f"source record changed content: {source.source_id}/{source.record_id}")
            records[key] = source.sha256
    selected = in_window(ids.values(), config.window)
    links = link_events(selected, config)
    return Assessment(
        id="assessment-" + digest({"events": [(e.id, [s.sha256 for s in e.sources]) for e in selected],
                                    "config": (config.window.total_seconds(), config.max_link_gap.total_seconds(),
                                               config.min_events, config.min_channels,
                                               config.min_source_groups, config.min_link_score)})[:16],
        window_start=selected[-1].occurred_at - config.window if selected else None,
        window_end=selected[-1].occurred_at if selected else None,
        events=selected, links=links, weak_signals=find_weak_signals(selected, links),
        hypotheses=hypotheses(selected, links, config),
    )


class GrayZoneEpisode:
    def __init__(self, events: Iterable[Event], window: str | timedelta = "30d") -> None:
        if isinstance(window, str):
            if not window.endswith("d") or not window[:-1].isdigit():
                raise ValueError("window must be a positive number of days, e.g. '30d'")
            window = timedelta(days=int(window[:-1]))
        self.events = tuple(events)
        self.window = window

    def assess(self, config: AssessmentConfig | None = None) -> Assessment:
        return assess(self.events, config or AssessmentConfig(window=self.window))
