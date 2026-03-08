"""Temporal operations for institutional memory.

Time-windowed recall and relevance decay for precedents and knowledge entries.
"""

from __future__ import annotations

import math
from datetime import datetime, timezone, timedelta
from typing import List

from .models import KnowledgeEntry, Precedent, TemporalRecallResult


def apply_decay(
    precedents: List[Precedent],
    reference_time: datetime | None = None,
) -> List[Precedent]:
    """Apply half-life decay to precedent relevance scores.

    Uses exponential decay: score *= 2^(-elapsed_days / half_life).
    Modifies precedents in-place and returns the list.
    """
    ref = reference_time or datetime.now(timezone.utc)

    for p in precedents:
        if not p.created_at:
            continue
        try:
            created = datetime.fromisoformat(p.created_at.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            continue

        elapsed_days = (ref - created).total_seconds() / 86400
        if elapsed_days <= 0 or p.decay_half_life_days <= 0:
            continue

        decay_factor = math.pow(2, -elapsed_days / p.decay_half_life_days)
        p.relevance_score = round(p.relevance_score * decay_factor, 4)

    return precedents


def filter_by_window(
    precedents: List[Precedent],
    window_hours: int = 24,
    reference_time: datetime | None = None,
) -> TemporalRecallResult:
    """Filter precedents to those created within the time window.

    Returns a TemporalRecallResult with matching precedents.
    """
    ref = reference_time or datetime.now(timezone.utc)
    cutoff = ref - timedelta(hours=window_hours)
    matches: List[Precedent] = []

    for p in precedents:
        if not p.created_at:
            continue
        try:
            created = datetime.fromisoformat(p.created_at.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            continue
        if created >= cutoff:
            matches.append(p)

    return TemporalRecallResult(
        query_window_hours=window_hours,
        precedents=matches,
        total_matches=len(matches),
    )
