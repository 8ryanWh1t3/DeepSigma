"""Memory graph stage — build MG delta and canon entries from pipeline output."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List

from ..types import Claim, DriftDetection, JRMEvent, PatchRecord


@dataclass
class MGResult:
    """Output of the memory graph stage."""

    mg_delta: Dict[str, Any]
    canon_postures: Dict[str, Any]


class MemoryGraphStage:
    """Build memory graph deltas and canon postures.

    Uses lightweight dict-based representation for portability.
    """

    def process(
        self,
        events: List[JRMEvent],
        claims: List[Claim],
        drifts: List[DriftDetection],
        patches: List[PatchRecord],
    ) -> MGResult:
        nodes_added: List[Dict[str, Any]] = []
        edges_added: List[Dict[str, Any]] = []

        # Evidence nodes from events
        for ev in events:
            nodes_added.append({
                "nodeId": ev.event_id,
                "kind": "evidence",
                "label": f"{ev.source_system}:{ev.action}",
                "timestamp": ev.timestamp,
                "properties": {"evidenceHash": ev.evidence_hash},
            })

        # Claim nodes
        for c in claims:
            nodes_added.append({
                "nodeId": c.claim_id,
                "kind": "claim",
                "label": c.statement[:80],
                "timestamp": c.timestamp,
                "properties": {"confidence": c.confidence},
            })
            # Edges: claim <- evidence
            for ev_id in c.source_events:
                edges_added.append({
                    "sourceId": ev_id,
                    "targetId": c.claim_id,
                    "kind": "evidence_of",
                })

        # Drift nodes
        for d in drifts:
            nodes_added.append({
                "nodeId": d.drift_id,
                "kind": "drift",
                "label": f"{d.drift_type.value}:{d.fingerprint}",
                "timestamp": d.detected_at,
                "properties": {"severity": d.severity.value},
            })
            # Edge: evidence -> triggered drift
            for ref in d.evidence_refs[:5]:
                edges_added.append({
                    "sourceId": ref,
                    "targetId": d.drift_id,
                    "kind": "triggered",
                })

        # Patch nodes
        for p in patches:
            nodes_added.append({
                "nodeId": p.patch_id,
                "kind": "patch",
                "label": f"rev={p.rev}",
                "timestamp": p.applied_at,
                "properties": {"rev": p.rev, "supersedes": p.supersedes},
            })
            # Edge: drift -> resolved_by patch
            edges_added.append({
                "sourceId": p.drift_id,
                "targetId": p.patch_id,
                "kind": "resolved_by",
            })
            # Edge: supersedes lineage
            if p.supersedes:
                edges_added.append({
                    "sourceId": p.patch_id,
                    "targetId": p.supersedes,
                    "kind": "claim_supersedes",
                })

        mg_delta = {
            "nodesAdded": nodes_added,
            "edgesAdded": edges_added,
            "generatedAt": datetime.now(timezone.utc).isoformat(),
        }

        canon_postures = self._build_canon(claims, patches)
        return MGResult(mg_delta=mg_delta, canon_postures=canon_postures)

    @staticmethod
    def _build_canon(
        claims: List[Claim],
        patches: List[PatchRecord],
    ) -> Dict[str, Any]:
        """Build canon postures — current stance per signature/action."""
        postures: Dict[str, Dict[str, Any]] = {}

        # From patches: track latest rev per fingerprint
        for p in patches:
            # Extract sig from changes
            for change in p.changes:
                detail = change.get("detail", "")
                postures[p.patch_id] = {
                    "rev": p.rev,
                    "previousRev": p.previous_rev,
                    "patchId": p.patch_id,
                    "driftType": change.get("drift_type", ""),
                    "action": change.get("action", ""),
                    "lastReviewedAt": p.applied_at,
                }

        # From claims: aggregate posture per claim key
        for c in claims:
            postures[c.claim_id] = {
                "statement": c.statement,
                "confidence": c.confidence,
                "assumptionCount": len(c.assumptions),
                "lastUpdatedAt": c.timestamp,
            }

        return {
            "entries": postures,
            "generatedAt": datetime.now(timezone.utc).isoformat(),
        }
