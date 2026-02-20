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
from dataclasses import asdict
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
        confidence: float = 0.0,
        warnings: Optional[List[str]] = None,
        elapsed_ms: float = 0.0,
    ):
        self.query_id = query_id
        self.query_type = query_type
        self.status = status
        self.summary = summary
        self.data = data or {}
        self.provenance = provenance or []
        self.confidence = min(1.0, max(0.0, confidence))
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
            "confidence": self.confidence,
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
    """Operator query resolution engine wired to all four Coherence Ops artifacts.

    Artifact confidence contributions (additive, capped at 1.0):
        WHY:          MG=0.50  DLR=0.35  RS=0.15
        WHAT_CHANGED: DLR=0.45 MG=0.35   DS=0.20
        WHAT_DRIFTED: DS=0.60  MG=0.40
        RECALL:       MG=0.50  DLR=0.30  RS=0.20
        STATUS:       scorer=0.70  DS=0.15  MG=0.15

    Usage:
        from coherence_ops.mg import MemoryGraph
        mg = MemoryGraph()
        engine = IRISEngine(config=IRISConfig(), memory_graph=mg,
                            dlr_entries=dlr.entries, rs=rs, ds=ds)
        response = engine.resolve(IRISQuery(query_type="WHY", episode_id="ep-001"))
    """

    def __init__(
        self,
        config: Optional[IRISConfig] = None,
        memory_graph: Optional[Any] = None,
        dlr_entries: Optional[List[Any]] = None,
        rs: Optional[Any] = None,
        ds: Optional[Any] = None,
    ):
        self.config = config or IRISConfig()
        issues = self.config.validate()
        if issues:
            raise ValueError("Invalid IRISConfig: " + "; ".join(issues))
        self._mg = memory_graph
        self._dlr_entries = dlr_entries or []
        self._rs = rs
        self._ds = ds

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
            "IRIS %s resolved %s in %.0fms -> %s (confidence=%.2f)",
            query_id, query.query_type, response.elapsed_ms,
            response.status, response.confidence,
        )
        return response

    # ------------------------------------------------------------------
    # Query resolvers
    # ------------------------------------------------------------------

    def _resolve_why(self, query: IRISQuery, query_id: str,
                     warnings: List[str]) -> IRISResponse:
        """WHY: trace claim → evidence → source for an episode or claim."""
        confidence = 0.0
        provenance: List[Dict[str, Any]] = []
        data: Dict[str, Any] = {}

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
            confidence += 0.50
            data["mg_claim"] = result
            provenance.append(self._prov("MG", query.claim_id, "source",
                                         "Claim node in MemoryGraph"))
            for ev in result.get("evidence", []):
                provenance.append(self._prov("MG", ev, "evidence", "Supporting evidence"))
            return IRISResponse(
                query_id=query_id,
                query_type=QueryType.WHY,
                status=self._status(confidence),
                summary=f"Claim {query.claim_id}: {result['node'].get('label', '')}",
                data=data,
                provenance=provenance,
                confidence=confidence,
                warnings=warnings,
            )

        if not query.episode_id:
            return IRISResponse(
                query_id=query_id,
                query_type=QueryType.WHY,
                status=ResolutionStatus.ERROR,
                summary="WHY query requires episode_id or claim_id.",
                warnings=warnings,
            )

        # MG: episode provenance node (primary — 0.50)
        mg_result = self._mg.query("why", episode_id=query.episode_id)
        claims_result = self._mg.query("claims", episode_id=query.episode_id)
        mg_result["claims"] = claims_result.get("claims", [])
        if mg_result.get("node"):
            confidence += 0.50
            data["mg_provenance"] = mg_result
            provenance.append(self._prov("MG", query.episode_id, "source",
                                         "Episode provenance node"))
            for ev in mg_result.get("evidence_refs", []):
                provenance.append(self._prov("MG", ev, "evidence", "Input evidence ref"))
            for c in mg_result.get("claims", []):
                provenance.append(self._prov("MG", c.get("node_id", ""),
                                             "evidence", "Deciding claim"))

        # DLR: policy context (+0.35)
        dlr_entry = self._find_dlr(query.episode_id)
        if dlr_entry is not None:
            confidence += 0.35
            data["dlr_entry"] = {
                "dlr_id": dlr_entry.dlr_id,
                "decision_type": dlr_entry.decision_type,
                "outcome_code": dlr_entry.outcome_code,
                "degrade_step": dlr_entry.degrade_step,
                "policy_stamp": dlr_entry.policy_stamp,
            }
            provenance.append(self._prov("DLR", dlr_entry.dlr_id, "context",
                                         f"Policy context: {dlr_entry.decision_type} "
                                         f"outcome={dlr_entry.outcome_code}"))

        # RS: reflection/learning context (+0.15)
        if self._rs is not None:
            rs_summary = self._rs.summarise()
            if rs_summary.episode_count > 0:
                confidence += 0.15
                data["rs_context"] = {
                    "episode_count": rs_summary.episode_count,
                    "outcome_distribution": rs_summary.outcome_distribution,
                    "verification_pass_rate": rs_summary.verification_pass_rate,
                }
                provenance.append(self._prov("RS", "reflection-session", "context",
                                             f"Reflection: {rs_summary.episode_count} episodes, "
                                             f"pass_rate={rs_summary.verification_pass_rate:.2f}"))

        if confidence == 0.0:
            return IRISResponse(
                query_id=query_id,
                query_type=QueryType.WHY,
                status=ResolutionStatus.NOT_FOUND,
                summary=f"Episode {query.episode_id} not found in any artifact.",
                data=data,
                provenance=provenance,
                confidence=0.0,
                warnings=warnings,
            )

        claim_count = len(mg_result.get("claims", []))
        return IRISResponse(
            query_id=query_id,
            query_type=QueryType.WHY,
            status=self._status(confidence),
            summary=(f"Episode {query.episode_id}: {claim_count} claims"
                     + (f", DLR outcome={dlr_entry.outcome_code}" if dlr_entry else "") + "."),
            data=data,
            provenance=provenance,
            confidence=confidence,
            warnings=warnings,
        )

    def _resolve_what_changed(self, query: IRISQuery, query_id: str,
                              warnings: List[str]) -> IRISResponse:
        """WHAT_CHANGED: DLR outcome distribution + MG patches + DS drift summary."""
        confidence = 0.0
        provenance: List[Dict[str, Any]] = []
        data: Dict[str, Any] = {}

        # DLR: outcome distribution, degraded episodes, policy stamp coverage (+0.45)
        if self._dlr_entries:
            entries = self._dlr_entries
            if query.episode_id:
                entries = [e for e in entries if e.episode_id == query.episode_id]
            if query.decision_type:
                entries = [e for e in entries if e.decision_type == query.decision_type]

            outcome_dist: Dict[str, int] = {}
            degraded: List[str] = []
            policy_missing: List[str] = []
            for e in entries:
                outcome_dist[e.outcome_code] = outcome_dist.get(e.outcome_code, 0) + 1
                if e.degrade_step:
                    degraded.append(e.episode_id)
                if not e.policy_stamp:
                    policy_missing.append(e.episode_id)

            if entries:
                confidence += 0.45
                data["dlr_summary"] = {
                    "total_entries": len(entries),
                    "outcome_distribution": outcome_dist,
                    "degraded_episodes": degraded,
                    "policy_missing": policy_missing,
                }
                provenance.append(self._prov("DLR", "dlr-summary", "source",
                                             f"{len(entries)} DLR entries analysed"))

        # MG: patches (+0.35)
        if query.episode_id:
            patches = self._mg.query("patches", episode_id=query.episode_id)
        elif query.claim_id:
            result = self._mg.query("claim", claim_id=query.claim_id)
            patches = {"patches": result.get("patches", [])}
        else:
            patches = {"patches": []}

        patch_list = patches.get("patches", [])
        if patch_list:
            confidence += 0.35
            data["patches"] = patch_list
            provenance.append(self._prov("MG", query.episode_id or query.claim_id,
                                         "evidence", f"{len(patch_list)} patches in graph"))

        # DS: drift summary (+0.20)
        if self._ds is not None and self._ds.event_count > 0:
            ds_summary = self._ds.summarise()
            confidence += 0.20
            data["drift_summary"] = {
                "total_signals": ds_summary.total_signals,
                "by_severity": ds_summary.by_severity,
                "by_type": ds_summary.by_type,
                "top_recurring": ds_summary.top_recurring,
            }
            provenance.append(self._prov("DS", "drift-scan", "context",
                                         f"{ds_summary.total_signals} drift signals"))

        if confidence == 0.0:
            return IRISResponse(
                query_id=query_id,
                query_type=QueryType.WHAT_CHANGED,
                status=ResolutionStatus.NOT_FOUND,
                summary="No changes found in DLR, MG, or DS for the given scope.",
                data=data,
                provenance=provenance,
                confidence=0.0,
                warnings=warnings,
            )

        dlr_total = data.get("dlr_summary", {}).get("total_entries", 0)
        patch_count = len(data.get("patches", []))
        return IRISResponse(
            query_id=query_id,
            query_type=QueryType.WHAT_CHANGED,
            status=self._status(confidence),
            summary=(f"{dlr_total} DLR entries, {patch_count} patches, "
                     f"{data.get('drift_summary', {}).get('total_signals', 0)} drift signals."),
            data=data,
            provenance=provenance,
            confidence=confidence,
            warnings=warnings,
        )

    def _resolve_what_drifted(self, query: IRISQuery, query_id: str,
                              warnings: List[str]) -> IRISResponse:
        """WHAT_DRIFTED: DS severity breakdown + fingerprint buckets + MG resolution ratio."""
        confidence = 0.0
        provenance: List[Dict[str, Any]] = []
        data: Dict[str, Any] = {}

        # DS: primary source for drift intelligence (+0.60)
        if self._ds is not None and self._ds.event_count > 0:
            ds_summary = self._ds.summarise()
            confidence += 0.60
            data["by_severity"] = ds_summary.by_severity
            data["by_type"] = ds_summary.by_type
            data["top_recurring"] = ds_summary.top_recurring
            data["total_signals"] = ds_summary.total_signals
            data["top_buckets"] = [
                {
                    "fingerprint_key": b.fingerprint_key,
                    "drift_type": b.drift_type,
                    "count": b.count,
                    "worst_severity": b.worst_severity,
                    "recommended_patches": b.recommended_patches,
                }
                for b in ds_summary.buckets[:5]
            ]
            provenance.append(self._prov("DS", "drift-scan", "source",
                                         f"{ds_summary.total_signals} signals, "
                                         f"{len(ds_summary.top_recurring)} recurring"))

        # MG: resolution ratio — patches / total drift nodes (+0.40)
        mg_stats = self._mg.query("stats")
        nodes_by_kind = mg_stats.get("nodes_by_kind", {})
        drift_nodes = nodes_by_kind.get("drift", 0)
        patch_nodes = nodes_by_kind.get("patch", 0)
        total_signals = data.get("total_signals", drift_nodes)

        if drift_nodes > 0 or total_signals > 0:
            confidence += 0.40
            denom = max(total_signals, drift_nodes)
            resolution_ratio = patch_nodes / denom if denom > 0 else 0.0
            data["resolution_ratio"] = round(resolution_ratio, 4)
            data["mg_drift_nodes"] = drift_nodes
            data["mg_patch_nodes"] = patch_nodes
            provenance.append(self._prov("MG", "mg-stats", "evidence",
                                         f"resolution_ratio={resolution_ratio:.2f} "
                                         f"({patch_nodes}/{denom})"))

        if confidence == 0.0:
            return IRISResponse(
                query_id=query_id,
                query_type=QueryType.WHAT_DRIFTED,
                status=ResolutionStatus.NOT_FOUND,
                summary="No drift signals found in DS or MG.",
                data=data,
                provenance=provenance,
                confidence=0.0,
                warnings=warnings,
            )

        red = data.get("by_severity", {}).get("red", 0)
        return IRISResponse(
            query_id=query_id,
            query_type=QueryType.WHAT_DRIFTED,
            status=self._status(confidence),
            summary=(f"{data.get('total_signals', drift_nodes)} drift signals "
                     f"({red} red). Resolution ratio: "
                     f"{data.get('resolution_ratio', 0.0):.0%}."),
            data=data,
            provenance=provenance,
            confidence=confidence,
            warnings=warnings,
        )

    def _resolve_recall(self, query: IRISQuery, query_id: str,
                        warnings: List[str]) -> IRISResponse:
        """RECALL: full episode graph walk + DLR enrichment."""
        if not query.episode_id:
            return IRISResponse(
                query_id=query_id,
                query_type=QueryType.RECALL,
                status=ResolutionStatus.ERROR,
                summary="RECALL query requires episode_id.",
                warnings=warnings,
            )

        confidence = 0.0
        provenance: List[Dict[str, Any]] = []
        data: Dict[str, Any] = {}

        # MG: full episode graph walk (+0.50)
        mg_result = self._mg.query("why", episode_id=query.episode_id)
        drift_result = self._mg.query("drift", episode_id=query.episode_id)
        patches_result = self._mg.query("patches", episode_id=query.episode_id)
        claims_result = self._mg.query("claims", episode_id=query.episode_id)

        if mg_result.get("node"):
            confidence += 0.50
            data["provenance"] = mg_result
            data["drift_events"] = drift_result.get("drift_events", [])
            data["patches"] = patches_result.get("patches", [])
            data["claims"] = claims_result.get("claims", [])
            provenance.append(self._prov("MG", query.episode_id, "source",
                                         "Full episode graph walk"))
            for ev in mg_result.get("evidence_refs", []):
                provenance.append(self._prov("MG", ev, "evidence", "Evidence ref"))
            for d in data["drift_events"]:
                provenance.append(self._prov("MG", d.get("node_id", ""),
                                             "evidence", "Drift event"))

        # DLR: decision record enrichment (+0.30)
        dlr_entry = self._find_dlr(query.episode_id)
        if dlr_entry is not None:
            confidence += 0.30
            data["dlr_entry"] = {
                "dlr_id": dlr_entry.dlr_id,
                "decision_type": dlr_entry.decision_type,
                "outcome_code": dlr_entry.outcome_code,
                "degrade_step": dlr_entry.degrade_step,
                "policy_stamp": dlr_entry.policy_stamp,
                "verification": dlr_entry.verification,
                "action_contract": dlr_entry.action_contract,
            }
            provenance.append(self._prov("DLR", dlr_entry.dlr_id, "context",
                                         f"Decision record: {dlr_entry.decision_type}"))

        # RS: reflection context (+0.20)
        if self._rs is not None:
            rs_summary = self._rs.summarise()
            if rs_summary.episode_count > 0:
                confidence += 0.20
                data["rs_context"] = {
                    "episode_count": rs_summary.episode_count,
                    "verification_pass_rate": rs_summary.verification_pass_rate,
                }
                provenance.append(self._prov("RS", "reflection-session", "context",
                                             "Reflection session context"))

        if confidence == 0.0:
            return IRISResponse(
                query_id=query_id,
                query_type=QueryType.RECALL,
                status=ResolutionStatus.NOT_FOUND,
                summary=f"Episode {query.episode_id} not found in any artifact.",
                data=data,
                provenance=provenance,
                confidence=0.0,
                warnings=warnings,
            )

        claim_count = len(data.get("claims", []))
        drift_count = len(data.get("drift_events", []))
        return IRISResponse(
            query_id=query_id,
            query_type=QueryType.RECALL,
            status=self._status(confidence),
            summary=(f"Episode {query.episode_id}: {claim_count} claims, "
                     f"{drift_count} drift events"
                     + (f", {dlr_entry.decision_type}" if dlr_entry else "") + "."),
            data=data,
            provenance=provenance,
            confidence=confidence,
            warnings=warnings,
        )

    def _resolve_status(self, query: IRISQuery, query_id: str,
                        warnings: List[str]) -> IRISResponse:
        """STATUS: CoherenceScorer composite with 4 dimensions."""
        confidence = 0.0
        provenance: List[Dict[str, Any]] = []
        data: Dict[str, Any] = {}

        # CoherenceScorer: primary source (+0.70)
        try:
            from coherence_ops.scoring import CoherenceScorer
            scorer = CoherenceScorer(
                dlr_builder=None,  # pass a compatible wrapper
                rs=self._rs,
                ds=self._ds,
                mg=self._mg,
            )
            # Inject DLR entries via a thin wrapper if entries are present
            if self._dlr_entries:
                class _DLRWrap:
                    def __init__(self, entries: list) -> None:
                        self.entries = entries
                scorer.dlr = _DLRWrap(self._dlr_entries)

            report = scorer.score()
            confidence += 0.70
            data["overall_score"] = report.overall_score
            data["grade"] = report.grade
            data["dimensions"] = [asdict(d) for d in report.dimensions]
            data["computed_at"] = report.computed_at
            provenance.append(self._prov("DLR", "coherence-scorer", "source",
                                         f"CoherenceScorer: {report.overall_score}/100 ({report.grade})"))
        except Exception as exc:
            warnings.append(f"CoherenceScorer unavailable: {exc}")

        # DS: drift headline (+0.15)
        if self._ds is not None and self._ds.event_count > 0:
            ds_summary = self._ds.summarise()
            confidence += 0.15
            red = ds_summary.by_severity.get("red", 0)
            recurring = len(ds_summary.top_recurring)
            data["drift_headline"] = {
                "total": ds_summary.total_signals,
                "red": red,
                "recurring_patterns": recurring,
            }
            provenance.append(self._prov("DS", "drift-scan", "evidence",
                                         f"{ds_summary.total_signals} signals, {red} red"))

        # MG: graph statistics (+0.15)
        mg_stats = self._mg.query("stats")
        if mg_stats.get("total_nodes", 0) > 0:
            confidence += 0.15
            data["mg_stats"] = mg_stats
            provenance.append(self._prov("MG", "mg-stats", "evidence",
                                         f"{mg_stats['total_nodes']} nodes, "
                                         f"{mg_stats['total_edges']} edges"))

        if confidence == 0.0:
            return IRISResponse(
                query_id=query_id,
                query_type=QueryType.STATUS,
                status=ResolutionStatus.NOT_FOUND,
                summary="No data available for STATUS query.",
                data=data,
                provenance=provenance,
                confidence=0.0,
                warnings=warnings,
            )

        grade = data.get("grade", "?")
        score = data.get("overall_score", 0.0)
        drift_total = data.get("drift_headline", {}).get("total", 0)
        return IRISResponse(
            query_id=query_id,
            query_type=QueryType.STATUS,
            status=self._status(confidence),
            summary=f"Coherence: {score}/100 ({grade}). Drift signals: {drift_total}.",
            data=data,
            provenance=provenance,
            confidence=confidence,
            warnings=warnings,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _find_dlr(self, episode_id: str) -> Optional[Any]:
        """Return the first DLR entry matching episode_id, or None."""
        return next((e for e in self._dlr_entries if e.episode_id == episode_id), None)

    @staticmethod
    def _prov(artifact: str, ref_id: str, role: str, detail: str) -> Dict[str, Any]:
        """Build a provenance chain link."""
        return {"artifact": artifact, "ref_id": ref_id, "role": role, "detail": detail}

    @staticmethod
    def _status(confidence: float) -> str:
        """Map confidence to ResolutionStatus."""
        if confidence <= 0.0:
            return ResolutionStatus.NOT_FOUND
        if confidence < 0.5:
            return ResolutionStatus.PARTIAL
        return ResolutionStatus.RESOLVED

    @staticmethod
    def _elapsed(start: float) -> float:
        """Elapsed time in milliseconds."""
        return (time.monotonic() - start) * 1000
