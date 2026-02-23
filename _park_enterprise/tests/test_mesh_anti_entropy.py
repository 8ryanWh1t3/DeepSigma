"""Tests for mesh anti-entropy + delta sync helpers."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mesh.anti_entropy import (  # noqa: E402
    DeltaCursor,
    apply_delta_replay_safe,
    build_delta_offer,
    digest,
    estimate_bandwidth_profile,
    reconcile_sets,
)


def _rec(rid: str, ts: str, value: int) -> dict:
    return {"id": rid, "timestamp": ts, "payload": {"value": value}}


def test_digest_is_deterministic_for_order_variants():
    a = [_rec("r1", "2026-02-23T00:00:00Z", 1), _rec("r2", "2026-02-23T00:00:01Z", 2)]
    b = [a[1], a[0]]
    assert digest(a) == digest(b)


def test_build_delta_offer_filters_known_and_old_records():
    local = [
        _rec("r1", "2026-02-23T00:00:00Z", 1),
        _rec("r2", "2026-02-23T00:00:01Z", 2),
        _rec("r3", "2026-02-23T00:00:02Z", 3),
    ]
    out = build_delta_offer(
        local_records=local,
        remote_known_ids={"r1"},
        since_timestamp="2026-02-23T00:00:00Z",
    )
    assert [r["id"] for r in out] == ["r2", "r3"]


def test_apply_delta_replay_safe_skips_duplicates():
    cursor = DeltaCursor(last_timestamp="2026-02-23T00:00:00Z", seen_ids={"r1"})
    incoming = [
        _rec("r1", "2026-02-23T00:00:01Z", 10),  # replay
        _rec("r2", "2026-02-23T00:00:02Z", 20),  # new
    ]
    result = apply_delta_replay_safe(incoming, cursor)
    assert [r["id"] for r in result.applied] == ["r2"]
    assert [r["id"] for r in result.skipped_replay] == ["r1"]
    assert result.cursor.last_timestamp == "2026-02-23T00:00:02Z"
    assert "r2" in result.cursor.seen_ids


def test_reconcile_sets_detects_missing_and_mismatch():
    local = [_rec("r1", "2026-02-23T00:00:00Z", 1), _rec("r2", "2026-02-23T00:00:01Z", 2)]
    remote = [_rec("r1", "2026-02-23T00:00:00Z", 1), _rec("r2", "2026-02-23T00:00:01Z", 9), _rec("r3", "2026-02-23T00:00:02Z", 3)]
    recon = reconcile_sets(local, remote)
    assert recon["in_sync"] is False
    assert recon["missing_on_local"] == ["r3"]
    assert recon["missing_on_remote"] == []
    assert recon["mismatched_records"] == ["r2"]


def test_bandwidth_profile_shows_savings():
    profile = estimate_bandwidth_profile(full_records=1000, delta_records=80, avg_record_bytes=256)
    assert profile["full_bytes"] == 256000.0
    assert profile["delta_bytes"] == 20480.0
    assert profile["saved_percent"] > 90.0
