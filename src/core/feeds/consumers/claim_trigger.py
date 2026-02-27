"""ClaimTriggerPipeline — atomic submit loop for claims.

Composes ClaimValidator, DriftSignalCollector, MemoryGraph, and Publisher
into a single atomic loop: validate -> detect drift -> record in graph -> publish.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.drift_signal import DriftSignalCollector
from core.memory_graph import MemoryGraph
from core.feeds.canon.claim_validator import ClaimValidator

logger = logging.getLogger(__name__)


@dataclass
class ClaimSubmitResult:
    """Result of a single claim submission through the pipeline."""

    claim_id: str
    accepted: bool
    issues: List[Dict[str, Any]] = field(default_factory=list)
    drift_signals: List[Dict[str, Any]] = field(default_factory=list)
    graph_node_id: Optional[str] = None
    published_events: List[str] = field(default_factory=list)


@dataclass
class ClaimTriggerResult:
    """Aggregate result of a batch claim trigger run."""

    submitted: int
    accepted: int
    rejected: int
    drift_signals_emitted: int
    results: List[ClaimSubmitResult] = field(default_factory=list)


class ClaimTriggerPipeline:
    """Atomic claim submit loop.

    For each claim:

    1. Validate via ClaimValidator (contradiction, TTL, consistency)
    2. Check authority (if ledger configured)
    3. Convert issues to drift signals
    4. Add claim to MemoryGraph (with episode link if provided)
    5. Ingest drift signals into DriftSignalCollector
    6. Publish drift signals via Publisher (if topics_root configured)

    Usage::

        pipeline = ClaimTriggerPipeline(
            canon_claims=canon_list,
            mg=memory_graph,
            ds=drift_collector,
            topics_root=Path("./topics"),
        )
        result = pipeline.submit(claims, episode_id="ep-001")
    """

    def __init__(
        self,
        canon_claims: Optional[List[Dict[str, Any]]] = None,
        mg: Optional[MemoryGraph] = None,
        ds: Optional[DriftSignalCollector] = None,
        topics_root: Optional[Path] = None,
        authority_ledger: Optional[Any] = None,
    ) -> None:
        self._validator = ClaimValidator(canon_claims=canon_claims)
        self._mg = mg
        self._ds = ds
        self._topics_root = topics_root
        self._authority_ledger = authority_ledger

    def submit(
        self,
        claims: List[Dict[str, Any]],
        episode_id: Optional[str] = None,
        packet_id: str = "",
        now: Optional[datetime] = None,
    ) -> ClaimTriggerResult:
        """Run the atomic claim trigger loop over a batch of claims."""
        results: List[ClaimSubmitResult] = []
        total_drift = 0

        for claim in claims:
            result = self._submit_one(claim, episode_id, packet_id, now)
            results.append(result)
            total_drift += len(result.drift_signals)

        accepted = sum(1 for r in results if r.accepted)
        return ClaimTriggerResult(
            submitted=len(claims),
            accepted=accepted,
            rejected=len(claims) - accepted,
            drift_signals_emitted=total_drift,
            results=results,
        )

    def _submit_one(
        self,
        claim: Dict[str, Any],
        episode_id: Optional[str],
        packet_id: str,
        now: Optional[datetime],
    ) -> ClaimSubmitResult:
        claim_id = claim.get("claimId", f"claim-{uuid.uuid4().hex[:8]}")

        # 1. Validate
        issues = self._validator.validate_claim(claim, now=now)

        # 2. Check authority (if ledger configured)
        if self._authority_ledger is not None:
            proof = self._authority_ledger.prove_authority(claim_id)
            if proof is None:
                issues.append({
                    "type": "unauthorized",
                    "claimId": claim_id,
                    "detail": f"Claim {claim_id} has no authority grant",
                    "severity": "red",
                })

        # 3. Convert issues to drift signals
        drift_signals = [
            self._validator.build_drift_signal(issue, packet_id=packet_id)
            for issue in issues
        ]

        # 4. Record in MemoryGraph
        graph_node_id = None
        if self._mg is not None:
            graph_node_id = self._mg.add_claim(claim, episode_id=episode_id)
            for ds_event in drift_signals:
                self._mg.add_drift(ds_event)

        # 5. Ingest drift signals into collector
        if self._ds is not None and drift_signals:
            self._ds.ingest(drift_signals)

        # 6. Publish drift signals to FEEDS bus
        published: List[str] = []
        if self._topics_root is not None and drift_signals:
            published = self._publish_drift_signals(drift_signals, packet_id)

        # A claim is "accepted" if it has no red-severity issues
        has_red = any(i.get("severity") == "red" for i in issues)
        return ClaimSubmitResult(
            claim_id=claim_id,
            accepted=not has_red,
            issues=issues,
            drift_signals=drift_signals,
            graph_node_id=graph_node_id,
            published_events=published,
        )

    def _publish_drift_signals(
        self, signals: List[Dict[str, Any]], packet_id: str,
    ) -> List[str]:
        """Publish drift signals to FEEDS bus. Returns list of event IDs."""
        if self._topics_root is None:
            return []
        try:
            from core.feeds.bus import Publisher
            from core.feeds.envelope import build_envelope, load_contract_fingerprint
            from core.feeds.types import FeedTopic

            pub = Publisher(self._topics_root)
            contract_fp = load_contract_fingerprint()
            event_ids: List[str] = []
            for sig in signals:
                envelope = build_envelope(
                    topic=FeedTopic.DRIFT_SIGNAL,
                    payload=sig,
                    packet_id=(
                        packet_id
                        or datetime.now(timezone.utc).strftime("CP-%Y-%m-%d-")
                        + f"{uuid.uuid4().int % 10000:04d}"
                    ),
                    producer="claim-trigger-pipeline",
                    contract_fingerprint=contract_fp,
                )
                pub.publish(FeedTopic.DRIFT_SIGNAL, envelope)
                event_ids.append(envelope["eventId"])
            return event_ids
        except (FileNotFoundError, ValueError) as exc:
            logger.warning("Failed to publish drift signals: %s", exc)
            return []
