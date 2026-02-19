"""Seed tenant data for multi-tenant credibility engine demo.

Creates isolated JSONL datasets for tenant-alpha, tenant-bravo, tenant-charlie
with distinct credibility profiles.

Usage: python tools/seed_tenants.py
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))

from tenancy.tenants import ensure_registry  # noqa: E402

BASE_DIR = REPO_ROOT / "data" / "credibility"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _write_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, default=str) + "\n")


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)
        f.write("\n")


def _make_drift_events(
    tid: str,
    prefix: str,
    severities: list[str],
    now: str,
) -> list[dict]:
    """Generate drift events from a severity list."""
    categories = [
        "timing_entropy", "correlation_drift", "confidence_volatility",
        "ttl_compression", "external_mismatch",
    ]
    regions = ["East", "Central", "West"]
    events = []
    for i, sev in enumerate(severities):
        events.append({
            "id": f"DRF-{prefix}-{i + 1:03d}",
            "severity": sev,
            "category": categories[i % len(categories)],
            "region": regions[i % len(regions)],
            "auto_resolved": i >= len(severities) // 2,
            "tenant_id": tid,
            "timestamp": now,
        })
    return events


# -- Tenant Alpha: Stable (index ~95) -----------------------------------------
# Penalty breakdown: drift=0, corr=0, quorum=-1, ttl=-3, sync=-1 = -5

def seed_alpha() -> None:
    tid = "tenant-alpha"
    d = BASE_DIR / tid
    now = _now()

    claims = [
        {"id": "CLM-T0-001", "title": "Primary institutional readiness assertion",
         "state": "VERIFIED", "confidence": 0.94, "k_required": 3, "n_total": 5,
         "margin": 2, "ttl_remaining": 185, "correlation_group": "CG-001",
         "region": "East", "domain": "E1", "last_verified": now, "tenant_id": tid},
        {"id": "CLM-T0-002", "title": "Cross-regional coordination integrity",
         "state": "VERIFIED", "confidence": 0.88, "k_required": 4, "n_total": 6,
         "margin": 2, "ttl_remaining": 0, "correlation_group": "CG-002",
         "region": "Central", "domain": "C2", "last_verified": now, "tenant_id": tid},
        {"id": "CLM-T0-003", "title": "External compliance attestation",
         "state": "VERIFIED", "confidence": 0.90, "k_required": 3, "n_total": 4,
         "margin": 1, "ttl_remaining": 25, "correlation_group": "CG-004",
         "region": "West", "domain": "W2", "last_verified": now, "tenant_id": tid},
    ]

    drift = _make_drift_events(tid, "A", ["low", "low"], now)

    clusters = [
        {"id": "CG-001", "label": "Internal Sensors (East)", "coefficient": 0.42,
         "status": "OK", "sources": ["S-001", "S-004", "S-008"],
         "claims_affected": 15, "domains": ["E1", "E2"], "regions": ["East"],
         "tenant_id": tid},
        {"id": "CG-002", "label": "Shared Infrastructure (East + Central)",
         "coefficient": 0.55, "status": "OK",
         "sources": ["S-003", "S-007", "S-012"],
         "claims_affected": 28, "domains": ["E2", "C1", "C2"],
         "regions": ["East", "Central"], "tenant_id": tid},
        {"id": "CG-003", "label": "Cross-Region API Feed", "coefficient": 0.48,
         "status": "OK", "sources": ["S-CR-017", "S-CR-022"],
         "claims_affected": 18, "domains": ["E3", "C2", "W1"],
         "regions": ["East", "Central", "West"], "tenant_id": tid},
    ]

    sync = [
        {"id": "East", "time_skew_ms": 12, "watermark_lag_s": 0.8, "replay_flags": 0,
         "status": "OK", "sync_nodes": 5, "sync_nodes_healthy": 5,
         "beacons": 2, "beacons_healthy": 2, "watermark_advancing": True,
         "last_watermark": now, "tenant_id": tid},
        {"id": "Central", "time_skew_ms": 120, "watermark_lag_s": 3.2, "replay_flags": 0,
         "status": "WARN", "sync_nodes": 5, "sync_nodes_healthy": 4,
         "beacons": 2, "beacons_healthy": 2, "watermark_advancing": True,
         "last_watermark": now, "tenant_id": tid},
        {"id": "West", "time_skew_ms": 8, "watermark_lag_s": 0.5, "replay_flags": 0,
         "status": "OK", "sync_nodes": 4, "sync_nodes_healthy": 4,
         "beacons": 2, "beacons_healthy": 2, "watermark_advancing": True,
         "last_watermark": now, "tenant_id": tid},
    ]

    snapshots = [
        {"credibility_index": 95, "band": "Stable", "timestamp": now,
         "summary": "CI=95 (Stable) \u2014 2 drift events", "tenant_id": tid},
    ]

    packet = {
        "tenant_id": tid, "packet_id": f"CP-SEED-{tid}",
        "generated_at": now, "generated_by": "seed-script",
        "credibility_index": {"score": 95, "band": "Stable", "components": {}},
        "dlr_summary": {"dlr_id": "DLR-SEED", "title": "Seed packet", "decided_by": "seed", "key_findings": []},
        "rs_summary": {"rs_id": "RS-SEED", "reasoning": {"overall_assessment": "Stable", "primary_risk": "None", "secondary_risk": "None", "recommendation": "Monitor"}},
        "ds_summary": {"ds_id": "DS-SEED", "active_signals": 0, "by_severity": {"low": 0, "medium": 0, "high": 0, "critical": 0}, "critical_signal": {"category": "none", "source": "none", "claims_affected": 0, "regions": [], "description": "No active drift signals"}},
        "mg_summary": {"mg_id": "MG-SEED", "changes_last_24h": {"nodes_added": 0, "edges_added": 0, "patches_applied": 0, "seals_created": 0}},
        "seal": {"sealed": False, "seal_hash": None, "sealed_at": None, "sealed_by": None, "role": None, "hash_chain_length": 157},
        "guardrails": {"abstract_model": True, "domain_specific": False, "description": "Seed packet. Abstract institutional architecture."},
    }

    _write_jsonl(d / "claims.jsonl", claims)
    _write_jsonl(d / "drift.jsonl", drift)
    _write_jsonl(d / "correlation.jsonl", clusters)
    _write_jsonl(d / "sync.jsonl", sync)
    _write_jsonl(d / "snapshots.jsonl", snapshots)
    _write_json(d / "packet_latest.json", packet)
    print(f"  Seeded {tid}: 3 claims, 2 drift, 3 clusters, 3 sync, CI ~95")


# -- Tenant Bravo: Entropy (index ~86) ----------------------------------------
# Penalty breakdown: drift=-7, corr=-2, quorum=-2, ttl=-2, sync=-1 = -14

def seed_bravo() -> None:
    tid = "tenant-bravo"
    d = BASE_DIR / tid
    now = _now()

    claims = [
        {"id": "CLM-T0-001", "title": "Primary institutional readiness assertion",
         "state": "VERIFIED", "confidence": 0.82, "k_required": 3, "n_total": 5,
         "margin": 2, "ttl_remaining": 120, "correlation_group": "CG-001",
         "region": "East", "domain": "E1", "last_verified": now, "tenant_id": tid},
        {"id": "CLM-T0-002", "title": "Cross-regional coordination integrity",
         "state": "DEGRADED", "confidence": 0.68, "k_required": 4, "n_total": 5,
         "margin": 1, "ttl_remaining": 0, "correlation_group": "CG-002",
         "region": "Central", "domain": "C2", "last_verified": now, "tenant_id": tid},
        {"id": "CLM-T0-003", "title": "External compliance attestation",
         "state": "VERIFIED", "confidence": 0.85, "k_required": 3, "n_total": 4,
         "margin": 1, "ttl_remaining": 60, "correlation_group": "CG-004",
         "region": "West", "domain": "W2", "last_verified": now, "tenant_id": tid},
    ]

    # 20 events: 2 critical + 3 high + 2 medium + 13 low → drift_penalty = -7
    drift = _make_drift_events(
        tid, "B",
        ["critical"] * 2 + ["high"] * 3 + ["medium"] * 2 + ["low"] * 13,
        now,
    )

    clusters = [
        {"id": "CG-001", "label": "Internal Sensors (East)", "coefficient": 0.55,
         "status": "OK", "sources": ["S-001", "S-004", "S-008"],
         "claims_affected": 15, "domains": ["E1", "E2"], "regions": ["East"],
         "tenant_id": tid},
        {"id": "CG-002", "label": "Shared Infrastructure (East + Central)",
         "coefficient": 0.82, "status": "REVIEW",
         "sources": ["S-003", "S-007", "S-012"],
         "claims_affected": 28, "domains": ["E2", "C1", "C2"],
         "regions": ["East", "Central"], "tenant_id": tid},
        {"id": "CG-003", "label": "Cross-Region API Feed", "coefficient": 0.52,
         "status": "OK", "sources": ["S-CR-017", "S-CR-022"],
         "claims_affected": 18, "domains": ["E3", "C2", "W1"],
         "regions": ["East", "Central", "West"], "tenant_id": tid},
    ]

    sync = [
        {"id": "East", "time_skew_ms": 45, "watermark_lag_s": 2.1, "replay_flags": 0,
         "status": "OK", "sync_nodes": 5, "sync_nodes_healthy": 4,
         "beacons": 2, "beacons_healthy": 2, "watermark_advancing": True,
         "last_watermark": now, "tenant_id": tid},
        {"id": "Central", "time_skew_ms": 110, "watermark_lag_s": 4.5, "replay_flags": 1,
         "status": "WARN", "sync_nodes": 5, "sync_nodes_healthy": 4,
         "beacons": 2, "beacons_healthy": 1, "watermark_advancing": True,
         "last_watermark": now, "tenant_id": tid},
        {"id": "West", "time_skew_ms": 22, "watermark_lag_s": 1.0, "replay_flags": 0,
         "status": "OK", "sync_nodes": 4, "sync_nodes_healthy": 4,
         "beacons": 2, "beacons_healthy": 2, "watermark_advancing": True,
         "last_watermark": now, "tenant_id": tid},
    ]

    snapshots = [
        {"credibility_index": 86, "band": "Minor Drift", "timestamp": now,
         "summary": "CI=86 (Minor Drift) \u2014 1 DEGRADED claim, 20 drift events",
         "tenant_id": tid},
    ]

    packet = {
        "tenant_id": tid, "packet_id": f"CP-SEED-{tid}",
        "generated_at": now, "generated_by": "seed-script",
        "credibility_index": {"score": 86, "band": "Minor Drift", "components": {}},
        "dlr_summary": {"dlr_id": "DLR-SEED", "title": "Seed packet", "decided_by": "seed", "key_findings": ["1 DEGRADED claim"]},
        "rs_summary": {"rs_id": "RS-SEED", "reasoning": {"overall_assessment": "Elevated stress", "primary_risk": "CG-002 REVIEW (0.82)", "secondary_risk": "CLM-T0-002 DEGRADED", "recommendation": "Review flagged claims"}},
        "ds_summary": {"ds_id": "DS-SEED", "active_signals": 10, "by_severity": {"low": 3, "medium": 2, "high": 3, "critical": 2}, "critical_signal": {"category": "timing_entropy", "source": "DRF-B-001", "claims_affected": 5, "regions": ["East"], "description": "timing_entropy drift event (critical)"}},
        "mg_summary": {"mg_id": "MG-SEED", "changes_last_24h": {"nodes_added": 0, "edges_added": 0, "patches_applied": 0, "seals_created": 0}},
        "seal": {"sealed": False, "seal_hash": None, "sealed_at": None, "sealed_by": None, "role": None, "hash_chain_length": 157},
        "guardrails": {"abstract_model": True, "domain_specific": False, "description": "Seed packet. Abstract institutional architecture."},
    }

    _write_jsonl(d / "claims.jsonl", claims)
    _write_jsonl(d / "drift.jsonl", drift)
    _write_jsonl(d / "correlation.jsonl", clusters)
    _write_jsonl(d / "sync.jsonl", sync)
    _write_jsonl(d / "snapshots.jsonl", snapshots)
    _write_json(d / "packet_latest.json", packet)
    print(f"  Seeded {tid}: 3 claims (1 DEGRADED), 20 drift, CG-002 REVIEW (0.82), CI ~86")


# -- Tenant Charlie: Correlation pressure (index ~68) --------------------------
# Penalty breakdown: drift=-12, corr=-7, quorum=-4, ttl=-5, sync=-4 = -32

def seed_charlie() -> None:
    tid = "tenant-charlie"
    d = BASE_DIR / tid
    now = _now()

    claims = [
        {"id": "CLM-T0-001", "title": "Primary institutional readiness assertion",
         "state": "DEGRADED", "confidence": 0.62, "k_required": 3, "n_total": 5,
         "margin": 1, "ttl_remaining": 0, "correlation_group": "CG-001",
         "region": "East", "domain": "E1", "last_verified": now, "tenant_id": tid},
        {"id": "CLM-T0-002", "title": "Cross-regional coordination integrity",
         "state": "UNKNOWN", "confidence": None, "k_required": 4, "n_total": 5,
         "margin": 0, "ttl_remaining": 0, "correlation_group": "CG-002",
         "region": "Central", "domain": "C2", "last_verified": now, "tenant_id": tid},
        {"id": "CLM-T0-003", "title": "External compliance attestation",
         "state": "VERIFIED", "confidence": 0.78, "k_required": 3, "n_total": 4,
         "margin": 1, "ttl_remaining": 25, "correlation_group": "CG-004",
         "region": "West", "domain": "W2", "last_verified": now, "tenant_id": tid},
    ]

    # 20 events: 4 critical + 3 high + 3 medium + 10 low → drift_penalty = -12
    drift = _make_drift_events(
        tid, "C",
        ["critical"] * 4 + ["high"] * 3 + ["medium"] * 3 + ["low"] * 10,
        now,
    )

    clusters = [
        {"id": "CG-001", "label": "Internal Sensors (East)", "coefficient": 0.82,
         "status": "REVIEW", "sources": ["S-001", "S-004", "S-008"],
         "claims_affected": 15, "domains": ["E1", "E2"], "regions": ["East"],
         "tenant_id": tid},
        {"id": "CG-002", "label": "Shared Infrastructure (East + Central)",
         "coefficient": 0.93, "status": "CRITICAL",
         "sources": ["S-003", "S-007", "S-012"],
         "claims_affected": 28, "domains": ["E2", "C1", "C2"],
         "regions": ["East", "Central"], "tenant_id": tid},
        {"id": "CG-003", "label": "Cross-Region API Feed", "coefficient": 0.72,
         "status": "REVIEW", "sources": ["S-CR-017", "S-CR-022"],
         "claims_affected": 18, "domains": ["E3", "C2", "W1"],
         "regions": ["East", "Central", "West"], "tenant_id": tid},
    ]

    sync = [
        {"id": "East", "time_skew_ms": 85, "watermark_lag_s": 4.2, "replay_flags": 0,
         "status": "OK", "sync_nodes": 5, "sync_nodes_healthy": 3,
         "beacons": 2, "beacons_healthy": 1, "watermark_advancing": True,
         "last_watermark": now, "tenant_id": tid},
        {"id": "Central", "time_skew_ms": 520, "watermark_lag_s": 35.0, "replay_flags": 6,
         "status": "CRITICAL", "sync_nodes": 5, "sync_nodes_healthy": 2,
         "beacons": 2, "beacons_healthy": 0, "watermark_advancing": False,
         "last_watermark": now, "tenant_id": tid},
        {"id": "West", "time_skew_ms": 150, "watermark_lag_s": 6.5, "replay_flags": 2,
         "status": "WARN", "sync_nodes": 4, "sync_nodes_healthy": 3,
         "beacons": 2, "beacons_healthy": 1, "watermark_advancing": True,
         "last_watermark": now, "tenant_id": tid},
    ]

    snapshots = [
        {"credibility_index": 68, "band": "Elevated", "timestamp": now,
         "summary": "CI=68 (Elevated) \u2014 1 UNKNOWN, 1 DEGRADED, 20 drift events",
         "tenant_id": tid},
    ]

    packet = {
        "tenant_id": tid, "packet_id": f"CP-SEED-{tid}",
        "generated_at": now, "generated_by": "seed-script",
        "credibility_index": {"score": 68, "band": "Elevated", "components": {}},
        "dlr_summary": {"dlr_id": "DLR-SEED", "title": "Seed packet", "decided_by": "seed", "key_findings": ["1 UNKNOWN, 1 DEGRADED", "CG-002 CRITICAL (0.93)"]},
        "rs_summary": {"rs_id": "RS-SEED", "reasoning": {"overall_assessment": "Structural degradation", "primary_risk": "CG-002 CRITICAL at 0.93", "secondary_risk": "CLM-T0-002 UNKNOWN", "recommendation": "Immediate remediation"}},
        "ds_summary": {"ds_id": "DS-SEED", "active_signals": 10, "by_severity": {"low": 0, "medium": 3, "high": 3, "critical": 4}, "critical_signal": {"category": "timing_entropy", "source": "DRF-C-001", "claims_affected": 5, "regions": ["Central"], "description": "timing_entropy drift event (critical)"}},
        "mg_summary": {"mg_id": "MG-SEED", "changes_last_24h": {"nodes_added": 0, "edges_added": 0, "patches_applied": 0, "seals_created": 0}},
        "seal": {"sealed": False, "seal_hash": None, "sealed_at": None, "sealed_by": None, "role": None, "hash_chain_length": 157},
        "guardrails": {"abstract_model": True, "domain_specific": False, "description": "Seed packet. Abstract institutional architecture."},
    }

    _write_jsonl(d / "claims.jsonl", claims)
    _write_jsonl(d / "drift.jsonl", drift)
    _write_jsonl(d / "correlation.jsonl", clusters)
    _write_jsonl(d / "sync.jsonl", sync)
    _write_jsonl(d / "snapshots.jsonl", snapshots)
    _write_json(d / "packet_latest.json", packet)
    print(f"  Seeded {tid}: 3 claims (1 UNKNOWN, 1 DEGRADED), 20 drift, CG-002 CRITICAL (0.93), CI ~68")


def main() -> None:
    print("Seeding tenant data...")
    ensure_registry()
    print("  Registry ensured at data/tenants.json")
    seed_alpha()
    seed_bravo()
    seed_charlie()
    print("Done.")


if __name__ == "__main__":
    main()
