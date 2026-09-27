"""Generate bounded, unreviewed pattern hypotheses from explicit gates."""

from __future__ import annotations

from .altcog import challenge
from .confidence import collection_gaps
from .correlate import components
from .provenance import digest, groups
from .schema import AssessmentConfig, Event, EventLink, Hypothesis


def hypotheses(events: tuple[Event, ...], links: tuple[EventLink, ...],
               config: AssessmentConfig) -> tuple[Hypothesis, ...]:
    by_id = {e.id: e for e in events}
    result: list[Hypothesis] = []
    for ids in components(events, links):
        group = tuple(by_id[i] for i in ids)
        channels = tuple(sorted({e.channel for e in group}))
        source_groups = groups(group)
        if (len(group) < config.min_events or len(channels) < config.min_channels
                or len(source_groups) < config.min_source_groups):
            continue
        associated = tuple((x.left, x.right) for x in links if x.left in ids and x.right in ids)
        max_edges = len(group) * (len(group) - 1) / 2
        density = len(associated) / max_edges
        # Transparent ranking for triage, not a calibrated likelihood.
        priority = min(100, round(15 + min(len(group), 5) * 8
                                  + min(len(channels), 4) * 7
                                  + min(len(source_groups), 4) * 5
                                  + density * 17))
        result.append(Hypothesis(
            id="hyp-" + digest(ids)[:12], event_ids=ids, link_ids=associated,
            source_groups=source_groups, channels=channels, priority_score=priority,
            statement="Possible related pattern across observations; coordination remains unproven.",
            alternatives=challenge(), collection_gaps=collection_gaps(group),
        ))
    return tuple(sorted(result, key=lambda h: (-h.priority_score, h.id)))
