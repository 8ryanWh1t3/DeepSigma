"""AuthorityOps domain mode — authority, policy, and governance enforcement.

Wraps authority graph, policy compiler, policy runtime, reasoning gate,
delegation chain, and audit into 12 function handlers keyed by AUTH-F01
through AUTH-F12.

The governance loop: intake → resolve → policy → evaluate → audit.

AuthorityOps is the cross-cutting governance layer that binds authority,
action, rationale, expiry, and audit into a single evaluable control plane.
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
