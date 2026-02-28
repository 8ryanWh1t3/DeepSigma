"""Truth stage — build Claim objects from JRM events."""

from __future__ import annotations

import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List

from ..types import Claim, EventType, JRMEvent


@dataclass
class TruthResult:
    """Output of the truth stage."""

    claims: List[Claim]
    truth_snapshot: Dict[str, Any]


class TruthStage:
    """Extract truth claims from normalized JRM events.

    Claims are keyed by (source_system, signature_key).  Multiple events
    with the same key are clustered into a single claim with aggregated
    evidence and averaged confidence.
    """

    def process(self, events: List[JRMEvent]) -> TruthResult:
        # Group events by claim key
        buckets: Dict[str, List[JRMEvent]] = defaultdict(list)
        for ev in events:
            key = self._claim_key(ev)
            buckets[key].append(ev)

        claims: List[Claim] = []
        for key, group in buckets.items():
            claim = self._build_claim(key, group)
            claims.append(claim)

        snapshot = self._build_snapshot(events, claims)
        return TruthResult(claims=claims, truth_snapshot=snapshot)

    # ── internals ────────────────────────────────────────────────

    @staticmethod
    def _claim_key(ev: JRMEvent) -> str:
        sig_id = ev.metadata.get("signature_id") or ev.metadata.get("sid")
        if sig_id:
            return f"{ev.source_system}:sig:{sig_id}"
        return f"{ev.source_system}:{ev.action}"

    @staticmethod
    def _build_claim(key: str, group: List[JRMEvent]) -> Claim:
        avg_conf = sum(e.confidence for e in group) / len(group)
        first = group[0]
        last = group[-1]

        # Merge unique assumptions
        all_assumptions: List[str] = []
        seen: set[str] = set()
        for ev in group:
            for a in ev.assumptions:
                if a not in seen:
                    seen.add(a)
                    all_assumptions.append(a)

        return Claim(
            claim_id=f"CLM-{uuid.uuid4().hex[:12]}",
            statement=f"Events observed for {key} ({len(group)} occurrences)",
            confidence=round(avg_conf, 4),
            evidence_refs=[e.evidence_hash for e in group],
            source_events=[e.event_id for e in group],
            timestamp=last.timestamp,
            assumptions=all_assumptions,
        )

    @staticmethod
    def _build_snapshot(
        events: List[JRMEvent], claims: List[Claim]
    ) -> Dict[str, Any]:
        severity_hist: Dict[str, int] = defaultdict(int)
        event_type_counts: Dict[str, int] = defaultdict(int)
        sensors: set[str] = set()
        sig_counts: Dict[str, int] = defaultdict(int)

        timestamps: List[str] = []
        for ev in events:
            severity_hist[ev.severity.value] += 1
            event_type_counts[ev.event_type.value] += 1
            sensors.add(ev.source_system)
            if ev.timestamp:
                timestamps.append(ev.timestamp)
            sig = ev.metadata.get("signature_id") or ev.metadata.get("sid")
            if sig:
                sig_counts[str(sig)] += 1

        timestamps.sort()
        top_sigs = sorted(sig_counts.items(), key=lambda x: x[1], reverse=True)[:10]

        return {
            "event_count": len(events),
            "claim_count": len(claims),
            "window_start": timestamps[0] if timestamps else "",
            "window_end": timestamps[-1] if timestamps else "",
            "severity_histogram": dict(severity_hist),
            "event_type_counts": dict(event_type_counts),
            "top_signatures": [{"id": s, "count": c} for s, c in top_sigs],
            "sensor_ids": sorted(sensors),
        }
