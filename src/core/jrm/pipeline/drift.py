"""Drift stage — detect local coherence drift from JRM events."""

from __future__ import annotations

import abc
import uuid
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List

from ..types import (
    Claim,
    DriftDetection,
    JRMDriftType,
    JRMEvent,
    ReasoningResult,
    Severity,
)


class DriftDetectorBase(abc.ABC):
    """Extension point for custom drift detectors."""

    @abc.abstractmethod
    def detect(
        self,
        events: List[JRMEvent],
        claims: List[Claim],
        reasoning: List[ReasoningResult],
    ) -> List[DriftDetection]:
        ...


@dataclass
class DriftOutput:
    """Output of the drift stage."""

    detections: List[DriftDetection]
    ds_entries: List[Dict[str, Any]]


class DriftStage:
    """Run built-in and extension drift detectors."""

    def __init__(
        self,
        fp_spike_threshold: int = 5,
        extra_detectors: List[DriftDetectorBase] | None = None,
    ) -> None:
        self._fp_threshold = fp_spike_threshold
        self._extra = extra_detectors or []

    def process(
        self,
        events: List[JRMEvent],
        claims: List[Claim],
        reasoning: List[ReasoningResult],
    ) -> DriftOutput:
        detections: List[DriftDetection] = []

        detections.extend(self._detect_fp_spike(events))
        detections.extend(self._detect_missing_mapping(events, claims))
        detections.extend(self._detect_stale_logic(events))
        detections.extend(self._detect_assumption_expired(claims))

        for detector in self._extra:
            detections.extend(detector.detect(events, claims, reasoning))

        ds_entries = [self._to_ds_entry(d) for d in detections]
        return DriftOutput(detections=detections, ds_entries=ds_entries)

    # ── Built-in detectors ───────────────────────────────────────

    def _detect_fp_spike(self, events: List[JRMEvent]) -> List[DriftDetection]:
        """Detect signatures with high fire count + low avg confidence."""
        sig_events: Dict[str, List[JRMEvent]] = defaultdict(list)
        for ev in events:
            sig = ev.metadata.get("signature_id") or ev.metadata.get("sid")
            if sig:
                sig_events[str(sig)].append(ev)

        results: List[DriftDetection] = []
        for sig, evts in sig_events.items():
            if len(evts) >= self._fp_threshold:
                avg_conf = sum(e.confidence for e in evts) / len(evts)
                if avg_conf < 0.7:
                    results.append(DriftDetection(
                        drift_id=f"DS-{uuid.uuid4().hex[:12]}",
                        drift_type=JRMDriftType.FP_SPIKE,
                        severity=Severity.MEDIUM,
                        detected_at=datetime.now(timezone.utc).isoformat(),
                        evidence_refs=[e.evidence_hash for e in evts],
                        fingerprint={"signature_id": sig, "count": str(len(evts))},
                        notes=f"Signature {sig} fired {len(evts)} times with avg confidence {avg_conf:.2f}",
                        recommended_action="QUEUE_PATCH: review threshold or suppress",
                    ))
        return results

    def _detect_missing_mapping(
        self, events: List[JRMEvent], claims: List[Claim]
    ) -> List[DriftDetection]:
        """Detect event types with no corresponding claims."""
        claimed_events: set[str] = set()
        for c in claims:
            claimed_events.update(c.source_events)

        unclaimed = [e for e in events if e.event_id not in claimed_events]
        if not unclaimed:
            return []

        type_counts: Dict[str, int] = Counter(e.event_type.value for e in unclaimed)
        results: List[DriftDetection] = []
        for etype, count in type_counts.items():
            results.append(DriftDetection(
                drift_id=f"DS-{uuid.uuid4().hex[:12]}",
                drift_type=JRMDriftType.MISSING_MAPPING,
                severity=Severity.LOW,
                detected_at=datetime.now(timezone.utc).isoformat(),
                evidence_refs=[e.evidence_hash for e in unclaimed if e.event_type.value == etype],
                fingerprint={"event_type": etype, "count": str(count)},
                notes=f"{count} events of type {etype} have no claim mapping",
                recommended_action="NOTIFY: add mapping or classify",
            ))
        return results

    def _detect_stale_logic(self, events: List[JRMEvent]) -> List[DriftDetection]:
        """Detect signature revisions that may be outdated."""
        sig_revs: Dict[str, set[str]] = defaultdict(set)
        for ev in events:
            sig = ev.metadata.get("signature_id") or ev.metadata.get("sid")
            rev = ev.metadata.get("rev")
            if sig and rev:
                sig_revs[str(sig)].add(str(rev))

        results: List[DriftDetection] = []
        for sig, revs in sig_revs.items():
            if len(revs) > 1:
                results.append(DriftDetection(
                    drift_id=f"DS-{uuid.uuid4().hex[:12]}",
                    drift_type=JRMDriftType.STALE_LOGIC,
                    severity=Severity.MEDIUM,
                    detected_at=datetime.now(timezone.utc).isoformat(),
                    evidence_refs=[],
                    fingerprint={"signature_id": sig, "revisions": ",".join(sorted(revs))},
                    notes=f"Signature {sig} has conflicting revisions: {sorted(revs)}",
                    recommended_action="QUEUE_PATCH: reconcile to latest rev",
                ))
        return results

    def _detect_assumption_expired(
        self, claims: List[Claim]
    ) -> List[DriftDetection]:
        """Detect claims with assumptions that look expired."""
        results: List[DriftDetection] = []
        for claim in claims:
            expired = [a for a in claim.assumptions if "expired" in a.lower()]
            if expired:
                results.append(DriftDetection(
                    drift_id=f"DS-{uuid.uuid4().hex[:12]}",
                    drift_type=JRMDriftType.ASSUMPTION_EXPIRED,
                    severity=Severity.HIGH,
                    detected_at=datetime.now(timezone.utc).isoformat(),
                    evidence_refs=claim.evidence_refs[:5],
                    fingerprint={"claim_id": claim.claim_id},
                    notes=f"Claim {claim.claim_id} has expired assumptions: {expired}",
                    recommended_action="REQUIRE_REVIEW: revalidate assumptions",
                ))
        return results

    @staticmethod
    def _to_ds_entry(d: DriftDetection) -> Dict[str, Any]:
        return {
            "driftId": d.drift_id,
            "driftType": d.drift_type.value,
            "severity": d.severity.value,
            "detectedAt": d.detected_at,
            "evidenceRefs": d.evidence_refs[:10],
            "fingerprint": d.fingerprint,
            "notes": d.notes,
            "recommendedAction": d.recommended_action,
        }
