"""Tests for mesh/sync_plane.py — multi-region sync plane.

Run:  pytest tests/test_sync_plane.py -v
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mesh.sync_plane import (  # noqa: E402
    SyncPlane,
    TimeBeacon,
    _iso_to_ms,
    _ms_delta,
)

REGIONS = ["East", "West", "Central"]


def _envelope(
    producer_id: str = "src-1",
    region_id: str = "East",
    event_time: str = "2026-02-19T00:00:01Z",
    sequence_number: int = 1,
    payload_hash: str = "abc123",
    timestamp: str = "",
) -> dict:
    """Minimal envelope dict for sync plane ingestion."""
    env = {
        "producer_id": producer_id,
        "region_id": region_id,
        "event_time": event_time,
        "sequence_number": sequence_number,
        "payload_hash": payload_hash,
    }
    env["timestamp"] = timestamp or event_time
    return env


# ── Setup & Topology ──────────────────────────────────────


class TestSyncPlaneSetup:
    """Basic topology and configuration."""

    def test_3_region_init(self):
        sp = SyncPlane(REGIONS)
        assert sp.regions == REGIONS
        assert sp.total_envelopes == 0

    def test_authority_distribution_starts_balanced(self):
        sp = SyncPlane(REGIONS)
        dist = sp.authority_distribution()
        assert len(dist) == 3
        for pct in dist.values():
            assert pct == 0.0

    def test_beacon_registration(self):
        sp = SyncPlane(REGIONS)
        beacon = TimeBeacon(
            beacon_id="ntp-east",
            region_id="East",
            reference_time="2026-02-19T00:00:00Z",
        )
        sp.add_beacon(beacon)
        status = sp.region_status("East")
        assert status["beacons"] >= 1


# ── Monotonic Sequence ────────────────────────────────────


class TestMonotonicSequence:
    """Monotonic source sequence enforcement."""

    def test_ascending_sequence_accepted(self):
        sp = SyncPlane(REGIONS)
        r1 = sp.ingest(_envelope(sequence_number=1))
        r2 = sp.ingest(_envelope(sequence_number=2))
        r3 = sp.ingest(_envelope(sequence_number=3))
        assert r1.accepted
        assert r2.accepted
        assert r3.accepted
        assert not any(
            r.quarantined for r in [r1, r2, r3]
        )

    def test_out_of_order_fires_violation(self):
        sp = SyncPlane(REGIONS)
        sp.ingest(_envelope(sequence_number=1))
        sp.ingest(_envelope(sequence_number=5))
        result = sp.ingest(_envelope(
            sequence_number=3,
            payload_hash="different",
        ))
        assert result.quarantined
        signals = [
            s for s in result.drift_signals
            if s["type"] == "SEQUENCE_VIOLATION"
        ]
        assert len(signals) == 1

    def test_quarantined_source_tracked(self):
        sp = SyncPlane(REGIONS)
        sp.ingest(_envelope(sequence_number=1))
        sp.ingest(_envelope(sequence_number=5))
        sp.ingest(_envelope(
            sequence_number=3,
            payload_hash="different",
        ))
        status = sp.region_status("East")
        assert status["status"] in ("OK", "degraded")

    def test_repeated_violations_accumulate(self):
        sp = SyncPlane(REGIONS)
        sp.ingest(_envelope(sequence_number=1))
        sp.ingest(_envelope(sequence_number=10))
        # Two violations from same source
        sp.ingest(_envelope(
            sequence_number=5, payload_hash="h1",
        ))
        sp.ingest(_envelope(
            sequence_number=7, payload_hash="h2",
        ))
        all_signals = sp.all_drift_signals()
        violations = [
            s for s in all_signals
            if s["type"] == "SEQUENCE_VIOLATION"
        ]
        assert len(violations) == 2


# ── Watermark ─────────────────────────────────────────────


class TestWatermark:
    """Watermark-based window closure."""

    def test_watermark_advances_on_in_order(self):
        sp = SyncPlane(REGIONS)
        t1 = "2026-02-19T00:00:01Z"
        t2 = "2026-02-19T00:00:02Z"
        r1 = sp.ingest(_envelope(
            event_time=t1, sequence_number=1,
        ))
        r2 = sp.ingest(_envelope(
            event_time=t2, sequence_number=2,
        ))
        assert r1.watermark_advanced
        assert r2.watermark_advanced

    def test_late_arrival_detected(self):
        sp = SyncPlane(REGIONS)
        sp.ingest(_envelope(
            event_time="2026-02-19T00:00:10Z",
            sequence_number=1,
        ))
        result = sp.ingest(_envelope(
            event_time="2026-02-19T00:00:01Z",
            sequence_number=2,
        ))
        late = [
            s for s in result.drift_signals
            if s["type"] == "LATE_ARRIVAL"
        ]
        assert len(late) == 1

    def test_clock_skew_detected(self):
        sp = SyncPlane(
            REGIONS,
            watermark_stall_threshold_ms=1000.0,
        )
        sp.ingest(_envelope(
            event_time="2026-02-19T00:00:00Z",
            sequence_number=1,
        ))
        # > 2x stall threshold = 2000ms
        result = sp.ingest(_envelope(
            event_time="2026-02-19T00:01:00Z",
            sequence_number=2,
        ))
        skew = [
            s for s in result.drift_signals
            if s["type"] == "CLOCK_SKEW"
        ]
        assert len(skew) == 1

    def test_stall_fires_signal_loss(self):
        sp = SyncPlane(
            REGIONS,
            watermark_stall_threshold_ms=5000.0,
        )
        sp.ingest(_envelope(
            event_time="2026-02-19T00:00:00Z",
            sequence_number=1,
        ))
        signals = sp.check_stalls("2026-02-19T00:00:15Z")
        loss = [
            s for s in signals
            if s["type"] == "SIGNAL_LOSS"
        ]
        assert len(loss) >= 1


# ── Beacon ────────────────────────────────────────────────


class TestBeacon:
    """Independent time beacon validation."""

    def test_within_tolerance_no_signal(self):
        sp = SyncPlane(REGIONS)
        sp.add_beacon(TimeBeacon(
            beacon_id="ntp-east",
            region_id="East",
            reference_time="2026-02-19T00:00:00Z",
            tolerance_ms=500.0,
        ))
        result = sp.ingest(_envelope(
            event_time="2026-02-19T00:00:00Z",
            sequence_number=1,
        ))
        bcn = [
            s for s in result.drift_signals
            if s["type"] == "BEACON_DIVERGENCE"
        ]
        assert len(bcn) == 0

    def test_divergence_fires_signal(self):
        sp = SyncPlane(REGIONS)
        sp.add_beacon(TimeBeacon(
            beacon_id="ntp-east",
            region_id="East",
            reference_time="2026-02-19T00:00:00Z",
            tolerance_ms=500.0,
        ))
        result = sp.ingest(_envelope(
            event_time="2026-02-19T00:00:10Z",
            sequence_number=1,
        ))
        bcn = [
            s for s in result.drift_signals
            if s["type"] == "BEACON_DIVERGENCE"
        ]
        assert len(bcn) == 1

    def test_check_beacon_updates_and_detects(self):
        sp = SyncPlane(REGIONS)
        sp.add_beacon(TimeBeacon(
            beacon_id="ntp-east",
            region_id="East",
            reference_time="2026-02-19T00:00:00Z",
            tolerance_ms=500.0,
        ))
        sp.ingest(_envelope(
            event_time="2026-02-19T00:00:00Z",
            sequence_number=1,
        ))
        signals = sp.check_beacon(
            "ntp-east", "2026-02-19T00:01:00Z",
        )
        assert len(signals) >= 1
        assert signals[0]["type"] == "BEACON_DIVERGENCE"


# ── Replay Detection ──────────────────────────────────────


class TestReplayDetection:
    """Replay detection via sequence + hash matching."""

    def test_duplicate_seq_same_hash_is_replay(self):
        sp = SyncPlane(REGIONS)
        sp.ingest(_envelope(
            sequence_number=1, payload_hash="hash_a",
        ))
        result = sp.ingest(_envelope(
            sequence_number=1, payload_hash="hash_a",
        ))
        assert not result.accepted
        assert result.quarantined
        replay = [
            s for s in result.drift_signals
            if s["type"] == "REPLAY_DETECTED"
        ]
        assert len(replay) == 1

    def test_duplicate_seq_diff_hash_is_violation(self):
        sp = SyncPlane(REGIONS)
        sp.ingest(_envelope(
            sequence_number=1, payload_hash="hash_a",
        ))
        result = sp.ingest(_envelope(
            sequence_number=1, payload_hash="hash_b",
        ))
        assert result.quarantined
        viol = [
            s for s in result.drift_signals
            if s["type"] == "SEQUENCE_VIOLATION"
        ]
        assert len(viol) == 1
        replay = [
            s for s in result.drift_signals
            if s["type"] == "REPLAY_DETECTED"
        ]
        assert len(replay) == 0

    def test_legitimate_late_not_replay(self):
        """Late arrival with new sequence is not replay."""
        sp = SyncPlane(REGIONS)
        sp.ingest(_envelope(
            event_time="2026-02-19T00:00:10Z",
            sequence_number=1,
        ))
        result = sp.ingest(_envelope(
            event_time="2026-02-19T00:00:01Z",
            sequence_number=2,
            payload_hash="new_hash",
        ))
        replay = [
            s for s in result.drift_signals
            if s["type"] == "REPLAY_DETECTED"
        ]
        assert len(replay) == 0


# ── Region Authority ──────────────────────────────────────


class TestRegionAuthority:
    """Region authority cap enforcement."""

    def test_balanced_passes(self):
        sp = SyncPlane(REGIONS, max_authority_pct=0.40)
        for i in range(30):
            region = REGIONS[i % 3]
            t = f"2026-02-19T00:00:{i + 1:02d}Z"
            sp.ingest(_envelope(
                producer_id=f"src-{region}",
                region_id=region,
                sequence_number=i + 1,
                event_time=t,
            ))
        assert sp.authority_check()

    def test_imbalanced_fails(self):
        sp = SyncPlane(
            REGIONS, max_authority_pct=0.40,
        )
        # 10 East, 1 West, 1 Central → East 83%
        for i in range(10):
            t = f"2026-02-19T00:00:{i + 1:02d}Z"
            sp.ingest(_envelope(
                producer_id="src-east",
                region_id="East",
                sequence_number=i + 1,
                event_time=t,
            ))
        sp.ingest(_envelope(
            producer_id="src-west",
            region_id="West",
            sequence_number=1,
        ))
        sp.ingest(_envelope(
            producer_id="src-central",
            region_id="Central",
            sequence_number=1,
        ))
        assert not sp.authority_check()


# ── Integration ───────────────────────────────────────────


class TestIntegration:
    """End-to-end sync plane scenarios."""

    def test_healthy_to_skew_to_recovery(self):
        """Healthy → skew → recovery."""
        sp = SyncPlane(
            REGIONS,
            watermark_stall_threshold_ms=5000.0,
        )
        sp.add_beacon(TimeBeacon(
            beacon_id="ntp-east",
            region_id="East",
            reference_time="2026-02-19T00:00:00Z",
            tolerance_ms=500.0,
        ))

        # Phase 1: Healthy in-order evidence
        for i in range(1, 6):
            t = f"2026-02-19T00:00:{i:02d}Z"
            result = sp.ingest(_envelope(
                event_time=t,
                sequence_number=i,
            ))
            assert result.accepted

        # Phase 2: Clock skew — far-future event
        sp2 = SyncPlane(
            REGIONS,
            watermark_stall_threshold_ms=1000.0,
        )
        sp2.ingest(_envelope(
            event_time="2026-02-19T00:00:01Z",
            sequence_number=1,
        ))
        skew_r = sp2.ingest(_envelope(
            event_time="2026-02-19T00:01:00Z",
            sequence_number=2,
        ))
        skew = [
            s for s in skew_r.drift_signals
            if s["type"] == "CLOCK_SKEW"
        ]
        assert len(skew) >= 1

        # Phase 3: Recovery — normal with fresh plane
        sp3 = SyncPlane(REGIONS)
        for i in range(1, 4):
            t = f"2026-02-19T00:02:{i:02d}Z"
            r = sp3.ingest(_envelope(
                event_time=t,
                sequence_number=i,
            ))
            assert r.accepted
            assert not r.quarantined

    def test_summary_matches_sync_jsonl_shape(self):
        """Summary has all sync.jsonl fields."""
        sp = SyncPlane(REGIONS)
        sp.add_beacon(TimeBeacon(
            beacon_id="ntp-east",
            region_id="East",
            reference_time="2026-02-19T00:00:00Z",
        ))
        sp.ingest(_envelope(
            event_time="2026-02-19T00:00:01Z",
            sequence_number=1,
        ))

        summary = sp.summary()
        assert len(summary) == 3

        east = [
            r for r in summary if r["id"] == "East"
        ][0]
        expected_keys = {
            "id", "status", "sync_nodes",
            "sync_nodes_healthy",
            "watermark_advancing", "last_watermark",
            "time_skew_ms", "watermark_lag_s",
            "replay_flags", "beacons",
            "beacons_healthy", "envelope_count",
        }
        assert expected_keys.issubset(set(east.keys()))
        assert east["status"] == "OK"
        assert east["watermark_advancing"] is True
        assert east["envelope_count"] == 1


# ── Utility Functions ─────────────────────────────────────


class TestUtilities:
    """Helper function coverage."""

    def test_iso_to_ms(self):
        ms = _iso_to_ms("2026-02-19T00:00:00Z")
        assert ms > 0

    def test_iso_to_ms_empty(self):
        assert _iso_to_ms("") == 0.0

    def test_ms_delta(self):
        delta = _ms_delta(
            "2026-02-19T00:00:00Z",
            "2026-02-19T00:00:01Z",
        )
        assert abs(delta - 1000.0) < 1.0

    def test_missing_fields_rejected(self):
        sp = SyncPlane(REGIONS)
        result = sp.ingest({
            "producer_id": "", "region_id": "",
        })
        assert not result.accepted

    def test_unknown_region_rejected(self):
        sp = SyncPlane(REGIONS)
        result = sp.ingest(_envelope(region_id="Mars"))
        assert not result.accepted
