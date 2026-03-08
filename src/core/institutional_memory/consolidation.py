"""Knowledge consolidation — merge related precedents into KnowledgeEntries."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import List

from .fingerprinting import similarity_score, compute_fingerprint
from .models import ConsolidationReport, KnowledgeEntry, Precedent


def merge_precedents(
    precedents: List[Precedent],
    similarity_threshold: float = 0.5,
) -> tuple[List[KnowledgeEntry], ConsolidationReport]:
    """Merge related precedents into consolidated KnowledgeEntry objects.

    Groups precedents by category and similarity, then merges groups
    with similarity above threshold into a single KnowledgeEntry.

    Returns (entries_created, consolidation_report).
    """
    now = datetime.now(timezone.utc).isoformat()
    entries: List[KnowledgeEntry] = []
    merged_count = 0

    # Group by category first
    by_category: dict[str, List[Precedent]] = {}
    for p in precedents:
        by_category.setdefault(p.category, []).append(p)

    for category, group in by_category.items():
        if len(group) < 2:
            continue

        # Simple greedy merge: walk the list, merge pairs above threshold
        used = set()
        for i, a in enumerate(group):
            if a.precedent_id in used:
                continue
            cluster = [a]
            for j in range(i + 1, len(group)):
                b = group[j]
                if b.precedent_id in used:
                    continue
                # Use relevance_score as a proxy for lightweight similarity
                if abs(a.relevance_score - b.relevance_score) < (1.0 - similarity_threshold):
                    cluster.append(b)
                    used.add(b.precedent_id)

            if len(cluster) >= 2:
                used.add(a.precedent_id)
                entry = KnowledgeEntry(
                    entry_id=f"KE-{uuid.uuid4().hex[:8]}",
                    title=f"{category}: {cluster[0].takeaway[:60]}",
                    summary="; ".join(p.takeaway for p in cluster),
                    source_precedent_ids=[p.precedent_id for p in cluster],
                    relevance_score=max(p.relevance_score for p in cluster),
                    created_at=now,
                )
                entries.append(entry)
                merged_count += len(cluster)

    report = ConsolidationReport(
        report_id=f"CR-{uuid.uuid4().hex[:8]}",
        entries_created=len(entries),
        precedents_merged=merged_count,
        total_precedents=len(precedents),
        created_at=now,
    )
    return entries, report
