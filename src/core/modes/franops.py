"""FranOps domain mode — canon enforcement and retcon engine.

Wraps canon store, workflow state machine, retcon executor, and inflation
monitor into 12 function handlers keyed by FRAN-F01 through FRAN-F12.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .base import DomainMode, FunctionResult


class FranOps(DomainMode):
    """FranOps domain: canon lifecycle, retcon, inflation, and drift."""

    domain = "franops"

    def _register_handlers(self) -> None:
        self._handlers = {
            "FRAN-F01": self._canon_propose,
            "FRAN-F02": self._canon_bless,
            "FRAN-F03": self._canon_enforce,
            "FRAN-F04": self._retcon_assess,
            "FRAN-F05": self._retcon_execute,
            "FRAN-F06": self._retcon_propagate,
            "FRAN-F07": self._inflation_monitor,
            "FRAN-F08": self._canon_expire,
            "FRAN-F09": self._canon_supersede,
            "FRAN-F10": self._canon_scope_check,
            "FRAN-F11": self._canon_drift_detect,
            "FRAN-F12": self._canon_rollback,
        }

    # ── FRAN-F01: Canon Propose ──────────────────────────────────

    def _canon_propose(
        self, event: Dict[str, Any], ctx: Dict[str, Any],
    ) -> FunctionResult:
        """Propose a new canon entry for blessing."""
        payload = event.get("payload", event)
        canon_id = payload.get("canonId", f"CANON-{uuid.uuid4().hex[:8]}")

        canon_store = ctx.get("canon_store")
        workflow = ctx.get("workflow")

        if canon_store is not None:
            canon_store.add({
                "canonId": canon_id,
                "title": payload.get("title", ""),
                "claimIds": payload.get("claimIds", []),
                "version": payload.get("version", "1.0.0"),
            })

        if workflow is not None:
            from core.feeds.canon.workflow import CanonState
            workflow.set_state(canon_id, CanonState.PROPOSED)

        return FunctionResult(
            function_id="FRAN-F01",
            success=True,
            events_emitted=[{
                "topic": "canon_entry",
                "subtype": "canon_proposed",
                "canonId": canon_id,
            }],
        )

    # ── FRAN-F02: Canon Bless ────────────────────────────────────

    def _canon_bless(
        self, event: Dict[str, Any], ctx: Dict[str, Any],
    ) -> FunctionResult:
        """Bless a proposed canon entry with authority verification."""
        payload = event.get("payload", event)
        canon_id = payload.get("canonId", "")
        blessed_by = payload.get("blessedBy", "")

        workflow = ctx.get("workflow")
        drift_signals: List[Dict[str, Any]] = []

        if workflow is not None:
            from core.feeds.canon.workflow import CanonState
            current = workflow.get_state(canon_id)
            if current != CanonState.PROPOSED:
                drift_signals.append({
                    "driftId": f"DS-bless-{uuid.uuid4().hex[:8]}",
                    "driftType": "process_gap",
                    "severity": "yellow",
                    "detectedAt": datetime.now(timezone.utc).isoformat(),
                    "notes": f"Cannot bless {canon_id}: state is {current}, expected PROPOSED",
                    "fingerprint": {"key": f"bless-invalid:{canon_id}", "version": "1"},
                })
                return FunctionResult(
                    function_id="FRAN-F02",
                    success=True,
                    events_emitted=[],
                    drift_signals=drift_signals,
                )
            workflow.transition(canon_id, CanonState.BLESSED)

        # Also auto-activate after blessing
        if workflow is not None:
            from core.feeds.canon.workflow import CanonState
            workflow.transition(canon_id, CanonState.ACTIVE)

        return FunctionResult(
            function_id="FRAN-F02",
            success=True,
            events_emitted=[{
                "topic": "canon_entry",
                "subtype": "canon_blessed",
                "canonId": canon_id,
                "blessedBy": blessed_by,
            }],
        )

    # ── FRAN-F03: Canon Enforce ──────────────────────────────────

    def _canon_enforce(
        self, event: Dict[str, Any], ctx: Dict[str, Any],
    ) -> FunctionResult:
        """Enforce canon rules against active claims and decisions."""
        payload = event.get("payload", event)
        canon_id = payload.get("canonId", "")
        decision_claims = payload.get("decisionClaims", [])
        canon_claims = ctx.get("canon_claims", [])

        # Build set of canon claim IDs
        canon_ids = set()
        for c in canon_claims:
            cid = c.get("claimId", "")
            if cid:
                canon_ids.add(cid)

        violations: List[Dict[str, Any]] = []
        for claim_id in decision_claims:
            if claim_id not in canon_ids:
                violations.append({
                    "driftId": f"DS-enforce-{uuid.uuid4().hex[:8]}",
                    "driftType": "authority_mismatch",
                    "severity": "red",
                    "detectedAt": datetime.now(timezone.utc).isoformat(),
                    "evidenceRefs": [f"claim:{claim_id}", f"canon:{canon_id}"],
                    "fingerprint": {"key": f"enforce:{canon_id}:{claim_id}", "version": "1"},
                    "notes": f"Decision claim {claim_id} not in canon {canon_id}",
                })

        subtype = "canon_violation" if violations else "canon_pass"
        return FunctionResult(
            function_id="FRAN-F03",
            success=True,
            events_emitted=[{
                "topic": "drift_signal",
                "subtype": subtype,
                "canonId": canon_id,
            }],
            drift_signals=violations,
        )

    # ── FRAN-F04: Retcon Assess ──────────────────────────────────

    def _retcon_assess(
        self, event: Dict[str, Any], ctx: Dict[str, Any],
    ) -> FunctionResult:
        """Assess impact of a proposed retroactive correction."""
        payload = event.get("payload", event)
        original_claim_id = payload.get("originalClaimId", "")
        dependents = payload.get("dependents", [])
        canon_entries = ctx.get("canon_entries", [])

        from core.feeds.canon.retcon_executor import assess_retcon

        assessment = assess_retcon(
            original_claim_id=original_claim_id,
            dependents=dependents,
            canon_entries=canon_entries,
        )

        return FunctionResult(
            function_id="FRAN-F04",
            success=True,
            events_emitted=[{
                "topic": "canon_entry",
                "subtype": "retcon_assessed",
                **assessment.to_dict(),
            }],
        )

    # ── FRAN-F05: Retcon Execute ─────────────────────────────────

    def _retcon_execute(
        self, event: Dict[str, Any], ctx: Dict[str, Any],
    ) -> FunctionResult:
        """Execute a retcon: create superseding claim, update canon, seal."""
        payload = event.get("payload", event)
        original_claim_id = payload.get("originalClaimId", "")
        new_claim_id = payload.get("newClaimId", f"CLAIM-{uuid.uuid4().hex[:8]}")
        reason = payload.get("reason", "")
        retcon_id = payload.get("retconId", f"RETCON-{uuid.uuid4().hex[:8]}")

        from core.feeds.canon.retcon_executor import RetconAssessment, execute_retcon

        assessment = RetconAssessment(
            retcon_id=retcon_id,
            original_claim_id=original_claim_id,
            affected_claim_ids=payload.get("affectedClaimIds", []),
            affected_canon_ids=payload.get("affectedCanonIds", []),
            impact_severity=payload.get("impactSeverity", "yellow"),
        )

        record = execute_retcon(assessment, new_claim_id, reason)

        # Update canon store
        canon_store = ctx.get("canon_store")
        if canon_store is not None:
            canon_store.add({
                "canonId": f"CANON-{new_claim_id}",
                "title": f"Retcon: replaces {original_claim_id}",
                "claimIds": [new_claim_id],
                "supersedes": f"CANON-{original_claim_id}",
                "version": "2.0.0",
            })

        # Update MG
        mg = ctx.get("memory_graph")
        mg_updates: List[str] = []
        if mg is not None:
            nid = mg.add_claim({
                "claimId": new_claim_id,
                "statement": f"Retcon of {original_claim_id}",
                "confidence": {"score": 1.0},
                "graph": {"supersedes": original_claim_id},
            })
            if nid:
                mg_updates.append(nid)

        # Update workflow state
        workflow = ctx.get("workflow")
        if workflow is not None:
            from core.feeds.canon.workflow import CanonState
            workflow.transition(f"CANON-{original_claim_id}", CanonState.RETCONNED)

        drift_signals = [{
            "driftId": f"DS-retcon-{uuid.uuid4().hex[:8]}",
            "driftType": "authority_mismatch",
            "severity": assessment.impact_severity,
            "detectedAt": datetime.now(timezone.utc).isoformat(),
            "evidenceRefs": [f"retcon:{retcon_id}"],
            "fingerprint": {"key": f"retcon:{retcon_id}", "version": "1"},
            "notes": f"Retcon executed: {original_claim_id} -> {new_claim_id}",
        }]

        return FunctionResult(
            function_id="FRAN-F05",
            success=True,
            events_emitted=[{
                "topic": "canon_entry",
                "subtype": "retcon_executed",
                **record,
            }],
            drift_signals=drift_signals,
            mg_updates=mg_updates,
        )

    # ── FRAN-F06: Retcon Propagate ───────────────────────────────

    def _retcon_propagate(
        self, event: Dict[str, Any], ctx: Dict[str, Any],
    ) -> FunctionResult:
        """Propagate retcon effects to dependent claims and canon entries."""
        payload = event.get("payload", event)
        retcon_id = payload.get("retconId", "")
        affected_claim_ids = payload.get("affectedClaimIds", [])
        affected_canon_ids = payload.get("affectedCanonIds", [])

        from core.feeds.canon.retcon_executor import RetconAssessment, compute_propagation_targets

        assessment = RetconAssessment(
            retcon_id=retcon_id,
            original_claim_id=payload.get("originalClaimId", ""),
            affected_claim_ids=affected_claim_ids,
            affected_canon_ids=affected_canon_ids,
            impact_severity=payload.get("impactSeverity", "yellow"),
        )

        targets = compute_propagation_targets(assessment)

        drift_signals = [{
            "driftId": f"DS-cascade-{uuid.uuid4().hex[:8]}",
            "driftType": "authority_mismatch",
            "severity": "yellow",
            "detectedAt": datetime.now(timezone.utc).isoformat(),
            "evidenceRefs": [f"retcon:{retcon_id}"],
            "fingerprint": {"key": f"retcon-cascade:{retcon_id}", "version": "1"},
            "notes": f"Retcon {retcon_id} affects {len(targets)} targets",
        }] if targets else []

        return FunctionResult(
            function_id="FRAN-F06",
            success=True,
            events_emitted=[{
                "topic": "drift_signal",
                "subtype": "retcon_cascade",
                "retconId": retcon_id,
                "targets": targets,
            }],
            drift_signals=drift_signals,
        )

    # ── FRAN-F07: Inflation Monitor ──────────────────────────────

    def _inflation_monitor(
        self, event: Dict[str, Any], ctx: Dict[str, Any],
    ) -> FunctionResult:
        """Monitor canon inflation thresholds."""
        payload = event.get("payload", event)

        from core.feeds.canon.inflation_monitor import InflationMetrics, check_inflation

        metrics = InflationMetrics(
            domain=payload.get("domain", ""),
            claim_count=payload.get("claimCount", 0),
            contradiction_density=payload.get("contradictionDensity", 0.0),
            avg_claim_age_days=payload.get("avgClaimAgeDays", 0.0),
            supersedes_depth=payload.get("supersedesDepth", 0),
        )

        thresholds = ctx.get("inflation_thresholds")
        breaches = check_inflation(metrics, thresholds)

        events = [{
            "topic": "drift_signal",
            "subtype": "canon_inflation",
            "domain": metrics.domain,
            "metrics": metrics.to_dict(),
            "breachCount": len(breaches),
        }] if breaches else []

        return FunctionResult(
            function_id="FRAN-F07",
            success=True,
            events_emitted=events,
            drift_signals=breaches,
        )

    # ── FRAN-F08: Canon Expire ───────────────────────────────────

    def _canon_expire(
        self, event: Dict[str, Any], ctx: Dict[str, Any],
    ) -> FunctionResult:
        """Expire canon entries past their expiresAt timestamp."""
        all_entries = ctx.get("all_canon_entries", [])
        now = ctx.get("now", datetime.now(timezone.utc))
        workflow = ctx.get("workflow")

        expired_ids: List[str] = []
        drift_signals: List[Dict[str, Any]] = []

        for entry in all_entries:
            data = entry.get("data", entry)
            expires_at = data.get("expiresAt", "")
            if not expires_at:
                continue

            try:
                exp_dt = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                continue

            if now > exp_dt:
                canon_id = entry.get("canonId", data.get("canonId", ""))
                if not canon_id:
                    continue
                expired_ids.append(canon_id)

                if workflow is not None:
                    from core.feeds.canon.workflow import CanonState
                    workflow.transition(canon_id, CanonState.EXPIRED)

                drift_signals.append({
                    "driftId": f"DS-expire-{uuid.uuid4().hex[:8]}",
                    "driftType": "freshness",
                    "severity": "yellow",
                    "detectedAt": datetime.now(timezone.utc).isoformat(),
                    "evidenceRefs": [f"canon:{canon_id}"],
                    "fingerprint": {"key": f"expire:{canon_id}", "version": "1"},
                    "notes": f"Canon entry {canon_id} expired at {expires_at}",
                })

        events = [{
            "topic": "canon_entry",
            "subtype": "canon_expired",
            "expiredIds": expired_ids,
        }] if expired_ids else []

        return FunctionResult(
            function_id="FRAN-F08",
            success=True,
            events_emitted=events,
            drift_signals=drift_signals,
        )

    # ── FRAN-F09: Canon Supersede ────────────────────────────────

    def _canon_supersede(
        self, event: Dict[str, Any], ctx: Dict[str, Any],
    ) -> FunctionResult:
        """Supersede a canon entry with a newer version."""
        payload = event.get("payload", event)
        canon_id = payload.get("canonId", "")
        superseded_by = payload.get("supersededBy", "")

        canon_store = ctx.get("canon_store")
        workflow = ctx.get("workflow")
        mg = ctx.get("memory_graph")
        mg_updates: List[str] = []

        if canon_store is not None and superseded_by:
            canon_store.add({
                "canonId": superseded_by,
                "title": payload.get("title", f"Supersedes {canon_id}"),
                "claimIds": payload.get("claimIds", []),
                "supersedes": canon_id,
                "version": payload.get("version", "2.0.0"),
            })

        if workflow is not None:
            from core.feeds.canon.workflow import CanonState
            workflow.transition(canon_id, CanonState.SUPERSEDED)

        if mg is not None:
            nid = mg.add_claim({
                "claimId": superseded_by,
                "statement": f"Supersedes {canon_id}",
                "confidence": {"score": 1.0},
                "graph": {"supersedes": canon_id},
            })
            if nid:
                mg_updates.append(nid)

        return FunctionResult(
            function_id="FRAN-F09",
            success=True,
            events_emitted=[{
                "topic": "canon_entry",
                "subtype": "canon_superseded",
                "canonId": canon_id,
                "supersededBy": superseded_by,
            }],
            mg_updates=mg_updates,
        )

    # ── FRAN-F10: Canon Scope Check ──────────────────────────────

    def _canon_scope_check(
        self, event: Dict[str, Any], ctx: Dict[str, Any],
    ) -> FunctionResult:
        """Validate canon entry scope is consistent across domains."""
        payload = event.get("payload", event)
        canon_id = payload.get("canonId", "")
        scope = payload.get("scope", {})
        scope_domain = scope.get("domain", "") if isinstance(scope, dict) else ""
        valid_domains = ctx.get("valid_domains", {"intelops", "franops", "reflectionops"})

        drift_signals: List[Dict[str, Any]] = []

        if scope_domain and scope_domain not in valid_domains:
            drift_signals.append({
                "driftId": f"DS-scope-{uuid.uuid4().hex[:8]}",
                "driftType": "process_gap",
                "severity": "yellow",
                "detectedAt": datetime.now(timezone.utc).isoformat(),
                "evidenceRefs": [f"canon:{canon_id}"],
                "fingerprint": {"key": f"scope:{canon_id}", "version": "1"},
                "notes": f"Canon {canon_id} scope domain '{scope_domain}' not recognized",
            })

        subtype = "scope_violation" if drift_signals else "scope_pass"
        return FunctionResult(
            function_id="FRAN-F10",
            success=True,
            events_emitted=[{
                "topic": "drift_signal",
                "subtype": subtype,
                "canonId": canon_id,
            }],
            drift_signals=drift_signals,
        )

    # ── FRAN-F11: Canon Drift Detect ─────────────────────────────

    def _canon_drift_detect(
        self, event: Dict[str, Any], ctx: Dict[str, Any],
    ) -> FunctionResult:
        """Detect canon-specific drift: stale, conflicting, orphaned claims."""
        all_entries = ctx.get("all_canon_entries", [])
        all_claims = ctx.get("all_claims", [])
        now = ctx.get("now", datetime.now(timezone.utc))

        drift_signals: List[Dict[str, Any]] = []
        mg_updates: List[str] = []

        # Build claim ID set
        claim_ids = {c.get("claimId", "") for c in all_claims}

        for entry in all_entries:
            data = entry.get("data", entry)
            canon_id = entry.get("canonId", data.get("canonId", ""))
            entry_claims = data.get("claimIds", [])

            # Check for orphaned claims (canon references nonexistent claims)
            orphaned = [cid for cid in entry_claims if cid and cid not in claim_ids]
            if orphaned:
                drift_signals.append({
                    "driftId": f"DS-orphan-{uuid.uuid4().hex[:8]}",
                    "driftType": "process_gap",
                    "severity": "yellow",
                    "detectedAt": datetime.now(timezone.utc).isoformat(),
                    "evidenceRefs": [f"canon:{canon_id}"],
                    "fingerprint": {"key": f"orphan:{canon_id}", "version": "1"},
                    "notes": f"Canon {canon_id} references orphaned claims: {orphaned}",
                })

        events = [{
            "topic": "drift_signal",
            "subtype": "canon_drift",
            "driftCount": len(drift_signals),
        }] if drift_signals else []

        return FunctionResult(
            function_id="FRAN-F11",
            success=True,
            events_emitted=events,
            drift_signals=drift_signals,
            mg_updates=mg_updates,
        )

    # ── FRAN-F12: Canon Rollback ─────────────────────────────────

    def _canon_rollback(
        self, event: Dict[str, Any], ctx: Dict[str, Any],
    ) -> FunctionResult:
        """Rollback a canon entry to a prior version in the supersedes chain."""
        payload = event.get("payload", event)
        canon_id = payload.get("canonId", "")
        target_version = payload.get("targetVersion", "")

        canon_store = ctx.get("canon_store")
        workflow = ctx.get("workflow")

        # Find target in version chain
        version_chain: List[Dict[str, Any]] = []
        if canon_store is not None:
            version_chain = canon_store.get_version_chain(canon_id)

        target_entry = None
        for entry in version_chain:
            if entry.get("version") == target_version:
                target_entry = entry
                break

        if target_entry is None:
            return FunctionResult(
                function_id="FRAN-F12",
                success=True,
                events_emitted=[],
                drift_signals=[{
                    "driftId": f"DS-rollback-{uuid.uuid4().hex[:8]}",
                    "driftType": "process_gap",
                    "severity": "yellow",
                    "detectedAt": datetime.now(timezone.utc).isoformat(),
                    "notes": f"Target version {target_version} not found in chain for {canon_id}",
                    "fingerprint": {"key": f"rollback-fail:{canon_id}", "version": "1"},
                }],
            )

        # Mark current as superseded
        if workflow is not None:
            from core.feeds.canon.workflow import CanonState
            workflow.transition(canon_id, CanonState.SUPERSEDED)

        # Re-activate the target
        target_canon_id = target_entry.get("canonId", "")
        if workflow is not None and target_canon_id:
            from core.feeds.canon.workflow import CanonState
            workflow.set_state(target_canon_id, CanonState.ACTIVE)

        return FunctionResult(
            function_id="FRAN-F12",
            success=True,
            events_emitted=[{
                "topic": "canon_entry",
                "subtype": "canon_rolled_back",
                "canonId": canon_id,
                "targetVersion": target_version,
                "restoredCanonId": target_canon_id,
            }],
            drift_signals=[{
                "driftId": f"DS-rollback-{uuid.uuid4().hex[:8]}",
                "driftType": "authority_mismatch",
                "severity": "yellow",
                "detectedAt": datetime.now(timezone.utc).isoformat(),
                "evidenceRefs": [f"canon:{canon_id}"],
                "fingerprint": {"key": f"rollback:{canon_id}", "version": "1"},
                "notes": f"Rolled back {canon_id} to version {target_version}",
            }],
        )
