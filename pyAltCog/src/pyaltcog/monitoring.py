from __future__ import annotations

from typing import Iterable, Tuple

from .ids import stable_id
from .models import AltCogCandidatePacket, DormantAlternativeMonitor, FrictionSignalRecord
from .text import feature_terms


def make_dormant_monitor(
    candidate: AltCogCandidatePacket,
    *,
    archived_at: str,
    trigger_terms: Iterable[str] = (),
) -> DormantAlternativeMonitor:
    terms = set(trigger_terms)
    terms |= feature_terms(candidate.hypothesis)
    terms |= feature_terms(candidate.revisit_trigger)
    return DormantAlternativeMonitor(
        id=stable_id("DAM", {"candidate_id": candidate.id, "terms": sorted(terms)}),
        candidate_id=candidate.id,
        archived_at=archived_at,
        trigger_terms=sorted(terms),
        revisit_trigger=candidate.revisit_trigger,
    )


def should_reactivate(
    monitor: DormantAlternativeMonitor,
    signals: Iterable[FrictionSignalRecord],
    *,
    minimum_term_hits: int = 1,
) -> Tuple[bool, list[str]]:
    if not monitor.active:
        return False, []
    trigger_set = set(monitor.trigger_terms)
    hits = set()
    for signal in signals:
        hits |= trigger_set & feature_terms(signal.statement, signal.tags)
    return len(hits) >= minimum_term_hits, sorted(hits)
