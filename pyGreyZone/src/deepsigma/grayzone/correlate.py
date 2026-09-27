"""Rule-based links require an explicit shared identity or compound context."""

from __future__ import annotations

from .schema import AssessmentConfig, Event, EventLink


def link_events(events: tuple[Event, ...], config: AssessmentConfig) -> tuple[EventLink, ...]:
    links: list[EventLink] = []
    for i, left in enumerate(events):
        for right in events[i + 1:]:
            gap = right.occurred_at - left.occurred_at
            if gap > config.max_link_gap:
                break
            same_entities = set(left.entities) & set(right.entities)
            same_assets = set(left.assets) & set(right.assets)
            same_tags = set(left.tags) & set(right.tags)
            same_location = bool(left.location and left.location == right.location)
            # Shared installation/location alone is not a meaningful relationship.
            if not (same_entities or same_assets or (same_location and same_tags)):
                continue
            score = 0.0
            reasons: list[str] = []
            if same_entities:
                score += .55
                reasons.append("shared entity: " + ", ".join(sorted(same_entities)))
            if same_assets:
                score += .50
                reasons.append("shared asset: " + ", ".join(sorted(same_assets)))
            if same_location:
                score += .15
                reasons.append("shared location: " + left.location)
            if same_tags:
                score += .20
                reasons.append("shared tag: " + ", ".join(sorted(same_tags)))
            score += .15
            reasons.append("within " + str(config.max_link_gap))
            if left.channel != right.channel:
                score += .10
                reasons.append("different channels")
            if score >= config.min_link_score:
                links.append(EventLink(left.id, right.id, round(min(score, 1), 2), tuple(reasons)))
    return tuple(links)


def components(events: tuple[Event, ...], links: tuple[EventLink, ...]) -> tuple[tuple[str, ...], ...]:
    adj: dict[str, set[str]] = {e.id: set() for e in events}
    for link in links:
        adj[link.left].add(link.right)
        adj[link.right].add(link.left)
    seen: set[str] = set()
    result: list[tuple[str, ...]] = []
    for event in events:
        if event.id in seen:
            continue
        todo = [event.id]
        group: set[str] = set()
        while todo:
            node = todo.pop()
            if node not in group:
                group.add(node)
                todo.extend(adj[node] - group)
        seen |= group
        result.append(tuple(sorted(group)))
    return tuple(sorted(result, key=lambda g: (-len(g), g)))
