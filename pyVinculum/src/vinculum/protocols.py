from __future__ import annotations

from typing import Protocol, Sequence

from .governance import GovernanceContext
from .models import Hypothesis


class CandidateGenerator(Protocol):
    """Pluggable P-side interface. Implementations may be human, statistical, or LLM-backed."""

    def generate(self, prompt: str) -> Sequence[Hypothesis]:
        ...


class GovernanceContextProvider(Protocol):
    """Extension seam for repository/KMS/signed-ledger backed governance state."""

    def load(self, context_id: str) -> GovernanceContext:
        ...
