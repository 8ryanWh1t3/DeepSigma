"""AgentSession — stateful decision logging for AI agents.

Provides the primary integration surface for the "AI agent decision
logging" wedge.  Accepts simplified decision dicts, internally builds
full sealed episodes, and maintains a coherence pipeline (DLR/RS/DS/MG)
across the session lifetime.

Usage::

    from core import AgentSession

    session = AgentSession("fraud-detector-v3")
    sealed = session.log_decision({
        "action": "quarantine_account",
        "reason": "Suspicious activity detected",
        "actor": {"type": "agent", "id": "fraud-detector-v3"},
        "targets": ["acc-12345"],
        "evidence": ["alert-789"],
        "confidence": 0.92,
    })
    report = session.score()
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .decision_log import DLRBuilder
from .drift_signal import DriftSignalCollector
from .memory_graph import MemoryGraph
from .reflection import ReflectionSession
from .scoring import CoherenceScorer

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _hash_canonical(data: dict) -> str:
    """SHA-256 hash of canonical JSON."""
    raw = json.dumps(data, sort_keys=True, separators=(",", ":"))
    return f"sha256:{hashlib.sha256(raw.encode()).hexdigest()}"


class AgentSession:
    """Stateful session for AI agent decision logging.

    Maintains a running coherence pipeline (DLR, RS, DS, MG) and
    provides methods to log decisions, detect drift, audit, and score.

    Parameters
    ----------
    agent_id
        Unique identifier for the agent.
    storage_dir
        Optional directory for JSON persistence.  When set, episodes
        and drift events are written to disk and reloaded on init.
    """

    def __init__(
        self,
        agent_id: str,
        storage_dir: Optional[str | Path] = None,
        authority_ledger: Optional[str | Path] = None,
    ) -> None:
        self.agent_id = agent_id
        self._episodes: List[Dict[str, Any]] = []
        self._drift_events: List[Dict[str, Any]] = []
        self._counter = 0

        self._storage_dir: Optional[Path] = None
        if storage_dir is not None:
            self._storage_dir = Path(storage_dir)
            self._storage_dir.mkdir(parents=True, exist_ok=True)
            self._load_from_disk()

        self._authority_ledger = None
        if authority_ledger is not None:
            from .authority import AuthorityLedger
            self._authority_ledger = AuthorityLedger(
                path=Path(authority_ledger)
            )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def log_decision(self, decision: Dict[str, Any]) -> Dict[str, Any]:
        """Log a single decision.  Returns the sealed episode dict.

        Accepts a simplified decision format::

            {
                "action": "quarantine_account",
                "reason": "Suspicious activity detected",
                "actor": {"type": "agent", "id": "my-agent"},
                "targets": ["acc-12345"],
                "evidence": ["alert-789"],
                "confidence": 0.92,
            }

        Or a full episode dict (auto-detected by ``episodeId`` key).
        """
        if "episodeId" in decision or "episode_id" in decision:
            episode = decision
        else:
            episode = self._build_episode(decision)

        self._episodes.append(episode)
        self._persist_episode(episode)
        return episode

    def detect_drift(
        self,
        decision: Dict[str, Any],
        baseline_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Compare a new decision against the session baseline.

        Returns a list of drift signal dicts (may be empty).
        """
        episode = self.log_decision(decision)
        ep_id = episode.get("episodeId", "")

        signals: List[Dict[str, Any]] = []

        if not baseline_id and len(self._episodes) >= 2:
            baseline = self._episodes[-2]
        elif baseline_id:
            baseline = next(
                (e for e in self._episodes if e.get("episodeId") == baseline_id),
                None,
            )
        else:
            return signals

        if baseline is None:
            return signals

        # Compare outcome codes
        base_outcome = baseline.get("outcome", {}).get("code", "")
        new_outcome = episode.get("outcome", {}).get("code", "")
        if base_outcome and new_outcome and base_outcome != new_outcome:
            drift = self._build_drift(
                ep_id, "outcome", "yellow",
                f"Outcome changed: {base_outcome} -> {new_outcome}",
            )
            signals.append(drift)
            self._drift_events.append(drift)

        # Compare decision type
        base_type = baseline.get("decisionType", "")
        new_type = episode.get("decisionType", "")
        if base_type and new_type and base_type != new_type:
            drift = self._build_drift(
                ep_id, "contention", "red",
                f"Decision type changed: {base_type} -> {new_type}",
            )
            signals.append(drift)
            self._drift_events.append(drift)

        # Compare confidence
        base_conf = baseline.get("context", {}).get("confidence")
        new_conf = episode.get("context", {}).get("confidence")
        if base_conf is not None and new_conf is not None:
            delta = abs(float(new_conf) - float(base_conf))
            if delta > 0.2:
                sev = "red" if delta > 0.4 else "yellow"
                drift = self._build_drift(
                    ep_id, "freshness", sev,
                    f"Confidence shifted by {delta:.2f}",
                )
                signals.append(drift)
                self._drift_events.append(drift)

        return signals

    def audit(self) -> Dict[str, Any]:
        """Run a coherence audit on all logged decisions."""
        from .audit import CoherenceAuditor
        from .manifest import ArtifactDeclaration, ArtifactKind, ComplianceLevel, CoherenceManifest

        dlr, rs, ds, mg = self._build_pipeline()

        manifest = CoherenceManifest(
            system_id=f"agent:{self.agent_id}", version="1.0.0",
        )
        for kind in ArtifactKind:
            manifest.declare(ArtifactDeclaration(
                kind=kind,
                schema_version="1.0.0",
                compliance=ComplianceLevel.FULL,
                source=f"agent:{self.agent_id}",
            ))

        auditor = CoherenceAuditor(
            manifest=manifest, dlr_builder=dlr, rs=rs, ds=ds, mg=mg,
        )
        report = auditor.run(audit_id=f"agent-audit-{self.agent_id}")
        return asdict(report)

    def score(self) -> Dict[str, Any]:
        """Compute the coherence score for this session."""
        dlr, rs, ds, mg = self._build_pipeline()
        scorer = CoherenceScorer(dlr_builder=dlr, rs=rs, ds=ds, mg=mg)
        report = scorer.score()
        return asdict(report)

    def prove(self, episode_id: str) -> Dict[str, Any]:
        """Export the provenance chain for a specific decision."""
        episode = next(
            (e for e in self._episodes if e.get("episodeId") == episode_id),
            None,
        )
        if episode is None:
            return {"error": f"Episode {episode_id} not found"}

        _, _, _, mg = self._build_pipeline()

        # Collect connected drift and patches from MG
        related_drift = [
            d for d in self._drift_events
            if d.get("episodeId") == episode_id
        ]

        return {
            "episodeId": episode_id,
            "decisionType": episode.get("decisionType", ""),
            "sealedAt": episode.get("sealedAt", ""),
            "seal": episode.get("seal", {}),
            "actor": episode.get("actor", {}),
            "actions": episode.get("actions", []),
            "outcome": episode.get("outcome", {}),
            "drift_signals": related_drift,
            "memory_graph_nodes": mg.node_count,
            "memory_graph_edges": mg.edge_count,
        }

    def export(self, format: str = "json") -> str:
        """Export all session data."""
        data = {
            "agent_id": self.agent_id,
            "episode_count": len(self._episodes),
            "drift_count": len(self._drift_events),
            "episodes": self._episodes,
            "drift_events": self._drift_events,
        }
        if format == "json":
            return json.dumps(data, indent=2, default=str)
        raise ValueError(f"Unsupported format: {format}")

    # ------------------------------------------------------------------
    # Authority API
    # ------------------------------------------------------------------

    def grant_authority(self, grant: Dict[str, Any]) -> Dict[str, Any]:
        """Append an authority grant and return the entry as dict."""
        if self._authority_ledger is None:
            return {"error": "No authority ledger configured"}
        from .authority import AuthorityEntry
        entry = AuthorityEntry(
            entry_id=grant.get("entry_id", ""),
            entry_type="grant",
            authority_source=grant.get(
                "authority_source", f"agent:{self.agent_id}"
            ),
            authority_role=grant.get("authority_role", "agent"),
            scope=grant.get("scope", "session"),
            claims_blessed=grant.get("claims_blessed", []),
            effective_at=grant.get("effective_at", _now_iso()),
            expires_at=grant.get("expires_at"),
            entry_hash="",
            prev_entry_hash=None,
        )
        self._authority_ledger.append(entry)
        return asdict(entry)

    def verify_authority(self) -> Dict[str, Any]:
        """Verify authority chain and return snapshot."""
        if self._authority_ledger is None:
            return {"error": "No authority ledger configured"}
        valid = self._authority_ledger.verify_chain()
        snapshot = self._authority_ledger.snapshot()
        return {**snapshot, "chain_valid": valid}

    def prove_claim_authority(
        self, claim_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Prove authority for a specific claim."""
        if self._authority_ledger is None:
            return {"error": "No authority ledger configured"}
        return self._authority_ledger.prove_authority(claim_id)

    # ------------------------------------------------------------------
    # Claims API
    # ------------------------------------------------------------------

    def submit_claims(
        self,
        claims: List[Dict[str, Any]],
        episode_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Submit claims through the ClaimTriggerPipeline.

        Uses the session's MG/DS pipeline and authority ledger.
        Extends ``_drift_events`` with any generated drift signals.
        """
        from .feeds.consumers.claim_trigger import ClaimTriggerPipeline

        _, _, ds, mg = self._build_pipeline()

        pipeline = ClaimTriggerPipeline(
            mg=mg,
            ds=ds,
            authority_ledger=self._authority_ledger,
        )
        result = pipeline.submit(claims, episode_id=episode_id)

        # Collect drift signals back into session state
        for r in result.results:
            self._drift_events.extend(r.drift_signals)

        return {
            "submitted": result.submitted,
            "accepted": result.accepted,
            "rejected": result.rejected,
            "drift_signals_emitted": result.drift_signals_emitted,
            "results": [
                {
                    "claim_id": r.claim_id,
                    "accepted": r.accepted,
                    "issues": r.issues,
                    "graph_node_id": r.graph_node_id,
                }
                for r in result.results
            ],
        }

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _next_id(self, prefix: str) -> str:
        self._counter += 1
        return f"{prefix}-{self.agent_id}-{self._counter:04d}"

    def _build_episode(self, decision: Dict[str, Any]) -> Dict[str, Any]:
        """Convert a simplified decision dict into a full episode."""
        ep_id = self._next_id("ep")
        now = _now_iso()

        actor = decision.get("actor", {"type": "agent", "id": self.agent_id})
        action_type = decision.get("action", "unknown")
        targets = decision.get("targets", [])
        evidence = decision.get("evidence", [])
        confidence = decision.get("confidence")
        reason = decision.get("reason", "")
        decision_type = decision.get("decision_type", action_type)

        episode = {
            "episodeId": ep_id,
            "decisionType": decision_type,
            "startedAt": now,
            "endedAt": now,
            "actions": [{
                "type": action_type,
                "blastRadiusTier": "account",
                "idempotencyKey": f"ik-{ep_id}",
                "targetRefs": targets,
            }],
            "context": {
                "evidenceRefs": evidence,
                "ttlMs": 1000,
                "maxFeatureAgeMs": 500,
                "ttlBreachesCount": 0,
            },
            "outcome": {"code": "success"},
            "degrade": {"step": "none"},
            "verification": {"result": "pass"},
            "telemetry": {
                "endToEndMs": 50,
                "stageMs": {"context": 10, "plan": 10, "act": 15, "verify": 15},
                "p95Ms": 100, "p99Ms": 120, "jitterMs": 5,
                "fallbackUsed": False, "fallbackStep": "none",
                "hopCount": 1, "fanout": 1,
            },
            "seal": {
                "sealHash": _hash_canonical({
                    "episodeId": ep_id,
                    "action": action_type,
                    "actor": actor,
                }),
                "sealedAt": now,
            },
            "sealedAt": now,
            "actor": actor,
            "dteRef": {"decisionType": decision_type, "version": "1.0"},
            "plan": {"planner": "agent", "summary": reason},
            "decisionWindowMs": 120,
        }

        if confidence is not None:
            episode["context"]["confidence"] = confidence

        return episode

    def _build_drift(
        self, episode_id: str, drift_type: str, severity: str, notes: str,
    ) -> Dict[str, Any]:
        """Build a drift signal dict."""
        drift_id = self._next_id("drift")
        return {
            "driftId": drift_id,
            "episodeId": episode_id,
            "driftType": drift_type,
            "severity": severity,
            "detectedAt": _now_iso(),
            "fingerprint": {"key": f"{drift_type}:{episode_id}"},
            "recommendedPatchType": "manual_review",
            "notes": notes,
        }

    def _build_pipeline(self):
        """Build the full coherence pipeline from session data."""
        dlr = DLRBuilder()
        if self._episodes:
            dlr.from_episodes(self._episodes)

        rs = ReflectionSession(f"agent-{self.agent_id}")
        if self._episodes:
            rs.ingest(self._episodes)

        ds = DriftSignalCollector()
        if self._drift_events:
            ds.ingest(self._drift_events)

        mg = MemoryGraph()
        for ep in self._episodes:
            mg.add_episode(ep)
        for d in self._drift_events:
            mg.add_drift(d)

        return dlr, rs, ds, mg

    def _persist_episode(self, episode: Dict[str, Any]) -> None:
        """Write episode to storage dir if configured."""
        if self._storage_dir is None:
            return
        ep_id = episode.get("episodeId", "unknown")
        path = self._storage_dir / f"{ep_id}.json"
        path.write_text(json.dumps(episode, indent=2, default=str) + "\n")

    def _load_from_disk(self) -> None:
        """Load persisted episodes from storage dir."""
        if self._storage_dir is None:
            return
        for f in sorted(self._storage_dir.glob("ep-*.json")):
            try:
                ep = json.loads(f.read_text())
                self._episodes.append(ep)
                self._counter = max(self._counter, len(self._episodes))
            except (json.JSONDecodeError, OSError):
                logger.warning("Failed to load %s", f)
