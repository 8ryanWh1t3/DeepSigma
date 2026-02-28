"""IntelOps domain mode — claim lifecycle automation.

Wraps existing FEEDS consumers (ClaimValidator, ClaimTriggerPipeline,
AuthorityGateConsumer, EvidenceCheckConsumer, TriageStore) into
12 function handlers keyed by INTEL-F01 through INTEL-F12.

The atomic loop: ingest -> validate -> drift -> patch -> MG update.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .base import DomainMode, FunctionResult


class IntelOps(DomainMode):
    """IntelOps domain: claim ingest, validation, drift, patching, and MG updates."""

    domain = "intelops"

    def _register_handlers(self) -> None:
        self._handlers = {
            "INTEL-F01": self._claim_ingest,
            "INTEL-F02": self._claim_validate,
            "INTEL-F03": self._claim_drift_detect,
            "INTEL-F04": self._claim_patch_recommend,
            "INTEL-F05": self._claim_mg_update,
            "INTEL-F06": self._claim_canon_promote,
            "INTEL-F07": self._claim_authority_check,
            "INTEL-F08": self._claim_evidence_verify,
            "INTEL-F09": self._claim_triage,
            "INTEL-F10": self._claim_supersede,
            "INTEL-F11": self._claim_half_life_check,
            "INTEL-F12": self._claim_confidence_recalc,
        }

    # ── INTEL-F01: Claim Ingest ─────────────────────────────────

    def _claim_ingest(
        self, event: Dict[str, Any], ctx: Dict[str, Any],
    ) -> FunctionResult:
        """Ingest a new claim into the canon store and memory graph."""
        payload = event.get("payload", event)
        claim_id = payload.get("claimId", f"CLAIM-{uuid.uuid4().hex[:8]}")

        canon_store = ctx.get("canon_store")
        mg = ctx.get("memory_graph")

        events: List[Dict[str, Any]] = []
        mg_updates: List[str] = []

        # Persist to canon store
        if canon_store is not None:
            canon_store.add({
                "canonId": f"CANON-{claim_id}",
                "title": payload.get("statement", ""),
                "claimIds": [claim_id],
                "version": "1.0.0",
            })

        # Record in memory graph
        if mg is not None:
            node_id = mg.add_claim(payload)
            if node_id:
                mg_updates.append(node_id)

        events.append({
            "topic": "canon_entry",
            "subtype": "claim_accepted",
            "claimId": claim_id,
        })

        return FunctionResult(
            function_id="INTEL-F01",
            success=True,
            events_emitted=events,
            mg_updates=mg_updates,
        )

    # ── INTEL-F02: Claim Validate ───────────────────────────────

    def _claim_validate(
        self, event: Dict[str, Any], ctx: Dict[str, Any],
    ) -> FunctionResult:
        """Validate a claim for contradictions, TTL, and consistency."""
        payload = event.get("payload", event)
        claim_id = payload.get("claimId", "")
        claim = ctx.get("claims", {}).get(claim_id, payload)

        from core.feeds.canon.claim_validator import ClaimValidator

        canon_claims = ctx.get("canon_claims", [])
        validator = ClaimValidator(canon_claims=canon_claims)
        issues = validator.validate_claim(claim, now=ctx.get("now"))

        drift_signals = [
            validator.build_drift_signal(issue)
            for issue in issues
        ]
        events: List[Dict[str, Any]] = []

        if not issues:
            events.append({
                "topic": "canon_entry",
                "subtype": "claim_valid",
                "claimId": claim_id,
            })
        else:
            for issue in issues:
                subtype = {
                    "contradiction": "claim_contradiction",
                    "expired": "claim_expired",
                    "inconsistent": "claim_expired",
                }.get(issue.get("type", ""), "claim_expired")
                events.append({
                    "topic": "drift_signal",
                    "subtype": subtype,
                    "claimId": claim_id,
                    "issue": issue,
                })

        return FunctionResult(
            function_id="INTEL-F02",
            success=True,
            events_emitted=events,
            drift_signals=drift_signals,
        )

    # ── INTEL-F03: Claim Drift Detect ───────────────────────────

    def _claim_drift_detect(
        self, event: Dict[str, Any], ctx: Dict[str, Any],
    ) -> FunctionResult:
        """Record drift from claim validation failures."""
        payload = event.get("payload", event)
        ds = ctx.get("drift_collector")
        mg = ctx.get("memory_graph")

        signals = payload.get("drift_signals", [payload])
        mg_updates: List[str] = []

        if ds is not None:
            ds.ingest(signals)

        if mg is not None:
            for sig in signals:
                node_id = mg.add_drift(sig)
                if node_id:
                    mg_updates.append(node_id)

        events = [{
            "topic": "drift_signal",
            "subtype": "claim_drift",
            "driftType": sig.get("driftType", "process_gap"),
        } for sig in signals]

        return FunctionResult(
            function_id="INTEL-F03",
            success=True,
            events_emitted=events,
            drift_signals=signals,
            mg_updates=mg_updates,
        )

    # ── INTEL-F04: Claim Patch Recommend ────────────────────────

    def _claim_patch_recommend(
        self, event: Dict[str, Any], ctx: Dict[str, Any],
    ) -> FunctionResult:
        """Generate a patch recommendation from a drift signal."""
        payload = event.get("payload", event)
        drift_type = payload.get("driftType", "process_gap")

        patch_type_map = {
            "authority_mismatch": "authority_update",
            "freshness": "ttl_change",
            "process_gap": "manual_review",
            "confidence_decay": "manual_review",
            "time": "dte_change",
            "fallback": "cache_bundle_change",
            "verify": "verification_change",
            "outcome": "action_scope_tighten",
        }

        # Derive deterministic patchId from fingerprint for replay
        fp = payload.get("fingerprint", {})
        fp_key = f"{fp.get('key', '')}:{fp.get('version', '')}"
        import hashlib as _hl
        patch_id = f"PATCH-{_hl.sha256(fp_key.encode()).hexdigest()[:8]}"

        patch = {
            "patchId": patch_id,
            "patchType": patch_type_map.get(drift_type, "manual_review"),
            "driftType": drift_type,
            "fingerprint": fp,
        }

        mg = ctx.get("memory_graph")
        mg_updates: List[str] = []
        if mg is not None:
            node_id = mg.add_patch(patch)
            if node_id:
                mg_updates.append(node_id)

        return FunctionResult(
            function_id="INTEL-F04",
            success=True,
            events_emitted=[{
                "topic": "canon_entry",
                "subtype": "patch_recommended",
                "patch": patch,
            }],
            mg_updates=mg_updates,
        )

    # ── INTEL-F05: Claim MG Update ──────────────────────────────

    def _claim_mg_update(
        self, event: Dict[str, Any], ctx: Dict[str, Any],
    ) -> FunctionResult:
        """Update the Memory Graph with claim/drift/patch nodes."""
        payload = event.get("payload", event)
        mg = ctx.get("memory_graph")
        mg_updates: List[str] = []

        if mg is not None:
            # Attempt to add whatever data is present
            if "claimId" in payload:
                nid = mg.add_claim(payload)
                if nid:
                    mg_updates.append(nid)
            if "driftId" in payload:
                nid = mg.add_drift(payload)
                if nid:
                    mg_updates.append(nid)
            if "patchId" in payload:
                nid = mg.add_patch(payload)
                if nid:
                    mg_updates.append(nid)

        return FunctionResult(
            function_id="INTEL-F05",
            success=True,
            events_emitted=[{
                "topic": "canon_entry",
                "subtype": "mg_updated",
            }],
            mg_updates=mg_updates,
        )

    # ── INTEL-F06: Claim Canon Promote ──────────────────────────

    def _claim_canon_promote(
        self, event: Dict[str, Any], ctx: Dict[str, Any],
    ) -> FunctionResult:
        """Promote a validated claim to canon entry."""
        payload = event.get("payload", event)
        claim_id = payload.get("claimId", "")
        confidence = payload.get("confidence", {})
        score = confidence.get("score", 0) if isinstance(confidence, dict) else confidence

        threshold = ctx.get("promotion_threshold", 0.7)
        canon_store = ctx.get("canon_store")

        if score < threshold:
            return FunctionResult(
                function_id="INTEL-F06",
                success=True,
                events_emitted=[],
                error=f"Confidence {score} below promotion threshold {threshold}",
            )

        if canon_store is not None:
            canon_store.add({
                "canonId": f"CANON-{claim_id}",
                "title": payload.get("statement", ""),
                "claimIds": [claim_id],
                "version": "1.0.0",
                "blessedBy": "auto-promote",
                "blessedAt": datetime.now(timezone.utc).isoformat(),
            })

        return FunctionResult(
            function_id="INTEL-F06",
            success=True,
            events_emitted=[{
                "topic": "canon_entry",
                "subtype": "canon_promoted",
                "claimId": claim_id,
            }],
        )

    # ── INTEL-F07: Claim Authority Check ────────────────────────

    def _claim_authority_check(
        self, event: Dict[str, Any], ctx: Dict[str, Any],
    ) -> FunctionResult:
        """Verify claim action is blessed by authority slice."""
        payload = event.get("payload", event)
        claims = payload.get("claims", {})
        action_claims = claims.get("action", []) if isinstance(claims, dict) else []
        blessed_claims = ctx.get("blessed_claims", set())

        drift_signals: List[Dict[str, Any]] = []
        for cid in action_claims:
            if cid not in blessed_claims:
                drift_signals.append({
                    "driftId": f"DS-auth-{uuid.uuid4().hex[:8]}",
                    "driftType": "authority_mismatch",
                    "severity": "red",
                    "detectedAt": datetime.now(timezone.utc).isoformat(),
                    "evidenceRefs": [f"claim:{cid}"],
                    "fingerprint": {"key": f"authority:{cid}", "version": "1"},
                })

        subtype = "authority_mismatch" if drift_signals else "authority_pass"
        return FunctionResult(
            function_id="INTEL-F07",
            success=True,
            events_emitted=[{
                "topic": "drift_signal",
                "subtype": subtype,
            }],
            drift_signals=drift_signals,
        )

    # ── INTEL-F08: Claim Evidence Verify ────────────────────────

    def _claim_evidence_verify(
        self, event: Dict[str, Any], ctx: Dict[str, Any],
    ) -> FunctionResult:
        """Verify claim evidence references exist in packet manifest."""
        payload = event.get("payload", event)
        evidence_refs = payload.get("evidenceRefs", [])
        manifest_artifacts = ctx.get("manifest_artifacts", set())

        missing = [ref for ref in evidence_refs if ref not in manifest_artifacts]
        drift_signals: List[Dict[str, Any]] = []

        if missing:
            drift_signals.append({
                "driftId": f"DS-evidence-{uuid.uuid4().hex[:8]}",
                "driftType": "process_gap",
                "severity": "yellow",
                "detectedAt": datetime.now(timezone.utc).isoformat(),
                "evidenceRefs": missing,
                "fingerprint": {"key": f"evidence-gap:{len(missing)}", "version": "1"},
            })

        subtype = "evidence_gap" if drift_signals else "evidence_pass"
        return FunctionResult(
            function_id="INTEL-F08",
            success=True,
            events_emitted=[{
                "topic": "drift_signal",
                "subtype": subtype,
            }],
            drift_signals=drift_signals,
        )

    # ── INTEL-F09: Claim Triage ─────────────────────────────────

    def _claim_triage(
        self, event: Dict[str, Any], ctx: Dict[str, Any],
    ) -> FunctionResult:
        """Triage drift signals by severity."""
        payload = event.get("payload", event)
        severity = payload.get("severity", "green")
        triage_store = ctx.get("triage_store")

        if triage_store is not None:
            triage_store.ingest_drift(payload)

        return FunctionResult(
            function_id="INTEL-F09",
            success=True,
            events_emitted=[{
                "topic": "drift_signal",
                "subtype": "triaged",
                "severity": severity,
            }],
        )

    # ── INTEL-F10: Claim Supersede ──────────────────────────────

    def _claim_supersede(
        self, event: Dict[str, Any], ctx: Dict[str, Any],
    ) -> FunctionResult:
        """Supersede a claim when a retcon or newer evidence arrives."""
        payload = event.get("payload", event)
        original_id = payload.get("originalClaimId", "")
        new_id = payload.get("newClaimId", "")

        canon_store = ctx.get("canon_store")
        mg = ctx.get("memory_graph")
        mg_updates: List[str] = []

        if canon_store is not None and new_id:
            canon_store.add({
                "canonId": f"CANON-{new_id}",
                "title": f"Supersedes {original_id}",
                "claimIds": [new_id],
                "supersedes": f"CANON-{original_id}",
                "version": "2.0.0",
            })

        if mg is not None:
            mg.add_claim(
                {
                    "claimId": new_id,
                    "statement": f"Supersedes {original_id}",
                    "confidence": {"score": 1.0},
                    "graph": {"supersedes": original_id},
                },
            )
            mg_updates.append(f"edge:{new_id}->{original_id}")

        return FunctionResult(
            function_id="INTEL-F10",
            success=True,
            events_emitted=[{
                "topic": "canon_entry",
                "subtype": "claim_superseded",
                "originalClaimId": original_id,
                "newClaimId": new_id,
            }],
            mg_updates=mg_updates,
        )

    # ── INTEL-F11: Claim Half-Life Check ────────────────────────

    def _claim_half_life_check(
        self, event: Dict[str, Any], ctx: Dict[str, Any],
    ) -> FunctionResult:
        """Sweep claims for TTL expiry based on half-life."""
        claims = ctx.get("all_claims", [])
        now = ctx.get("now")

        from core.feeds.canon.claim_validator import ClaimValidator

        validator = ClaimValidator()
        drift_signals: List[Dict[str, Any]] = []
        events: List[Dict[str, Any]] = []

        for claim in claims:
            from core.feeds.canon.claim_validator import _half_life_expired
            if _half_life_expired(claim, now=now):
                issue = {
                    "type": "expired",
                    "claimId": claim.get("claimId", ""),
                    "detail": f"Claim {claim.get('claimId', '')} TTL expired",
                    "severity": "yellow",
                }
                sig = validator.build_drift_signal(issue)
                drift_signals.append(sig)
                events.append({
                    "topic": "drift_signal",
                    "subtype": "claim_expired",
                    "claimId": claim.get("claimId", ""),
                })

        return FunctionResult(
            function_id="INTEL-F11",
            success=True,
            events_emitted=events,
            drift_signals=drift_signals,
        )

    # ── INTEL-F12: Claim Confidence Recalc ──────────────────────

    def _claim_confidence_recalc(
        self, event: Dict[str, Any], ctx: Dict[str, Any],
    ) -> FunctionResult:
        """Recalculate claim confidence based on evidence freshness and contradiction density."""
        payload = event.get("payload", event)
        claim_id = payload.get("claimId", "")
        claim = ctx.get("claims", {}).get(claim_id, payload)

        # Decay factors
        contradiction_count = ctx.get("contradiction_count", 0)
        evidence_age_days = ctx.get("evidence_age_days", 0)

        confidence = claim.get("confidence", {})
        original_score = confidence.get("score", 1.0) if isinstance(confidence, dict) else confidence

        # Simple decay model: -0.1 per contradiction, -0.01 per day of evidence age
        decay = (contradiction_count * 0.1) + (evidence_age_days * 0.01)
        new_score = max(0.0, min(1.0, original_score - decay))

        drift_signals: List[Dict[str, Any]] = []
        events: List[Dict[str, Any]] = []

        if new_score < original_score:
            drift_signals.append({
                "driftId": f"DS-confidence-{uuid.uuid4().hex[:8]}",
                "driftType": "confidence_decay",
                "severity": "yellow" if new_score >= 0.3 else "red",
                "detectedAt": datetime.now(timezone.utc).isoformat(),
                "evidenceRefs": [f"claim:{claim_id}"],
                "fingerprint": {"key": f"confidence-decay:{claim_id}", "version": "1"},
                "notes": f"Confidence decayed from {original_score:.2f} to {new_score:.2f}",
            })

        events.append({
            "topic": "canon_entry",
            "subtype": "confidence_updated",
            "claimId": claim_id,
            "oldScore": original_score,
            "newScore": new_score,
        })

        return FunctionResult(
            function_id="INTEL-F12",
            success=True,
            events_emitted=events,
            drift_signals=drift_signals,
        )
