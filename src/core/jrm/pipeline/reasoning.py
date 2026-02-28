"""Reasoning stage — assign decision lanes and generate DLR entries."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

from ..types import (
    Claim,
    DecisionLane,
    JRMEvent,
    ReasoningResult,
    Severity,
    WhyBullet,
)


@dataclass
class ReasoningOutput:
    """Output of the reasoning stage."""

    results: List[ReasoningResult]
    dlr_entries: List[Dict[str, Any]]


class ReasoningStage:
    """Classify events into decision lanes and generate reasoning records.

    Lane assignment rules:
      critical/high + confidence >= 0.8  →  REQUIRE_REVIEW
      high + confidence < 0.8            →  QUEUE_PATCH
      medium                             →  NOTIFY
      low/info                           →  LOG_ONLY
    """

    def process(
        self,
        events: List[JRMEvent],
        claims: List[Claim],
    ) -> ReasoningOutput:
        # Build claim lookup by source_event
        claim_by_event: Dict[str, List[Claim]] = {}
        for c in claims:
            for eid in c.source_events:
                claim_by_event.setdefault(eid, []).append(c)

        results: List[ReasoningResult] = []
        dlr_entries: List[Dict[str, Any]] = []

        for ev in events:
            lane = self._assign_lane(ev)
            bullets = self._generate_why(ev, lane)
            ev_claims = claim_by_event.get(ev.event_id, [])

            rr = ReasoningResult(
                event_id=ev.event_id,
                lane=lane,
                why_bullets=bullets,
                claims=ev_claims,
                metadata={"severity": ev.severity.value, "confidence": ev.confidence},
            )
            results.append(rr)

            dlr_entries.append({
                "eventId": ev.event_id,
                "lane": lane.value,
                "whyBullets": [
                    {"text": b.text, "evidenceRef": b.evidence_ref, "confidence": b.confidence}
                    for b in bullets
                ],
                "claims": [c.claim_id for c in ev_claims],
                "severity": ev.severity.value,
                "confidence": ev.confidence,
                "timestamp": ev.timestamp,
            })

        return ReasoningOutput(results=results, dlr_entries=dlr_entries)

    @staticmethod
    def _assign_lane(ev: JRMEvent) -> DecisionLane:
        if ev.severity in (Severity.CRITICAL, Severity.HIGH) and ev.confidence >= 0.8:
            return DecisionLane.REQUIRE_REVIEW
        if ev.severity == Severity.HIGH and ev.confidence < 0.8:
            return DecisionLane.QUEUE_PATCH
        if ev.severity == Severity.MEDIUM:
            return DecisionLane.NOTIFY
        return DecisionLane.LOG_ONLY

    @staticmethod
    def _generate_why(ev: JRMEvent, lane: DecisionLane) -> List[WhyBullet]:
        bullets: List[WhyBullet] = []

        # Primary reason: severity + confidence
        bullets.append(WhyBullet(
            text=f"Severity={ev.severity.value}, confidence={ev.confidence:.2f} → {lane.value}",
            evidence_ref=ev.evidence_hash,
            confidence=ev.confidence,
        ))

        # Signature context
        sig = ev.metadata.get("signature_id") or ev.metadata.get("sid")
        if sig:
            rev = ev.metadata.get("rev", "?")
            bullets.append(WhyBullet(
                text=f"Matched signature {sig} rev {rev}",
                evidence_ref=ev.evidence_hash,
                confidence=ev.confidence,
            ))

        # Guardrail context for agent events
        flags = ev.metadata.get("guardrail_flags", [])
        if flags:
            bullets.append(WhyBullet(
                text=f"Guardrail flags: {', '.join(flags)}",
                evidence_ref=ev.evidence_hash,
                confidence=ev.confidence,
            ))

        return bullets
