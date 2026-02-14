"""IRIS Interface Layer — operator query resolution engine.

IRIS (Interface for Resolution, Insight, and Status) sits on top of PRIME
and queries against the four canonical artifacts (DLR / RS / DS / MG) to
answer operator questions with full provenance chains.

Supported query types:
    WHY           — "Why did we decide X?"   → MG lookup + DLR context
        WHAT_CHANGED  — "What changed?"          → DLR diff across time windows
            WHAT_DRIFTED  — "What's drifting?"       → DS scan + severity ranking
                RECALL        — "What do we know about?" → MG graph traversal
                    STATUS        — "How healthy are we?"    → CoherenceScorer composite

                    Every response includes:
                        - provenance_chain: ordered list of artifact references that produced the answer
                            - resolved_at: ISO-8601 timestamp
                                - elapsed_ms: wall-clock time (target: < 60 000 ms)
                                    - confidence: 0.0–1.0 estimate of answer completeness

                                    IRIS is read-only — it never mutates DLR/RS/DS/MG state.

                                    Reference: coherence_ops/prime.py for PRIME Threshold Gate integration patterns.
                                    """

from __future__ import annotations

import hashlib
import json
import logging
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from coherence_ops.dlr import DLRBuilder
from coherence_ops.ds import DriftSignalCollector
from coherence_ops.mg import MemoryGraph
from coherence_ops.rs import ReflectionSession
from coherence_ops.scoring import CoherenceScorer

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Maximum wall-clock time (ms) before IRIS logs a performance warning.
RESPONSE_TIME_TARGET_MS = 60_000


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class QueryType(str, Enum):
      """Supported IRIS query types."""

    WHY = "WHY"
    WHAT_CHANGED = "WHAT_CHANGED"
    WHAT_DRIFTED = "WHAT_DRIFTED"
    RECALL = "RECALL"
    STATUS = "STATUS"


class ResolutionStatus(str, Enum):
      """Outcome status of an IRIS resolution."""

    RESOLVED = "RESOLVED"
    PARTIAL = "PARTIAL"
    NOT_FOUND = "NOT_FOUND"
    ERROR = "ERROR"


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass
class ProvenanceLink:
      """A single link in a provenance chain."""

    artifact: str  # e.g. "DLR", "MG", "DS", "RS", "PRIME"
    ref_id: str  # identifier within the artifact
    role: str  # e.g. "source", "evidence", "context"
    detail: str = ""


@dataclass
class IRISQuery:
      """Operator query submitted to IRIS."""

    query_type: QueryType
    text: str = ""
    episode_id: str = ""
    decision_type: str = ""
    time_window_seconds: float = 3600.0
    limit: int = 20
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class IRISResponse:
      """Structured response from IRIS."""

    query_id: str
    query_type: QueryType
    status: ResolutionStatus
    summary: str
    data: Dict[str, Any] = field(default_factory=dict)
    provenance_chain: List[ProvenanceLink] = field(default_factory=list)
    confidence: float = 0.0
    resolved_at: str = ""
    elapsed_ms: float = 0.0
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
              """Serialise to a plain dict (enums → values)."""
              d = asdict(self)
              d["query_type"] = self.query_type.value
              d["status"] = self.status.value
              return d

    def to_json(self, indent: int = 2) -> str:
              """Serialise to JSON string."""
              return json.dumps(self.to_dict(), indent=indent, default=str)


@dataclass
class IRISConfig:
      """Configuration for the IRIS engine."""

    response_time_target_ms: float = RESPONSE_TIME_TARGET_MS
    max_provenance_depth: int = 50
    default_time_window_seconds: float = 3600.0
    default_limit: int = 20
    include_raw_artifacts: bool = False

    def validate(self) -> List[str]:
              """Return a list of configuration issues (empty = valid)."""
              issues: List[str] = []
              if self.response_time_target_ms <= 0:
                            issues.append("response_time_target_ms must be positive")
                        if self.max_provenance_depth < 1:
                                      issues.append("max_provenance_depth must be >= 1")
                                  if self.default_time_window_seconds <= 0:
                                                issues.append("default_time_window_seconds must be positive")
                                            return issues


