from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping

from .authoritative import (
    AuthoritativeCommitReceipt,
    AuthoritativeGovernanceRuntime,
)
from .exceptions import TrustError
from .models import BindingReport
from .receipts import sha256_receipt
from .trust import TrustReceipt


@dataclass(frozen=True)
class AuthoritativeBinding:
    """A BindingReport inseparably paired with the committed COMPOSER state used."""

    report: BindingReport
    trust: TrustReceipt
    commit: AuthoritativeCommitReceipt

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "vinculum.authoritative-binding.v0.4",
            "report": self.report.to_dict(),
            "report_sha256": self.report.sha256(),
            "trust": self.trust.to_dict(),
            "authoritative_commit": self.commit.to_dict(),
            "authoritative_commit_sha256": self.commit.sha256(),
        }

    def sha256(self) -> str:
        return sha256_receipt(self.to_dict())


class CerpaPhase(str, Enum):
    REVIEW = "REVIEW"
    APPLY_GUARD = "APPLY_GUARD"


@dataclass(frozen=True)
class CerpaHandoff:
    """Read-only handoff record from VINCULUM into a CERPA review/apply path.

    v0.4 never performs CERPA APPLY itself. It produces a tamper-evident envelope and
    provides a freshness guard that CERPA can call immediately before its own APPLY.
    Human/enterprise authority remains outside the binding engine.
    """

    episode_id: str
    claim_id: str
    phase: CerpaPhase | str
    binding_sha256: str
    binding_report_sha256: str
    authoritative_commit_sha256: str
    commit_record_sha256: str
    bundle_sha256: str
    context_sha256: str
    best_supported_id: str | None
    result_states: Mapping[str, str]
    created_at: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)
    schema: str = "vinculum.cerpa-handoff.v0.4"

    def __post_init__(self) -> None:
        phase = self.phase if isinstance(self.phase, CerpaPhase) else CerpaPhase(str(self.phase))
        object.__setattr__(self, "phase", phase)
        if not self.episode_id.strip():
            raise TrustError("CERPA handoff episode_id cannot be empty")
        if not self.claim_id.strip():
            raise TrustError("CERPA handoff claim_id cannot be empty")
        for name in (
            "binding_sha256",
            "binding_report_sha256",
            "authoritative_commit_sha256",
            "commit_record_sha256",
            "bundle_sha256",
            "context_sha256",
        ):
            value = getattr(self, name)
            if len(value) != 64:
                raise TrustError(f"CERPA handoff {name} must be SHA-256")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "episode_id": self.episode_id,
            "claim_id": self.claim_id,
            "phase": self.phase.value,
            "binding_sha256": self.binding_sha256,
            "binding_report_sha256": self.binding_report_sha256,
            "authoritative_commit_sha256": self.authoritative_commit_sha256,
            "commit_record_sha256": self.commit_record_sha256,
            "bundle_sha256": self.bundle_sha256,
            "context_sha256": self.context_sha256,
            "best_supported_id": self.best_supported_id,
            "result_states": dict(sorted(self.result_states.items())),
            "created_at": self.created_at,
            "metadata": dict(self.metadata),
        }

    def sha256(self) -> str:
        return sha256_receipt(self.to_dict())


