"""Credibility Engine — Data Models.

Abstract institutional credibility architecture.
No real-world system modeled.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


@dataclass
class Claim:
    """Tier 0 claim in the credibility lattice."""

    id: str
    title: str
    state: str = "VERIFIED"  # VERIFIED | DEGRADED | UNKNOWN
    k_required: int = 3
    n_total: int = 5
    margin: int = 2
    ttl_remaining: int = 240  # minutes
    correlation_group: str = ""
    confidence: float | None = 0.94
    region: str = "East"
    domain: str = "E1"
    last_verified: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Claim:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class DriftEvent:
    """A single drift event."""

    id: str
    severity: str = "low"  # low | medium | high | critical
    fingerprint: str = ""
    timestamp: str = field(default_factory=_now_iso)
    tier_impact: int = 0
    category: str = "timing_entropy"
    region: str = "East"
    auto_resolved: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> DriftEvent:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class CorrelationCluster:
    """Correlation cluster tracking shared-source risk."""

    id: str
    label: str = ""
    coefficient: float = 0.0
    status: str = "OK"  # OK | REVIEW | CRITICAL
    sources: list[str] = field(default_factory=list)
    claims_affected: int = 0
    domains: list[str] = field(default_factory=list)
    regions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> CorrelationCluster:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class SyncRegion:
    """Sync plane region health."""

    id: str
    time_skew_ms: int = 0
    watermark_lag_s: float = 0.0
    replay_flags: int = 0
    status: str = "OK"  # OK | WARN | CRITICAL
    sync_nodes: int = 5
    sync_nodes_healthy: int = 5
    beacons: int = 2
    beacons_healthy: int = 2
    watermark_advancing: bool = True
    last_watermark: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> SyncRegion:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class Snapshot:
    """Point-in-time credibility state."""

    timestamp: str = field(default_factory=_now_iso)
    credibility_index: int = 100
    band: str = "Stable"
    summary: str = ""
    components: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Snapshot:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


# -- Baseline factories -------------------------------------------------------

def make_default_claims() -> list[Claim]:
    """Create 5 Tier 0 claims matching the dashboard schema."""
    now = _now_iso()
    return [
        Claim(
            id="CLM-T0-001", title="Primary institutional readiness assertion",
            state="VERIFIED", confidence=0.94, k_required=3, n_total=5, margin=2,
            ttl_remaining=185, correlation_group="CG-001",
            region="East", domain="E1", last_verified=now,
        ),
        Claim(
            id="CLM-T0-002", title="Cross-regional coordination integrity",
            state="VERIFIED", confidence=0.88, k_required=4, n_total=6, margin=2,
            ttl_remaining=95, correlation_group="CG-002",
            region="Central", domain="C2", last_verified=now,
        ),
        Claim(
            id="CLM-T0-003", title="External compliance attestation",
            state="VERIFIED", confidence=0.90, k_required=3, n_total=4, margin=2,
            ttl_remaining=45, correlation_group="CG-004",
            region="West", domain="W2", last_verified=now,
        ),
        Claim(
            id="CLM-T0-004", title="Infrastructure continuity baseline",
            state="VERIFIED", confidence=0.96, k_required=3, n_total=7, margin=4,
            ttl_remaining=410, correlation_group="CG-005",
            region="East", domain="E3", last_verified=now,
        ),
        Claim(
            id="CLM-T0-005", title="Decision authority chain validation",
            state="VERIFIED", confidence=0.91, k_required=3, n_total=5, margin=2,
            ttl_remaining=220, correlation_group="CG-005",
            region="Central", domain="C1", last_verified=now,
        ),
    ]


def make_default_clusters() -> list[CorrelationCluster]:
    """Create 6 correlation clusters matching the dashboard schema."""
    return [
        CorrelationCluster(
            id="CG-001", label="Internal Sensors (East)",
            sources=["S-001", "S-004", "S-008"], coefficient=0.42,
            claims_affected=15, domains=["E1", "E2"], regions=["East"],
        ),
        CorrelationCluster(
            id="CG-002", label="Shared Infrastructure (East + Central)",
            sources=["S-003", "S-007", "S-012"], coefficient=0.55,
            claims_affected=28, domains=["E2", "C1", "C2"],
            regions=["East", "Central"],
        ),
        CorrelationCluster(
            id="CG-003", label="Cross-Region API Feed",
            sources=["S-CR-017", "S-CR-022"], coefficient=0.48,
            claims_affected=18, domains=["E3", "C2", "W1"],
            regions=["East", "Central", "West"],
        ),
        CorrelationCluster(
            id="CG-004", label="Compliance Feeds (West)",
            sources=["S-006", "S-010"], coefficient=0.34,
            claims_affected=10, domains=["W2"], regions=["West"],
        ),
        CorrelationCluster(
            id="CG-005", label="Central Primary (Central)",
            sources=["S-011", "S-013", "S-014", "S-019"], coefficient=0.45,
            claims_affected=22, domains=["C1", "C3", "C4"],
            regions=["Central"],
        ),
        CorrelationCluster(
            id="CG-006", label="Reference Data (All Regions)",
            sources=["S-015", "S-016"], coefficient=0.38,
            claims_affected=8, domains=["E1", "C1", "W1"],
            regions=["East", "Central", "West"],
        ),
    ]


def make_default_sync_regions() -> list[SyncRegion]:
    """Create 3 sync plane regions."""
    now = _now_iso()
    return [
        SyncRegion(
            id="East", time_skew_ms=12, watermark_lag_s=0.8,
            watermark_advancing=True, replay_flags=0,
            sync_nodes=5, sync_nodes_healthy=5,
            beacons=2, beacons_healthy=2, last_watermark=now,
        ),
        SyncRegion(
            id="Central", time_skew_ms=18, watermark_lag_s=1.2,
            watermark_advancing=True, replay_flags=0,
            sync_nodes=5, sync_nodes_healthy=5,
            beacons=2, beacons_healthy=2, last_watermark=now,
        ),
        SyncRegion(
            id="West", time_skew_ms=8, watermark_lag_s=0.5,
            watermark_advancing=True, replay_flags=0,
            sync_nodes=4, sync_nodes_healthy=4,
            beacons=2, beacons_healthy=2, last_watermark=now,
        ),
    ]
