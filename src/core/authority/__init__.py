"""AuthorityOps — authority, policy, and governance enforcement.

Cross-cutting governance layer that binds authority, action, rationale,
expiry, and audit into a single evaluable control plane.

Re-exports the core AuthorityLedger for backwards compatibility.
"""

from __future__ import annotations

from .ledger import AuthorityLedger, AuthorityEntry

__all__ = [
    "AuthorityLedger",
    "AuthorityEntry",
]
