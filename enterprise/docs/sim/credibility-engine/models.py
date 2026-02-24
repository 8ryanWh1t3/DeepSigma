"""Credibility Engine Simulation - Data Models.

Abstract institutional credibility architecture.
No real-world system modeled.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Claim:
    """Tier 0 claim in the credibility lattice."""

    claim_id: str
    title: str
    status: str  # VERIFIED | DEGRADED | UNKNOWN
    confidence: float | None
    k_required: int
    n_total: int
    margin: int
    ttl_minutes: int
    ttl_remaining_minutes: int
    correlation_groups_required: int
    correlation_groups_actual: int
    out_of_band_required: bool
    out_of_band_present: bool
    region: str
    domain: str
    last_verified: str
    degradation_reason: str | None = None

    def to_dict(self) -> dict:
        d = {
            "claim_id": self.claim_id,
            "title": self.title,
            "status": self.status,
            "confidence": self.confidence,
            "k_required": self.k_required,
            "n_total": self.n_total,
            "margin": self.margin,
            "ttl_minutes": self.ttl_minutes,
            "ttl_remaining_minutes": max(0, self.ttl_remaining_minutes),
            "correlation_groups_required": self.correlation_groups_required,
            "correlation_groups_actual": self.correlation_groups_actual,
            "out_of_band_required": self.out_of_band_required,
            "out_of_band_present": self.out_of_band_present,
            "region": self.region,
            "domain": self.domain,
            "last_verified": self.last_verified,
        }
        if self.degradation_reason:
            d["degradation_reason"] = self.degradation_reason
        return d


@dataclass
class CorrelationCluster:
    """Correlation cluster tracking shared-source risk."""

    cluster_id: str
    label: str
    sources: list[str]
    coefficient: float
    claims_affected: int
    domains: list[str]
    regions: list[str]

    @property
    def status(self) -> str:
        if self.coefficient > 0.9:
            return "CRITICAL"
        if self.coefficient > 0.7:
            return "REVIEW"
        return "OK"

    @property
    def risk_level(self) -> str:
        if self.coefficient > 0.9:
            return "high"
        if self.coefficient > 0.7:
            return "medium"
        return "low"

    def to_dict(self) -> dict:
        return {
            "cluster_id": self.cluster_id,
            "label": self.label,
            "sources": list(self.sources),
            "coefficient": round(self.coefficient, 2),
            "status": self.status,
            "claims_affected": self.claims_affected,
            "domains": list(self.domains),
            "regions": list(self.regions),
            "risk_level": self.risk_level,
        }


@dataclass
class SyncRegion:
    """Sync plane region health."""

    region: str
    sync_nodes: int
    sync_nodes_healthy: int
    beacons: int
    beacons_healthy: int
    time_skew_ms: int
    watermark_lag_s: float
    watermark_advancing: bool
    replay_flags_count: int
    last_watermark: str
    warning_detail: str | None = None

    @property
    def status(self) -> str:
        if (self.time_skew_ms > 500 or self.watermark_lag_s > 30
                or self.replay_flags_count >= 5):
            return "CRITICAL"
        if (self.time_skew_ms > 100 or self.watermark_lag_s > 5
                or self.replay_flags_count >= 1):
            return "WARN"
        return "OK"

    def to_dict(self) -> dict:
        d = {
            "region": self.region,
            "sync_nodes": self.sync_nodes,
            "sync_nodes_healthy": self.sync_nodes_healthy,
            "beacons": self.beacons,
            "beacons_healthy": self.beacons_healthy,
            "time_skew_ms": self.time_skew_ms,
            "watermark_lag_s": round(self.watermark_lag_s, 1),
            "watermark_advancing": self.watermark_advancing,
            "replay_flags_count": self.replay_flags_count,
            "last_watermark": self.last_watermark,
            "status": self.status,
        }
        if self.warning_detail:
            d["warning_detail"] = self.warning_detail
        return d


@dataclass
class DriftFingerprint:
    """Recurring drift pattern fingerprint."""

    fingerprint: str
    description: str
    recurrence_count: int
    tier_impact: int
    severity: str
    auto_resolved: bool

    def to_dict(self) -> dict:
        return {
            "fingerprint": self.fingerprint,
            "description": self.description,
            "recurrence_count": self.recurrence_count,
            "tier_impact": self.tier_impact,
            "severity": self.severity,
            "auto_resolved": self.auto_resolved,
        }


# -- Baseline factories -------------------------------------------------------

def make_baseline_claims() -> list[Claim]:
    """Create the 5 Tier 0 claims matching the dashboard schema."""
    return [
        Claim(
            claim_id="CLM-T0-001",
            title="Primary institutional readiness assertion",
            status="VERIFIED", confidence=0.94,
            k_required=3, n_total=5, margin=2,
            ttl_minutes=240, ttl_remaining_minutes=185,
            correlation_groups_required=2, correlation_groups_actual=3,
            out_of_band_required=True, out_of_band_present=True,
            region="East", domain="E1",
            last_verified="2026-02-19T17:30:00Z",
        ),
        Claim(
            claim_id="CLM-T0-002",
            title="Cross-regional coordination integrity",
            status="VERIFIED", confidence=0.88,
            k_required=4, n_total=6, margin=2,
            ttl_minutes=120, ttl_remaining_minutes=95,
            correlation_groups_required=2, correlation_groups_actual=2,
            out_of_band_required=True, out_of_band_present=True,
            region="Central", domain="C2",
            last_verified="2026-02-19T17:45:00Z",
        ),
        Claim(
            claim_id="CLM-T0-003",
            title="External compliance attestation",
            status="VERIFIED", confidence=0.90,
            k_required=3, n_total=4, margin=2,
            ttl_minutes=60, ttl_remaining_minutes=45,
            correlation_groups_required=2, correlation_groups_actual=2,
            out_of_band_required=True, out_of_band_present=True,
            region="West", domain="W2",
            last_verified="2026-02-19T17:50:00Z",
        ),
        Claim(
            claim_id="CLM-T0-004",
            title="Infrastructure continuity baseline",
            status="VERIFIED", confidence=0.96,
            k_required=3, n_total=7, margin=4,
            ttl_minutes=480, ttl_remaining_minutes=410,
            correlation_groups_required=2, correlation_groups_actual=4,
            out_of_band_required=True, out_of_band_present=True,
            region="East", domain="E3",
            last_verified="2026-02-19T18:20:00Z",
        ),
        Claim(
            claim_id="CLM-T0-005",
            title="Decision authority chain validation",
            status="VERIFIED", confidence=0.91,
            k_required=3, n_total=5, margin=2,
            ttl_minutes=360, ttl_remaining_minutes=220,
            correlation_groups_required=2, correlation_groups_actual=3,
            out_of_band_required=True, out_of_band_present=True,
            region="Central", domain="C1",
            last_verified="2026-02-19T17:55:00Z",
        ),
    ]


def make_baseline_clusters() -> list[CorrelationCluster]:
    """Create the 6 correlation clusters matching the dashboard schema."""
    return [
        CorrelationCluster(
            cluster_id="CG-001", label="Internal Sensors (East)",
            sources=["S-001", "S-004", "S-008"], coefficient=0.42,
            claims_affected=15, domains=["E1", "E2"], regions=["East"],
        ),
        CorrelationCluster(
            cluster_id="CG-002", label="Shared Infrastructure (East + Central)",
            sources=["S-003", "S-007", "S-012"], coefficient=0.55,
            claims_affected=28, domains=["E2", "C1", "C2"],
            regions=["East", "Central"],
        ),
        CorrelationCluster(
            cluster_id="CG-003", label="Cross-Region API Feed",
            sources=["S-CR-017", "S-CR-022"], coefficient=0.48,
            claims_affected=18, domains=["E3", "C2", "W1"],
            regions=["East", "Central", "West"],
        ),
        CorrelationCluster(
            cluster_id="CG-004", label="Compliance Feeds (West)",
            sources=["S-006", "S-010"], coefficient=0.34,
            claims_affected=10, domains=["W2"], regions=["West"],
        ),
        CorrelationCluster(
            cluster_id="CG-005", label="Central Primary (Central)",
            sources=["S-011", "S-013", "S-014", "S-019"], coefficient=0.45,
            claims_affected=22, domains=["C1", "C3", "C4"],
            regions=["Central"],
        ),
        CorrelationCluster(
            cluster_id="CG-006", label="Reference Data (All Regions)",
            sources=["S-015", "S-016"], coefficient=0.38,
            claims_affected=8, domains=["E1", "C1", "W1"],
            regions=["East", "Central", "West"],
        ),
    ]


def make_baseline_sync() -> list[SyncRegion]:
    """Create 3 sync plane regions matching the dashboard schema."""
    return [
        SyncRegion(
            region="East", sync_nodes=5, sync_nodes_healthy=5,
            beacons=2, beacons_healthy=2, time_skew_ms=12,
            watermark_lag_s=0.8, watermark_advancing=True,
            replay_flags_count=0,
            last_watermark="2026-02-19T18:44:30Z",
        ),
        SyncRegion(
            region="Central", sync_nodes=5, sync_nodes_healthy=5,
            beacons=2, beacons_healthy=2, time_skew_ms=18,
            watermark_lag_s=1.2, watermark_advancing=True,
            replay_flags_count=0,
            last_watermark="2026-02-19T18:44:12Z",
        ),
        SyncRegion(
            region="West", sync_nodes=4, sync_nodes_healthy=4,
            beacons=2, beacons_healthy=2, time_skew_ms=8,
            watermark_lag_s=0.5, watermark_advancing=True,
            replay_flags_count=0,
            last_watermark="2026-02-19T18:44:45Z",
        ),
    ]


def make_baseline_fingerprints() -> list[DriftFingerprint]:
    """Create baseline drift fingerprints."""
    return [
        DriftFingerprint(
            fingerprint="TTL-BATCH-EXPIRE-T1",
            description="Tier 1 evidence batch TTL expiration",
            recurrence_count=0, tier_impact=1,
            severity="low", auto_resolved=True,
        ),
        DriftFingerprint(
            fingerprint="CONF-VOLATILITY-C2",
            description="Confidence oscillation in Central Domain C2",
            recurrence_count=0, tier_impact=0,
            severity="medium", auto_resolved=True,
        ),
        DriftFingerprint(
            fingerprint="CORR-DRIFT-S003",
            description="Cross-region correlation drift from Source-S003",
            recurrence_count=0, tier_impact=0,
            severity="medium", auto_resolved=True,
        ),
        DriftFingerprint(
            fingerprint="TIMING-LAG-WEST",
            description="Ingestion lag variance in West region feeds",
            recurrence_count=0, tier_impact=2,
            severity="low", auto_resolved=True,
        ),
        DriftFingerprint(
            fingerprint="SYNC-BEACON-SKEW",
            description="Beacon-W2 time skew exceeding 200ms",
            recurrence_count=0, tier_impact=1,
            severity="low", auto_resolved=True,
        ),
    ]
