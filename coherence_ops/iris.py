"""IRIS — Operator Query Resolution Engine (Phase 2).

IRIS resolves operator queries (WHY, WHAT_CHANGED, WHAT_DRIFTED,
RECALL, STATUS) by walking the MemoryGraph's claim topology and
DLR rationale graph.

Target: sub-60-second response for any supported query type.
"""
from __future__ import annotations

import logging
import time
import uuid
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class QueryType:
    """Supported IRIS query types."""

    WHY = "WHY"
    WHAT_CHANGED = "WHAT_CHANGED"
    WHAT_DRIFTED = "WHAT_DRIFTED"
    RECALL = "RECALL"
    STATUS = "STATUS"
    ALL = [WHY, WHAT_CHANGED, WHAT_DRIFTED, RECALL, STATUS]


class ResolutionStatus:
    """Resolution outcome status."""

    RESOLVED = "RESOLVED"
    PARTIAL = "PARTIAL"
    NOT_FOUND = "NOT_FOUND"
    ERROR = "ERROR"


class IRISQuery:
    """Structured query input for IRIS."""

    def __init__(
        self,
        query_type: str = QueryType.WHY,
        text: str = "",
        episode_id: str = "",
        claim_id: str = "",
        decision_type: str = "",
    ):
        self.query_type = query_type
        self.text = text
        self.episode_id = episode_id
        self.claim_id = claim_id
        self.decision_type = decision_type


class IRISResponse:
    """Structured response with provenance chain."""

    def __init__(
        self,
        query_id: str,
        query_type: str,
        status: str,
        summary: str,
        data: Optional[Dict[str, Any]] = None,
        provenance: Optional[List[Dict[str, Any]]] = None,
        warnings: Optional[List[str]] = None,
        elapsed_ms: float = 0.0,
    ):
        self.query_id = query_id
        self.query_type = query_type
        self.status = status
        self.summary = summary
        self.data = data or {}
        self.provenance = provenance or []
        self.warnings = list(warnings or [])
        self.elapsed_ms = elapsed_ms

    def to_dict(self) -> Dict[str, Any]:
        """Serialise response to dict."""
        return {
            "query_id": self.query_id,
            "query_type": self.query_type,
            "status": self.status,
            "summary": self.summary,
            "data": self.data,
            "provenance": self.provenance,
            "warnings": self.warnings,
            "elapsed_ms": self.elapsed_ms,
        }


class IRISConfig:
    """Configuration for the IRIS engine."""

    def __init__(self, response_time_target_ms: int = 60_000):
        self.response_time_target_ms = response_time_target_ms

    def validate(self) -> List[str]:
        """Return list of config validation issues."""
        issues: List[str] = []
        if self.response_time_target_ms <= 0:
            issues.append("response_time_target_ms must be positive")
        return issues


