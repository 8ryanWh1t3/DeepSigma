"""Drift Signal Collector (DS) — collect and structure runtime drift.

The DS layer ingests raw DriftEvent records emitted by RAL and
organises them by type, severity, fingerprint, and recurrence.
It feeds the audit loop and scoring engine with structured drift
intelligence.

DS answers: "what is breaking, how often, and how badly?"
"""

from __future__ import annotations

import json
import logging
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Canonical drift types from schemas/core/drift.schema.json
DRIFT_TYPES = frozenset([
    "time", "freshness", "fallback", "bypass",
    "verify", "outcome", "fanout", "contention",
])

SEVERITY_ORDER = {"green": 0, "yellow": 1, "red": 2}


@dataclass
class DriftBucket:
    """Aggregation bucket for a single drift fingerprint."""

    fingerprint_key: str
    drift_type: str
    count: int = 0
    worst_severity: str = "green"
    first_seen: Optional[str] = None
    last_seen: Optional[str] = None
    episode_ids: List[str] = field(default_factory=list)
    recommended_patches: List[str] = field(default_factory=list)


@dataclass
class DriftSummary:
    """Output of a DriftSignalCollector analysis."""

    collected_at: str
    total_signals: int
    by_type: Dict[str, int]
    by_severity: Dict[str, int]
    buckets: List[DriftBucket]
    top_recurring: List[str]
    metadata: Dict[str, Any] = field(default_factory=dict)


class DriftSignalCollector:
    """Ingest drift events and produce structured summaries.

    Usage:
        ds = DriftSignalCollector()
        ds.ingest(drift_events)
        summary = ds.summarise()
    """

    def __init__(self) -> None:
        self._events: List[Dict[str, Any]] = []
        self._buckets: Dict[str, DriftBucket] = {}

    @property
    def event_count(self) -> int:
        """Number of raw events ingested."""
        return len(self._events)

    def ingest(self, events: List[Dict[str, Any]]) -> None:
        """Add drift events and update fingerprint buckets."""
        for ev in events:
            self._events.append(ev)
            self._bucket_event(ev)
        logger.debug("Ingested %d drift events (total: %d)", len(events), len(self._events))

    def summarise(self) -> DriftSummary:
        """Produce a DriftSummary from all ingested events."""
        by_type: Counter = Counter(ev.get("driftType", "unknown") for ev in self._events)
        by_severity: Counter = Counter(ev.get("severity", "green") for ev in self._events)

        sorted_buckets = sorted(
            self._buckets.values(),
            key=lambda b: (SEVERITY_ORDER.get(b.worst_severity, 0), b.count),
            reverse=True,
        )
        top_recurring = [
            b.fingerprint_key for b in sorted_buckets[:5] if b.count > 1
        ]

        return DriftSummary(
            collected_at=datetime.now(timezone.utc).isoformat(),
            total_signals=len(self._events),
            by_type=dict(by_type),
            by_severity=dict(by_severity),
            buckets=sorted_buckets,
            top_recurring=top_recurring,
        )

    def to_json(self, indent: int = 2) -> str:
        """Summarise and serialise to JSON."""
        return json.dumps(asdict(self.summarise()), indent=indent)

    def clear(self) -> None:
        """Discard all collected events and buckets."""
        self._events.clear()
        self._buckets.clear()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _bucket_event(self, ev: Dict[str, Any]) -> None:
        """Place an event into its fingerprint bucket."""
        fp = ev.get("fingerprint", {})
        key = fp.get("key", "unknown")
        drift_type = ev.get("driftType", "unknown")
        severity = ev.get("severity", "green")
        detected_at = ev.get("detectedAt", "")
        episode_id = ev.get("episodeId", "")
        patch_type = ev.get("recommendedPatchType", "")

        if key not in self._buckets:
            self._buckets[key] = DriftBucket(
                fingerprint_key=key,
                drift_type=drift_type,
                first_seen=detected_at,
            )

        bucket = self._buckets[key]
        bucket.count += 1
        bucket.last_seen = detected_at

        if SEVERITY_ORDER.get(severity, 0) > SEVERITY_ORDER.get(bucket.worst_severity, 0):
            bucket.worst_severity = severity

        if episode_id and episode_id not in bucket.episode_ids:
            bucket.episode_ids.append(episode_id)

        if patch_type and patch_type not in bucket.recommended_patches:
            bucket.recommended_patches.append(patch_type)
