"""Mesh Sync Plane — Evidence timing verification across regions.

Enforces monotonic source sequences, watermark-based window closure,
independent time beacon validation, and replay detection.

Abstract institutional credibility architecture.
No real-world system modeled.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _iso_to_ms(iso: str) -> float:
    """Convert ISO timestamp to milliseconds since epoch."""
    if not iso:
        return 0.0
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return dt.timestamp() * 1000.0
    except (ValueError, TypeError):
        return 0.0


def _ms_delta(t1: str, t2: str) -> float:
    """Absolute difference in ms between two ISO timestamps."""
    return abs(_iso_to_ms(t1) - _iso_to_ms(t2))


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class SourceState:
    """Per-source tracking state within a sync node."""

    source_id: str
    last_sequence: int = 0
    last_event_time: str = ""
    envelope_count: int = 0
    quarantined: bool = False
    quarantine_reason: str = ""
    violations: int = 0


@dataclass
class TimeBeacon:
    """External independent time reference."""

    beacon_id: str
    region_id: str = ""
    reference_time: str = ""
    tolerance_ms: float = 500.0
    healthy: bool = True


@dataclass
class IngestResult:
    """Result of ingesting an envelope through the sync plane."""

    accepted: bool = True
    quarantined: bool = False
    drift_signals: list[dict] = field(default_factory=list)
    watermark_advanced: bool = False
    ingestion_lag_ms: float = 0.0


# ---------------------------------------------------------------------------
# SyncNode — per-region sync tracking
# ---------------------------------------------------------------------------

@dataclass
class SyncNode:
    """Sync node tracking sources and watermark for a region."""

    node_id: str
    region_id: str
    sources: dict[str, SourceState] = field(default_factory=dict)
    watermark: str = ""
    beacon_refs: list[str] = field(default_factory=list)
    drift_signals: list[dict] = field(default_factory=list)
    envelope_count: int = 0
    # seq_key → payload_hash
    _hashes: dict[str, str] = field(default_factory=dict)

    def _source(self, source_id: str) -> SourceState:
        if source_id not in self.sources:
            self.sources[source_id] = SourceState(source_id=source_id)
        return self.sources[source_id]


# ---------------------------------------------------------------------------
# SyncPlane — multi-region coordinator
# ---------------------------------------------------------------------------

class SyncPlane:
    """Multi-region sync plane for evidence timing verification.

    Parameters
    ----------
    regions : list[str]
        Region IDs (e.g. ["East", "West", "Central"]).
    nodes_per_region : int
        Number of sync nodes per region.
    max_authority_pct : float
        Maximum fraction of total envelopes from any single region.
    watermark_stall_threshold_ms : float
        If a source's watermark hasn't advanced in this many ms,
        fire SIGNAL_LOSS.
    """

    def __init__(
        self,
        regions: list[str],
        nodes_per_region: int = 3,
        max_authority_pct: float = 0.40,
        watermark_stall_threshold_ms: float = 30_000.0,
    ) -> None:
        self._regions = list(regions)
        self._nodes_per_region = nodes_per_region
        self._max_authority_pct = max_authority_pct
        self._stall_threshold_ms = watermark_stall_threshold_ms
        self._beacons: dict[str, TimeBeacon] = {}
        self._total_envelopes = 0
        self._region_envelope_counts: dict[str, int] = {r: 0 for r in regions}

        # Create sync nodes
        self._nodes: dict[str, list[SyncNode]] = {}
        for region in regions:
            self._nodes[region] = [
                SyncNode(
                    node_id=f"sync-{region}-{i}",
                    region_id=region,
                )
                for i in range(nodes_per_region)
            ]

    @property
    def regions(self) -> list[str]:
        return list(self._regions)

    @property
    def total_envelopes(self) -> int:
        return self._total_envelopes

    def add_beacon(self, beacon: TimeBeacon) -> None:
        """Register an external time beacon."""
        self._beacons[beacon.beacon_id] = beacon
        # Assign to region nodes if region matches
        if beacon.region_id:
            for node in self._nodes.get(beacon.region_id, []):
                if beacon.beacon_id not in node.beacon_refs:
                    node.beacon_refs.append(beacon.beacon_id)

    def ingest(self, envelope: dict) -> IngestResult:
        """Ingest an evidence envelope through the sync plane.

        Checks monotonic sequence, watermark, beacon divergence,
        and replay detection.
        """
        result = IngestResult()

        source_id = envelope.get("producer_id", "")
        region_id = envelope.get("region_id", "")
        event_time = (
            envelope.get("event_time", "")
            or envelope.get("timestamp", "")
        )
        ingest_time = envelope.get("timestamp", "")
        seq = envelope.get("sequence_number", 0)
        payload_hash = envelope.get("payload_hash", "")

        if not source_id or not region_id:
            result.accepted = False
            return result

        # Track region authority
        self._total_envelopes += 1
        if region_id in self._region_envelope_counts:
            self._region_envelope_counts[region_id] += 1

        # Compute ingestion lag
        if event_time and ingest_time:
            result.ingestion_lag_ms = _ms_delta(event_time, ingest_time)

        # Route to region's primary sync node
        nodes = self._nodes.get(region_id, [])
        if not nodes:
            result.accepted = False
            return result

        node = nodes[0]  # primary
        node.envelope_count += 1
        src = node._source(source_id)
        src.envelope_count += 1

        # --- Monotonic sequence check ---
        if seq > 0 and src.last_sequence > 0:
            if seq <= src.last_sequence:
                # Check for replay (same seq + same hash)
                seq_key = f"{source_id}:{seq}"
                stored = node._hashes.get(seq_key)
                if stored and stored == payload_hash:
                    sig = self._signal(
                        "REPLAY_DETECTED", region_id, source_id,
                        f"Duplicate seq={seq} with matching hash",
                    )
                    result.drift_signals.append(sig)
                    node.drift_signals.append(sig)
                    result.quarantined = True
                    result.accepted = False
                    src.quarantined = True
                    src.quarantine_reason = "replay_detected"
                    src.violations += 1
                    return result
                else:
                    desc = (
                        f"Non-monotonic: got seq={seq}, "
                        f"expected > {src.last_sequence}"
                    )
                    sig = self._signal(
                        "SEQUENCE_VIOLATION",
                        region_id, source_id, desc,
                    )
                    result.drift_signals.append(sig)
                    node.drift_signals.append(sig)
                    result.quarantined = True
                    src.quarantined = True
                    src.quarantine_reason = "sequence_violation"
                    src.violations += 1

        # Track hash for replay detection
        if seq > 0 and payload_hash:
            node._hashes[f"{source_id}:{seq}"] = payload_hash

        # Update source sequence
        if seq > src.last_sequence:
            src.last_sequence = seq

        # --- Watermark check ---
        if event_time and node.watermark:
            et_ms = _iso_to_ms(event_time)
            wm_ms = _iso_to_ms(node.watermark)

            if et_ms < wm_ms:
                desc = (
                    f"event_time {event_time} "
                    f"below watermark {node.watermark}"
                )
                sig = self._signal(
                    "LATE_ARRIVAL", region_id,
                    source_id, desc,
                )
                result.drift_signals.append(sig)
                node.drift_signals.append(sig)

            elif et_ms > wm_ms + (self._stall_threshold_ms * 2):
                # Far above watermark → clock skew
                desc = (
                    f"event_time {event_time} far above "
                    f"watermark {node.watermark}"
                )
                sig = self._signal(
                    "CLOCK_SKEW", region_id,
                    source_id, desc,
                )
                result.drift_signals.append(sig)
                node.drift_signals.append(sig)

        # Advance watermark
        if event_time:
            if not node.watermark or event_time > node.watermark:
                node.watermark = event_time
                result.watermark_advanced = True

        # Update source event time
        if event_time:
            src.last_event_time = event_time

        # --- Beacon divergence check ---
        if event_time:
            for beacon_id in node.beacon_refs:
                beacon = self._beacons.get(beacon_id)
                if beacon and beacon.reference_time and beacon.healthy:
                    delta_ms = _ms_delta(event_time, beacon.reference_time)
                    if delta_ms > beacon.tolerance_ms:
                        sig = self._signal(
                            "BEACON_DIVERGENCE", region_id, source_id,
                            f"Divergence {delta_ms:.0f}ms from beacon "
                            f"{beacon_id} (tolerance {beacon.tolerance_ms}ms)",
                        )
                        result.drift_signals.append(sig)
                        node.drift_signals.append(sig)

        return result

    def check_beacon(self, beacon_id: str, reference_time: str) -> list[dict]:
        """Update a beacon's reference time and check for divergence."""
        beacon = self._beacons.get(beacon_id)
        if not beacon:
            return []

        beacon.reference_time = reference_time
        signals = []

        # Check all region nodes with this beacon
        region_id = beacon.region_id
        for node in self._nodes.get(region_id, []):
            if beacon_id not in node.beacon_refs:
                continue
            if node.watermark:
                delta_ms = _ms_delta(node.watermark, reference_time)
                if delta_ms > beacon.tolerance_ms:
                    sig = self._signal(
                        "BEACON_DIVERGENCE", region_id, "",
                        f"Watermark divergence {delta_ms:.0f}ms from "
                        f"beacon {beacon_id}",
                    )
                    signals.append(sig)
                    node.drift_signals.append(sig)

        return signals

    def check_stalls(self, current_time: str = "") -> list[dict]:
        """Check all sources for watermark stalls (SIGNAL_LOSS)."""
        if not current_time:
            current_time = _now_iso()

        signals = []
        now_ms = _iso_to_ms(current_time)

        for region_id, nodes in self._nodes.items():
            for node in nodes:
                for src in node.sources.values():
                    if src.last_event_time and src.envelope_count > 0:
                        delta = now_ms - _iso_to_ms(src.last_event_time)
                        if delta > self._stall_threshold_ms:
                            desc = (
                                f"No evidence for "
                                f"{delta:.0f}ms "
                                f"(threshold "
                                f"{self._stall_threshold_ms:.0f}"
                                f"ms)"
                            )
                            sig = self._signal(
                                "SIGNAL_LOSS",
                                region_id,
                                src.source_id,
                                desc,
                            )
                            signals.append(sig)
                            node.drift_signals.append(sig)

        return signals

    def region_status(self, region_id: str) -> dict:
        """Get sync status for a region."""
        nodes = self._nodes.get(region_id, [])
        if not nodes:
            return {"region_id": region_id, "status": "unknown"}

        node = nodes[0]
        beacon_ids = node.beacon_refs
        beacons_healthy = sum(
            1 for bid in beacon_ids
            if self._beacons.get(bid, TimeBeacon(beacon_id="")).healthy
        )

        # Compute time skew from beacons
        skew_ms = 0.0
        if node.watermark:
            for bid in beacon_ids:
                b = self._beacons.get(bid)
                if b and b.reference_time and b.healthy:
                    d = _ms_delta(
                        node.watermark, b.reference_time,
                    )
                    skew_ms = max(skew_ms, d)

        replay_flags = sum(
            1 for s in node.drift_signals if s["type"] == "REPLAY_DETECTED"
        )

        return {
            "id": region_id,
            "status": self._compute_region_health(node),
            "sync_nodes": len(nodes),
            "sync_nodes_healthy": sum(1 for _ in nodes),
            "watermark_advancing": node.watermark != "",
            "last_watermark": node.watermark,
            "time_skew_ms": round(skew_ms, 1),
            "watermark_lag_s": 0.0,  # TODO: compute from stall check
            "replay_flags": replay_flags,
            "beacons": len(beacon_ids),
            "beacons_healthy": beacons_healthy,
            "envelope_count": node.envelope_count,
        }

    def summary(self) -> list[dict]:
        """Get sync status for all regions (matches sync.jsonl shape)."""
        return [self.region_status(r) for r in self._regions]

    def authority_check(self) -> bool:
        """Verify no region exceeds max authority percentage."""
        if self._total_envelopes == 0:
            return True
        for region_id, count in self._region_envelope_counts.items():
            pct = count / self._total_envelopes
            if pct > self._max_authority_pct:
                return False
        return True

    def authority_distribution(self) -> dict[str, float]:
        """Return per-region authority fractions."""
        total = max(self._total_envelopes, 1)
        return {
            r: count / total
            for r, count in self._region_envelope_counts.items()
        }

    def all_drift_signals(self) -> list[dict]:
        """Collect all drift signals across all nodes."""
        signals = []
        for nodes in self._nodes.values():
            for node in nodes:
                signals.extend(node.drift_signals)
        return signals

    # -------------------------------------------------------------------
    # Internal
    # -------------------------------------------------------------------

    def _signal(
        self,
        signal_type: str,
        region_id: str,
        source_id: str,
        description: str,
    ) -> dict:
        return {
            "type": signal_type,
            "region_id": region_id,
            "source_id": source_id,
            "description": description,
            "timestamp": _now_iso(),
        }

    def _compute_region_health(self, node: SyncNode) -> str:
        quarantined = sum(
            1 for s in node.sources.values() if s.quarantined
        )
        if quarantined > len(node.sources) * 0.5:
            return "degraded"
        replay_count = sum(
            1 for s in node.drift_signals if s["type"] == "REPLAY_DETECTED"
        )
        if replay_count > 0:
            return "degraded"
        return "OK"

    @staticmethod
    def _hash_envelope(envelope: dict) -> str:
        """Hash envelope for replay comparison."""
        pid = envelope.get('producer_id', '')
        ph = envelope.get('payload_hash', '')
        raw = f"{pid}:{ph}"
        return hashlib.sha256(raw.encode()).hexdigest()[:20]
