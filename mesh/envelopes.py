"""Mesh Envelopes — Evidence, Validation, and Aggregation record schemas.

Abstract institutional credibility architecture.
No real-world system modeled.
"""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

from mesh.crypto import canonical_bytes, sign


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


# ---------------------------------------------------------------------------
# Evidence Envelope
# ---------------------------------------------------------------------------

@dataclass
class EvidenceEnvelope:
    """Signed evidence signal from an edge node."""

    tenant_id: str
    envelope_id: str = field(default_factory=lambda: _new_id("ENV"))
    timestamp: str = field(default_factory=_now_iso)
    producer_id: str = ""
    region_id: str = ""
    correlation_group: str = ""
    signal_type: str = "evidence"
    payload: dict = field(default_factory=dict)
    payload_hash: str = ""
    signature: str = ""
    public_key: str = ""
    event_time: str = ""  # source-reported observation time
    sequence_number: int = 0  # monotonic per-source sequence

    def compute_payload_hash(self) -> str:
        raw = canonical_bytes(self.payload)
        self.payload_hash = hashlib.sha256(raw).hexdigest()[:40]
        return self.payload_hash

    def sign_envelope(self, private_key_hex: str, public_key_hex: str) -> None:
        """Compute payload hash and sign the envelope."""
        self.compute_payload_hash()
        self.public_key = public_key_hex
        msg = canonical_bytes(self._signable())
        self.signature = sign(private_key_hex, msg)

    def _signable(self) -> dict:
        """Fields included in signature computation."""
        return {
            "tenant_id": self.tenant_id,
            "envelope_id": self.envelope_id,
            "timestamp": self.timestamp,
            "producer_id": self.producer_id,
            "region_id": self.region_id,
            "correlation_group": self.correlation_group,
            "signal_type": self.signal_type,
            "payload_hash": self.payload_hash,
        }

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# Validation Record
# ---------------------------------------------------------------------------

@dataclass
class ValidationRecord:
    """Validation verdict from a validator node."""

    tenant_id: str
    validation_id: str = field(default_factory=lambda: _new_id("VAL"))
    timestamp: str = field(default_factory=_now_iso)
    validator_id: str = ""
    region_id: str = ""
    envelope_id: str = ""
    verdict: str = "ACCEPT"  # ACCEPT | REJECT
    reasons: list[str] = field(default_factory=list)
    signature: str = ""
    public_key: str = ""

    def sign_record(self, private_key_hex: str, public_key_hex: str) -> None:
        self.public_key = public_key_hex
        msg = canonical_bytes(self._signable())
        self.signature = sign(private_key_hex, msg)

    def _signable(self) -> dict:
        return {
            "tenant_id": self.tenant_id,
            "validation_id": self.validation_id,
            "timestamp": self.timestamp,
            "validator_id": self.validator_id,
            "envelope_id": self.envelope_id,
            "verdict": self.verdict,
        }

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# Claim Summary (used in aggregation)
# ---------------------------------------------------------------------------

@dataclass
class ClaimSummary:
    """Minimal claim state for aggregation."""

    claim_id: str = ""
    state: str = "UNKNOWN"
    k_required: int = 3
    n_total: int = 5
    margin: int = 2
    correlation_groups_required: int = 2
    correlation_group_actuals: list[str] = field(default_factory=list)
    ttl_remaining_seconds: float = 900.0

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# Correlation Cluster (used in aggregation)
# ---------------------------------------------------------------------------

@dataclass
class CorrelationCluster:
    """Correlation cluster for aggregation."""

    cluster_id: str = ""
    region_id: str = ""
    coefficient: float = 0.0
    risk_level: str = "low"  # low | review | invalid
    members: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# Sync Region (used in aggregation)
# ---------------------------------------------------------------------------

@dataclass
class SyncRegion:
    """Sync region health for aggregation."""

    region_id: str = ""
    node_count: int = 0
    online_count: int = 0
    last_heartbeat: str = ""
    status: str = "healthy"  # healthy | degraded | offline

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# Aggregation Record
# ---------------------------------------------------------------------------

@dataclass
class AggregationRecord:
    """Federated aggregation snapshot from an aggregator node."""

    tenant_id: str
    aggregate_id: str = field(default_factory=lambda: _new_id("AGG"))
    timestamp: str = field(default_factory=_now_iso)
    aggregator_id: str = ""
    window_start: str = ""
    window_end: str = ""
    tier0_claims_state: list[dict] = field(default_factory=list)
    correlation_clusters: list[dict] = field(default_factory=list)
    sync_regions: list[dict] = field(default_factory=list)
    credibility_snapshot: dict = field(default_factory=dict)
    policy_hash: str = ""
    seal_candidate_hash: str = ""

    def compute_seal_candidate(self) -> str:
        """Compute hash of aggregate content for seal input."""
        content = canonical_bytes({
            "claims": self.tier0_claims_state,
            "clusters": self.correlation_clusters,
            "regions": self.sync_regions,
            "snapshot": self.credibility_snapshot,
            "policy_hash": self.policy_hash,
        })
        self.seal_candidate_hash = hashlib.sha256(content).hexdigest()[:40]
        return self.seal_candidate_hash

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def create_envelope(
    tenant_id: str,
    producer_id: str,
    region_id: str,
    correlation_group: str,
    payload: dict[str, Any],
    private_key: str,
    public_key: str,
    signal_type: str = "evidence",
    event_time: str = "",
    sequence_number: int = 0,
) -> EvidenceEnvelope:
    """Factory: create and sign an evidence envelope."""
    env = EvidenceEnvelope(
        tenant_id=tenant_id,
        producer_id=producer_id,
        region_id=region_id,
        correlation_group=correlation_group,
        signal_type=signal_type,
        payload=payload,
        event_time=event_time,
        sequence_number=sequence_number,
    )
    env.sign_envelope(private_key, public_key)
    return env


def create_validation(
    tenant_id: str,
    validator_id: str,
    region_id: str,
    envelope_id: str,
    verdict: str,
    reasons: list[str],
    private_key: str,
    public_key: str,
) -> ValidationRecord:
    """Factory: create and sign a validation record."""
    val = ValidationRecord(
        tenant_id=tenant_id,
        validator_id=validator_id,
        region_id=region_id,
        envelope_id=envelope_id,
        verdict=verdict,
        reasons=reasons,
    )
    val.sign_record(private_key, public_key)
    return val
