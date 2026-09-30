from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Iterable, Mapping, TYPE_CHECKING

from .authority import AuthorityGrant, AuthorityRegistry, AuthorityStatus
from .evidence import EvidenceRecord, EvidenceStatus
from .exceptions import DuplicateRecordError
from .provenance import ProvenanceLedger, ProvenanceRecord
from .receipts import sha256_receipt

if TYPE_CHECKING:
    from .constraints import Constraint
    from .models import Hypothesis


class GovernanceStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    UNKNOWN = "UNKNOWN"


class GovernanceCategory(str, Enum):
    EVIDENCE = "EVIDENCE"
    PROVENANCE = "PROVENANCE"
    AUTHORITY = "AUTHORITY"


@dataclass(frozen=True)
class GovernanceEvaluation:
    target_type: str
    target_id: str
    category: GovernanceCategory
    status: GovernanceStatus
    ref_id: str | None
    reason: str = ""
    details: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class GovernancePolicy:
    """Controls which governance facts must exist before a candidate may be accepted."""

    name: str = "COMPATIBILITY_V0_1"
    require_hypothesis_evidence: bool = False
    require_hypothesis_provenance: bool = False
    require_constraint_evidence: bool = False
    require_constraint_provenance: bool = False
    require_constraint_authority: bool = False
    require_authority_provenance: bool = False
    require_authority_evidence: bool = False
    require_materialized_evidence: bool = False
    authority_action: str = "DEFINE_CONSTRAINT"

    @classmethod
    def compatibility(cls) -> "GovernancePolicy":
        return cls()

    @classmethod
    def strict(cls) -> "GovernancePolicy":
        return cls(
            name="STRICT_V0_2",
            require_hypothesis_evidence=True,
            require_hypothesis_provenance=True,
            require_constraint_provenance=True,
            require_constraint_authority=True,
            require_authority_provenance=True,
            authority_action="DEFINE_CONSTRAINT",
        )


    @classmethod
    def trusted(cls) -> "GovernancePolicy":
        """Strict governance semantics intended for root-signed v0.3 contexts."""
        return cls(
            name="TRUSTED_V0_3",
            require_hypothesis_evidence=True,
            require_hypothesis_provenance=True,
            require_constraint_provenance=True,
            require_constraint_authority=True,
            require_authority_provenance=True,
            authority_action="DEFINE_CONSTRAINT",
        )

    @classmethod
    def authoritative(cls) -> "GovernancePolicy":
        """Governance gates for v0.4 COMPOSER-authoritative operation.

        The rule semantics intentionally match trusted v0.3; v0.4 changes where the
        context is allowed to come from, not how evidence/provenance/authority are
        interpreted.
        """
        return cls(
            name="AUTHORITATIVE_V0_4",
            require_hypothesis_evidence=True,
            require_hypothesis_provenance=True,
            require_constraint_provenance=True,
            require_constraint_authority=True,
            require_authority_provenance=True,
            authority_action="DEFINE_CONSTRAINT",
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "require_hypothesis_evidence": self.require_hypothesis_evidence,
            "require_hypothesis_provenance": self.require_hypothesis_provenance,
            "require_constraint_evidence": self.require_constraint_evidence,
            "require_constraint_provenance": self.require_constraint_provenance,
            "require_constraint_authority": self.require_constraint_authority,
            "require_authority_provenance": self.require_authority_provenance,
            "require_authority_evidence": self.require_authority_evidence,
            "require_materialized_evidence": self.require_materialized_evidence,
            "authority_action": self.authority_action,
        }


