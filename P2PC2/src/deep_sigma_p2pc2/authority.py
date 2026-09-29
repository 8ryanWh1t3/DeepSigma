from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .models import AuthorityEnvelope, Scope


@dataclass(frozen=True, slots=True)
class AuthorityDecision:
    allowed: bool
    reason: str
    authority_id: str | None = None


class AuthorityEngine:
    """Local evaluator for bounded delegated authority.

    This is deliberately policy-oriented: it decides whether a peer is allowed
    to perform an operation. It does not issue orders or select actions.
    """

    def __init__(self) -> None:
        self._envelopes: dict[str, AuthorityEnvelope] = {}

    def install(self, envelope: AuthorityEnvelope) -> None:
        self._envelopes[envelope.authority_id] = envelope

    def get(self, authority_id: str) -> AuthorityEnvelope | None:
        return self._envelopes.get(authority_id)

    def decide(
        self,
        *,
        subject: str,
        authority_id: str | None,
        required_scope: Scope,
        context: dict[str, Any] | None = None,
    ) -> AuthorityDecision:
        if not authority_id:
            return AuthorityDecision(False, "missing authority reference")
        env = self._envelopes.get(authority_id)
        if env is None:
            return AuthorityDecision(False, "unknown authority", authority_id)
        if env.subject != subject:
            return AuthorityDecision(False, "authority not delegated to subject", authority_id)
        if not env.is_time_valid():
            return AuthorityDecision(False, "authority expired or not yet valid", authority_id)
        if required_scope not in env.scopes:
            return AuthorityDecision(False, f"scope {required_scope.value} not delegated", authority_id)

        context = context or {}
        for key, expected in env.constraints.items():
            if key not in context:
                return AuthorityDecision(False, f"required constraint context missing: {key}", authority_id)
            actual = context[key]
            if isinstance(expected, (list, tuple, set)):
                if actual not in expected:
                    return AuthorityDecision(False, f"constraint failed: {key}", authority_id)
            elif actual != expected:
                return AuthorityDecision(False, f"constraint failed: {key}", authority_id)

        return AuthorityDecision(True, "authorized", authority_id)
