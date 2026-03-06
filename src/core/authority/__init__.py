"""AuthorityOps — authority, policy, and governance enforcement.

Cross-cutting governance layer that binds authority, action, rationale,
expiry, and audit into a single evaluable control plane.

Re-exports core types plus the 7 OpenPQL primitives.
"""

from __future__ import annotations

from .artifact_builder import build_artifact, load_artifact, write_artifact
from .audit_retrieval import AuditRetrieval
from .evidence_chain import EvidenceChain, EvidenceEntry
from .ledger import AuthorityEntry, AuthorityLedger
from .policy_source import PolicySource, build_policy_source
from .runtime_gate import GateDecision, RuntimeGate
from .seal_and_hash import canonical_json, compute_hash, seal, verify_seal

__all__ = [
    # Legacy
    "AuthorityLedger",
    "AuthorityEntry",
    # Primitive 1: Policy Source
    "PolicySource",
    "build_policy_source",
    # Primitive 3: Artifacts
    "build_artifact",
    "write_artifact",
    "load_artifact",
    # Primitive 4: Runtime Gate
    "RuntimeGate",
    "GateDecision",
    # Primitive 5: Evidence Chain
    "EvidenceChain",
    "EvidenceEntry",
    # Primitive 6: Audit Retrieval
    "AuditRetrieval",
    # Primitive 7: Seal & Hash
    "compute_hash",
    "canonical_json",
    "seal",
    "verify_seal",
]
