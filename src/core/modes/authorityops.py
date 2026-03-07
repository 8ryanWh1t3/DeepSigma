"""AuthorityOps domain mode — authority, policy, and governance enforcement.

Wraps authority graph, policy compiler, policy runtime, reasoning gate,
delegation chain, audit, drift detection, and blast radius simulation into
19 function handlers keyed by AUTH-F01 through AUTH-F19.

The governance loop: intake → resolve → policy → evaluate → audit.
The drift loop: scan → detect → simulate impact → recommend action.

AuthorityOps is the cross-cutting governance layer that binds authority,
action, rationale, expiry, and audit into a single evaluable control plane.
It detects when those permissions themselves become unstable.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .base import DomainMode, FunctionResult


class AuthorityOps(DomainMode):
    """AuthorityOps domain: authority enforcement, policy evaluation, audit.

    Sits at: IntelOps → ReOps → AuthorityOps → Execution → FranOps
    """

    domain = "authorityops"

    def _register_handlers(self) -> None:
        self._handlers = {
            "AUTH-F01": self._action_request_intake,
            "AUTH-F02": self._actor_resolve,
            "AUTH-F03": self._resource_resolve,
            "AUTH-F04": self._policy_load,
            "AUTH-F05": self._dlr_presence_check,
            "AUTH-F06": self._assumption_validate,
            "AUTH-F07": self._half_life_check,
            "AUTH-F08": self._blast_radius_threshold,
            "AUTH-F09": self._kill_switch_check,
            "AUTH-F10": self._decision_gate,
            "AUTH-F11": self._audit_record_emit,
            "AUTH-F12": self._delegation_chain_validate,
            # Capability: Authority Drift Detection
            "AUTH-F13": self._authority_drift_scan,
            "AUTH-F14": self._delegation_health_monitor,
            "AUTH-F15": self._privilege_expiry_scan,
            "AUTH-F16": self._authority_integrity_check,
            # Capability: Authority Blast Radius Simulation
            "AUTH-F17": self._blast_radius_simulate,
            "AUTH-F18": self._trust_impact_calculate,
            "AUTH-F19": self._dependency_map,
        }

    # ── AUTH-F01: Action Request Intake ──────────────────────────

    def _action_request_intake(
        self, event: Dict[str, Any], ctx: Dict[str, Any],
    ) -> FunctionResult:
        """Validate action request and create an authority evaluation context."""
        payload = event.get("payload", event)
        action_id = payload.get("actionId", f"ACT-{uuid.uuid4().hex[:8]}")
        actor_id = payload.get("actorId", "")
        resource_ref = payload.get("resourceRef", "")
        episode_id = payload.get("episodeId", "")

        events: List[Dict[str, Any]] = []
        drift_signals: List[Dict[str, Any]] = []

        # Validate required fields
        missing = []
        if not actor_id:
            missing.append("actorId")
        if not resource_ref:
            missing.append("resourceRef")
        if not payload.get("actionType"):
            missing.append("actionType")

        if missing:
            drift_signals.append({
                "topic": "drift_signal",
                "subtype": "authority_intake_incomplete",
                "severity": "yellow",
                "driftType": "MISSING_MAPPING",
                "missingFields": missing,
                "actionId": action_id,
            })

        events.append({
            "topic": "authority_slice",
            "subtype": "authority_evaluation_started",
            "actionId": action_id,
            "actorId": actor_id,
            "resourceRef": resource_ref,
            "episodeId": episode_id,
        })

        return FunctionResult(
            function_id="AUTH-F01",
            success=True,
            events_emitted=events,
            drift_signals=drift_signals,
        )

    # ── AUTH-F02: Actor Resolution ───────────────────────────────

    def _actor_resolve(
        self, event: Dict[str, Any], ctx: Dict[str, Any],
    ) -> FunctionResult:
        """Resolve actor identity, roles, and delegation source."""
        from ..authority.authority_graph import resolve_actor

        payload = event.get("payload", event)
        actor_id = payload.get("actorId", "")
        events: List[Dict[str, Any]] = []
        drift_signals: List[Dict[str, Any]] = []
        mg_updates: List[str] = []

        actor = resolve_actor(actor_id, ctx)
        if actor is None:
            drift_signals.append({
                "topic": "drift_signal",
                "subtype": "actor_unknown",
                "severity": "yellow",
                "driftType": "MISSING_MAPPING",
                "actorId": actor_id,
            })
            events.append({
                "topic": "authority_slice",
                "subtype": "actor_unknown",
                "actorId": actor_id,
            })
        else:
            events.append({
                "topic": "authority_slice",
                "subtype": "actor_resolved",
                "actorId": actor.actor_id,
                "actorType": actor.actor_type,
                "roleCount": len(actor.roles),
            })

        return FunctionResult(
            function_id="AUTH-F02",
            success=True,
            events_emitted=events,
            drift_signals=drift_signals,
            mg_updates=mg_updates,
        )

    # ── AUTH-F03: Resource Resolution ────────────────────────────

    def _resource_resolve(
        self, event: Dict[str, Any], ctx: Dict[str, Any],
    ) -> FunctionResult:
        """Resolve resource classification and constraints."""
        from ..authority.authority_graph import resolve_resource

        payload = event.get("payload", event)
        resource_ref = payload.get("resourceRef", "")
        events: List[Dict[str, Any]] = []
        drift_signals: List[Dict[str, Any]] = []

        resource = resolve_resource(resource_ref, ctx)
        if resource is None:
            events.append({
                "topic": "authority_slice",
                "subtype": "resource_unknown",
                "resourceRef": resource_ref,
            })
        else:
            events.append({
                "topic": "authority_slice",
                "subtype": "resource_resolved",
                "resourceId": resource.resource_id,
                "resourceType": resource.resource_type,
                "classification": resource.classification,
            })

        return FunctionResult(
            function_id="AUTH-F03",
            success=True,
            events_emitted=events,
            drift_signals=drift_signals,
        )

    # ── AUTH-F04: Policy Load ────────────────────────────────────

    def _policy_load(
        self, event: Dict[str, Any], ctx: Dict[str, Any],
    ) -> FunctionResult:
        """Load and compile applicable policy pack."""
        from ..authority.policy_compiler import compile_policy, extract_constraints

        payload = event.get("payload", event)
        action_type = payload.get("actionType", "")
        policy_packs = ctx.get("policy_packs", {})
        events: List[Dict[str, Any]] = []

        policy = policy_packs.get(action_type, policy_packs.get("default"))
        if policy is None:
            events.append({
                "topic": "authority_slice",
                "subtype": "policy_missing",
                "actionType": action_type,
            })
        else:
            constraints = extract_constraints(policy, action_type)
            events.append({
                "topic": "authority_slice",
                "subtype": "policy_loaded",
                "policyPackId": policy.get("policyPackId", ""),
                "constraintCount": len(constraints),
            })

            # OpenPQL: if a PolicySource is provided, compile it
            policy_source = ctx.get("policy_source")
            if policy_source is not None:
                from ..authority.policy_compiler import compile_from_source
                compiled = compile_from_source(policy_source)
                ctx["_compiled"] = compiled

        return FunctionResult(
            function_id="AUTH-F04",
            success=True,
            events_emitted=events,
        )

    # ── AUTH-F05: DLR Presence Check ─────────────────────────────

    def _dlr_presence_check(
        self, event: Dict[str, Any], ctx: Dict[str, Any],
    ) -> FunctionResult:
        """Verify a DLR exists for this decision."""
        from ..authority.reasoning_gate import check_dlr_presence

        payload = event.get("payload", event)
        dlr_ref = payload.get("dlrRef", payload.get("episodeId", ""))
        events: List[Dict[str, Any]] = []

        present, detail = check_dlr_presence(dlr_ref, ctx)
        if present:
            events.append({
                "topic": "authority_slice",
                "subtype": "dlr_present",
                "dlrRef": dlr_ref,
                "detail": detail,
            })
        else:
            events.append({
                "topic": "authority_slice",
                "subtype": "dlr_missing",
                "dlrRef": dlr_ref,
                "detail": detail,
            })

        return FunctionResult(
            function_id="AUTH-F05",
            success=True,
            events_emitted=events,
        )

    # ── AUTH-F06: Assumption Validation ──────────────────────────

    def _assumption_validate(
        self, event: Dict[str, Any], ctx: Dict[str, Any],
    ) -> FunctionResult:
        """Check assumption freshness across referenced claims."""
        from ..authority.reasoning_gate import check_assumption_freshness

        payload = event.get("payload", event)
        claims = ctx.get("claims", payload.get("claims", []))
        now = ctx.get("now")
        events: List[Dict[str, Any]] = []
        drift_signals: List[Dict[str, Any]] = []

        fresh, stale = check_assumption_freshness(claims, now)
        if fresh:
            events.append({
                "topic": "drift_signal",
                "subtype": "assumptions_valid",
            })
        else:
            events.append({
                "topic": "drift_signal",
                "subtype": "assumptions_stale",
                "staleClaims": stale,
            })
            drift_signals.append({
                "topic": "drift_signal",
                "subtype": "assumptions_stale",
                "severity": "yellow",
                "driftType": "ASSUMPTION_EXPIRED",
                "staleClaims": stale,
            })

        return FunctionResult(
            function_id="AUTH-F06",
            success=True,
            events_emitted=events,
            drift_signals=drift_signals,
        )

    # ── AUTH-F07: Half-Life Check ────────────────────────────────

    def _half_life_check(
        self, event: Dict[str, Any], ctx: Dict[str, Any],
    ) -> FunctionResult:
        """Check claim half-lives for authority-scoped claims."""
        payload = event.get("payload", event)
        claims = ctx.get("claims", payload.get("claims", []))
        now = ctx.get("now", datetime.now(timezone.utc))
        if isinstance(now, str):
            now = datetime.fromisoformat(now.replace("Z", "+00:00"))
        events: List[Dict[str, Any]] = []
        drift_signals: List[Dict[str, Any]] = []

        expired_ids: List[str] = []
        for claim in claims:
            half_life = claim.get("halfLife", claim.get("half_life", {}))
            expires_at = half_life.get("expiresAt", half_life.get("expires_at"))
            if expires_at:
                try:
                    exp = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
                    if exp.tzinfo is None:
                        exp = exp.replace(tzinfo=timezone.utc)
                    if now >= exp:
                        cid = claim.get("claimId", claim.get("claim_id", "unknown"))
                        expired_ids.append(cid)
                except (ValueError, TypeError):
                    pass

        if expired_ids:
            events.append({
                "topic": "drift_signal",
                "subtype": "claims_expired",
                "expiredClaims": expired_ids,
            })
            drift_signals.append({
                "topic": "drift_signal",
                "subtype": "claims_expired",
                "severity": "yellow",
                "driftType": "STALE_LOGIC",
                "expiredClaims": expired_ids,
            })
        else:
            events.append({
                "topic": "drift_signal",
                "subtype": "claims_fresh",
            })

        return FunctionResult(
            function_id="AUTH-F07",
            success=True,
            events_emitted=events,
            drift_signals=drift_signals,
        )

    # ── AUTH-F08: Blast Radius Threshold ─────────────────────────

    def _blast_radius_threshold(
        self, event: Dict[str, Any], ctx: Dict[str, Any],
    ) -> FunctionResult:
        """Compare requested blast radius against policy maximum."""
        payload = event.get("payload", event)
        actual_br = payload.get("blastRadiusTier", "small")
        policy_packs = ctx.get("policy_packs", {})
        action_type = payload.get("actionType", "")
        policy = policy_packs.get(action_type, policy_packs.get("default", {}))
        max_br = policy.get("maxBlastRadius", "large")

        order = {"tiny": 0, "small": 1, "medium": 2, "large": 3}
        events: List[Dict[str, Any]] = []

        if order.get(actual_br, 1) > order.get(max_br, 3):
            events.append({
                "topic": "authority_slice",
                "subtype": "blast_radius_exceeded",
                "actual": actual_br,
                "max": max_br,
            })
        else:
            events.append({
                "topic": "authority_slice",
                "subtype": "blast_radius_ok",
                "actual": actual_br,
                "max": max_br,
            })

        return FunctionResult(
            function_id="AUTH-F08",
            success=True,
            events_emitted=events,
        )

    # ── AUTH-F09: Kill Switch Check ──────────────────────────────

    def _kill_switch_check(
        self, event: Dict[str, Any], ctx: Dict[str, Any],
    ) -> FunctionResult:
        """Check if kill-switch is active."""
        events: List[Dict[str, Any]] = []

        if ctx.get("kill_switch_active", False):
            events.append({
                "topic": "drift_signal",
                "subtype": "killswitch_active",
                "severity": "red",
            })
        else:
            events.append({
                "topic": "drift_signal",
                "subtype": "killswitch_clear",
            })

        return FunctionResult(
            function_id="AUTH-F09",
            success=True,
            events_emitted=events,
        )

    # ── AUTH-F10: Decision Gate ──────────────────────────────────

    def _decision_gate(
        self, event: Dict[str, Any], ctx: Dict[str, Any],
    ) -> FunctionResult:
        """Aggregate all checks and compute final verdict."""
        payload = event.get("payload", event)
        events: List[Dict[str, Any]] = []
        mg_updates: List[str] = []

        # OpenPQL: use RuntimeGate if a compiled artifact exists
        compiled = ctx.get("_compiled")
        if compiled is not None:
            from ..authority.runtime_gate import RuntimeGate
            gate = RuntimeGate()
            decision = gate.evaluate(compiled, payload, ctx)
            verdict = decision.verdict
            result = decision
        else:
            from ..authority.policy_runtime import evaluate
            result = evaluate(payload, ctx)
            verdict = result.verdict

        subtype_map = {
            "ALLOW": "authority_allow",
            "BLOCK": "authority_block",
            "ESCALATE": "authority_escalate",
            "EXPIRED": "authority_block",
            "MISSING_REASONING": "authority_block",
            "KILL_SWITCH_ACTIVE": "authority_block",
        }

        events.append({
            "topic": "authority_slice",
            "subtype": subtype_map.get(verdict, "authority_block"),
            "verdict": verdict,
            "gateId": result.gate_id,
            "passedChecks": result.passed_checks,
            "failedChecks": result.failed_checks,
        })

        # Record in MG
        mg = ctx.get("memory_graph")
        if mg is not None:
            eval_id = mg.add_policy_evaluation({
                "evaluation_id": result.gate_id,
                "verdict": verdict,
                "evaluated_at": result.evaluated_at,
                "policy_id": getattr(result, "policy_ref", getattr(result, "artifact_id", "")),
                "steps": [],
            })
            if eval_id:
                mg_updates.append(eval_id)

        return FunctionResult(
            function_id="AUTH-F10",
            success=True,
            events_emitted=events,
            mg_updates=mg_updates,
        )

    # ── AUTH-F11: Audit Record Emit ──────────────────────────────

    def _audit_record_emit(
        self, event: Dict[str, Any], ctx: Dict[str, Any],
    ) -> FunctionResult:
        """Create append-only audit record with hash chain."""
        from ..authority.authority_audit import AuthorityAuditLog
        from ..authority.models import AuditRecord

        payload = event.get("payload", event)
        events: List[Dict[str, Any]] = []
        mg_updates: List[str] = []

        audit_log = ctx.get("authority_audit")
        if audit_log is None:
            audit_log = AuthorityAuditLog()

        record = AuditRecord(
            audit_id=f"AUDIT-{uuid.uuid4().hex[:12]}",
            action_id=payload.get("actionId", ""),
            actor_id=payload.get("actorId", ""),
            resource_id=payload.get("resourceId", payload.get("resourceRef", "")),
            verdict=payload.get("verdict", "BLOCK"),
            evaluated_at=datetime.now(timezone.utc).isoformat(),
            policy_ref=payload.get("policyRef", ""),
            dlr_ref=payload.get("dlrRef"),
            failed_checks=payload.get("failedChecks", []),
            passed_checks=payload.get("passedChecks", []),
        )

        chain_hash = audit_log.append(record)

        events.append({
            "topic": "decision_lineage",
            "subtype": "authority_audited",
            "auditId": record.audit_id,
            "chainHash": chain_hash,
            "verdict": record.verdict,
        })

        # OpenPQL: also append to evidence chain if present
        evidence_chain = ctx.get("evidence_chain")
        if evidence_chain is not None:
            from ..authority.evidence_chain import EvidenceEntry
            compiled = ctx.get("_compiled")
            ev_entry = EvidenceEntry(
                evidence_id="",
                gate_id=payload.get("gateId", ""),
                action_id=record.action_id,
                actor_id=record.actor_id,
                resource_id=record.resource_id,
                verdict=record.verdict,
                evaluated_at=record.evaluated_at,
                artifact_id=compiled.artifact_id if compiled else "",
                policy_hash=compiled.policy_hash if compiled else "",
                dlr_ref=record.dlr_ref or "",
                failed_checks=record.failed_checks,
                passed_checks=record.passed_checks,
            )
            evidence_chain.append(ev_entry)

        # Write to MG
        mg = ctx.get("memory_graph")
        if mg is not None:
            from dataclasses import asdict
            node_id = mg.add_audit_record(asdict(record))
            if node_id:
                mg_updates.append(node_id)

        return FunctionResult(
            function_id="AUTH-F11",
            success=True,
            events_emitted=events,
            mg_updates=mg_updates,
        )

    # ── AUTH-F12: Delegation Chain Validate ──────────────────────

    def _delegation_chain_validate(
        self, event: Dict[str, Any], ctx: Dict[str, Any],
    ) -> FunctionResult:
        """Validate delegation chain for an actor."""
        from ..authority.delegation_chain import validate_chain
        from ..authority.models import Actor, Delegation

        payload = event.get("payload", event)
        actor_id = payload.get("actorId", "")
        events: List[Dict[str, Any]] = []
        drift_signals: List[Dict[str, Any]] = []
        mg_updates: List[str] = []

        # Build delegation chain from context
        raw_delegations = payload.get("delegations", ctx.get("delegations", []))
        delegations = [
            Delegation(
                delegation_id=d.get("delegationId", d.get("delegation_id", "")),
                from_actor_id=d.get("fromActorId", d.get("from_actor_id", "")),
                to_actor_id=d.get("toActorId", d.get("to_actor_id", "")),
                scope=d.get("scope", ""),
                max_depth=d.get("maxDepth", d.get("max_depth", 5)),
                effective_at=d.get("effectiveAt", d.get("effective_at", "")),
                expires_at=d.get("expiresAt", d.get("expires_at")),
                revoked_at=d.get("revokedAt", d.get("revoked_at")),
            )
            for d in raw_delegations
        ]

        actor = Actor(actor_id=actor_id, actor_type="agent")
        valid, issues = validate_chain(delegations, actor)

        if valid:
            events.append({
                "topic": "authority_slice",
                "subtype": "delegation_valid",
                "actorId": actor_id,
                "chainDepth": len(delegations),
            })
        else:
            events.append({
                "topic": "authority_slice",
                "subtype": "delegation_broken",
                "actorId": actor_id,
                "issues": issues,
            })
            drift_signals.append({
                "topic": "drift_signal",
                "subtype": "delegation_broken",
                "severity": "yellow",
                "driftType": "STALE_LOGIC",
                "actorId": actor_id,
                "issues": issues,
            })

        return FunctionResult(
            function_id="AUTH-F12",
            success=True,
            events_emitted=events,
            drift_signals=drift_signals,
            mg_updates=mg_updates,
        )

    # ── AUTH-F13: Authority Drift Scan ────────────────────────────

    def _authority_drift_scan(
        self, event: Dict[str, Any], ctx: Dict[str, Any],
    ) -> FunctionResult:
        """Master drift scan across all authority state."""
        from ..authority.authority_drift import scan_authority_drift
        from ..authority.authority_health import build_health_summary

        payload = event.get("payload", event)
        now = ctx.get("now", datetime.now(timezone.utc))
        if isinstance(now, str):
            now = datetime.fromisoformat(now.replace("Z", "+00:00"))
        events: List[Dict[str, Any]] = []
        drift_signals: List[Dict[str, Any]] = []
        mg_updates: List[str] = []

        signals = scan_authority_drift(
            actors=payload.get("actors", ctx.get("actors", [])),
            delegations=payload.get("delegations", ctx.get("delegations", [])),
            grants=payload.get("grants", ctx.get("grants", [])),
            revocations=payload.get("revocations", ctx.get("revocations", [])),
            policies=payload.get("policies", ctx.get("policies", [])),
            now=now,
        )
        drift_signals.extend(signals)

        summary = build_health_summary(signals)
        events.append({
            "topic": "drift_signal",
            "subtype": "authority_drift_signal",
            "signalCount": summary["signalCount"],
            "overallSeverity": summary["overallSeverity"],
        })

        mg = ctx.get("memory_graph")
        if mg is not None:
            for sig in signals:
                node_id = mg.add_drift(sig)
                if node_id:
                    mg_updates.append(node_id)

        return FunctionResult(
            function_id="AUTH-F13",
            success=True,
            events_emitted=events,
            drift_signals=drift_signals,
            mg_updates=mg_updates,
        )

    # ── AUTH-F14: Delegation Health Monitor ───────────────────────

    def _delegation_health_monitor(
        self, event: Dict[str, Any], ctx: Dict[str, Any],
    ) -> FunctionResult:
        """Focused delegation chain health check."""
        from ..authority.authority_drift import check_delegation_health

        payload = event.get("payload", event)
        now = ctx.get("now", datetime.now(timezone.utc))
        if isinstance(now, str):
            now = datetime.fromisoformat(now.replace("Z", "+00:00"))
        events: List[Dict[str, Any]] = []
        drift_signals: List[Dict[str, Any]] = []
        mg_updates: List[str] = []

        signals = check_delegation_health(
            delegations=payload.get("delegations", ctx.get("delegations", [])),
            actors=payload.get("actors", ctx.get("actors", [])),
            now=now,
        )
        drift_signals.extend(signals)

        events.append({
            "topic": "drift_signal",
            "subtype": "delegation_health_checked",
            "signalCount": len(signals),
        })

        mg = ctx.get("memory_graph")
        if mg is not None:
            for sig in signals:
                node_id = mg.add_drift(sig)
                if node_id:
                    mg_updates.append(node_id)

        return FunctionResult(
            function_id="AUTH-F14",
            success=True,
            events_emitted=events,
            drift_signals=drift_signals,
            mg_updates=mg_updates,
        )

    # ── AUTH-F15: Privilege Expiry Scanner ────────────────────────

    def _privilege_expiry_scan(
        self, event: Dict[str, Any], ctx: Dict[str, Any],
    ) -> FunctionResult:
        """Scan grants and delegations for expired or near-expiry privileges."""
        from ..authority.authority_drift import check_privilege_expiry

        payload = event.get("payload", event)
        now = ctx.get("now", datetime.now(timezone.utc))
        if isinstance(now, str):
            now = datetime.fromisoformat(now.replace("Z", "+00:00"))
        events: List[Dict[str, Any]] = []
        drift_signals: List[Dict[str, Any]] = []
        mg_updates: List[str] = []

        signals = check_privilege_expiry(
            grants=payload.get("grants", ctx.get("grants", [])),
            delegations=payload.get("delegations", ctx.get("delegations", [])),
            now=now,
        )
        drift_signals.extend(signals)

        events.append({
            "topic": "drift_signal",
            "subtype": "privilege_expiry_scanned",
            "signalCount": len(signals),
        })

        mg = ctx.get("memory_graph")
        if mg is not None:
            for sig in signals:
                node_id = mg.add_drift(sig)
                if node_id:
                    mg_updates.append(node_id)

        return FunctionResult(
            function_id="AUTH-F15",
            success=True,
            events_emitted=events,
            drift_signals=drift_signals,
            mg_updates=mg_updates,
        )

    # ── AUTH-F16: Authority Integrity Check ──────────────────────

    def _authority_integrity_check(
        self, event: Dict[str, Any], ctx: Dict[str, Any],
    ) -> FunctionResult:
        """Verify seal/hash/chain integrity."""
        from ..authority.authority_drift import check_authority_integrity

        payload = event.get("payload", event)
        events: List[Dict[str, Any]] = []
        drift_signals: List[Dict[str, Any]] = []
        mg_updates: List[str] = []

        signals = check_authority_integrity(
            ledger_snapshot=payload.get("ledgerSnapshot", ctx.get("ledger_snapshot", {})),
            grants=payload.get("grants", ctx.get("grants", [])),
            policies=payload.get("policies", ctx.get("policies", [])),
        )
        drift_signals.extend(signals)

        events.append({
            "topic": "drift_signal",
            "subtype": "authority_integrity_checked",
            "signalCount": len(signals),
        })

        mg = ctx.get("memory_graph")
        if mg is not None:
            for sig in signals:
                node_id = mg.add_drift(sig)
                if node_id:
                    mg_updates.append(node_id)

        return FunctionResult(
            function_id="AUTH-F16",
            success=True,
            events_emitted=events,
            drift_signals=drift_signals,
            mg_updates=mg_updates,
        )

    # ── AUTH-F17: Blast Radius Simulator ─────────────────────────

    def _blast_radius_simulate(
        self, event: Dict[str, Any], ctx: Dict[str, Any],
    ) -> FunctionResult:
        """Simulate blast radius for an authority entity change."""
        from ..authority.authority_blast_radius import simulate_blast_radius

        payload = event.get("payload", event)
        events: List[Dict[str, Any]] = []
        drift_signals: List[Dict[str, Any]] = []
        mg_updates: List[str] = []

        target_type = payload.get("targetType", "")
        target_id = payload.get("targetId", "")
        mg = ctx.get("memory_graph")

        result = simulate_blast_radius(target_type, target_id, mg, ctx)

        events.append({
            "topic": "authority_slice",
            "subtype": "authority_risk_propagated",
            "severity": result["severity"],
            "affectedClaimsCount": result["affectedClaimsCount"],
            "affectedDecisionsCount": result["affectedDecisionsCount"],
            "affectedAgentsCount": result["affectedAgentsCount"],
            "recommendedAction": result["recommendedAction"],
        })

        if result["severity"] in ("SEV-1", "SEV-2"):
            drift_signals.append({
                "topic": "drift_signal",
                "subtype": "authority_revocation_cascade",
                "severity": "red" if result["severity"] == "SEV-1" else "orange",
                "driftType": "authority_mismatch",
                "targetType": target_type,
                "targetId": target_id,
            })

        if result["severity"] == "SEV-1":
            events.append({
                "topic": "drift_signal",
                "subtype": "authority_lockdown_recommended",
                "targetId": target_id,
                "severity": "red",
            })

        return FunctionResult(
            function_id="AUTH-F17",
            success=True,
            events_emitted=events,
            drift_signals=drift_signals,
            mg_updates=mg_updates,
        )

    # ── AUTH-F18: Trust Impact Calculator ────────────────────────

    def _trust_impact_calculate(
        self, event: Dict[str, Any], ctx: Dict[str, Any],
    ) -> FunctionResult:
        """Compute severity from impact counts."""
        from ..authority.authority_blast_radius import (
            build_recommended_action,
            compute_impact_severity,
        )

        payload = event.get("payload", event)
        counts = {
            "claims": payload.get("affectedClaimsCount", 0),
            "episodes": payload.get("affectedDecisionsCount", 0),
            "canon_entries": payload.get("affectedCanonArtifactsCount", 0),
            "patches": payload.get("affectedPatchObjectsCount", 0),
            "actors": payload.get("affectedAgentsCount", 0),
        }
        severity = compute_impact_severity(
            affected_claims=counts["claims"],
            affected_decisions=counts["episodes"],
            affected_canon=counts["canon_entries"],
            affected_patches=counts["patches"],
            affected_agents=counts["actors"],
        )
        recommended = build_recommended_action(severity, counts)

        subtype = "trust_surface_degraded" if severity != "SEV-3" else "authority_risk_propagated"

        return FunctionResult(
            function_id="AUTH-F18",
            success=True,
            events_emitted=[{
                "topic": "authority_slice",
                "subtype": subtype,
                "severity": severity,
                "recommendedAction": recommended,
            }],
        )

    # ── AUTH-F19: Dependency Mapper ───────────────────────────────

    def _dependency_map(
        self, event: Dict[str, Any], ctx: Dict[str, Any],
    ) -> FunctionResult:
        """Walk memory graph to map authority dependencies."""
        from ..authority.dependency_map import (
            count_affected_by_kind,
            walk_authority_dependencies,
        )

        payload = event.get("payload", event)
        target_id = payload.get("targetId", "")
        mg = ctx.get("memory_graph")

        deps = walk_authority_dependencies(target_id, mg)
        counts = count_affected_by_kind(deps)

        return FunctionResult(
            function_id="AUTH-F19",
            success=True,
            events_emitted=[{
                "topic": "authority_slice",
                "subtype": "authority_risk_propagated",
                "targetId": target_id,
                "dependencyCounts": counts,
                "totalAffected": sum(counts.values()),
            }],
        )