class GovernanceContext:
    """Immutable-at-use materialized governance context.

    The context is deterministic input to the engine. It verifies internal consistency,
    lineage completeness, status, action, and scope. On its own it does *not* establish
    enterprise authenticity; v0.3 trusted mode authenticates the complete context as a
    root-signed, epoch-ordered governance bundle.
    """

    def __init__(
        self,
        *,
        evidence: Iterable[EvidenceRecord] = (),
        provenance: Iterable[ProvenanceRecord] = (),
        authorities: Iterable[AuthorityGrant] = (),
        context_id: str = "",
        metadata: Mapping[str, Any] | None = None,
    ) -> None:
        self.context_id = context_id
        self.metadata = dict(metadata or {})
        self.evidence = tuple(evidence)
        self.provenance = tuple(provenance)
        self.authorities = tuple(authorities)

        self._evidence: dict[str, EvidenceRecord] = {}
        for record in self.evidence:
            if record.id in self._evidence:
                raise DuplicateRecordError(f"duplicate evidence id: {record.id}")
            self._evidence[record.id] = record

        self.provenance_ledger = ProvenanceLedger(self.provenance)
        self.authority_registry = AuthorityRegistry(self.authorities)

    def _evidence_check(
        self,
        *,
        target_type: str,
        target_id: str,
        ref_id: str,
        require_materialized: bool,
    ) -> GovernanceEvaluation:
        record = self._evidence.get(ref_id)
        if record is None:
            return GovernanceEvaluation(
                target_type, target_id, GovernanceCategory.EVIDENCE,
                GovernanceStatus.UNKNOWN, ref_id, "evidence record not found"
            )
        if record.status is not EvidenceStatus.ACTIVE:
            return GovernanceEvaluation(
                target_type, target_id, GovernanceCategory.EVIDENCE,
                GovernanceStatus.FAIL, ref_id,
                f"evidence status is {record.status.value}",
                {"sha256": record.sha256},
            )
        if record.materialized:
            current_digest = sha256_receipt(record.payload)
            if current_digest != record.sha256:
                return GovernanceEvaluation(
                    target_type, target_id, GovernanceCategory.EVIDENCE,
                    GovernanceStatus.FAIL, ref_id,
                    "materialized evidence content no longer matches its recorded digest",
                    {"sha256": record.sha256, "computed_sha256": current_digest},
                )
        if require_materialized and not record.materialized:
            return GovernanceEvaluation(
                target_type, target_id, GovernanceCategory.EVIDENCE,
                GovernanceStatus.UNKNOWN, ref_id,
                "evidence content is not materialized for local digest verification",
                {"sha256": record.sha256},
            )
        return GovernanceEvaluation(
            target_type, target_id, GovernanceCategory.EVIDENCE,
            GovernanceStatus.PASS, ref_id, "",
            {"sha256": record.sha256, "materialized": record.materialized},
        )

    def _provenance_check(
        self,
        *,
        target_type: str,
        target_id: str,
        ref_id: str,
    ) -> GovernanceEvaluation:
        status, reason = self.provenance_ledger.validate(ref_id)
        gs = GovernanceStatus(status)
        return GovernanceEvaluation(
            target_type, target_id, GovernanceCategory.PROVENANCE,
            gs, ref_id, reason,
            {"lineage": list(self.provenance_ledger.lineage(ref_id))},
        )

    def _authority_check(
        self,
        *,
        target_type: str,
        target_id: str,
        grant_id: str,
        action: str,
        scope: str,
        policy: GovernancePolicy,
    ) -> list[GovernanceEvaluation]:
        grant = self.authority_registry.get(grant_id)
        if grant is None:
            return [GovernanceEvaluation(
                target_type, target_id, GovernanceCategory.AUTHORITY,
                GovernanceStatus.UNKNOWN, grant_id, "authority grant not found",
                {"action": action, "scope": scope},
            )]

        if grant.status is not AuthorityStatus.ACTIVE:
            return [GovernanceEvaluation(
                target_type, target_id, GovernanceCategory.AUTHORITY,
                GovernanceStatus.FAIL, grant_id,
                f"authority status is {grant.status.value}",
                {"action": action, "scope": scope},
            )]

        if not grant.allows(action=action, scope=scope):
            return [GovernanceEvaluation(
                target_type, target_id, GovernanceCategory.AUTHORITY,
                GovernanceStatus.FAIL, grant_id,
                "authority grant does not allow requested action/scope",
                {"action": action, "scope": scope, "role": grant.role},
            )]

        out = [GovernanceEvaluation(
            target_type, target_id, GovernanceCategory.AUTHORITY,
            GovernanceStatus.PASS, grant_id, "",
            {
                "action": action,
                "scope": scope,
                "principal_id": grant.principal_id,
                "role": grant.role,
            },
        )]

        if grant.provenance_ref:
            out.append(self._provenance_check(
                target_type="authority",
                target_id=grant.id,
                ref_id=grant.provenance_ref,
            ))
        elif policy.require_authority_provenance:
            out.append(GovernanceEvaluation(
                "authority", grant.id, GovernanceCategory.PROVENANCE,
                GovernanceStatus.UNKNOWN, None,
                "authority provenance is required but not declared",
            ))

        if grant.evidence_refs:
            for ref_id in grant.evidence_refs:
                out.append(self._evidence_check(
                    target_type="authority",
                    target_id=grant.id,
                    ref_id=ref_id,
                    require_materialized=policy.require_materialized_evidence,
                ))
        elif policy.require_authority_evidence:
            out.append(GovernanceEvaluation(
                "authority", grant.id, GovernanceCategory.EVIDENCE,
                GovernanceStatus.UNKNOWN, None,
                "authority evidence is required but not declared",
            ))

        return out

    def evaluate_hypothesis(
        self,
        hypothesis: "Hypothesis",
        policy: GovernancePolicy,
    ) -> tuple[GovernanceEvaluation, ...]:
        out: list[GovernanceEvaluation] = []

        if hypothesis.evidence_refs:
            for ref_id in hypothesis.evidence_refs:
                out.append(self._evidence_check(
                    target_type="hypothesis",
                    target_id=hypothesis.id,
                    ref_id=ref_id,
                    require_materialized=policy.require_materialized_evidence,
                ))
        elif policy.require_hypothesis_evidence:
            out.append(GovernanceEvaluation(
                "hypothesis", hypothesis.id, GovernanceCategory.EVIDENCE,
                GovernanceStatus.UNKNOWN, None,
                "hypothesis evidence is required but not declared",
            ))

        if hypothesis.provenance_ref:
            out.append(self._provenance_check(
                target_type="hypothesis",
                target_id=hypothesis.id,
                ref_id=hypothesis.provenance_ref,
            ))
        elif policy.require_hypothesis_provenance:
            out.append(GovernanceEvaluation(
                "hypothesis", hypothesis.id, GovernanceCategory.PROVENANCE,
                GovernanceStatus.UNKNOWN, None,
                "hypothesis provenance is required but not declared",
            ))

        return tuple(out)

    def evaluate_constraint(
        self,
        constraint: "Constraint",
        policy: GovernancePolicy,
    ) -> tuple[GovernanceEvaluation, ...]:
        out: list[GovernanceEvaluation] = []

        if constraint.evidence_refs:
            for ref_id in constraint.evidence_refs:
                out.append(self._evidence_check(
                    target_type="constraint",
                    target_id=constraint.id,
                    ref_id=ref_id,
                    require_materialized=policy.require_materialized_evidence,
                ))
        elif policy.require_constraint_evidence:
            out.append(GovernanceEvaluation(
                "constraint", constraint.id, GovernanceCategory.EVIDENCE,
                GovernanceStatus.UNKNOWN, None,
                "constraint evidence is required but not declared",
            ))

        if constraint.provenance_ref:
            out.append(self._provenance_check(
                target_type="constraint",
                target_id=constraint.id,
                ref_id=constraint.provenance_ref,
            ))
        elif policy.require_constraint_provenance:
            out.append(GovernanceEvaluation(
                "constraint", constraint.id, GovernanceCategory.PROVENANCE,
                GovernanceStatus.UNKNOWN, None,
                "constraint provenance is required but not declared",
            ))

        if constraint.authority_ref:
            out.extend(self._authority_check(
                target_type="constraint",
                target_id=constraint.id,
                grant_id=constraint.authority_ref,
                action=constraint.authority_action or policy.authority_action,
                scope=constraint.authority_scope,
                policy=policy,
            ))
        elif policy.require_constraint_authority:
            out.append(GovernanceEvaluation(
                "constraint", constraint.id, GovernanceCategory.AUTHORITY,
                GovernanceStatus.UNKNOWN, None,
                "constraint authority is required but not declared",
                {"action": constraint.authority_action or policy.authority_action,
                 "scope": constraint.authority_scope},
            ))

        return tuple(out)

    def receipt_view(self) -> dict[str, Any]:
        return {
            "context_id": self.context_id,
            "metadata": dict(self.metadata),
            "evidence": [self._evidence[k].receipt_view() for k in sorted(self._evidence)],
            "provenance": self.provenance_ledger.receipt_view(),
            "authorities": self.authority_registry.receipt_view(),
        }

    def to_dict(self, *, include_payload: bool = False) -> dict[str, Any]:
        evidence = []
        for record in sorted(self.evidence, key=lambda r: r.id):
            row = record.receipt_view()
            if include_payload:
                row["payload"] = record.payload
            evidence.append(row)
        return {
            "context_id": self.context_id,
            "metadata": dict(self.metadata),
            "evidence": evidence,
            "provenance": self.provenance_ledger.receipt_view(),
            "authorities": self.authority_registry.receipt_view(),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "GovernanceContext":
        evidence = tuple(
            EvidenceRecord(
                id=str(row["id"]),
                kind=str(row["kind"]),
                source=str(row["source"]),
                sha256=str(row["sha256"]),
                payload=row.get("payload"),
                status=str(row.get("status", "ACTIVE")),
                observed_at=str(row.get("observed_at", "")),
                metadata=dict(row.get("metadata", {})),
            )
            for row in value.get("evidence", ())
        )
        provenance = tuple(
            ProvenanceRecord(
                id=str(row["id"]),
                kind=str(row["kind"]),
                artifact_sha256=str(row["artifact_sha256"]),
                source=str(row["source"]),
                version=str(row.get("version", "")),
                parent_ids=tuple(row.get("parent_ids", ())),
                status=str(row.get("status", "ACTIVE")),
                metadata=dict(row.get("metadata", {})),
            )
            for row in value.get("provenance", ())
        )
        authorities = tuple(
            AuthorityGrant(
                id=str(row["id"]),
                principal_id=str(row["principal_id"]),
                role=str(row["role"]),
                actions=tuple(row.get("actions", ())),
                scopes=tuple(row.get("scopes", ("*",))),
                status=str(row.get("status", "ACTIVE")),
                provenance_ref=row.get("provenance_ref"),
                evidence_refs=tuple(row.get("evidence_refs", ())),
                metadata=dict(row.get("metadata", {})),
            )
            for row in value.get("authorities", ())
        )
        return cls(
            context_id=str(value.get("context_id", "")),
            metadata=dict(value.get("metadata", {})),
            evidence=evidence,
            provenance=provenance,
            authorities=authorities,
        )

    def sha256(self) -> str:
        return sha256_receipt(self.receipt_view())


def governance_status(evaluations: Iterable[GovernanceEvaluation]) -> GovernanceStatus:
    rows = tuple(evaluations)
    if any(e.status is GovernanceStatus.FAIL for e in rows):
        return GovernanceStatus.FAIL
    if any(e.status is GovernanceStatus.UNKNOWN for e in rows):
        return GovernanceStatus.UNKNOWN
    return GovernanceStatus.PASS


def governance_coverage(evaluations: Iterable[GovernanceEvaluation]) -> float:
    rows = tuple(evaluations)
    if not rows:
        return 1.0
    decided = sum(e.status in (GovernanceStatus.PASS, GovernanceStatus.FAIL) for e in rows)
    return decided / len(rows)
