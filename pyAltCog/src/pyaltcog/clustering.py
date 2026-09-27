from __future__ import annotations

from collections import defaultdict
from typing import Iterable, List

from .ids import stable_id
from .models import DiscoverySurface, ExceptionClusterCard, FrictionSignalRecord
from .text import feature_terms, jaccard


def _similarity(a: FrictionSignalRecord, b: FrictionSignalRecord) -> float:
    lexical = jaccard(feature_terms(a.statement, a.tags), feature_terms(b.statement, b.tags))
    same_domain = 0.12 if a.domain and a.domain == b.domain else 0.0
    same_surface = 0.08 if a.surface == b.surface else 0.0
    return min(1.0, lexical + same_domain + same_surface)


def cluster_signals(
    signals: Iterable[FrictionSignalRecord],
    *,
    min_similarity: float = 0.25,
    created_at: str = "",
) -> List[ExceptionClusterCard]:
    """Deterministically cluster signals using connected components over pair similarity."""
    items = sorted(list(signals), key=lambda s: s.id)
    if not items:
        return []

    parent = list(range(len(items)))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)

    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            if items[i].stream_id != items[j].stream_id:
                continue
            if _similarity(items[i], items[j]) >= min_similarity:
                union(i, j)

    groups: dict[int, list[FrictionSignalRecord]] = defaultdict(list)
    for i, item in enumerate(items):
        groups[find(i)].append(item)

    cards: List[ExceptionClusterCard] = []
    for _, group in sorted(groups.items(), key=lambda kv: min(x.id for x in kv[1])):
        ids = sorted(s.id for s in group)
        all_terms = set()
        surfaces: set[DiscoverySurface] = set()
        domains = set()
        strengths = []
        for s in group:
            all_terms |= feature_terms(s.statement, s.tags)
            surfaces.add(s.surface)
            if s.domain:
                domains.add(s.domain)
            strengths.append(s.strength)
        payload = {"stream_id": group[0].stream_id, "signal_ids": ids}
        cards.append(
            ExceptionClusterCard(
                id=stable_id("ECC", payload),
                stream_id=group[0].stream_id,
                signal_ids=ids,
                created_at=created_at,
                centroid_terms=sorted(all_terms)[:24],
                surfaces=sorted(surfaces, key=lambda x: x.value),
                domains=sorted(domains),
                strength=sum(strengths) / len(strengths),
            )
        )
    return cards
