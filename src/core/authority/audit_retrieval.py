"""Audit Retrieval — Primitive 6: Forensic Query Interface.

Provides natural-language-style queries over the evidence chain and
authority audit log: "Why was this allowed?", "Which rule fired?",
"What assumption failed?".
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .authority_audit import AuthorityAuditLog
from .evidence_chain import EvidenceChain, EvidenceEntry


@dataclass
class AuditAnswer:
    """Structured answer to a forensic audit query."""

    query_type: str
    action_id: str
    found: bool
    verdict: str = ""
    detail: str = ""
    evidence: Optional[Dict[str, Any]] = None
    entries: List[Dict[str, Any]] = field(default_factory=list)


class AuditRetrieval:
    """Forensic query interface over evidence chain and audit log.

    Accepts an EvidenceChain and/or AuthorityAuditLog and provides
    structured answers to common audit questions.
    """

    def __init__(
        self,
        evidence_chain: Optional[EvidenceChain] = None,
        audit_log: Optional[AuthorityAuditLog] = None,
    ) -> None:
        self._chain = evidence_chain
        self._audit = audit_log

    def _find_entries(self, action_id: str) -> List[EvidenceEntry]:
        """Find evidence entries matching an action_id."""
        if self._chain is None:
            return []
        return [e for e in self._chain.entries if e.action_id == action_id]

    def why_allowed(self, action_id: str) -> AuditAnswer:
        """Why was this action allowed? Returns passed checks and artifact used."""
        entries = self._find_entries(action_id)
        allowed = [e for e in entries if e.verdict == "ALLOW"]
        if not allowed:
            return AuditAnswer(
                query_type="why_allowed", action_id=action_id, found=False,
                detail="no ALLOW verdict found",
            )
        latest = allowed[-1]
        return AuditAnswer(
            query_type="why_allowed",
            action_id=action_id,
            found=True,
            verdict="ALLOW",
            detail=f"passed {len(latest.passed_checks)} checks",
            evidence={
                "artifact_id": latest.artifact_id,
                "policy_hash": latest.policy_hash,
                "passed_checks": latest.passed_checks,
            },
        )

    def why_blocked(self, action_id: str) -> AuditAnswer:
        """Why was this action blocked? Returns the failed check and terminal verdict."""
        entries = self._find_entries(action_id)
        blocked = [e for e in entries if e.verdict != "ALLOW"]
        if not blocked:
            return AuditAnswer(
                query_type="why_blocked", action_id=action_id, found=False,
                detail="no block verdict found",
            )
        latest = blocked[-1]
        return AuditAnswer(
            query_type="why_blocked",
            action_id=action_id,
            found=True,
            verdict=latest.verdict,
            detail=f"failed: {', '.join(latest.failed_checks)}" if latest.failed_checks else "blocked",
            evidence={
                "artifact_id": latest.artifact_id,
                "failed_checks": latest.failed_checks,
            },
        )

    def which_rule_fired(self, action_id: str) -> AuditAnswer:
        """Which specific constraint decided the verdict?"""
        entries = self._find_entries(action_id)
        if not entries:
            return AuditAnswer(
                query_type="which_rule_fired", action_id=action_id, found=False,
            )
        latest = entries[-1]
        # The first failed check is typically the deciding rule
        deciding = latest.failed_checks[0] if latest.failed_checks else "all_passed"
        return AuditAnswer(
            query_type="which_rule_fired",
            action_id=action_id,
            found=True,
            verdict=latest.verdict,
            detail=deciding,
        )

    def which_assumption_failed(self, action_id: str) -> AuditAnswer:
        """Which assumption was stale when this action was evaluated?"""
        entries = self._find_entries(action_id)
        if not entries:
            return AuditAnswer(
                query_type="which_assumption_failed", action_id=action_id, found=False,
            )
        latest = entries[-1]
        stale = latest.assumptions_snapshot.get("stale", [])
        if not stale and "assumption_validate" not in latest.failed_checks:
            return AuditAnswer(
                query_type="which_assumption_failed",
                action_id=action_id,
                found=True,
                detail="no stale assumptions",
                verdict=latest.verdict,
            )
        return AuditAnswer(
            query_type="which_assumption_failed",
            action_id=action_id,
            found=True,
            verdict=latest.verdict,
            detail=f"stale: {', '.join(stale)}" if stale else "assumption_validate failed",
            evidence={"assumptions_snapshot": latest.assumptions_snapshot},
        )

    def which_policy_hash(self, action_id: str) -> AuditAnswer:
        """What policy hash was used for this evaluation?"""
        entries = self._find_entries(action_id)
        if not entries:
            return AuditAnswer(
                query_type="which_policy_hash", action_id=action_id, found=False,
            )
        latest = entries[-1]
        return AuditAnswer(
            query_type="which_policy_hash",
            action_id=action_id,
            found=True,
            verdict=latest.verdict,
            detail=latest.policy_hash,
            evidence={"artifact_id": latest.artifact_id, "policy_hash": latest.policy_hash},
        )

    def actor_history(self, actor_id: str) -> List[AuditAnswer]:
        """All evaluations for a given actor, chronological."""
        if self._chain is None:
            return []
        entries = [e for e in self._chain.entries if e.actor_id == actor_id]
        return [
            AuditAnswer(
                query_type="actor_history",
                action_id=e.action_id,
                found=True,
                verdict=e.verdict,
                detail=f"gate={e.gate_id}",
                evidence={"evaluated_at": e.evaluated_at, "artifact_id": e.artifact_id},
            )
            for e in entries
        ]

    def resource_history(self, resource_id: str) -> List[AuditAnswer]:
        """All evaluations for a given resource, chronological."""
        if self._chain is None:
            return []
        entries = [e for e in self._chain.entries if e.resource_id == resource_id]
        return [
            AuditAnswer(
                query_type="resource_history",
                action_id=e.action_id,
                found=True,
                verdict=e.verdict,
                detail=f"gate={e.gate_id}",
                evidence={"evaluated_at": e.evaluated_at, "artifact_id": e.artifact_id},
            )
            for e in entries
        ]
