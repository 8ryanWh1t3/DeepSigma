"""Credibility Engine — Runtime Engine.

Stateful engine that maintains live claim state, processes drift events,
and recalculates the Credibility Index. Does NOT depend on the simulator.

Abstract institutional credibility architecture.
No real-world system modeled.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from credibility_engine.index import calculate_index_detailed
from credibility_engine.models import (
    Claim,
    CorrelationCluster,
    DriftEvent,
    Snapshot,
    SyncRegion,
    make_default_claims,
    make_default_clusters,
    make_default_sync_regions,
)
from credibility_engine.constants import DEFAULT_TENANT_ID
from credibility_engine.store import CredibilityStore


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class CredibilityEngine:
    """Runtime Credibility Engine.

    Maintains live state and persists to JSONL.
    Can be driven by the simulator or by direct API calls.
    Tenant-aware: each instance is scoped to a single tenant via its store.
    """

    def __init__(
        self,
        store: CredibilityStore | None = None,
        tenant_id: str | None = None,
    ) -> None:
        tid = tenant_id or DEFAULT_TENANT_ID
        self.store = store or CredibilityStore(tenant_id=tid)
        self.tenant_id = self.store.tenant_id

        # Live state
        self.claims: list[Claim] = []
        self.clusters: list[CorrelationCluster] = []
        self.sync_regions: list[SyncRegion] = []
        self.drift_events: list[DriftEvent] = []
        self.trend_history: list[int] = []

        # Operational counters
        self.patches_applied: int = 0
        self.seals_created: int = 0
        self.nodes_added: int = 0
        self.edges_added: int = 0
        self.seal_chain_length: int = 157

        # Latest index
        self._index_cache: dict[str, Any] | None = None

    # -- Initialization --------------------------------------------------------

    def initialize_default_state(self) -> None:
        """Initialize with baseline claim/cluster/sync state."""
        self.claims = make_default_claims()
        self.clusters = make_default_clusters()
        self.sync_regions = make_default_sync_regions()
        self.drift_events = []
        self.trend_history = []
        self._index_cache = None

        # Persist initial state
        self._persist_claims()
        self._persist_clusters()
        self._persist_sync()

    def load_from_store(self) -> bool:
        """Load state from persistence. Returns True if state was found."""
        claim_dicts = self.store.latest_claims()
        if not claim_dicts:
            return False
        self.claims = [Claim.from_dict(d) for d in claim_dicts]

        cluster_dicts = self.store.latest_clusters()
        if cluster_dicts:
            self.clusters = [CorrelationCluster.from_dict(d) for d in cluster_dicts]

        sync_dicts = self.store.latest_sync()
        if sync_dicts:
            self.sync_regions = [SyncRegion.from_dict(d) for d in sync_dicts]

        drift_dicts = self.store.drift_last_24h()
        self.drift_events = [DriftEvent.from_dict(d) for d in drift_dicts]

        # Load trend history from recent snapshots
        snapshots = self.store.load_last_n(self.store.SNAPSHOTS_FILE, 5)
        self.trend_history = [s.get("credibility_index", 100) for s in snapshots]

        self._index_cache = None
        return True

    # -- Event processing ------------------------------------------------------

    def process_drift_event(self, event: DriftEvent) -> None:
        """Ingest a single drift event."""
        self.drift_events.append(event)
        self.store.append_drift(event.to_dict())
        self._index_cache = None

    def process_drift_batch(self, events: list[DriftEvent]) -> None:
        """Ingest a batch of drift events."""
        for event in events:
            self.drift_events.append(event)
            self.store.append_drift(event.to_dict())
        self._index_cache = None

    # -- State updates ---------------------------------------------------------

    def update_claim_state(self, claim_id: str, **kwargs: Any) -> Claim | None:
        """Update a claim's state fields."""
        for claim in self.claims:
            if claim.id == claim_id:
                for key, value in kwargs.items():
                    if hasattr(claim, key):
                        setattr(claim, key, value)
                self._persist_claims()
                self._index_cache = None
                return claim
        return None

    def update_correlation(self, cluster_id: str, **kwargs: Any) -> CorrelationCluster | None:
        """Update a correlation cluster."""
        for cluster in self.clusters:
            if cluster.id == cluster_id:
                for key, value in kwargs.items():
                    if hasattr(cluster, key):
                        setattr(cluster, key, value)
                # Auto-compute status from coefficient
                coeff = cluster.coefficient
                if coeff > 0.9:
                    cluster.status = "CRITICAL"
                elif coeff > 0.7:
                    cluster.status = "REVIEW"
                else:
                    cluster.status = "OK"
                self._persist_clusters()
                self._index_cache = None
                return cluster
        return None

    def update_sync(self, region_id: str, **kwargs: Any) -> SyncRegion | None:
        """Update a sync region."""
        for region in self.sync_regions:
            if region.id == region_id:
                for key, value in kwargs.items():
                    if hasattr(region, key):
                        setattr(region, key, value)
                # Auto-compute status
                if (region.time_skew_ms > 500 or region.watermark_lag_s > 30
                        or region.replay_flags >= 5):
                    region.status = "CRITICAL"
                elif (region.time_skew_ms > 100 or region.watermark_lag_s > 5
                      or region.replay_flags >= 1):
                    region.status = "WARN"
                else:
                    region.status = "OK"
                self._persist_sync()
                self._index_cache = None
                return region
        return None

    # -- Index recalculation ---------------------------------------------------

    def recalculate_index(self) -> dict[str, Any]:
        """Recalculate the Credibility Index from current state."""
        claim_dicts = [c.to_dict() for c in self.claims]
        cluster_dicts = [c.to_dict() for c in self.clusters]
        drift_dicts = [e.to_dict() for e in self.drift_events[-500:]]
        sync_dicts = [r.to_dict() for r in self.sync_regions]

        result = calculate_index_detailed(
            drift_events=drift_dicts,
            correlation_clusters=cluster_dicts,
            claims=claim_dicts,
            sync_regions=sync_dicts,
        )
        self._index_cache = result

        # Update trend
        self.trend_history.append(result["score"])
        if len(self.trend_history) > 5:
            self.trend_history = self.trend_history[-5:]

        return result

    @property
    def credibility_index(self) -> int:
        if self._index_cache is None:
            self.recalculate_index()
        return self._index_cache["score"]

    @property
    def index_band(self) -> str:
        if self._index_cache is None:
            self.recalculate_index()
        return self._index_cache["band"]

    @property
    def index_components(self) -> dict[str, Any]:
        if self._index_cache is None:
            self.recalculate_index()
        return self._index_cache["components"]

    # -- Snapshot generation ---------------------------------------------------

    def generate_snapshot(self) -> Snapshot:
        """Generate and persist a point-in-time snapshot."""
        if self._index_cache is None:
            self.recalculate_index()

        snapshot = Snapshot(
            timestamp=_now_iso(),
            credibility_index=self._index_cache["score"],
            band=self._index_cache["band"],
            summary=self._build_summary(),
            components=self._index_cache["components"],
        )
        self.store.append_snapshot(snapshot.to_dict())
        return snapshot

    def persist_state(self) -> None:
        """Persist all current state to JSONL files."""
        self._persist_claims()
        self._persist_clusters()
        self._persist_sync()

    # -- Dashboard-compatible snapshots ----------------------------------------

    def snapshot_credibility(self) -> dict[str, Any]:
        """Produce credibility_snapshot.json compatible with dashboard."""
        if self._index_cache is None:
            self.recalculate_index()

        labels = ["T-4", "T-3", "T-2", "T-1", "Now"]
        history = list(self.trend_history[-5:])
        while len(history) < 5:
            history.insert(0, history[0] if history else self.credibility_index)

        auto_resolved = sum(1 for e in self.drift_events if e.auto_resolved)
        active_signals = sum(1 for e in self.drift_events if not e.auto_resolved)
        auto_rate = round(auto_resolved / max(len(self.drift_events), 1), 2)

        return {
            "tenant_id": self.tenant_id,
            "index_score": self.credibility_index,
            "index_band": self.index_band,
            "index_band_color": self._band_color(),
            "trend_points": history,
            "trend_labels": labels,
            "last_updated": _now_iso(),
            "total_nodes": 36000,
            "regions": 3,
            "active_drift_signals": active_signals,
            "auto_patch_rate": auto_rate,
            "bands": [
                {"range": "90\u2013100", "label": "Stable", "action": "Monitor"},
                {"range": "75\u201389", "label": "Minor Drift",
                 "action": "Review flagged claims"},
                {"range": "60\u201374", "label": "Elevated",
                 "action": "Patch required"},
                {"range": "40\u201359", "label": "Degraded",
                 "action": "Immediate remediation"},
                {"range": "<40", "label": "Compromised",
                 "action": "Halt dependent decisions"},
            ],
            "components": self.index_components,
        }

    def snapshot_claims(self) -> dict[str, Any]:
        """Produce claims_tier0.json compatible with dashboard."""
        return {
            "tenant_id": self.tenant_id,
            "tier": 0,
            "total_count": 200,
            "claims": [
                {
                    "claim_id": c.id,
                    "title": c.title,
                    "status": c.state,
                    "confidence": c.confidence,
                    "k_required": c.k_required,
                    "n_total": c.n_total,
                    "margin": c.margin,
                    "ttl_minutes": c.ttl_remaining + 60,
                    "ttl_remaining_minutes": max(0, c.ttl_remaining),
                    "correlation_groups_required": 2,
                    "correlation_groups_actual": 2,
                    "out_of_band_required": True,
                    "out_of_band_present": c.state != "UNKNOWN",
                    "region": c.region,
                    "domain": c.domain,
                    "last_verified": c.last_verified,
                }
                for c in self.claims
            ],
        }

    def snapshot_drift(self) -> dict[str, Any]:
        """Produce drift_events_24h.json compatible with dashboard."""
        by_severity = {"low": 0, "medium": 0, "high": 0, "critical": 0}
        by_category = {
            "timing_entropy": 0, "correlation_drift": 0,
            "confidence_volatility": 0, "ttl_compression": 0,
            "external_mismatch": 0,
        }
        by_region = {"East": 0, "Central": 0, "West": 0}
        auto_resolved = 0
        pending = 0
        escalated = 0

        for e in self.drift_events:
            by_severity[e.severity] = by_severity.get(e.severity, 0) + 1
            by_category[e.category] = by_category.get(e.category, 0) + 1
            by_region[e.region] = by_region.get(e.region, 0) + 1
            if e.auto_resolved:
                auto_resolved += 1
            else:
                pending += 1

        return {
            "tenant_id": self.tenant_id,
            "window": "24h",
            "window_start": _now_iso(),
            "window_end": _now_iso(),
            "total_count": len(self.drift_events),
            "by_severity": by_severity,
            "by_category": by_category,
            "by_region": by_region,
            "auto_resolved": auto_resolved,
            "pending_review": pending,
            "escalated": escalated,
            "top_fingerprints": [],
            "hourly_distribution": [0] * 24,
        }

    def snapshot_correlation(self) -> dict[str, Any]:
        """Produce correlation_map.json compatible with dashboard."""
        return {
            "tenant_id": self.tenant_id,
            "clusters": [
                {
                    "cluster_id": c.id,
                    "label": c.label,
                    "sources": c.sources,
                    "coefficient": round(c.coefficient, 2),
                    "status": c.status,
                    "claims_affected": c.claims_affected,
                    "domains": c.domains,
                    "regions": c.regions,
                    "risk_level": (
                        "high" if c.coefficient > 0.9
                        else "medium" if c.coefficient > 0.7
                        else "low"
                    ),
                }
                for c in self.clusters
            ],
            "thresholds": {
                "ok_max": 0.7,
                "review_max": 0.9,
                "critical_min": 0.9,
            },
        }

    def snapshot_sync(self) -> dict[str, Any]:
        """Produce sync_integrity.json compatible with dashboard."""
        max_skew = max((r.time_skew_ms for r in self.sync_regions), default=0)
        min_skew = min((r.time_skew_ms for r in self.sync_regions), default=0)
        cross_skew = max_skew - min_skew

        fed_status = "OK" if cross_skew < 200 else "WARN"
        if cross_skew > 500:
            fed_status = "CRITICAL"

        return {
            "tenant_id": self.tenant_id,
            "regions": [
                {
                    "region": r.id,
                    "sync_nodes": r.sync_nodes,
                    "sync_nodes_healthy": r.sync_nodes_healthy,
                    "beacons": r.beacons,
                    "beacons_healthy": r.beacons_healthy,
                    "time_skew_ms": r.time_skew_ms,
                    "watermark_lag_s": round(r.watermark_lag_s, 1),
                    "watermark_advancing": r.watermark_advancing,
                    "replay_flags_count": r.replay_flags,
                    "last_watermark": r.last_watermark,
                    "status": r.status,
                }
                for r in self.sync_regions
            ],
            "federation": {
                "cross_region_skew_ms": cross_skew,
                "max_acceptable_skew_ms": 200,
                "status": fed_status,
            },
            "thresholds": {
                "time_skew_warn_ms": 100,
                "time_skew_critical_ms": 500,
                "watermark_lag_warn_s": 5,
                "watermark_lag_critical_s": 30,
                "replay_warn_count": 1,
                "replay_critical_count": 5,
            },
        }

    # -- Internal helpers ------------------------------------------------------

    def _persist_claims(self) -> None:
        for c in self.claims:
            self.store.append_claim(c.to_dict())

    def _persist_clusters(self) -> None:
        for c in self.clusters:
            self.store.append_correlation(c.to_dict())

    def _persist_sync(self) -> None:
        for r in self.sync_regions:
            self.store.append_sync(r.to_dict())

    def _build_summary(self) -> str:
        unknown = sum(1 for c in self.claims if c.state == "UNKNOWN")
        degraded = sum(1 for c in self.claims if c.state == "DEGRADED")
        parts = [f"CI={self.credibility_index} ({self.index_band})"]
        if unknown:
            parts.append(f"{unknown} UNKNOWN claim(s)")
        if degraded:
            parts.append(f"{degraded} DEGRADED claim(s)")
        parts.append(f"{len(self.drift_events)} drift events")
        return " — ".join(parts)

    def _band_color(self) -> str:
        s = self.credibility_index
        if s >= 90:
            return "green"
        if s >= 75:
            return "yellow"
        return "red"
