"""ReflectionOps domain mode — gate enforcement and episode completeness.

Wraps RuntimeGate, CoherenceGate, ReflectionSession, IRISEngine, degrade
ladder, episode state machine, audit log, and kill-switch into 12 function
handlers keyed by RE-F01 through RE-F12.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .base import DomainMode, FunctionResult


class ReflectionOps(DomainMode):
    """ReflectionOps domain: episodes, gates, severity, audit, and kill-switch."""

    domain = "reflectionops"

    def _register_handlers(self) -> None:
        self._handlers = {
            "RE-F01": self._episode_begin,
            "RE-F02": self._episode_seal,
            "RE-F03": self._episode_archive,
            "RE-F04": self._gate_evaluate,
            "RE-F05": self._gate_degrade,
            "RE-F06": self._gate_killswitch,
            "RE-F07": self._audit_non_coercion,
            "RE-F08": self._severity_score,
            "RE-F09": self._coherence_check,
            "RE-F10": self._reflection_ingest,
            "RE-F11": self._iris_resolve,
            "RE-F12": self._episode_replay,
        }

    # ── RE-F01: Episode Begin ────────────────────────────────────

    def _episode_begin(
        self, event: Dict[str, Any], ctx: Dict[str, Any],
    ) -> FunctionResult:
        """Begin a new decision episode, transition to ACTIVE."""
        payload = event.get("payload", event)
        episode_id = payload.get("episodeId", f"EP-{uuid.uuid4().hex[:8]}")
        decision_type = payload.get("decisionType", "unknown")

        tracker = ctx.get("episode_tracker")
        mg = ctx.get("memory_graph")
        mg_updates: List[str] = []

        if tracker is not None:
            from core.episode_state import EpisodeState
            tracker.set_state(episode_id, EpisodeState.PENDING)
            tracker.transition(episode_id, EpisodeState.ACTIVE)

        if mg is not None:
            nid = mg.add_episode({
                "episodeId": episode_id,
                "decisionType": decision_type,
                "startedAt": datetime.now(timezone.utc).isoformat(),
            })
            if nid:
                mg_updates.append(nid)

        return FunctionResult(
            function_id="RE-F01",
            success=True,
            events_emitted=[{
                "topic": "decision_lineage",
                "subtype": "episode_active",
                "episodeId": episode_id,
                "decisionType": decision_type,
            }],
            mg_updates=mg_updates,
        )

    # ── RE-F02: Episode Seal ─────────────────────────────────────

    def _episode_seal(
        self, event: Dict[str, Any], ctx: Dict[str, Any],
    ) -> FunctionResult:
        """Seal an active episode with hash chain."""
        payload = event.get("payload", event)
        episode_id = payload.get("episodeId", "")

        tracker = ctx.get("episode_tracker")
        audit_log = ctx.get("audit_log")

        if tracker is not None:
            from core.episode_state import EpisodeState
            ok = tracker.transition(episode_id, EpisodeState.SEALED)
            if not ok:
                return FunctionResult(
                    function_id="RE-F02",
                    success=True,
                    events_emitted=[],
                    drift_signals=[{
                        "driftId": f"DS-seal-{uuid.uuid4().hex[:8]}",
                        "driftType": "process_gap",
                        "severity": "yellow",
                        "detectedAt": datetime.now(timezone.utc).isoformat(),
                        "notes": f"Cannot seal {episode_id}: not in ACTIVE state",
                        "fingerprint": {"key": f"seal-fail:{episode_id}", "version": "1"},
                    }],
                )

        # Compute seal hash
        seal_content = json.dumps({
            "episodeId": episode_id,
            "sealedAt": datetime.now(timezone.utc).isoformat(),
        }, sort_keys=True, separators=(",", ":"))
        seal_hash = f"sha256:{hashlib.sha256(seal_content.encode('utf-8')).hexdigest()}"

        if audit_log is not None:
            from core.audit_log import AuditEntry
            audit_log.append(AuditEntry(
                entry_type="episode_sealed",
                episode_id=episode_id,
                function_id="RE-F02",
                detail=f"Episode {episode_id} sealed",
            ))

        return FunctionResult(
            function_id="RE-F02",
            success=True,
            events_emitted=[{
                "topic": "decision_lineage",
                "subtype": "episode_sealed",
                "episodeId": episode_id,
                "sealHash": seal_hash,
            }],
        )

    # ── RE-F03: Episode Archive ──────────────────────────────────

    def _episode_archive(
        self, event: Dict[str, Any], ctx: Dict[str, Any],
    ) -> FunctionResult:
        """Archive a sealed episode to cold storage."""
        payload = event.get("payload", event)
        episode_id = payload.get("episodeId", "")

        tracker = ctx.get("episode_tracker")

        if tracker is not None:
            from core.episode_state import EpisodeState
            ok = tracker.transition(episode_id, EpisodeState.ARCHIVED)
            if not ok:
                return FunctionResult(
                    function_id="RE-F03",
                    success=True,
                    events_emitted=[],
                    drift_signals=[{
                        "driftId": f"DS-archive-{uuid.uuid4().hex[:8]}",
                        "driftType": "process_gap",
                        "severity": "yellow",
                        "detectedAt": datetime.now(timezone.utc).isoformat(),
                        "notes": f"Cannot archive {episode_id}: not in SEALED state",
                        "fingerprint": {"key": f"archive-fail:{episode_id}", "version": "1"},
                    }],
                )

        return FunctionResult(
            function_id="RE-F03",
            success=True,
            events_emitted=[{
                "topic": "decision_lineage",
                "subtype": "episode_archived",
                "episodeId": episode_id,
            }],
        )

    # ── RE-F04: Gate Evaluate ────────────────────────────────────

    def _gate_evaluate(
        self, event: Dict[str, Any], ctx: Dict[str, Any],
    ) -> FunctionResult:
        """Evaluate RuntimeGate constraints."""
        payload = event.get("payload", event)
        episode_id = payload.get("episodeId", "")
        gate_context = payload.get("gateContext", {})
        audit_log = ctx.get("audit_log")

        # Gate evaluation: use gates from context or simple pass
        gates = ctx.get("gates", [])
        drift_signals: List[Dict[str, Any]] = []

        passed = True
        for gate in gates:
            gate_type = gate.get("type", "")
            threshold = gate.get("threshold", 0)
            value = gate_context.get(gate_type, 0)

            if isinstance(value, (int, float)) and isinstance(threshold, (int, float)):
                if value > threshold:
                    passed = False
                    drift_signals.append({
                        "driftId": f"DS-gate-{uuid.uuid4().hex[:8]}",
                        "driftType": "process_gap",
                        "severity": "yellow",
                        "detectedAt": datetime.now(timezone.utc).isoformat(),
                        "notes": f"Gate {gate_type} failed: {value} > {threshold}",
                        "fingerprint": {"key": f"gate:{episode_id}:{gate_type}", "version": "1"},
                    })

        if audit_log is not None:
            from core.audit_log import AuditEntry
            audit_log.append(AuditEntry(
                entry_type="gate_evaluated",
                episode_id=episode_id,
                function_id="RE-F04",
                detail=f"Gate evaluation: {'pass' if passed else 'deny'}",
            ))

        subtype = "gate_pass" if passed else "gate_deny"
        return FunctionResult(
            function_id="RE-F04",
            success=True,
            events_emitted=[{
                "topic": "drift_signal",
                "subtype": subtype,
                "episodeId": episode_id,
            }],
            drift_signals=drift_signals,
        )

    # ── RE-F05: Gate Degrade ─────────────────────────────────────

    def _gate_degrade(
        self, event: Dict[str, Any], ctx: Dict[str, Any],
    ) -> FunctionResult:
        """Apply a degrade step from the degrade ladder."""
        payload = event.get("payload", event)
        episode_id = payload.get("episodeId", "")
        degrade_step = payload.get("degradeStep", "none")
        audit_log = ctx.get("audit_log")

        if audit_log is not None:
            from core.audit_log import AuditEntry
            audit_log.append(AuditEntry(
                entry_type="degrade_applied",
                episode_id=episode_id,
                function_id="RE-F05",
                detail=f"Degrade step: {degrade_step}",
            ))

        return FunctionResult(
            function_id="RE-F05",
            success=True,
            events_emitted=[{
                "topic": "decision_lineage",
                "subtype": "degrade_applied",
                "episodeId": episode_id,
                "degradeStep": degrade_step,
            }],
        )

    # ── RE-F06: Gate Kill-Switch ─────────────────────────────────

    def _gate_killswitch(
        self, event: Dict[str, Any], ctx: Dict[str, Any],
    ) -> FunctionResult:
        """Activate kill-switch: freeze all episodes."""
        payload = event.get("payload", event)
        authorized_by = payload.get("authorizedBy", "system")
        reason = payload.get("reason", "unspecified")

        tracker = ctx.get("episode_tracker")
        audit_log = ctx.get("audit_log")

        from core.killswitch import activate_killswitch
        from core.episode_state import EpisodeTracker

        if tracker is None:
            tracker = EpisodeTracker()

        halt_proof = activate_killswitch(
            tracker=tracker,
            authorized_by=authorized_by,
            reason=reason,
            audit_log=audit_log,
        )

        return FunctionResult(
            function_id="RE-F06",
            success=True,
            events_emitted=[
                {
                    "topic": "drift_signal",
                    "subtype": "killswitch_activated",
                    "severity": "red",
                    **halt_proof,
                },
                {
                    "topic": "decision_lineage",
                    "subtype": "episodes_frozen",
                    "frozenCount": halt_proof["frozenCount"],
                },
            ],
        )

    # ── RE-F07: Audit Non-Coercion ───────────────────────────────

    def _audit_non_coercion(
        self, event: Dict[str, Any], ctx: Dict[str, Any],
    ) -> FunctionResult:
        """Log non-coercion attestation."""
        payload = event.get("payload", event)
        episode_id = payload.get("episodeId", "")
        attestation = payload.get("attestation", "Agent acted without coercion.")
        audit_log = ctx.get("audit_log")

        chain_hash = ""
        if audit_log is not None:
            from core.audit_log import AuditEntry
            chain_hash = audit_log.append(AuditEntry(
                entry_type="non_coercion_attestation",
                episode_id=episode_id,
                function_id="RE-F07",
                detail=attestation,
                actor=payload.get("actor", "agent"),
            ))

        return FunctionResult(
            function_id="RE-F07",
            success=True,
            events_emitted=[{
                "topic": "decision_lineage",
                "subtype": "non_coercion_attested",
                "episodeId": episode_id,
                "chainHash": chain_hash,
            }],
        )

    # ── RE-F08: Severity Score ───────────────────────────────────

    def _severity_score(
        self, event: Dict[str, Any], ctx: Dict[str, Any],
    ) -> FunctionResult:
        """Compute centralized severity score."""
        payload = event.get("payload", event)
        drift_type = payload.get("driftType", "process_gap")
        severity = payload.get("severity", "yellow")

        from core.severity import compute_severity_score, classify_severity

        score = compute_severity_score(
            drift_type, severity,
            context={"recurrence_count": payload.get("recurrenceCount", 0)},
        )
        classification = classify_severity(score)

        return FunctionResult(
            function_id="RE-F08",
            success=True,
            events_emitted=[{
                "topic": "drift_signal",
                "subtype": "severity_scored",
                "driftType": drift_type,
                "inputSeverity": severity,
                "computedScore": score,
                "classification": classification,
            }],
        )

    # ── RE-F09: Coherence Check ──────────────────────────────────

    def _coherence_check(
        self, event: Dict[str, Any], ctx: Dict[str, Any],
    ) -> FunctionResult:
        """Run coherence gate evaluation with domain context."""
        payload = event.get("payload", event)
        episode_id = payload.get("episodeId", "")

        mg = ctx.get("memory_graph")
        ds = ctx.get("drift_collector")
        coherence_score = ctx.get("coherence_score")

        # Use provided score or compute a simple one from context
        if coherence_score is None:
            # Simple heuristic: based on drift signal count
            signal_count = ds.event_count if ds is not None else 0
            if signal_count == 0:
                coherence_score = 95.0
            elif signal_count <= 3:
                coherence_score = 70.0
            else:
                coherence_score = 40.0

        if coherence_score >= 80:
            signal = "green"
        elif coherence_score >= 50:
            signal = "yellow"
        else:
            signal = "red"

        subtype = f"coherence_{signal}"
        drift_signals: List[Dict[str, Any]] = []

        if signal != "green":
            drift_signals.append({
                "driftId": f"DS-coherence-{uuid.uuid4().hex[:8]}",
                "driftType": "process_gap",
                "severity": signal,
                "detectedAt": datetime.now(timezone.utc).isoformat(),
                "notes": f"Coherence score {coherence_score:.0f} ({signal})",
                "fingerprint": {"key": f"coherence:{episode_id}", "version": "1"},
            })

        return FunctionResult(
            function_id="RE-F09",
            success=True,
            events_emitted=[{
                "topic": "drift_signal",
                "subtype": subtype,
                "episodeId": episode_id,
                "coherenceScore": coherence_score,
                "signal": signal,
            }],
            drift_signals=drift_signals,
        )

    # ── RE-F10: Reflection Ingest ────────────────────────────────

    def _reflection_ingest(
        self, event: Dict[str, Any], ctx: Dict[str, Any],
    ) -> FunctionResult:
        """Ingest a sealed episode into the reflection session."""
        payload = event.get("payload", event)
        episode_id = payload.get("episodeId", "")
        episode_data = payload.get("episodeData", payload)

        rs = ctx.get("reflection_session")
        if rs is not None:
            rs.ingest([episode_data])

        return FunctionResult(
            function_id="RE-F10",
            success=True,
            events_emitted=[{
                "topic": "decision_lineage",
                "subtype": "reflection_ingested",
                "episodeId": episode_id,
            }],
        )

    # ── RE-F11: IRIS Resolve ─────────────────────────────────────

    def _iris_resolve(
        self, event: Dict[str, Any], ctx: Dict[str, Any],
    ) -> FunctionResult:
        """Resolve an IRIS query."""
        payload = event.get("payload", event)
        query_type = payload.get("queryType", "STATUS")
        query_text = payload.get("text", "")
        episode_id = payload.get("episodeId", "")

        iris = ctx.get("iris_engine")
        response_data: Dict[str, Any] = {}

        if iris is not None:
            from core.iris import IRISQuery
            query = IRISQuery(
                query_type=query_type,
                text=query_text,
                episode_id=episode_id,
            )
            response = iris.resolve(query)
            response_data = {
                "queryId": response.query_id,
                "status": response.status.value if hasattr(response.status, 'value') else str(response.status),
                "summary": response.summary,
                "confidence": response.confidence,
            }
        else:
            response_data = {
                "queryId": f"IRIS-{uuid.uuid4().hex[:8]}",
                "status": "resolved",
                "summary": f"No IRIS engine configured; query type={query_type}",
                "confidence": 0.0,
            }

        return FunctionResult(
            function_id="RE-F11",
            success=True,
            events_emitted=[{
                "topic": "decision_lineage",
                "subtype": "iris_response",
                "queryType": query_type,
                **response_data,
            }],
        )

    # ── RE-F12: Episode Replay ───────────────────────────────────

    def _episode_replay(
        self, event: Dict[str, Any], ctx: Dict[str, Any],
    ) -> FunctionResult:
        """Deterministically replay a sealed episode and verify hash match."""
        payload = event.get("payload", event)
        episode_id = payload.get("episodeId", "")
        expected_hash = payload.get("expectedHash", "")
        replay_data = payload.get("replayData", {})
        audit_log = ctx.get("audit_log")

        # Compute replay hash from episode data
        canonical = json.dumps(
            {"episodeId": episode_id, **replay_data},
            sort_keys=True, separators=(",", ":"),
        )
        actual_hash = f"sha256:{hashlib.sha256(canonical.encode('utf-8')).hexdigest()}"
        matched = actual_hash == expected_hash

        if audit_log is not None:
            from core.audit_log import AuditEntry
            audit_log.append(AuditEntry(
                entry_type="episode_replay",
                episode_id=episode_id,
                function_id="RE-F12",
                detail=f"Replay {'pass' if matched else 'fail'}: expected={expected_hash}, actual={actual_hash}",
            ))

        subtype = "replay_pass" if matched else "replay_fail"
        drift_signals: List[Dict[str, Any]] = []
        if not matched:
            drift_signals.append({
                "driftId": f"DS-replay-{uuid.uuid4().hex[:8]}",
                "driftType": "process_gap",
                "severity": "red",
                "detectedAt": datetime.now(timezone.utc).isoformat(),
                "notes": f"Replay mismatch for {episode_id}",
                "fingerprint": {"key": f"replay:{episode_id}", "version": "1"},
            })

        return FunctionResult(
            function_id="RE-F12",
            success=True,
            events_emitted=[{
                "topic": "decision_lineage",
                "subtype": subtype,
                "episodeId": episode_id,
                "expectedHash": expected_hash,
                "actualHash": actual_hash,
                "matched": matched,
            }],
            drift_signals=drift_signals,
        )