class CerpaBridge:
    """Freshness-checked adapter from AuthoritativeBinding to CERPA.

    The bridge never writes authoritative governance state and never executes CERPA's
    APPLY. Its job is to ensure that the state reviewed/applied by CERPA is still the
    exact COMPOSER state that VINCULUM bounded.
    """

    @staticmethod
    def _assert_current(binding: AuthoritativeBinding, runtime: AuthoritativeGovernanceRuntime) -> None:
        current = runtime.snapshot()
        if current.commit_receipt.commit_record_sha256 != binding.commit.commit_record_sha256:
            raise TrustError("STALE_AUTHORITATIVE_STATE: COMPOSER head changed after VINCULUM binding")
        if current.commit_receipt.bundle_sha256 != binding.commit.bundle_sha256:
            raise TrustError("STALE_AUTHORITATIVE_STATE: bundle changed after VINCULUM binding")
        if current.commit_receipt.context_sha256 != binding.commit.context_sha256:
            raise TrustError("STALE_AUTHORITATIVE_STATE: governance context changed after VINCULUM binding")
        if current.trust_receipt.to_dict() != binding.trust.to_dict():
            raise TrustError("STALE_AUTHORITATIVE_STATE: trust receipt changed after VINCULUM binding")

    @staticmethod
    def _assert_handoff_matches_binding(handoff: CerpaHandoff, binding: AuthoritativeBinding) -> None:
        expected_states = {r.hypothesis.id: r.state.value for r in binding.report.results}
        checks = {
            "binding_sha256": (handoff.binding_sha256, binding.sha256()),
            "binding_report_sha256": (handoff.binding_report_sha256, binding.report.sha256()),
            "authoritative_commit_sha256": (handoff.authoritative_commit_sha256, binding.commit.sha256()),
            "commit_record_sha256": (handoff.commit_record_sha256, binding.commit.commit_record_sha256),
            "bundle_sha256": (handoff.bundle_sha256, binding.commit.bundle_sha256),
            "context_sha256": (handoff.context_sha256, binding.commit.context_sha256),
            "best_supported_id": (handoff.best_supported_id, binding.report.best_supported_id),
            "result_states": (dict(handoff.result_states), expected_states),
        }
        for name, (actual, expected) in checks.items():
            if actual != expected:
                raise TrustError(f"CERPA_HANDOFF_{name.upper()}_MISMATCH")

    def prepare_review(
        self,
        *,
        binding: AuthoritativeBinding,
        runtime: AuthoritativeGovernanceRuntime,
        episode_id: str,
        claim_id: str,
        created_at: str = "",
        metadata: Mapping[str, Any] | None = None,
    ) -> CerpaHandoff:
        self._assert_current(binding, runtime)
        return CerpaHandoff(
            episode_id=episode_id,
            claim_id=claim_id,
            phase=CerpaPhase.REVIEW,
            binding_sha256=binding.sha256(),
            binding_report_sha256=binding.report.sha256(),
            authoritative_commit_sha256=binding.commit.sha256(),
            commit_record_sha256=binding.commit.commit_record_sha256,
            bundle_sha256=binding.commit.bundle_sha256,
            context_sha256=binding.commit.context_sha256,
            best_supported_id=binding.report.best_supported_id,
            result_states={r.hypothesis.id: r.state.value for r in binding.report.results},
            created_at=created_at,
            metadata=dict(metadata or {}),
        )

    def validate_apply_guard(
        self,
        *,
        handoff: CerpaHandoff,
        binding: AuthoritativeBinding,
        runtime: AuthoritativeGovernanceRuntime,
    ) -> CerpaHandoff:
        """Revalidate the exact handoff immediately before CERPA performs APPLY."""
        if handoff.phase is not CerpaPhase.REVIEW:
            raise TrustError("CERPA_HANDOFF_PHASE_MISMATCH")
        self._assert_handoff_matches_binding(handoff, binding)
        self._assert_current(binding, runtime)
        return CerpaHandoff(
            episode_id=handoff.episode_id,
            claim_id=handoff.claim_id,
            phase=CerpaPhase.APPLY_GUARD,
            binding_sha256=handoff.binding_sha256,
            binding_report_sha256=handoff.binding_report_sha256,
            authoritative_commit_sha256=handoff.authoritative_commit_sha256,
            commit_record_sha256=handoff.commit_record_sha256,
            bundle_sha256=handoff.bundle_sha256,
            context_sha256=handoff.context_sha256,
            best_supported_id=handoff.best_supported_id,
            result_states=handoff.result_states,
            created_at=handoff.created_at,
            metadata={**dict(handoff.metadata), "apply_guard": "CURRENT"},
        )