class IRISEngine:
    """Operator query resolution engine wired to MemoryGraph and DLR artifacts.

    Usage:
        from coherence_ops.mg import MemoryGraph
        mg = MemoryGraph()
        # ... add episodes, claims, drift ...
        engine = IRISEngine(config=IRISConfig(), memory_graph=mg)
        response = engine.resolve(IRISQuery(query_type="WHY", episode_id="ep-001"))
    """

    def __init__(
        self,
        config: Optional[IRISConfig] = None,
        memory_graph: Optional[Any] = None,
        dlr_entries: Optional[List[Dict[str, Any]]] = None,
    ):
        self.config = config or IRISConfig()
        issues = self.config.validate()
        if issues:
            raise ValueError("Invalid IRISConfig: " + "; ".join(issues))
        self._mg = memory_graph
        self._dlr_entries = dlr_entries or []

    def resolve(self, query: IRISQuery) -> IRISResponse:
        """Resolve an IRIS query by dispatching to the appropriate handler."""
        start = time.monotonic()
        query_id = f"iris-{uuid.uuid4().hex[:12]}"
        warnings: List[str] = []

        if not self._mg:
            return IRISResponse(
                query_id=query_id,
                query_type=query.query_type,
                status=ResolutionStatus.ERROR,
                summary="No MemoryGraph wired to IRIS engine.",
                warnings=["IRIS engine requires a MemoryGraph instance."],
                elapsed_ms=self._elapsed(start),
            )

        if query.query_type == QueryType.WHY:
            response = self._resolve_why(query, query_id, warnings)
        elif query.query_type == QueryType.WHAT_CHANGED:
            response = self._resolve_what_changed(query, query_id, warnings)
        elif query.query_type == QueryType.WHAT_DRIFTED:
            response = self._resolve_what_drifted(query, query_id, warnings)
        elif query.query_type == QueryType.RECALL:
            response = self._resolve_recall(query, query_id, warnings)
        elif query.query_type == QueryType.STATUS:
            response = self._resolve_status(query, query_id, warnings)
        else:
            response = IRISResponse(
                query_id=query_id,
                query_type=query.query_type,
                status=ResolutionStatus.ERROR,
                summary=f"Unknown query type: {query.query_type}",
                warnings=[f"Supported types: {', '.join(QueryType.ALL)}"],
            )

        response.elapsed_ms = self._elapsed(start)

        # Check SLA
        if response.elapsed_ms > self.config.response_time_target_ms:
            response.warnings.append(
                f"Response time {response.elapsed_ms:.0f}ms exceeded "
                f"target {self.config.response_time_target_ms}ms"
            )

        logger.info(
            "IRIS %s resolved %s in %.0fms -> %s",
            query_id, query.query_type, response.elapsed_ms, response.status,
        )
        return response

    # ------------------------------------------------------------------
    # Query resolvers
    # ------------------------------------------------------------------

    def _resolve_why(self, query: IRISQuery, query_id: str,
                     warnings: List[str]) -> IRISResponse:
        """WHY: trace claim -> evidence -> source for an episode or claim."""
        if query.claim_id:
            result = self._mg.query("claim", claim_id=query.claim_id)
            if "error" in result:
                return IRISResponse(
                    query_id=query_id,
                    query_type=QueryType.WHY,
                    status=ResolutionStatus.NOT_FOUND,
                    summary=f"Claim {query.claim_id} not found in MemoryGraph.",
                    warnings=warnings,
                )
            provenance = [
                {"type": "claim", "ref": query.claim_id, "role": "root_assertion"},
            ]
            for ev in result.get("evidence", []):
                provenance.append({"type": "evidence", "ref": ev, "role": "supporting_evidence"})
            return IRISResponse(
                query_id=query_id,
                query_type=QueryType.WHY,
                status=ResolutionStatus.RESOLVED,
                summary=f"Claim {query.claim_id}: {result['node'].get('label', '')}",
                data=result,
                provenance=provenance,
                warnings=warnings,
            )

        if query.episode_id:
            result = self._mg.query("why", episode_id=query.episode_id)
            claims = self._mg.query("claims", episode_id=query.episode_id)
            result["claims"] = claims.get("claims", [])
            provenance = [
                {"type": "episode", "ref": query.episode_id, "role": "decision_context"},
            ]
            for ev in result.get("evidence_refs", []):
                provenance.append({"type": "evidence", "ref": ev, "role": "input_evidence"})
            for c in result.get("claims", []):
                provenance.append({"type": "claim", "ref": c.get("node_id", ""), "role": "deciding_claim"})
            return IRISResponse(
                query_id=query_id,
                query_type=QueryType.WHY,
                status=ResolutionStatus.RESOLVED if result.get("node") else ResolutionStatus.NOT_FOUND,
                summary=f"Episode {query.episode_id} with {len(result.get('claims', []))} claims.",
                data=result,
                provenance=provenance,
                warnings=warnings,
            )

        return IRISResponse(
            query_id=query_id,
            query_type=QueryType.WHY,
            status=ResolutionStatus.ERROR,
            summary="WHY query requires episode_id or claim_id.",
            warnings=warnings,
        )

    def _resolve_what_changed(self, query: IRISQuery, query_id: str,
                              warnings: List[str]) -> IRISResponse:
        """WHAT_CHANGED: find patches and supersession chains."""
        if query.episode_id:
            patches = self._mg.query("patches", episode_id=query.episode_id)
            return IRISResponse(
                query_id=query_id,
                query_type=QueryType.WHAT_CHANGED,
                status=ResolutionStatus.RESOLVED if patches.get("patches") else ResolutionStatus.NOT_FOUND,
                summary=f"Episode {query.episode_id}: {len(patches.get('patches', []))} patches found.",
                data=patches,
                warnings=warnings,
            )
        if query.claim_id:
            result = self._mg.query("claim", claim_id=query.claim_id)
            supersedes = result.get("supersedes", [])
            return IRISResponse(
                query_id=query_id,
                query_type=QueryType.WHAT_CHANGED,
                status=ResolutionStatus.RESOLVED,
                summary=f"Claim {query.claim_id} supersedes {len(supersedes)} prior claims.",
                data={"supersedes": supersedes, "claim": result},
                warnings=warnings,
            )
        return IRISResponse(
            query_id=query_id,
            query_type=QueryType.WHAT_CHANGED,
            status=ResolutionStatus.ERROR,
            summary="WHAT_CHANGED requires episode_id or claim_id.",
            warnings=warnings,
        )

    def _resolve_what_drifted(self, query: IRISQuery, query_id: str,
                              warnings: List[str]) -> IRISResponse:
        """WHAT_DRIFTED: find drift events and contradicting claims."""
        data: Dict[str, Any] = {}
        if query.episode_id:
            drift = self._mg.query("drift", episode_id=query.episode_id)
            data["drift_events"] = drift.get("drift_events", [])
        if query.claim_id:
            result = self._mg.query("claim", claim_id=query.claim_id)
            data["contradicts"] = result.get("contradicts", [])
        count = len(data.get("drift_events", [])) + len(data.get("contradicts", []))
        return IRISResponse(
            query_id=query_id,
            query_type=QueryType.WHAT_DRIFTED,
            status=ResolutionStatus.RESOLVED if count > 0 else ResolutionStatus.NOT_FOUND,
            summary=f"Found {count} drift signals.",
            data=data,
            warnings=warnings,
        )

    def _resolve_recall(self, query: IRISQuery, query_id: str,
                        warnings: List[str]) -> IRISResponse:
        """RECALL: retrieve from memory graph by text search or ID."""
        stats = self._mg.query("stats")
        return IRISResponse(
            query_id=query_id,
            query_type=QueryType.RECALL,
            status=ResolutionStatus.RESOLVED,
            summary=f"Memory graph: {stats['total_nodes']} nodes, {stats['total_edges']} edges.",
            data=stats,
            warnings=warnings,
        )

    def _resolve_status(self, query: IRISQuery, query_id: str,
                        warnings: List[str]) -> IRISResponse:
        """STATUS: current system health from graph statistics."""
        stats = self._mg.query("stats")
        nodes_by_kind = stats.get("nodes_by_kind", {})
        claim_count = nodes_by_kind.get("claim", 0)
        drift_count = nodes_by_kind.get("drift", 0)
        patch_count = nodes_by_kind.get("patch", 0)

        if drift_count > patch_count:
            health = "yellow"
            msg = f"Unresolved drift: {drift_count - patch_count} events without patches."
        elif drift_count > 0 and drift_count == patch_count:
            health = "green"
            msg = "All drift events have patches."
        else:
            health = "green"
            msg = "No drift detected."

        return IRISResponse(
            query_id=query_id,
            query_type=QueryType.STATUS,
            status=ResolutionStatus.RESOLVED,
            summary=f"Health: {health}. {msg} Claims: {claim_count}.",
            data={"health": health, "stats": stats},
            warnings=warnings,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _elapsed(start: float) -> float:
        """Elapsed time in milliseconds."""
        return (time.monotonic() - start) * 1000