# ---------------------------------------------------------------------------
# IRIS Engine
# ---------------------------------------------------------------------------


class IRISEngine:
      """Operator query resolution engine.

          IRIS sits on top of PRIME and queries against DLR / RS / DS / MG to
              resolve operator questions with full provenance chains.

                  Usage::

                          engine = IRISEngine(
                                      dlr_builder=dlr,
                                                  rs=reflection_session,
                                                              ds=drift_collector,
                                                                          mg=memory_graph,
                                                                                  )
                                                                                          response = engine.resolve(IRISQuery(
                                                                                                      query_type=QueryType.WHY,
                                                                                                                  episode_id="ep-001",
                                                                                                                          ))
                                                                                                                                  print(response.summary)
                                                                                                                                      """

    def __init__(
              self,
              dlr_builder: Optional[DLRBuilder] = None,
              rs: Optional[ReflectionSession] = None,
              ds: Optional[DriftSignalCollector] = None,
              mg: Optional[MemoryGraph] = None,
              config: Optional[IRISConfig] = None,
    ) -> None:
              self.dlr = dlr_builder
        self.rs = rs
        self.ds = ds
        self.mg = mg
        self.config = config or IRISConfig()

        issues = self.config.validate()
        if issues:
                      raise ValueError(f"Invalid IRISConfig: {'; '.join(issues)}")

        self._resolvers = {
                      QueryType.WHY: self._resolve_why,
                      QueryType.WHAT_CHANGED: self._resolve_what_changed,
                      QueryType.WHAT_DRIFTED: self._resolve_what_drifted,
                      QueryType.RECALL: self._resolve_recall,
                      QueryType.STATUS: self._resolve_status,
        }

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def resolve(self, query: IRISQuery) -> IRISResponse:
              """Resolve an operator query and return a structured response.

                      This is the main entry point. It delegates to the appropriate
                              resolver based on ``query.query_type``, wraps the result in an
                                      :class:`IRISResponse` with provenance chain, and enforces the
                                              sub-60-second response-time target.
                                                      """
        start = time.monotonic()
        query_id = self._make_query_id(query)

        resolver = self._resolvers.get(query.query_type)
        if resolver is None:
                      return self._error_response(
                                        query_id, query.query_type,
                                        f"Unsupported query type: {query.query_type.value}",
                      )

        try:
                      response = resolver(query, query_id)
