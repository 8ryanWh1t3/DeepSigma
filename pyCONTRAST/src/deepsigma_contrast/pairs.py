from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from typing import Iterable

from .models import Episode
from .scorer import lexical_episode_similarity, structural_episode_similarity, weighted_similarity


@dataclass(frozen=True)
class EpisodePair:
    left_id: str
    right_id: str
    relation: str
    similarity: float
    rationale: str


def _outcome_status(e: Episode) -> str | None:
    return e.outcome.status if e.outcome else None


def generate_pairs(
    episodes: Iterable[Episode],
    *,
    positive_threshold: float = 0.72,
    hard_negative_threshold: float = 0.50,
) -> list[EpisodePair]:
    items = list(episodes)
    pairs: list[EpisodePair] = []
    for left, right in combinations(items, 2):
        sim = weighted_similarity(
            lexical_episode_similarity(left, right),
            structural_episode_similarity(left, right),
        )
        same_outcome = _outcome_status(left) == _outcome_status(right) and _outcome_status(left) is not None

        if sim >= positive_threshold and same_outcome:
            relation = "POSITIVE"
            rationale = "Episodes are highly similar and share the same observed outcome."
        elif sim >= hard_negative_threshold and not same_outcome:
            relation = "HARD_NEGATIVE"
            rationale = "Episodes are similar but diverge in outcome; high-value contrast candidate."
        else:
            relation = "NEGATIVE"
            rationale = "Episodes are not sufficiently aligned to form a controlled positive pair."

        pairs.append(EpisodePair(left.id, right.id, relation, sim, rationale))
    return pairs
