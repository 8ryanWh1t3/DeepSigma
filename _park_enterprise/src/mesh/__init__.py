"""Mesh — Distributed Credibility Mesh for multi-node operation.

Signed envelopes, HTTP replication, federated quorum, and
cross-node seal verification.

Abstract institutional credibility architecture.
No real-world system modeled.
"""

from mesh.crypto import canonical_bytes, generate_keypair, sign, verify
from mesh.envelopes import AggregationRecord, EvidenceEnvelope, ValidationRecord
from mesh.logstore import append_jsonl, dedupe_by_id, load_last_n, load_since

__all__ = [
    "generate_keypair",
    "sign",
    "verify",
    "canonical_bytes",
    "EvidenceEnvelope",
    "ValidationRecord",
    "AggregationRecord",
    "append_jsonl",
    "load_last_n",
    "load_since",
    "dedupe_by_id",
]
