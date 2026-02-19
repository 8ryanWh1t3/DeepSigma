"""Mesh Verify — Cross-node signature and seal chain verification.

Abstract institutional credibility architecture.
No real-world system modeled.
"""

from __future__ import annotations

import hashlib
from typing import Any

from mesh.crypto import canonical_bytes, verify as crypto_verify
from mesh.logstore import load_all
from mesh.transport import (
    ENVELOPES_LOG,
    SEAL_CHAIN_MIRROR_LOG,
    _BASE_DATA_DIR,
)


def verify_envelope_signatures(
    tenant_id: str,
    node_id: str | None = None,
) -> dict[str, Any]:
    """Verify all envelope signatures for a tenant (or specific node).

    Returns a report with pass/fail counts and details.
    """
    tenant_dir = _BASE_DATA_DIR / tenant_id
    if not tenant_dir.exists():
        return {"tenant_id": tenant_id, "status": "not_found", "nodes": []}

    node_dirs = []
    if node_id:
        nd = tenant_dir / node_id
        if nd.exists():
            node_dirs.append(nd)
    else:
        node_dirs = sorted(
            d for d in tenant_dir.iterdir() if d.is_dir()
        )

    report: dict[str, Any] = {
        "tenant_id": tenant_id,
        "nodes": [],
        "total_checked": 0,
        "total_passed": 0,
        "total_failed": 0,
    }

    for nd in node_dirs:
        nid = nd.name
        envs = load_all(nd / ENVELOPES_LOG)
        passed = 0
        failed = 0
        failures = []

        for env in envs:
            signable = {
                "tenant_id": env.get("tenant_id", ""),
                "envelope_id": env.get("envelope_id", ""),
                "timestamp": env.get("timestamp", ""),
                "producer_id": env.get("producer_id", ""),
                "region_id": env.get("region_id", ""),
                "correlation_group": env.get("correlation_group", ""),
                "signal_type": env.get("signal_type", ""),
                "payload_hash": env.get("payload_hash", ""),
            }
            msg = canonical_bytes(signable)
            sig = env.get("signature", "")
            pub = env.get("public_key", "")

            if crypto_verify(pub, msg, sig):
                passed += 1
            else:
                failed += 1
                failures.append(env.get("envelope_id", "unknown"))

            # Also check payload hash
            payload_raw = canonical_bytes(env.get("payload", {}))
            expected = hashlib.sha256(payload_raw).hexdigest()[:40]
            if env.get("payload_hash") != expected:
                failed += 1
                failures.append(f"{env.get('envelope_id', 'unknown')}:payload_hash")

        report["nodes"].append({
            "node_id": nid,
            "envelopes_checked": len(envs),
            "passed": passed,
            "failed": failed,
            "failures": failures[:20],  # cap detail
        })
        report["total_checked"] += len(envs)
        report["total_passed"] += passed
        report["total_failed"] += failed

    report["status"] = "clean" if report["total_failed"] == 0 else "failures_detected"
    return report


def verify_seal_chain(
    tenant_id: str,
    node_id: str | None = None,
) -> dict[str, Any]:
    """Verify seal chain continuity for a tenant.

    Checks:
    - prev_seal_hash matches previous entry's seal_hash
    - First entry has prev_seal_hash = "GENESIS"
    - policy_hash and snapshot_hash are present

    Returns a verification report.
    """
    tenant_dir = _BASE_DATA_DIR / tenant_id
    if not tenant_dir.exists():
        return {"tenant_id": tenant_id, "status": "not_found", "chains": []}

    # Find all seal chain mirrors
    node_dirs = []
    if node_id:
        nd = tenant_dir / node_id
        if nd.exists():
            node_dirs.append(nd)
    else:
        node_dirs = sorted(
            d for d in tenant_dir.iterdir() if d.is_dir()
        )

    report: dict[str, Any] = {
        "tenant_id": tenant_id,
        "chains": [],
        "total_seals": 0,
        "chain_breaks": 0,
        "missing_fields": 0,
    }

    for nd in node_dirs:
        nid = nd.name
        seals = load_all(nd / SEAL_CHAIN_MIRROR_LOG)
        if not seals:
            continue

        chain_ok = True
        breaks = []
        missing = []

        for i, seal in enumerate(seals):
            # Check required fields
            for req_field in ["seal_hash", "prev_seal_hash", "policy_hash", "snapshot_hash"]:
                if not seal.get(req_field):
                    missing.append(f"seal[{i}].{req_field}")
                    report["missing_fields"] += 1

            # Check chain continuity
            if i == 0:
                if seal.get("prev_seal_hash") != "GENESIS":
                    breaks.append({
                        "index": 0,
                        "expected": "GENESIS",
                        "actual": seal.get("prev_seal_hash"),
                    })
                    chain_ok = False
                    report["chain_breaks"] += 1
            else:
                prev_hash = seals[i - 1].get("seal_hash", "")
                if seal.get("prev_seal_hash") != prev_hash:
                    breaks.append({
                        "index": i,
                        "expected": prev_hash,
                        "actual": seal.get("prev_seal_hash"),
                    })
                    chain_ok = False
                    report["chain_breaks"] += 1

        report["chains"].append({
            "node_id": nid,
            "seal_count": len(seals),
            "chain_intact": chain_ok,
            "breaks": breaks[:10],
            "missing_fields": missing[:10],
            "first_seal": seals[0].get("seal_hash", "") if seals else None,
            "last_seal": seals[-1].get("seal_hash", "") if seals else None,
        })
        report["total_seals"] += len(seals)

    report["status"] = (
        "intact" if report["chain_breaks"] == 0 and report["missing_fields"] == 0
        else "breaks_detected"
    )
    return report


def full_verification(tenant_id: str) -> dict[str, Any]:
    """Run complete verification suite for a tenant."""
    sig_report = verify_envelope_signatures(tenant_id)
    chain_report = verify_seal_chain(tenant_id)

    overall = "PASS"
    if sig_report.get("status") != "clean":
        overall = "FAIL"
    if chain_report.get("status") != "intact":
        overall = "FAIL"

    return {
        "tenant_id": tenant_id,
        "overall": overall,
        "envelope_signatures": sig_report,
        "seal_chain": chain_report,
    }
