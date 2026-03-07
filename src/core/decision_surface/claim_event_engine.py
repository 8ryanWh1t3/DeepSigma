"""Claim-Event Engine — shared evaluation logic for all surface adapters.

ALL evaluation logic lives here. Adapters only handle storage and
retrieval; they never duplicate scoring, drift detection, or patch
recommendation logic.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .models import (
    Assumption,
    Claim,
    ClaimStatus,
    DriftSignal,
    EvaluationResult,
    Event,
    MemoryGraphUpdate,
    PatchRecommendation,
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _uid(prefix: str = "DS") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


# ── Matching ────────────────────────────────────────────────────────


def match_events_to_claims(
    claims: List[Claim],
    events: List[Event],
) -> Dict[str, List[str]]:
    """Match events to claims via claim_refs on events.

    Returns:
        Mapping of claim_id → [event_id, ...] for claims with matches.
    """
    matches: Dict[str, List[str]] = {c.claim_id: [] for c in claims}
    for event in events:
        for cid in event.claim_refs:
            if cid in matches:
                matches[cid].append(event.event_id)
    return matches


# ── Contradiction Detection ─────────────────────────────────────────


_CONTRADICTORY_PAIRS = {
    frozenset({"approved", "denied"}),
    frozenset({"confirmed", "refuted"}),
    frozenset({"started", "cancelled"}),
    frozenset({"enabled", "disabled"}),
}


def detect_contradictions(
    claims: List[Claim],
    events: List[Event],
) -> List[DriftSignal]:
    """Detect contradictory events referencing the same claim.

    Two events are contradictory when their event_type values form
    a known antonym pair (e.g. approved/denied).
    """
    signals: List[DriftSignal] = []
    claim_events: Dict[str, List[Event]] = {c.claim_id: [] for c in claims}
    for ev in events:
        for cid in ev.claim_refs:
            if cid in claim_events:
                claim_events[cid].append(ev)

    for cid, evts in claim_events.items():
        types = {e.event_type for e in evts}
        for pair in _CONTRADICTORY_PAIRS:
            if pair <= types:
                signals.append(DriftSignal(
                    signal_id=_uid("SIG"),
                    drift_type="contradiction",
                    severity="red",
                    source_claim_id=cid,
                    detail=f"Contradictory events: {sorted(pair)}",
                    detected_at=_now_iso(),
                ))
                break
    return signals


# ── Expired Assumptions ─────────────────────────────────────────────


def detect_expired_assumptions(
    claims: List[Claim],
    assumptions: List[Assumption],
) -> List[DriftSignal]:
    """Detect claims linked to expired assumptions.

    An assumption is expired when ``expires_at`` is in the past or
    ``expired`` is explicitly True.
    """
    signals: List[DriftSignal] = []
    now = _now_iso()
    claim_ids = {c.claim_id for c in claims}

    for asmp in assumptions:
        is_expired = asmp.expired
        if not is_expired and asmp.expires_at:
            is_expired = asmp.expires_at <= now
        if is_expired:
            asmp.expired = True
            for cid in asmp.linked_claim_ids:
                if cid in claim_ids:
                    signals.append(DriftSignal(
                        signal_id=_uid("SIG"),
                        drift_type="expired_assumption",
                        severity="yellow",
                        source_claim_id=cid,
                        detail=f"Assumption expired: {asmp.statement}",
                        detected_at=_now_iso(),
                    ))
    return signals


# ── Blast Radius ────────────────────────────────────────────────────


def compute_blast_radius(claim: Claim, claims: List[Claim]) -> int:
    """Count claims sharing evidence_refs with the given claim.

    Simple overlap count — no graph traversal for MVP.
    """
    if not claim.evidence_refs:
        return 0
    refs = set(claim.evidence_refs)
    count = 0
    for other in claims:
        if other.claim_id == claim.claim_id:
            continue
        if refs & set(other.evidence_refs):
            count += 1
    return count


# ── Patch Recommendations ──────────────────────────────────────────


_DRIFT_ACTION_MAP: Dict[str, str] = {
    "contradiction": "investigate_contradiction",
    "expired_assumption": "review_assumption",
    "unsupported": "gather_evidence",
}


def build_patch_recommendation(signal: DriftSignal) -> PatchRecommendation:
    """Map a drift signal to a patch recommendation."""
    action = _DRIFT_ACTION_MAP.get(signal.drift_type, "review_claim")
    return PatchRecommendation(
        patch_id=_uid("PATCH"),
        drift_signal_id=signal.signal_id,
        action=action,
        rationale=signal.detail,
        issued_at=_now_iso(),
    )


# ── Memory Graph Update ────────────────────────────────────────────


def build_memory_graph_update(
    claims: List[Claim],
    signals: List[DriftSignal],
) -> MemoryGraphUpdate:
    """Build MG nodes and edges from evaluated claims and drift signals.

    Uses NodeKind/EdgeKind values from core.memory_graph as strings.
    """
    nodes: List[Dict[str, Any]] = []
    edges: List[Dict[str, Any]] = []

    for c in claims:
        nodes.append({
            "node_id": c.claim_id,
            "kind": "claim",
            "label": c.statement[:80],
            "properties": {"status": c.status, "confidence": c.confidence},
        })

    for sig in signals:
        nodes.append({
            "node_id": sig.signal_id,
            "kind": "drift",
            "label": f"{sig.drift_type}: {sig.detail[:60]}",
            "properties": {"severity": sig.severity},
        })
        if sig.source_claim_id:
            edges.append({
                "source": sig.signal_id,
                "target": sig.source_claim_id,
                "kind": "triggered",
            })

    return MemoryGraphUpdate(nodes=nodes, edges=edges)


# ── Evaluate (orchestrator) ─────────────────────────────────────────


def evaluate(
    claims: List[Claim],
    events: List[Event],
    assumptions: Optional[List[Assumption]] = None,
) -> EvaluationResult:
    """Run the full evaluation pipeline.

    1. Match events to claims
    2. Set claim statuses based on matches
    3. Detect contradictions → DRIFTED
    4. Detect expired assumptions → DRIFTED
    5. Build patch recommendations for each signal
    6. Build memory graph update
    7. Return EvaluationResult
    """
    assumptions = assumptions or []

    # 1. Match
    matches = match_events_to_claims(claims, events)

    # 2. Status assignment
    for claim in claims:
        matched_event_ids = matches.get(claim.claim_id, [])
        if matched_event_ids:
            claim.status = ClaimStatus.SATISFIED.value
            if claim.confidence < 0.5:
                claim.status = ClaimStatus.AT_RISK.value
        else:
            claim.status = ClaimStatus.PENDING.value

    # 3. Contradictions
    contradiction_signals = detect_contradictions(claims, events)
    drifted_claim_ids: set[str] = set()
    for sig in contradiction_signals:
        drifted_claim_ids.add(sig.source_claim_id)

    # 4. Expired assumptions
    assumption_signals = detect_expired_assumptions(claims, assumptions)
    for sig in assumption_signals:
        drifted_claim_ids.add(sig.source_claim_id)

    # Mark drifted claims
    for claim in claims:
        if claim.claim_id in drifted_claim_ids:
            claim.status = ClaimStatus.DRIFTED.value

    # 5. Patches
    all_signals = contradiction_signals + assumption_signals
    patches = [build_patch_recommendation(s) for s in all_signals]

    # 6. Memory graph
    mg = build_memory_graph_update(claims, all_signals)

    # 7. Counts
    counts = {s.value: 0 for s in ClaimStatus}
    for claim in claims:
        counts[claim.status] = counts.get(claim.status, 0) + 1

    return EvaluationResult(
        claims_evaluated=len(claims),
        satisfied=counts.get(ClaimStatus.SATISFIED.value, 0),
        at_risk=counts.get(ClaimStatus.AT_RISK.value, 0),
        drifted=counts.get(ClaimStatus.DRIFTED.value, 0),
        pending=counts.get(ClaimStatus.PENDING.value, 0),
        drift_signals=all_signals,
        patches=patches,
        memory_graph_update=mg,
    )