except Exception as exc:  # noqa: BLE001
            logger.exception("IRIS resolver error for %s", query.query_type.value)
            response = self._error_response(
                              query_id, query.query_type,
                              f"Resolution failed: {exc}",
            )

        elapsed_ms = (time.monotonic() - start) * 1000
        response.elapsed_ms = round(elapsed_ms, 2)
        response.resolved_at = datetime.now(timezone.utc).isoformat()

        if elapsed_ms > self.config.response_time_target_ms:
                      response.warnings.append(
                                        f"Response time {elapsed_ms:.0f} ms exceeds "
                                        f"target {self.config.response_time_target_ms:.0f} ms"
                      )
                      logger.warning(
                          "IRIS response time %.0f ms exceeds target for %s",
                          elapsed_ms, query.query_type.value,
                      )

        logger.info(
                      "IRIS resolved %s (query_id=%s) in %.0f ms — %s",
                      query.query_type.value, query_id, elapsed_ms, response.status.value,
        )
        return response

    def available_query_types(self) -> List[str]:
              """Return the list of supported query type values."""
        return [qt.value for qt in QueryType]

    # ------------------------------------------------------------------
    # WHY resolver — MG lookup + DLR context
    # ------------------------------------------------------------------

    def _resolve_why(self, query: IRISQuery, query_id: str) -> IRISResponse:
              """Answer: 'Why did we decide X?'

                      Strategy:
                                  1. Query MG for episode provenance (evidence, actions, drift).
                                              2. Find the matching DLR entry for policy context.
                                                          3. Merge into a unified explanation with provenance chain.
                                                                  """
        provenance: List[ProvenanceLink] = []
        data: Dict[str, Any] = {}
        parts: List[str] = []
        confidence = 0.0

        episode_id = query.episode_id
        if not episode_id:
                      return self._not_found_response(
                                        query_id, query.query_type,
                                        "WHY query requires an episode_id",
                      )

        # --- MG lookup ---
        if self.mg is not None:
                      mg_why = self.mg.query("why", episode_id=episode_id)
                      mg_node = mg_why.get("node")

            if mg_node is not None:
                              data["mg_provenance"] = mg_why
                              provenance.append(ProvenanceLink(
                                  artifact="MG", ref_id=episode_id,
                                  role="source",
                                  detail=f"Memory Graph node: {mg_node.get('label', '')}",
                              ))
                              for ev_ref in mg_why.get("evidence_refs", []):
                                                    provenance.append(ProvenanceLink(
                                                                              artifact="MG", ref_id=ev_ref,
                                                                              role="evidence",
                                                                              detail="Evidence reference from Memory Graph",
                                                    ))
                                                parts.append(
                                                                      f"Episode '{episode_id}' found in Memory Graph "
                                                                      f"with {len(mg_why.get('evidence_refs', []))} evidence ref(s) "
                                                                      f"and {len(mg_why.get('actions', []))} action(s)."
                                                )
                confidence += 0.4
else:
                parts.append(f"Episode '{episode_id}' not found in Memory Graph.")

            # Drift context from MG
            mg_drift = self.mg.query("drift", episode_id=episode_id)
            drift_events = mg_drift.get("drift_events", [])
            if drift_events:
                              data["mg_drift"] = drift_events
                provenance.append(ProvenanceLink(
                                      artifact="MG", ref_id=episode_id,
                                      role="context",
                                      detail=f"{len(drift_events)} drift event(s) linked",
                ))
                parts.append(
                                      f"{len(drift_events)} drift event(s) associated with this episode."
                )
                confidence += 0.1

        # --- DLR context ---
        if self.dlr is not None:
                      matching = [
                                        e for e in self.dlr.entries
                                        if e.episode_id == episode_id
                      ]
            if matching:
                              entry = matching[0]
                data["dlr_entry"] = asdict(entry)
                provenance.append(ProvenanceLink(
                                      artifact="DLR", ref_id=entry.dlr_id,
                                      role="context",
                                      detail=f"Policy stamp: {entry.policy_stamp is not None}, "
                                             f"outcome: {entry.outcome_code}",
                ))
                parts.append(
                                      f"DLR record '{entry.dlr_id}' shows decision type "
                                      f"'{entry.decision_type}' with outcome '{entry.outcome_code}'."
                )
                if entry.policy_stamp:
                                      parts.append("Policy stamp present — decision was policy-governed.")
                                  if entry.degrade_step and entry.degrade_step != "none":
                                                        parts.append(f"Degrade step active: {entry.degrade_step}.")
                                                    confidence += 0.3
