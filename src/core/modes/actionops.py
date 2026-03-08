"""ActionOps domain mode -- execution governance and commitment tracking.

19 function handlers keyed by ACTION-F01 through ACTION-F19.

The commitment loop: intake -> validate -> track -> deadline check ->
compliance -> risk -> breach -> escalate -> remediate -> adjust ->
complete -> report.

ACTION-F13 through ACTION-F19 implement Decision Accounting: cost tracking,
time-to-decision, value assessment, debt detection, ROI computation,
budget enforcement, and accounting reports.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List

from .base import DomainMode, FunctionResult


class ActionOps(DomainMode):
    """Sixth domain mode: execution governance and commitment lifecycle.

    Sits at: AuthorityOps -> ActionOps -> FranOps
    Owns the APPLY primitive -- tracks whether authorized actions
    actually execute and meet their commitments.
    """

    domain = "actionops"

    def _register_handlers(self) -> None:
        self._handlers = {
            "ACTION-F01": self._commitment_intake,
            "ACTION-F02": self._commitment_validate,
            "ACTION-F03": self._deliverable_track,
            "ACTION-F04": self._deadline_check,
            "ACTION-F05": self._compliance_evaluate,
            "ACTION-F06": self._risk_assess,
            "ACTION-F07": self._breach_detect,
            "ACTION-F08": self._escalation_trigger,
            "ACTION-F09": self._remediation_recommend,
            "ACTION-F10": self._commitment_adjust,
            "ACTION-F11": self._commitment_complete,
            "ACTION-F12": self._commitment_report,
            # Module A: Decision Accounting
            "ACTION-F13": self._cost_record,
            "ACTION-F14": self._time_to_decision,
            "ACTION-F15": self._value_assess,
            "ACTION-F16": self._debt_detect,
            "ACTION-F17": self._roi_compute,
            "ACTION-F18": self._budget_enforce,
            "ACTION-F19": self._accounting_report,
        }

    # ── ACTION-F01: Commitment Intake ─────────────────────────────

    def _commitment_intake(
        self, event: Dict[str, Any], ctx: Dict[str, Any],
    ) -> FunctionResult:
        """Register a new commitment from a CERPA claim.

        -- ACTION-F01: commitment_intake --
        """
        from core.action_ops import (
            Commitment, CommitmentLifecycle, CommitmentRegistry,
            CommitmentState, Deliverable, validate_commitment,
        )

        payload = event.get("payload", event)
        events: List[Dict[str, Any]] = []
        drift_signals: List[Dict[str, Any]] = []
        mg_updates: List[str] = []

        errors = validate_commitment(payload)
        if errors:
            return FunctionResult(
                function_id="ACTION-F01", success=False,
                error="; ".join(errors),
            )

        commitment_id = payload.get(
            "commitmentId", f"CMT-{uuid.uuid4().hex[:8]}",
        )
        now = ctx.get("now", datetime.now(timezone.utc))
        now_iso = now.isoformat() if hasattr(now, "isoformat") else str(now)

        deliverables = [
            Deliverable(
                deliverable_id=d.get("deliverableId", f"DLV-{uuid.uuid4().hex[:6]}"),
                description=d.get("description", ""),
                status=d.get("status", "pending"),
                due_date=d.get("dueDate"),
            )
            for d in payload.get("deliverables", [])
        ]

        commitment = Commitment(
            commitment_id=commitment_id,
            commitment_type=payload.get("commitmentType", "delivery"),
            text=payload.get("text", ""),
            domain=payload.get("domain", ""),
            owner=payload.get("owner", ""),
            lifecycle_state=CommitmentState.PROPOSED.value,
            deadline=payload.get("deadline"),
            claim_refs=payload.get("claimRefs", []),
            deliverables=deliverables,
            created_at=now_iso,
            metadata=payload.get("metadata", {}),
        )

        registry: CommitmentRegistry = ctx.get("commitment_registry")  # type: ignore[assignment]
        if registry is not None:
            registry.add(commitment)

        lifecycle: CommitmentLifecycle = ctx.get("commitment_lifecycle")  # type: ignore[assignment]
        if lifecycle is not None:
            lifecycle.set_state(commitment_id, CommitmentState.PROPOSED)

        mg = ctx.get("memory_graph")
        if mg is not None:
            from core.memory_graph import GraphNode, NodeKind
            mg._add_node(GraphNode(
                node_id=commitment_id,
                kind=NodeKind.COMMITMENT,
                label=commitment.text[:80],
                timestamp=now_iso,
                properties={
                    "lifecycle_state": "proposed",
                    "commitment_type": commitment.commitment_type,
                    "owner": commitment.owner,
                },
            ))
            mg_updates.append(commitment_id)

        events.append({
            "topic": "action_event",
            "subtype": "commitment_registered",
            "commitmentId": commitment_id,
            "commitmentType": commitment.commitment_type,
            "domain": commitment.domain,
        })

        return FunctionResult(
            function_id="ACTION-F01", success=True,
            events_emitted=events,
            drift_signals=drift_signals,
            mg_updates=mg_updates,
        )

    # ── ACTION-F02: Commitment Validate ───────────────────────────

    def _commitment_validate(
        self, event: Dict[str, Any], ctx: Dict[str, Any],
    ) -> FunctionResult:
        """Validate commitment assumptions and activate.

        -- ACTION-F02: commitment_validate --
        """
        from core.action_ops import (
            CommitmentLifecycle, CommitmentRegistry, CommitmentState,
        )

        payload = event.get("payload", event)
        events: List[Dict[str, Any]] = []

        registry: CommitmentRegistry = ctx.get("commitment_registry")  # type: ignore[assignment]
        commitment_id = payload.get("commitmentId", "")
        commitment = registry.get(commitment_id) if registry else None

        if commitment is None:
            return FunctionResult(
                function_id="ACTION-F02", success=False,
                error=f"Commitment not found: {commitment_id}",
            )

        # Validate assumptions from payload
        assumptions = payload.get("assumptions", [])
        invalid = [a for a in assumptions if a.get("valid") is False]
        if invalid:
            names = ", ".join(a.get("name", "?") for a in invalid)
            return FunctionResult(
                function_id="ACTION-F02", success=False,
                error=f"Invalid assumptions: {names}",
            )

        # Activate the commitment
        lifecycle: CommitmentLifecycle = ctx.get("commitment_lifecycle")  # type: ignore[assignment]
        if lifecycle is not None:
            lifecycle.transition(commitment_id, CommitmentState.ACTIVE)

        now = ctx.get("now", datetime.now(timezone.utc))
        commitment.lifecycle_state = CommitmentState.ACTIVE.value
        commitment.updated_at = now.isoformat() if hasattr(now, "isoformat") else str(now)
        if registry is not None:
            registry.update(commitment)

        events.append({
            "topic": "action_event",
            "subtype": "commitment_activated",
            "commitmentId": commitment_id,
        })

        return FunctionResult(
            function_id="ACTION-F02", success=True,
            events_emitted=events,
        )

    # ── ACTION-F03: Deliverable Track ─────────────────────────────

    def _deliverable_track(
        self, event: Dict[str, Any], ctx: Dict[str, Any],
    ) -> FunctionResult:
        """Update deliverable status within a commitment.

        -- ACTION-F03: deliverable_track --
        """
        from core.action_ops import (
            CommitmentRegistry, validate_deliverable_update,
        )

        payload = event.get("payload", event)
        events: List[Dict[str, Any]] = []

        errors = validate_deliverable_update(payload)
        if errors:
            return FunctionResult(
                function_id="ACTION-F03", success=False,
                error="; ".join(errors),
            )

        registry: CommitmentRegistry = ctx.get("commitment_registry")  # type: ignore[assignment]
        commitment_id = payload.get("commitmentId", payload.get("commitment_id", ""))
        commitment = registry.get(commitment_id) if registry else None

        if commitment is None:
            return FunctionResult(
                function_id="ACTION-F03", success=False,
                error=f"Commitment not found: {commitment_id}",
            )

        deliverable_id = payload.get("deliverableId", payload.get("deliverable_id", ""))
        target = None
        for d in commitment.deliverables:
            if d.deliverable_id == deliverable_id:
                target = d
                break

        if target is None:
            return FunctionResult(
                function_id="ACTION-F03", success=False,
                error=f"Deliverable not found: {deliverable_id}",
            )

        new_status = payload.get("status", target.status)
        target.status = new_status

        now = ctx.get("now", datetime.now(timezone.utc))
        now_iso = now.isoformat() if hasattr(now, "isoformat") else str(now)
        if new_status == "delivered":
            target.completed_at = now_iso
        commitment.updated_at = now_iso
        registry.update(commitment)

        events.append({
            "topic": "action_event",
            "subtype": "deliverable_updated",
            "commitmentId": commitment_id,
            "deliverableId": deliverable_id,
            "status": new_status,
        })

        return FunctionResult(
            function_id="ACTION-F03", success=True,
            events_emitted=events,
        )

    # ── ACTION-F04: Deadline Check ────────────────────────────────

    def _deadline_check(
        self, event: Dict[str, Any], ctx: Dict[str, Any],
    ) -> FunctionResult:
        """Check deadline proximity and emit at-risk signals.

        -- ACTION-F04: deadline_check --
        """
        from core.action_ops import (
            CommitmentLifecycle, CommitmentRegistry, CommitmentState,
            check_deadline_proximity,
        )

        payload = event.get("payload", event)
        events: List[Dict[str, Any]] = []
        drift_signals: List[Dict[str, Any]] = []

        registry: CommitmentRegistry = ctx.get("commitment_registry")  # type: ignore[assignment]
        commitment_id = payload.get("commitmentId", "")
        commitment = registry.get(commitment_id) if registry else None

        if commitment is None:
            return FunctionResult(
                function_id="ACTION-F04", success=False,
                error=f"Commitment not found: {commitment_id}",
            )

        now = ctx.get("now", datetime.now(timezone.utc))
        proximity = check_deadline_proximity(commitment, now)

        if proximity["at_risk"]:
            lifecycle: CommitmentLifecycle = ctx.get("commitment_lifecycle")  # type: ignore[assignment]
            if lifecycle is not None and commitment.lifecycle_state == CommitmentState.ACTIVE.value:
                lifecycle.transition(commitment_id, CommitmentState.AT_RISK)
                commitment.lifecycle_state = CommitmentState.AT_RISK.value
                commitment.updated_at = now.isoformat() if hasattr(now, "isoformat") else str(now)
                registry.update(commitment)

            drift_signals.append({
                "driftType": "deadline_proximity",
                "severity": "yellow",
                "commitmentId": commitment_id,
                "daysRemaining": proximity["days_remaining"],
                "proximity": proximity["proximity"],
            })

            events.append({
                "topic": "action_event",
                "subtype": "commitment_at_risk",
                "commitmentId": commitment_id,
                "daysRemaining": proximity["days_remaining"],
            })

        return FunctionResult(
            function_id="ACTION-F04", success=True,
            events_emitted=events,
            drift_signals=drift_signals,
        )

    # ── ACTION-F05: Compliance Evaluate ───────────────────────────

    def _compliance_evaluate(
        self, event: Dict[str, Any], ctx: Dict[str, Any],
    ) -> FunctionResult:
        """Evaluate compliance metrics against targets.

        -- ACTION-F05: compliance_evaluate --
        """
        from core.action_ops import CommitmentRegistry, run_compliance_check

        payload = event.get("payload", event)
        events: List[Dict[str, Any]] = []

        registry: CommitmentRegistry = ctx.get("commitment_registry")  # type: ignore[assignment]
        commitment_id = payload.get("commitmentId", "")
        commitment = registry.get(commitment_id) if registry else None

        if commitment is None:
            return FunctionResult(
                function_id="ACTION-F05", success=False,
                error=f"Commitment not found: {commitment_id}",
            )

        now = ctx.get("now", datetime.now(timezone.utc))
        observed_state = payload.get("observedState", {})
        check = run_compliance_check(commitment, observed_state, now)

        events.append({
            "topic": "action_event",
            "subtype": "compliance_checked",
            "commitmentId": commitment_id,
            "checkId": check.check_id,
            "passed": check.passed,
            "checkType": check.check_type,
        })

        return FunctionResult(
            function_id="ACTION-F05", success=True,
            events_emitted=events,
        )

    # ── ACTION-F06: Risk Assess ───────────────────────────────────

    def _risk_assess(
        self, event: Dict[str, Any], ctx: Dict[str, Any],
    ) -> FunctionResult:
        """Compute fulfillment risk score.

        -- ACTION-F06: risk_assess --
        """
        from core.action_ops import CommitmentRegistry, compute_risk_score

        payload = event.get("payload", event)
        events: List[Dict[str, Any]] = []

        registry: CommitmentRegistry = ctx.get("commitment_registry")  # type: ignore[assignment]
        commitment_id = payload.get("commitmentId", "")
        commitment = registry.get(commitment_id) if registry else None

        if commitment is None:
            return FunctionResult(
                function_id="ACTION-F06", success=False,
                error=f"Commitment not found: {commitment_id}",
            )

        now = ctx.get("now", datetime.now(timezone.utc))
        checks = payload.get("checks", [])
        risk = compute_risk_score(commitment, checks, now)
        commitment.risk_score = risk
        commitment.updated_at = now.isoformat() if hasattr(now, "isoformat") else str(now)
        registry.update(commitment)

        events.append({
            "topic": "action_event",
            "subtype": "risk_assessed",
            "commitmentId": commitment_id,
            "riskScore": risk,
        })

        return FunctionResult(
            function_id="ACTION-F06", success=True,
            events_emitted=events,
        )

    # ── ACTION-F07: Breach Detect ─────────────────────────────────

    def _breach_detect(
        self, event: Dict[str, Any], ctx: Dict[str, Any],
    ) -> FunctionResult:
        """Detect commitment breach (deadline missed, SLA violated).

        -- ACTION-F07: breach_detect --
        """
        from core.action_ops import (
            CommitmentLifecycle, CommitmentRegistry, CommitmentState,
            assess_breach_severity, evaluate_deliverables,
        )

        payload = event.get("payload", event)
        events: List[Dict[str, Any]] = []
        drift_signals: List[Dict[str, Any]] = []

        registry: CommitmentRegistry = ctx.get("commitment_registry")  # type: ignore[assignment]
        commitment_id = payload.get("commitmentId", "")
        commitment = registry.get(commitment_id) if registry else None

        if commitment is None:
            return FunctionResult(
                function_id="ACTION-F07", success=False,
                error=f"Commitment not found: {commitment_id}",
            )

        deliv_status = evaluate_deliverables(commitment)
        severity = assess_breach_severity(commitment)

        if not deliv_status["compliant"] or commitment.risk_score >= 0.8:
            lifecycle: CommitmentLifecycle = ctx.get("commitment_lifecycle")  # type: ignore[assignment]
            if lifecycle is not None:
                lifecycle.transition(commitment_id, CommitmentState.BREACHED)

            now = ctx.get("now", datetime.now(timezone.utc))
            now_iso = now.isoformat() if hasattr(now, "isoformat") else str(now)
            commitment.lifecycle_state = CommitmentState.BREACHED.value
            commitment.updated_at = now_iso
            registry.update(commitment)

            drift_signals.append({
                "driftType": "commitment_breach",
                "severity": severity,
                "commitmentId": commitment_id,
                "failedDeliverables": deliv_status["failed"],
                "riskScore": commitment.risk_score,
            })

            events.append({
                "topic": "action_event",
                "subtype": "commitment_breached",
                "commitmentId": commitment_id,
                "severity": severity,
            })

        return FunctionResult(
            function_id="ACTION-F07", success=True,
            events_emitted=events,
            drift_signals=drift_signals,
        )

    # ── ACTION-F08: Escalation Trigger ────────────────────────────

    def _escalation_trigger(
        self, event: Dict[str, Any], ctx: Dict[str, Any],
    ) -> FunctionResult:
        """Trigger escalation when breach is confirmed.

        -- ACTION-F08: escalation_trigger --
        """
        from core.action_ops import (
            CommitmentLifecycle, CommitmentRegistry, CommitmentState,
        )

        payload = event.get("payload", event)
        events: List[Dict[str, Any]] = []
        drift_signals: List[Dict[str, Any]] = []

        registry: CommitmentRegistry = ctx.get("commitment_registry")  # type: ignore[assignment]
        commitment_id = payload.get("commitmentId", "")
        commitment = registry.get(commitment_id) if registry else None

        if commitment is None:
            return FunctionResult(
                function_id="ACTION-F08", success=False,
                error=f"Commitment not found: {commitment_id}",
            )

        if commitment.lifecycle_state != CommitmentState.BREACHED.value:
            return FunctionResult(
                function_id="ACTION-F08", success=False,
                error=f"Cannot escalate: state is {commitment.lifecycle_state}, expected breached",
            )

        lifecycle: CommitmentLifecycle = ctx.get("commitment_lifecycle")  # type: ignore[assignment]
        if lifecycle is not None:
            lifecycle.transition(commitment_id, CommitmentState.ESCALATED)

        now = ctx.get("now", datetime.now(timezone.utc))
        now_iso = now.isoformat() if hasattr(now, "isoformat") else str(now)
        commitment.lifecycle_state = CommitmentState.ESCALATED.value
        commitment.escalated_at = now_iso
        commitment.updated_at = now_iso
        registry.update(commitment)

        escalation_target = payload.get("escalationTarget", commitment.owner)

        drift_signals.append({
            "driftType": "commitment_escalation",
            "severity": "red",
            "commitmentId": commitment_id,
            "escalationTarget": escalation_target,
        })

        events.append({
            "topic": "action_event",
            "subtype": "commitment_escalated",
            "commitmentId": commitment_id,
            "escalationTarget": escalation_target,
        })

        return FunctionResult(
            function_id="ACTION-F08", success=True,
            events_emitted=events,
            drift_signals=drift_signals,
        )

    # ── ACTION-F09: Remediation Recommend ─────────────────────────

    def _remediation_recommend(
        self, event: Dict[str, Any], ctx: Dict[str, Any],
    ) -> FunctionResult:
        """Recommend corrective actions for a breached/escalated commitment.

        -- ACTION-F09: remediation_recommend --
        """
        from core.action_ops import CommitmentRegistry, RemediationRecord

        payload = event.get("payload", event)
        events: List[Dict[str, Any]] = []

        registry: CommitmentRegistry = ctx.get("commitment_registry")  # type: ignore[assignment]
        commitment_id = payload.get("commitmentId", "")
        commitment = registry.get(commitment_id) if registry else None

        if commitment is None:
            return FunctionResult(
                function_id="ACTION-F09", success=False,
                error=f"Commitment not found: {commitment_id}",
            )

        now = ctx.get("now", datetime.now(timezone.utc))
        now_iso = now.isoformat() if hasattr(now, "isoformat") else str(now)

        # Build recommendations based on breach type
        recommendations: List[Dict[str, Any]] = []
        if commitment.risk_score >= 0.8:
            recommendations.append({
                "action": "reassign",
                "rationale": f"Risk score {commitment.risk_score} exceeds threshold",
            })
        if commitment.deadline:
            recommendations.append({
                "action": "adjust_deadline",
                "rationale": "Deadline may need extension",
            })

        failed_deliverables = [
            d for d in commitment.deliverables if d.status == "failed"
        ]
        if failed_deliverables:
            recommendations.append({
                "action": "reduce_scope",
                "rationale": f"{len(failed_deliverables)} deliverable(s) failed",
            })

        if not recommendations:
            recommendations.append({
                "action": "escalate",
                "rationale": "No automated remediation available",
            })

        events.append({
            "topic": "action_event",
            "subtype": "remediation_recommended",
            "commitmentId": commitment_id,
            "recommendations": recommendations,
        })

        return FunctionResult(
            function_id="ACTION-F09", success=True,
            events_emitted=events,
        )

    # ── ACTION-F10: Commitment Adjust ─────────────────────────────

    def _commitment_adjust(
        self, event: Dict[str, Any], ctx: Dict[str, Any],
    ) -> FunctionResult:
        """Adjust commitment terms (new deadline, scope change).

        -- ACTION-F10: commitment_adjust --
        """
        from core.action_ops import (
            CommitmentLifecycle, CommitmentRegistry, CommitmentState,
        )

        payload = event.get("payload", event)
        events: List[Dict[str, Any]] = []

        registry: CommitmentRegistry = ctx.get("commitment_registry")  # type: ignore[assignment]
        commitment_id = payload.get("commitmentId", "")
        commitment = registry.get(commitment_id) if registry else None

        if commitment is None:
            return FunctionResult(
                function_id="ACTION-F10", success=False,
                error=f"Commitment not found: {commitment_id}",
            )

        now = ctx.get("now", datetime.now(timezone.utc))
        now_iso = now.isoformat() if hasattr(now, "isoformat") else str(now)
        changes: List[str] = []

        if "deadline" in payload:
            commitment.deadline = payload["deadline"]
            changes.append(f"deadline={payload['deadline']}")
        if "text" in payload:
            commitment.text = payload["text"]
            changes.append("text updated")
        if "owner" in payload:
            commitment.owner = payload["owner"]
            changes.append(f"owner={payload['owner']}")

        # If remediated/escalated, transition back to active
        lifecycle: CommitmentLifecycle = ctx.get("commitment_lifecycle")  # type: ignore[assignment]
        if lifecycle is not None and commitment.lifecycle_state in (
            CommitmentState.REMEDIATED.value,
            CommitmentState.AT_RISK.value,
        ):
            lifecycle.transition(commitment_id, CommitmentState.ACTIVE)
            commitment.lifecycle_state = CommitmentState.ACTIVE.value

        commitment.updated_at = now_iso
        commitment.risk_score = 0.0  # Reset risk after adjustment
        registry.update(commitment)

        events.append({
            "topic": "action_event",
            "subtype": "commitment_adjusted",
            "commitmentId": commitment_id,
            "changes": changes,
        })

        return FunctionResult(
            function_id="ACTION-F10", success=True,
            events_emitted=events,
        )

    # ── ACTION-F11: Commitment Complete ───────────────────────────

    def _commitment_complete(
        self, event: Dict[str, Any], ctx: Dict[str, Any],
    ) -> FunctionResult:
        """Mark commitment as fulfilled.

        -- ACTION-F11: commitment_complete --
        """
        from core.action_ops import (
            CommitmentLifecycle, CommitmentRegistry, CommitmentState,
        )

        payload = event.get("payload", event)
        events: List[Dict[str, Any]] = []
        mg_updates: List[str] = []

        registry: CommitmentRegistry = ctx.get("commitment_registry")  # type: ignore[assignment]
        commitment_id = payload.get("commitmentId", "")
        commitment = registry.get(commitment_id) if registry else None

        if commitment is None:
            return FunctionResult(
                function_id="ACTION-F11", success=False,
                error=f"Commitment not found: {commitment_id}",
            )

        lifecycle: CommitmentLifecycle = ctx.get("commitment_lifecycle")  # type: ignore[assignment]
        if lifecycle is not None:
            ok = lifecycle.transition(commitment_id, CommitmentState.COMPLETED)
            if not ok:
                return FunctionResult(
                    function_id="ACTION-F11", success=False,
                    error=f"Cannot complete: state is {commitment.lifecycle_state}",
                )

        now = ctx.get("now", datetime.now(timezone.utc))
        now_iso = now.isoformat() if hasattr(now, "isoformat") else str(now)
        commitment.lifecycle_state = CommitmentState.COMPLETED.value
        commitment.completed_at = now_iso
        commitment.updated_at = now_iso
        registry.update(commitment)

        mg = ctx.get("memory_graph")
        if mg is not None:
            mg_updates.append(commitment_id)

        events.append({
            "topic": "action_event",
            "subtype": "commitment_completed",
            "commitmentId": commitment_id,
            "claimRefs": commitment.claim_refs,
        })

        return FunctionResult(
            function_id="ACTION-F11", success=True,
            events_emitted=events,
            mg_updates=mg_updates,
        )

    # ── ACTION-F12: Commitment Report ─────────────────────────────

    def _commitment_report(
        self, event: Dict[str, Any], ctx: Dict[str, Any],
    ) -> FunctionResult:
        """Generate compliance summary for audit.

        -- ACTION-F12: commitment_report --
        """
        from core.action_ops import (
            CommitmentRegistry, evaluate_deliverables,
        )

        payload = event.get("payload", event)
        events: List[Dict[str, Any]] = []

        registry: CommitmentRegistry = ctx.get("commitment_registry")  # type: ignore[assignment]
        commitment_id = payload.get("commitmentId", "")
        commitment = registry.get(commitment_id) if registry else None

        if commitment is None:
            return FunctionResult(
                function_id="ACTION-F12", success=False,
                error=f"Commitment not found: {commitment_id}",
            )

        deliv = evaluate_deliverables(commitment)

        report = {
            "commitmentId": commitment_id,
            "state": commitment.lifecycle_state,
            "type": commitment.commitment_type,
            "owner": commitment.owner,
            "domain": commitment.domain,
            "riskScore": commitment.risk_score,
            "deliverables": deliv,
            "claimRefs": commitment.claim_refs,
            "createdAt": commitment.created_at,
            "completedAt": commitment.completed_at,
        }

        events.append({
            "topic": "action_event",
            "subtype": "commitment_report_generated",
            "commitmentId": commitment_id,
            "report": report,
        })

        return FunctionResult(
            function_id="ACTION-F12", success=True,
            events_emitted=events,
        )

    # ── ACTION-F13: Cost Record ───────────────────────────────

    def _cost_record(
        self, event: Dict[str, Any], ctx: Dict[str, Any],
    ) -> FunctionResult:
        """Record a cost event against a commitment.

        -- ACTION-F13: cost_record --
        """
        from core.decision_accounting import (
            AccountingRegistry, record_handler_cost, validate_cost_record,
        )

        payload = event.get("payload", event)
        events: List[Dict[str, Any]] = []
        mg_updates: List[str] = []

        errors = validate_cost_record(payload)
        if errors:
            return FunctionResult(
                function_id="ACTION-F13", success=False,
                error="; ".join(errors),
            )

        commitment_id = payload.get("commitmentId", payload.get("commitment_id", ""))
        category = payload.get("category", "time")
        amount = payload.get("amount", 0.0)
        handler_id = payload.get("handlerId")

        registry: AccountingRegistry = ctx.get("accounting_registry")  # type: ignore[assignment]
        if registry is None:
            registry = AccountingRegistry()

        cost = record_handler_cost(registry, commitment_id, category, amount, handler_id)

        mg = ctx.get("memory_graph")
        if mg is not None:
            from core.memory_graph import EdgeKind, GraphEdge, GraphNode, NodeKind
            mg._add_node(GraphNode(
                node_id=cost.cost_id,
                kind=NodeKind.COST_RECORD,
                label=f"{category}:{amount}",
                timestamp=cost.recorded_at,
                properties={"category": category, "amount": amount},
            ))
            mg._add_edge(GraphEdge(
                source_id=cost.cost_id,
                target_id=commitment_id,
                kind=EdgeKind.COST_OF,
                label="cost of commitment",
            ))
            mg_updates.append(cost.cost_id)

        events.append({
            "topic": "action_event",
            "subtype": "cost_recorded",
            "commitmentId": commitment_id,
            "costId": cost.cost_id,
            "category": category,
            "amount": amount,
        })

        return FunctionResult(
            function_id="ACTION-F13", success=True,
            events_emitted=events,
            mg_updates=mg_updates,
        )

    # ── ACTION-F14: Time to Decision ──────────────────────────

    def _time_to_decision(
        self, event: Dict[str, Any], ctx: Dict[str, Any],
    ) -> FunctionResult:
        """Compute elapsed time from episode begin to commitment complete.

        -- ACTION-F14: time_to_decision --
        """
        from core.decision_accounting import TimeToDecision

        payload = event.get("payload", event)
        events: List[Dict[str, Any]] = []

        commitment_id = payload.get("commitmentId", "")
        episode_id = payload.get("episodeId", "")
        elapsed_ms = payload.get("elapsedMs", 0.0)
        handler_chain_ms = payload.get("handlerChainMs", {})

        now = ctx.get("now", datetime.now(timezone.utc))
        now_iso = now.isoformat() if hasattr(now, "isoformat") else str(now)

        ttd = TimeToDecision(
            commitment_id=commitment_id,
            episode_id=episode_id,
            elapsed_ms=elapsed_ms,
            handler_chain_ms=handler_chain_ms,
            measured_at=now_iso,
        )

        events.append({
            "topic": "action_event",
            "subtype": "time_to_decision_measured",
            "commitmentId": commitment_id,
            "episodeId": episode_id,
            "elapsedMs": elapsed_ms,
        })

        return FunctionResult(
            function_id="ACTION-F14", success=True,
            events_emitted=events,
        )

    # ── ACTION-F15: Value Assess ──────────────────────────────

    def _value_assess(
        self, event: Dict[str, Any], ctx: Dict[str, Any],
    ) -> FunctionResult:
        """Assess delivered value for a commitment.

        -- ACTION-F15: value_assess --
        """
        from core.action_ops import CommitmentRegistry
        from core.decision_accounting import (
            AccountingRegistry, ValueAssessment,
            compute_composite_value, compute_outcome_quality,
        )

        payload = event.get("payload", event)
        events: List[Dict[str, Any]] = []
        mg_updates: List[str] = []

        commitment_id = payload.get("commitmentId", "")

        commit_registry: CommitmentRegistry = ctx.get("commitment_registry")  # type: ignore[assignment]
        commitment = commit_registry.get(commitment_id) if commit_registry else None

        if commitment is None:
            return FunctionResult(
                function_id="ACTION-F15", success=False,
                error=f"Commitment not found: {commitment_id}",
            )

        statuses = [d.status for d in commitment.deliverables]
        outcome_quality = compute_outcome_quality(statuses)
        total = len(statuses) or 1
        delivered = sum(1 for s in statuses if s == "delivered")
        deliverable_completion = round(delivered / total, 4)
        composite = compute_composite_value(outcome_quality, deliverable_completion)

        now = ctx.get("now", datetime.now(timezone.utc))
        now_iso = now.isoformat() if hasattr(now, "isoformat") else str(now)

        assessment_id = f"VA-{uuid.uuid4().hex[:8]}"
        assessment = ValueAssessment(
            assessment_id=assessment_id,
            commitment_id=commitment_id,
            outcome_quality=outcome_quality,
            deliverable_completion=deliverable_completion,
            composite_value=composite,
            assessed_at=now_iso,
        )

        acct_registry: AccountingRegistry = ctx.get("accounting_registry")  # type: ignore[assignment]
        if acct_registry is not None:
            acct_registry.set_assessment(assessment)

        mg = ctx.get("memory_graph")
        if mg is not None:
            from core.memory_graph import EdgeKind, GraphEdge, GraphNode, NodeKind
            mg._add_node(GraphNode(
                node_id=assessment_id,
                kind=NodeKind.VALUE_ASSESSMENT,
                label=f"value:{composite:.2f}",
                timestamp=now_iso,
                properties={
                    "outcome_quality": outcome_quality,
                    "deliverable_completion": deliverable_completion,
                    "composite_value": composite,
                },
            ))
            mg._add_edge(GraphEdge(
                source_id=assessment_id,
                target_id=commitment_id,
                kind=EdgeKind.VALUE_OF,
                label="value of commitment",
            ))
            mg_updates.append(assessment_id)

        events.append({
            "topic": "action_event",
            "subtype": "value_assessed",
            "commitmentId": commitment_id,
            "assessmentId": assessment_id,
            "outcomeQuality": outcome_quality,
            "compositeValue": composite,
        })

        return FunctionResult(
            function_id="ACTION-F15", success=True,
            events_emitted=events,
            mg_updates=mg_updates,
        )

    # ── ACTION-F16: Debt Detect ───────────────────────────────

    def _debt_detect(
        self, event: Dict[str, Any], ctx: Dict[str, Any],
    ) -> FunctionResult:
        """Detect decision debt (rework, scope reduction, quality shortfall).

        -- ACTION-F16: debt_detect --
        """
        from core.action_ops import CommitmentRegistry
        from core.decision_accounting import (
            AccountingRegistry, detect_debt,
        )

        payload = event.get("payload", event)
        events: List[Dict[str, Any]] = []
        drift_signals: List[Dict[str, Any]] = []
        mg_updates: List[str] = []

        commitment_id = payload.get("commitmentId", "")
        rework_count = payload.get("reworkCount", 0)

        commit_registry: CommitmentRegistry = ctx.get("commitment_registry")  # type: ignore[assignment]
        commitment = commit_registry.get(commitment_id) if commit_registry else None

        if commitment is None:
            return FunctionResult(
                function_id="ACTION-F16", success=False,
                error=f"Commitment not found: {commitment_id}",
            )

        statuses = [d.status for d in commitment.deliverables]
        debts = detect_debt(commitment_id, statuses, commitment.risk_score, rework_count)

        acct_registry: AccountingRegistry = ctx.get("accounting_registry")  # type: ignore[assignment]
        mg = ctx.get("memory_graph")

        debt_ids: List[str] = []
        for debt in debts:
            if acct_registry is not None:
                acct_registry.add_debt(debt)
            debt_ids.append(debt.debt_id)

            if mg is not None:
                from core.memory_graph import EdgeKind, GraphEdge, GraphNode, NodeKind
                mg._add_node(GraphNode(
                    node_id=debt.debt_id,
                    kind=NodeKind.DECISION_DEBT,
                    label=f"{debt.debt_type}:{debt.estimated_cost}",
                    timestamp=debt.detected_at,
                    properties={
                        "debt_type": debt.debt_type,
                        "estimated_cost": debt.estimated_cost,
                    },
                ))
                mg._add_edge(GraphEdge(
                    source_id=debt.debt_id,
                    target_id=commitment_id,
                    kind=EdgeKind.DEBT_FROM,
                    label="debt from commitment",
                ))
                mg_updates.append(debt.debt_id)

        if debts:
            drift_signals.append({
                "driftType": "decision_debt",
                "severity": "yellow",
                "commitmentId": commitment_id,
                "debtCount": len(debts),
                "debtTypes": [d.debt_type for d in debts],
            })

        events.append({
            "topic": "action_event",
            "subtype": "decision_debt_detected",
            "commitmentId": commitment_id,
            "debtIds": debt_ids,
            "debtCount": len(debts),
        })

        return FunctionResult(
            function_id="ACTION-F16", success=True,
            events_emitted=events,
            drift_signals=drift_signals,
            mg_updates=mg_updates,
        )

    # ── ACTION-F17: ROI Compute ───────────────────────────────

    def _roi_compute(
        self, event: Dict[str, Any], ctx: Dict[str, Any],
    ) -> FunctionResult:
        """Compute ROI: (value - cost) / cost.

        -- ACTION-F17: roi_compute --
        """
        from core.decision_accounting import AccountingRegistry, compute_roi

        payload = event.get("payload", event)
        events: List[Dict[str, Any]] = []

        commitment_id = payload.get("commitmentId", "")

        acct_registry: AccountingRegistry = ctx.get("accounting_registry")  # type: ignore[assignment]
        if acct_registry is None:
            return FunctionResult(
                function_id="ACTION-F17", success=False,
                error="No accounting_registry in context",
            )

        report = compute_roi(acct_registry, commitment_id)

        events.append({
            "topic": "action_event",
            "subtype": "roi_computed",
            "commitmentId": commitment_id,
            "reportId": report.report_id,
            "totalCost": report.total_cost,
            "totalValue": report.total_value,
            "roi": report.roi,
            "debtOutstanding": report.debt_outstanding,
        })

        return FunctionResult(
            function_id="ACTION-F17", success=True,
            events_emitted=events,
        )

    # ── ACTION-F18: Budget Enforce ────────────────────────────

    def _budget_enforce(
        self, event: Dict[str, Any], ctx: Dict[str, Any],
    ) -> FunctionResult:
        """Check cost vs. budget thresholds, emit drift on overrun.

        -- ACTION-F18: budget_enforce --
        """
        from core.decision_accounting import (
            AccountingRegistry, CostBudget,
            compute_budget_status, detect_overrun,
        )

        payload = event.get("payload", event)
        events: List[Dict[str, Any]] = []
        drift_signals: List[Dict[str, Any]] = []

        commitment_id = payload.get("commitmentId", "")
        max_amount = payload.get("maxAmount")

        acct_registry: AccountingRegistry = ctx.get("accounting_registry")  # type: ignore[assignment]
        if acct_registry is None:
            return FunctionResult(
                function_id="ACTION-F18", success=False,
                error="No accounting_registry in context",
            )

        # Set budget if provided
        if max_amount is not None:
            budget = CostBudget(
                budget_id=f"BUD-{uuid.uuid4().hex[:8]}",
                commitment_id=commitment_id,
                max_amount=float(max_amount),
            )
            acct_registry.set_budget(budget)

        status = compute_budget_status(acct_registry, commitment_id)

        if status.get("overrun"):
            drift_signals.append({
                "driftType": "budget_overrun",
                "severity": "red",
                "commitmentId": commitment_id,
                "utilization": status.get("utilization", 0),
                "totalCost": status.get("total_cost", 0),
                "maxAmount": status.get("max_amount", 0),
            })

            events.append({
                "topic": "action_event",
                "subtype": "budget_overrun",
                "commitmentId": commitment_id,
                "utilization": status.get("utilization", 0),
            })
        else:
            events.append({
                "topic": "action_event",
                "subtype": "budget_checked",
                "commitmentId": commitment_id,
                "utilization": status.get("utilization", 0),
                "overrun": False,
            })

        return FunctionResult(
            function_id="ACTION-F18", success=True,
            events_emitted=events,
            drift_signals=drift_signals,
        )

    # ── ACTION-F19: Accounting Report ─────────────────────────

    def _accounting_report(
        self, event: Dict[str, Any], ctx: Dict[str, Any],
    ) -> FunctionResult:
        """Generate full accounting report (cost breakdown, value, debt, ROI).

        -- ACTION-F19: accounting_report --
        """
        from core.decision_accounting import (
            AccountingRegistry, compute_budget_status, compute_roi,
        )

        payload = event.get("payload", event)
        events: List[Dict[str, Any]] = []

        commitment_id = payload.get("commitmentId", "")

        acct_registry: AccountingRegistry = ctx.get("accounting_registry")  # type: ignore[assignment]
        if acct_registry is None:
            return FunctionResult(
                function_id="ACTION-F19", success=False,
                error="No accounting_registry in context",
            )

        costs = acct_registry.get_costs(commitment_id)
        cost_breakdown = {}
        for c in costs:
            cost_breakdown[c.category] = cost_breakdown.get(c.category, 0) + c.amount

        assessment = acct_registry.get_assessment(commitment_id)
        debts = acct_registry.get_debts(commitment_id)
        budget_status = compute_budget_status(acct_registry, commitment_id)
        roi_report = compute_roi(acct_registry, commitment_id)

        report = {
            "commitmentId": commitment_id,
            "costBreakdown": cost_breakdown,
            "totalCost": roi_report.total_cost,
            "value": {
                "outcomeQuality": assessment.outcome_quality if assessment else 0.0,
                "compositeValue": assessment.composite_value if assessment else 0.0,
            },
            "debts": [
                {
                    "debtId": d.debt_id,
                    "type": d.debt_type,
                    "estimatedCost": d.estimated_cost,
                    "resolved": d.resolved,
                }
                for d in debts
            ],
            "budget": budget_status,
            "roi": roi_report.roi,
            "debtOutstanding": roi_report.debt_outstanding,
        }

        events.append({
            "topic": "action_event",
            "subtype": "accounting_report_generated",
            "commitmentId": commitment_id,
            "report": report,
        })

        return FunctionResult(
            function_id="ACTION-F19", success=True,
            events_emitted=events,
        )
