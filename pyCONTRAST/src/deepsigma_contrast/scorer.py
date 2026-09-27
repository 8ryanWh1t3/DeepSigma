from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from math import sqrt
from typing import Any

from .models import Episode


_WORD_RE = re.compile(r"[A-Za-z0-9_'-]+")


def normalize_text(value: str) -> str:
    return " ".join(_WORD_RE.findall(value.lower()))


def tokens(value: str) -> set[str]:
    return set(normalize_text(value).split())


def jaccard(a: Iterable[str], b: Iterable[str]) -> float:
    sa, sb = set(a), set(b)
    if not sa and not sb:
        return 1.0
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def lexical_episode_similarity(a: Episode, b: Episode) -> float:
    left = " ".join(
        [
            a.title,
            a.claim,
            a.decision,
            a.rationale,
            " ".join(sorted(a.tags)),
            " ".join(a.entities),
            " ".join(x.statement for x in a.assumptions),
        ]
    )
    right = " ".join(
        [
            b.title,
            b.claim,
            b.decision,
            b.rationale,
            " ".join(sorted(b.tags)),
            " ".join(b.entities),
            " ".join(x.statement for x in b.assumptions),
        ]
    )
    return jaccard(tokens(left), tokens(right))


def structural_episode_similarity(a: Episode, b: Episode) -> float:
    scores: list[float] = []
    scores.append(jaccard(a.tags, b.tags))
    scores.append(jaccard(a.entities, b.entities))
    scores.append(jaccard((x.id for x in a.assumptions), (x.id for x in b.assumptions)))
    scores.append(jaccard(a.metadata.keys(), b.metadata.keys()))
    scores.append(1.0 if bool(a.outcome) == bool(b.outcome) else 0.0)
    return sum(scores) / len(scores)


def weighted_similarity(lexical: float, structural: float) -> float:
    return round((0.60 * lexical) + (0.40 * structural), 6)


def completeness(episode: Episode) -> float:
    checks = [
        bool(episode.claim),
        bool(episode.decision),
        bool(episode.rationale),
        bool(episode.assumptions),
        bool(episode.outcome),
        bool(episode.evidence),
        bool(episode.tags),
        bool(episode.entities),
    ]
    return sum(checks) / len(checks)


def evidence_strength(episode: Episode) -> float:
    if not episode.evidence:
        return 0.0
    total = sum(e.weight for e in episode.evidence)
    return min(1.0, total / len(episode.evidence))


def contrast_confidence(a: Episode, b: Episode, similarity: float) -> float:
    quality = (completeness(a) + completeness(b)) / 2.0
    evidence = (evidence_strength(a) + evidence_strength(b)) / 2.0
    # Similar episodes create more useful "controlled" contrasts.
    score = (0.45 * quality) + (0.35 * evidence) + (0.20 * similarity)
    return round(max(0.0, min(1.0, score)), 6)


def metric_distance(prior: Mapping[str, Any], current: Mapping[str, Any]) -> float:
    shared = set(prior) & set(current)
    if not shared:
        return 0.0
    distances = []
    for key in shared:
        a, b = prior[key], current[key]
        if isinstance(a, (int, float)) and isinstance(b, (int, float)):
            denom = max(abs(float(a)), abs(float(b)), 1.0)
            distances.append(min(1.0, abs(float(a) - float(b)) / denom))
        else:
            distances.append(0.0 if a == b else 1.0)
    return sum(distances) / len(distances)