else:
                parts.append("No DLR entry found for this episode.")

        # --- RS context (if available) ---
        if self.rs is not None:
                      provenance.append(ProvenanceLink(
                                        artifact="RS", ref_id=f"session:{self.rs.session_id}",
                                        role="context",
                                        detail="Reflection session available for broader context",
                      ))
            confidence += 0.1

        confidence = min(confidence, 1.0)
        status = (
                      ResolutionStatus.RESOLVED if confidence >= 0.5
                      else ResolutionStatus.PARTIAL if confidence > 0
                      else ResolutionStatus.NOT_FOUND
        )
        summary = " ".join(parts) if parts else f"No data found for episode '{episode_id}'."

        return IRISResponse(
                      query_id=query_id,
                      query_type=query.query_type,
                      status=status,
                      summary=summary,
                      data=data,
                      provenance_chain=provenance,
                      confidence=round(confidence, 3),
        )

    # ------------------------------------------------------------------
    # WHAT_CHANGED resolver — DLR diff
    # ------------------------------------------------------------------

    def _resolve_what_changed(self, query: IRISQuery, query_id: str) -> IRISResponse:
              """Answer: 'What changed?'

                      Strategy:
                                  1. Retrieve DLR entries within the requested time window.
                                              2. Compute diff: new entries, outcome shifts, degrade changes.
                                                          3. Enrich with MG patch history when available.
                                                                  """
        provenance: List[ProvenanceLink] = []
        data: Dict[str, Any] = {}
        parts: List[str] = []
        confidence = 0.0

        if self.dlr is None or not self.dlr.entries:
                      return self._not_found_response(
                                        query_id, query.query_type,
                                        "No DLR entries available for change analysis.",
                      )

        entries = self.dlr.entries
        limit = query.limit or self.config.default_limit

        # Partition by outcome
        outcomes: Dict[str, List[str]] = {}
        degrade_entries: List[str] = []
        policy_missing: List[str] = []

        for entry in entries:
                      code = entry.outcome_code
            outcomes.setdefault(code, []).append(entry.episode_id)
            if entry.degrade_step and entry.degrade_step != "none":
                              degrade_entries.append(entry.episode_id)
            if not entry.policy_stamp:
                              policy_missing.append(entry.episode_id)

        data["total_entries"] = len(entries)
        data["outcome_distribution"] = {k: len(v) for k, v in outcomes.items()}
        data["degraded_episodes"] = degrade_entries[:limit]
        data["policy_missing"] = policy_missing[:limit]

        provenance.append(ProvenanceLink(
                      artifact="DLR", ref_id="all",
                      role="source",
                      detail=f"Analysed {len(entries)} DLR entries",
        ))

        parts.append(f"Analysed {len(entries)} DLR entries.")
        if degrade_entries:
                      parts.append(f"{len(degrade_entries)} episode(s) had active degrade steps.")
        if policy_missing:
                      parts.append(f"{len(policy_missing)} episode(s) missing policy stamps.")

        for code, ids in outcomes.items():
                      parts.append(f"Outcome '{code}': {len(ids)} episode(s).")

        confidence += 0.5

        # Enrich with MG patch data
        if self.mg is not None:
                      mg_stats = self.mg.query("stats")
            patch_count = mg_stats.get("nodes_by_kind", {}).get("patch", 0)
            if patch_count > 0:
                              data["patch_count"] = patch_count
                provenance.append(ProvenanceLink(
                                      artifact="MG", ref_id="stats",
                                      role="context",
                                      detail=f"{patch_count} patch node(s) in Memory Graph",
                ))
                parts.append(f"{patch_count} patch(es) recorded in Memory Graph.")
                confidence += 0.2

        # Enrich with DS drift summary
        if self.ds is not None and self.ds.event_count > 0:
                      ds_summary = self.ds.summarise()
            data["drift_summary"] = {
                              "total_signals": ds_summary.total_signals,
                              "by_severity": ds_summary.by_severity,
            }
            provenance.append(ProvenanceLink(
                              artifact="DS", ref_id="summary",
                              role="context",
                              detail=f"{ds_summary.total_signals} drift signal(s)",
            ))
            parts.append(
                              f"{ds_summary.total_signals} drift signal(s) detected "
                              f"(red: {ds_summary.by_severity.get('red', 0)})."
            )
            confidence += 0.2

        confidence = min(confidence, 1.0)
        summary = " ".join(parts)

        return IRISResponse(
                      query_id=query_id,
                      query_type=query.query_type,
                      status=ResolutionStatus.RESOLVED,
                      summary=summary,
                      data=data,
                      provenance_chain=provenance,
                      confidence=round(confidence, 3),
        )

    # ------------------------------------------------------------------
    # WHAT_DRIFTED resolver — DS scan
    # ------------------------------------------------------------------

    def _resolve_what_drifted(self, query: IRISQuery, query_id: str) -> IRISResponse:
              """Answer: 'What's drifting?'

                      Strategy:
                                  1. Pull DS summary (buckets sorted by severity × count).
                                              2. Return top-N drift fingerprints with recommended patches.
                                                          3. Cross-reference MG for patch resolution status.
                                                                  """
        provenance: List[ProvenanceLink] = []
        data: Dict[str, Any] = {}
        parts: List[str] = []
        confidence = 0.0

        if self.ds is None or self.ds.event_count == 0:
                      return self._not_found_response(
                                        query_id, query.query_type,
                                        "No drift signals available.",
                      )

        ds_summary = self.ds.summarise()
        limit = query.limit or self.config.default_limit

        buckets_data = []
        for bucket in ds_summary.buckets[:limit]:
                      buckets_data.append(asdict(bucket))

        data["total_signals"] = ds_summary.total_signals
        data["by_type"] = ds_summary.by_type
        data["by_severity"] = ds_summary.by_severity
        data["top_buckets"] = buckets_data
        data["top_recurring"] = ds_summary.top_recurring

        provenance.append(ProvenanceLink(
                      artifact="DS", ref_id="summary",
                      role="source",
                      detail=f"Drift scan: {ds_summary.total_signals} signals, "
                             f"{len(ds_summary.buckets)} fingerprints",
        ))

        red_count = ds_summary.by_severity.get("red", 0)
        yellow_count = ds_summary.by_severity.get("yellow", 0)
        green_count = ds_summary.by_severity.get("green", 0)

        parts.append(
                      f"{ds_summary.total_signals} drift signal(s) across "
                      f"{len(ds_summary.buckets)} fingerprint(s)."
        )
        parts.append(f"Severity breakdown: red={red_count}, yellow={yellow_count}, green={green_count}.")

        if ds_summary.top_recurring:
                      parts.append(
                                        f"Top recurring patterns: {', '.join(ds_summary.top_recurring[:5])}."
                      )

        confidence += 0.6

        # Cross-reference MG for patch resolution
        if self.mg is not None:
                      mg_stats = self.mg.query("stats")
            drift_nodes = mg_stats.get("nodes_by_kind", {}).get("drift", 0)
            patch_nodes = mg_stats.get("nodes_by_kind", {}).get("patch", 0)

            data["mg_drift_nodes"] = drift_nodes
            data["mg_patch_nodes"] = patch_nodes

            if drift_nodes > 0:
                              resolution_ratio = patch_nodes / drift_nodes if drift_nodes else 0.0
                data["resolution_ratio"] = round(resolution_ratio, 4)
                provenance.append(ProvenanceLink(
                                      artifact="MG", ref_id="stats",
                                      role="context",
                                      detail=f"Drift resolution ratio: {resolution_ratio:.2%} "
                                             f"({patch_nodes}/{drift_nodes})",
                ))
                parts.append(
                                      f"Memory Graph shows {patch_nodes}/{drift_nodes} "
                                      f"drift(s) resolved ({resolution_ratio:.0%})."
                )
                confidence += 0.2

        confidence = min(confidence, 1.0)
        summary = " ".join(parts)

        return IRISResponse(
                      query_id=query_id,
                      query_type=query.query_type,
                      status=ResolutionStatus.RESOLVED,
                      summary=summary,
                      data=data,
                      provenance_chain=provenance,
                      confidence=round(confidence, 3),
        )

    # ------------------------------------------------------------------
    # RECALL resolver — MG graph traversal
    # ------------------------------------------------------------------

    def _resolve_recall(self, query: IRISQuery, query_id: str) -> IRISResponse:
              """Answer: 'What do we know about X?'

                      Strategy:
                                  1. Query MG for the episode (why + drift + patches).
                                              2. Merge all graph context into a single recall bundle.
                                                          3. Attach DLR entry if available.
                                                                  """
        provenance: List[ProvenanceLink] = []
        data: Dict[str, Any] = {}
        parts: List[str] = []
        confidence = 0.0

        episode_id = query.episode_id
        if not episode_id:
                      return self._not_found_response(
                                        query_id, query.query_type,
                                        "RECALL query requires an episode_id.",
                      )

        if self.mg is None:
                      return self._not_found_response(
                                        query_id, query.query_type,
                                        "Memory Graph not available for recall.",
                      )

        # Full MG traversal
        mg_why = self.mg.query("why", episode_id=episode_id)
        mg_drift = self.mg.query("drift", episode_id=episode_id)
        mg_patches = self.mg.query("patches", episode_id=episode_id)

        data["provenance"] = mg_why
        data["drift_events"] = mg_drift.get("drift_events", [])
        data["patches"] = mg_patches.get("patches", [])

        mg_node = mg_why.get("node")
        if mg_node is not None:
                      provenance.append(ProvenanceLink(
                                        artifact="MG", ref_id=episode_id,
                                        role="source",
                                        detail=f"Full recall: node label='{mg_node.get('label', '')}'",
                      ))
            parts.append(
                              f"Recalled episode '{episode_id}' "
                              f"(type: {mg_node.get('label', 'unknown')})."
            )
            confidence += 0.3

            evidence = mg_why.get("evidence_refs", [])
            actions = mg_why.get("actions", [])
            drift_events = mg_drift.get("drift_events", [])
            patches = mg_patches.get("patches", [])

            parts.append(
                              f"Graph context: {len(evidence)} evidence ref(s), "
                              f"{len(actions)} action(s), {len(drift_events)} drift(s), "
                              f"{len(patches)} patch(es)."
            )

            for ev_ref in evidence:
                              provenance.append(ProvenanceLink(
                                  artifact="MG", ref_id=ev_ref,
                                  role="evidence", detail="Evidence reference",
            ))
            for act_id in actions:
                              provenance.append(ProvenanceLink(
                                  artifact="MG", ref_id=act_id,
                                  role="context", detail="Action node",
            ))

            confidence += 0.3
