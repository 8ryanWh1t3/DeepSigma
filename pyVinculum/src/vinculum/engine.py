from __future__ import annotations

from dataclasses import replace
from typing import Iterable

from .constraints import Constraint
from .governance import (
    GovernanceContext,
    GovernancePolicy,
    GovernanceStatus,
    governance_coverage,
    governance_status,
)
from .metrics import report_metrics
from .models import (
    BindingReport,
    BindingResult,
    BoundedState,
    ConstraintStatus,
    Hypothesis,
)


class VinculumEngine:
    """Deterministic P + D → B binding engine with optional governance gates."""

    def __init__(
        self,
        *,
        require_hard_constraint: bool = True,
        governance_policy: GovernancePolicy | None = None,
    ) -> None:
        self.require_hard_constraint = require_hard_constraint
        self.governance_policy = governance_policy or GovernancePolicy.compatibility()

    def bind(
        self,
        hypotheses: Iterable[Hypothesis],
        constraints: Iterable[Constraint],
        *,
        context: GovernanceContext | None = None,
    ) -> BindingReport:
        hs = tuple(hypotheses)
        ds = tuple(constraints)
        ctx = context or GovernanceContext()

        # Constraint governance is candidate-independent and therefore resolved once.
        constraint_governance = tuple(
            evaluation
            for constraint in ds
            for evaluation in ctx.evaluate_constraint(constraint, self.governance_policy)
        )

        results = tuple(self._bind_one(h, ds, ctx, constraint_governance) for h in hs)

        accepted = [r for r in results if r.state is BoundedState.ACCEPTED]
        best = None
        if accepted:
            # Deterministic ordering: governed coherence first, retained P second, stable ID last.
            accepted.sort(
                key=lambda r: (
                    -r.coherence_score,
                    -r.bounded_confidence,
                    -r.hypothesis.probability,
                    r.hypothesis.id,
                )
            )
            best = accepted[0].hypothesis.id

        context_hash = ctx.sha256() if (
            ctx.evidence or ctx.provenance or ctx.authorities or ctx.context_id or ctx.metadata
        ) else None

        return BindingReport(
            results=results,
            best_supported_id=best,
            metrics=report_metrics(results),
            governance_context_sha256=context_hash,
            governance_policy=self.governance_policy.to_dict(),
        )


    def bind_trusted(
        self,
        hypotheses: Iterable[Hypothesis],
        constraints: Iterable[Constraint],
        *,
        runtime,
    ) -> BindingReport:
        """Bind only against a root-authenticated, anti-rollback governance context."""
        from .trust import TrustedGovernanceRuntime

        if not isinstance(runtime, TrustedGovernanceRuntime):
            raise TypeError("runtime must be TrustedGovernanceRuntime")
        context = runtime.require_context()
        receipt = runtime.require_receipt()
        report = self.bind(hypotheses, constraints, context=context)
        if report.governance_context_sha256 != receipt.context_sha256:
            raise RuntimeError("trusted context receipt mismatch")
        return replace(report, trust=receipt.to_dict())

    def bind_authoritative(
        self,
        hypotheses: Iterable[Hypothesis],
        constraints: Iterable[Constraint],
        *,
        runtime,
    ):
        """Bind against the current committed COMPOSER authoritative head.

        Unlike ``bind_trusted()``, callers cannot hand VINCULUM an arbitrary signed
        bundle or caller-selected governance context. The runtime re-reads the
        authoritative repository and returns the exact committed snapshot.
        """
        from .authoritative import AuthoritativeGovernanceRuntime
        from .integration import AuthoritativeBinding

        if not isinstance(runtime, AuthoritativeGovernanceRuntime):
            raise TypeError("runtime must be AuthoritativeGovernanceRuntime")
        snapshot = runtime.snapshot()
        report = self.bind(hypotheses, constraints, context=snapshot.context)
        if report.governance_context_sha256 != snapshot.commit_receipt.context_sha256:
            raise RuntimeError("authoritative context receipt mismatch")
        return AuthoritativeBinding(
            report=report,
            trust=snapshot.trust_receipt,
            commit=snapshot.commit_receipt,
        )

    def _bind_one(
        self,
        hypothesis: Hypothesis,
        constraints: tuple[Constraint, ...],
        context: GovernanceContext,
        constraint_governance: tuple,
    ) -> BindingResult:
        evaluations = tuple(c.evaluate(hypothesis.payload) for c in constraints)

        total_weight = sum(e.weight for e in evaluations)
        decided_weight = sum(
            e.weight for e in evaluations if e.status in (ConstraintStatus.PASS, ConstraintStatus.FAIL)
        )
        coverage = decided_weight / total_weight if total_weight else 0.0

        hard_evaluations = [e for e in evaluations if e.hard]
        hard_fail = any(e.status is ConstraintStatus.FAIL for e in hard_evaluations)
        hard_unknown = any(e.status is ConstraintStatus.UNKNOWN for e in hard_evaluations)
        lacks_required_hard_boundary = self.require_hard_constraint and not hard_evaluations

        soft_decided = [
            e for e in evaluations if not e.hard and e.status in (ConstraintStatus.PASS, ConstraintStatus.FAIL)
        ]
        soft_weight = sum(e.weight for e in soft_decided)
        soft_pass_weight = sum(e.weight for e in soft_decided if e.status is ConstraintStatus.PASS)
        soft_compliance = soft_pass_weight / soft_weight if soft_weight else 1.0

        hypothesis_governance = context.evaluate_hypothesis(hypothesis, self.governance_policy)
        governance_evaluations = tuple(hypothesis_governance) + tuple(constraint_governance)
        g_status = governance_status(governance_evaluations)
        g_coverage = governance_coverage(governance_evaluations)

        # Preserve P as a declared prior-like confidence. D only discounts it by the
        # deterministic surface that was actually decidable. Governance does not pretend
        # to be probabilistic evidence; it gates admissibility and affects only the
        # operational coherence score.
        bounded_confidence = hypothesis.probability * coverage
        coherence_score = bounded_confidence * soft_compliance * g_coverage

        # Fail closed. A known hard-rule failure or a known governance failure rejects.
        # Unknown load-bearing facts stay unresolved rather than becoming permission.
        if hard_fail or g_status is GovernanceStatus.FAIL:
            state = BoundedState.REJECTED
            bounded_confidence = 0.0
            coherence_score = 0.0
        elif (
            hard_unknown
            or lacks_required_hard_boundary
            or g_status is GovernanceStatus.UNKNOWN
        ):
            state = BoundedState.UNRESOLVED
        else:
            state = BoundedState.ACCEPTED

        return BindingResult(
            hypothesis=hypothesis,
            state=state,
            evaluations=evaluations,
            governance_evaluations=governance_evaluations,
            governance_status=g_status,
            constraint_coverage=round(coverage, 12),
            governance_coverage=round(g_coverage, 12),
            soft_compliance=round(soft_compliance, 12),
            bounded_confidence=round(bounded_confidence, 12),
            coherence_score=round(coherence_score, 12),
        )