else:
            parts.append(f"Episode '{episode_id}' not found in Memory Graph.")

        # DLR enrichment
        if self.dlr is not None:
                      matching = [
                                        e for e in self.dlr.entries
                                        if e.episode_id == episode_id
                      ]
            if matching:
                              entry = matching[0]
                data["dlr_entry"] = asdict(entry)
                provenance.append(ProvenanceLink(
                                      artifact="DLR", ref_id=entry.dlr_id,
                                      role="context",
                                      detail=f"Decision type: {entry.decision_type}, "
                                             f"outcome: {entry.outcome_code}",
                ))
                parts.append(
                                      f"DLR record confirms decision type '{entry.decision_type}'."
                )
                confidence += 0.2

        confidence = min(confidence, 1.0)
        status = (
                      ResolutionStatus.RESOLVED if confidence >= 0.5
                      else ResolutionStatus.PARTIAL if confidence > 0
                      else ResolutionStatus.NOT_FOUND
        )
        summary = " ".join(parts) if parts else f"No recall data for '{episode_id}'."

        return IRISResponse(
                      query_id=query_id,
                      query_type=query.query_type,
                      status=status,
                      summary=summary,
                      data=data,
                      provenance_chain=provenance,
                      confidence=round(confidence, 3),
        )

    # ------------------------------------------------------------------
    # STATUS resolver — CoherenceScorer composite
    # ------------------------------------------------------------------

    def _resolve_status(self, query: IRISQuery, query_id: str) -> IRISResponse:
              """Answer: 'How healthy are we?'

                      Strategy:
                                  1. Run CoherenceScorer across all four artifacts.
                                              2. Surface per-dimension breakdown and overall grade.
                                                          3. Attach graph stats from MG and drift summary from DS.
                                                                  """
        provenance: List[ProvenanceLink] = []
        data: Dict[str, Any] = {}
        parts: List[str] = []

        scorer = CoherenceScorer(
                      dlr_builder=self.dlr,
                      rs=self.rs,
                      ds=self.ds,
                      mg=self.mg,
        )
        report = scorer.score()

        data["overall_score"] = report.overall_score
        data["grade"] = report.grade
        data["dimensions"] = [asdict(d) for d in report.dimensions]

        provenance.append(ProvenanceLink(
                      artifact="DLR",
                      ref_id="scorer",
                      role="source",
                      detail="Policy adherence dimension",
        ))
        provenance.append(ProvenanceLink(
                      artifact="RS",
                      ref_id="scorer",
                      role="source",
                      detail="Outcome health dimension",
        ))
        provenance.append(ProvenanceLink(
                      artifact="DS",
                      ref_id="scorer",
                      role="source",
                      detail="Drift control dimension",
        ))
        provenance.append(ProvenanceLink(
                      artifact="MG",
                      ref_id="scorer",
                      role="source",
                      detail="Memory completeness dimension",
        ))

        parts.append(
                      f"System coherence: {report.overall_score}/100 (grade {report.grade})."
        )
        for dim in report.dimensions:
                      parts.append(f"{dim.name}: {dim.score:.1f}/100 (weight {dim.weight:.0%}).")

        # Graph stats
        if self.mg is not None:
                      mg_stats = self.mg.query("stats")
            data["mg_stats"] = mg_stats
            provenance.append(ProvenanceLink(
                              artifact="MG", ref_id="stats",
                              role="context",
                              detail=f"Graph: {mg_stats.get('total_nodes', 0)} nodes, "
                                     f"{mg_stats.get('total_edges', 0)} edges",
            ))

        # Drift headline
        if self.ds is not None and self.ds.event_count > 0:
                      ds_summary = self.ds.summarise()
            data["drift_headline"] = {
                              "total": ds_summary.total_signals,
                              "red": ds_summary.by_severity.get("red", 0),
                              "recurring": len(ds_summary.top_recurring),
            }

        # Confidence: STATUS is always answerable if scorer runs
        confidence = min(report.overall_score / 100, 1.0)
        summary = " ".join(parts)

        return IRISResponse(
                      query_id=query_id,
                      query_type=query.query_type,
                      status=ResolutionStatus.RESOLVED,
                      summary=summary,
                      data=data,
                      provenance_chain=provenance,
                      confidence=round(confidence, 3),
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _make_query_id(query: IRISQuery) -> str:
              """Generate a deterministic, short query id."""
        payload = json.dumps({
                      "type": query.query_type.value,
                      "episode_id": query.episode_id,
                      "text": query.text,
                      "ts": time.time(),
        }, sort_keys=True, default=str)
        digest = hashlib.sha256(payload.encode()).hexdigest()[:12]
        return f"iris-{digest}"

    @staticmethod
    def _error_response(
              query_id: str,
              query_type: QueryType,
              message: str,
    ) -> IRISResponse:
              """Build a standard error response."""
        return IRISResponse(
                      query_id=query_id,
                      query_type=query_type,
                      status=ResolutionStatus.ERROR,
                      summary=message,
        )

    @staticmethod
    def _not_found_response(
              query_id: str,
              query_type: QueryType,
              message: str,
    ) -> IRISResponse:
              """Build a standard not-found response."""
        return IRISResponse(
                      query_id=query_id,
                      query_type=query_type,
                      status=ResolutionStatus.NOT_FOUND,
                      summary=message,
        )
