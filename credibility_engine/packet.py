"""Credibility Engine — Credibility Packet Generator.

Produces sealed credibility packets containing DLR, RS, DS, MG summaries.
Persists the latest packet to data/credibility/packet_latest.json.

v0.9.0: Seal chaining — each seal links to the previous seal for that tenant
via prev_seal_hash, policy_hash, and snapshot_hash fields.

Abstract institutional credibility architecture.
No real-world system modeled.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from credibility_engine.engine import CredibilityEngine

SEAL_CHAIN_FILE = "seal_chain.jsonl"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _canonical_json(data: dict[str, Any]) -> str:
    """Produce a canonical JSON string for hashing."""
    return json.dumps(data, sort_keys=True, default=str)


def _load_last_seal(engine: "CredibilityEngine") -> dict[str, Any] | None:
    """Load the last seal chain entry for the tenant."""
    return engine.store.load_latest(SEAL_CHAIN_FILE)


def _append_seal_chain(engine: "CredibilityEngine", entry: dict[str, Any]) -> None:
    """Append a seal chain record."""
    engine.store.append_record(SEAL_CHAIN_FILE, entry)


def generate_credibility_packet(
    engine: CredibilityEngine,
    role: str = "Coherence Steward",
    user: str = "credibility-engine-runtime",
) -> dict[str, Any]:
    from governance.audit import audit_action  # noqa: F811
    from tenancy.policies import get_policy_hash, load_policy  # noqa: F811

    """Generate a complete credibility packet from current engine state.

    Returns the packet dict and persists it to the store.
    """
    ts = _now_iso()
    now = datetime.now(timezone.utc)
    packet_id = f"CP-{now.strftime('%Y-%m-%d-%H%M')}"

    # DLR summary
    dlr = _build_dlr(engine, packet_id)

    # RS summary
    rs = _build_rs(engine, packet_id)

    # DS summary
    ds = _build_ds(engine, packet_id)

    # MG summary
    mg = {
        "mg_id": f"MG-{packet_id}",
        "changes_last_24h": {
            "nodes_added": engine.nodes_added,
            "edges_added": engine.edges_added,
            "nodes_modified": 0,
            "drift_signals_created": len(engine.drift_events),
            "patches_applied": engine.patches_applied,
            "seals_created": engine.seals_created,
        },
    }

    # Policy hash
    policy = load_policy(engine.tenant_id)
    policy_hash = get_policy_hash(policy)

    # Seal — generated packets are unsealed; use seal_credibility_packet() to seal
    seal = {
        "sealed": False,
        "seal_hash": None,
        "sealed_at": None,
        "sealed_by": None,
        "role": None,
        "hash_chain_length": engine.seal_chain_length,
        "prev_seal_hash": None,
        "policy_hash": policy_hash,
        "snapshot_hash": None,
    }

    # Policy evaluation summary (if available)
    policy_eval = getattr(engine, "_last_policy_eval", None)

    packet = {
        "tenant_id": engine.tenant_id,
        "packet_id": packet_id,
        "generated_at": ts,
        "generated_by": user,
        "credibility_index": {
            "score": engine.credibility_index,
            "band": engine.index_band,
            "components": engine.index_components,
        },
        "dlr_summary": dlr,
        "rs_summary": rs,
        "ds_summary": ds,
        "mg_summary": mg,
        "policy_hash": policy_hash,
        "policy_evaluation": {
            "violation_count": policy_eval.get("violation_count", 0) if policy_eval else 0,
            "violations": policy_eval.get("violations", []) if policy_eval else [],
        },
        "seal": seal,
        "guardrails": {
            "abstract_model": True,
            "domain_specific": False,
            "description": (
                "Runtime-generated credibility packet. "
                "Abstract institutional architecture. "
                "No real-world system modeled."
            ),
        },
    }

    # Persist
    engine.store.save_packet(packet)

    # Audit
    audit_action(
        tenant_id=engine.tenant_id,
        actor_user=user,
        actor_role=role,
        action="PACKET_GENERATE",
        target_type="PACKET",
        target_id=packet_id,
        outcome="SUCCESS",
        metadata={"score": engine.credibility_index, "band": engine.index_band},
    )

    return packet


def seal_credibility_packet(
    engine: CredibilityEngine,
    packet: dict[str, Any] | None = None,
    role: str = "Coherence Steward",
    user: str = "credibility-engine-runtime",
) -> dict[str, Any]:
    """Seal an existing packet (or the latest) with a chained SHA-256 hash.

    Chained sealing includes:
    - prev_seal_hash: hash of the last seal for this tenant (or "GENESIS")
    - policy_hash: hash of the current policy
    - snapshot_hash: hash of the latest snapshot

    Sealing requires the coherence_steward role (enforced at API layer).
    Returns the sealed packet and persists it.
    """
    from governance.audit import audit_action  # noqa: F811
    from tenancy.policies import get_policy_hash, load_policy  # noqa: F811

    if packet is None:
        packet = engine.store.latest_packet()
    if packet is None:
        # No packet to seal — generate one first
        packet = generate_credibility_packet(engine, role=role, user=user)

    ts = _now_iso()
    packet_id = packet["packet_id"]

    # Load chain context
    last_seal = _load_last_seal(engine)
    prev_seal_hash = (
        last_seal.get("seal_hash", "GENESIS") if last_seal else "GENESIS"
    )

    # Policy hash
    policy = load_policy(engine.tenant_id)
    policy_hash = get_policy_hash(policy)

    # Snapshot hash
    latest_snapshot = engine.store.latest_snapshot()
    snapshot_hash = (
        hashlib.sha256(_canonical_json(latest_snapshot).encode()).hexdigest()[:40]
        if latest_snapshot
        else "NO_SNAPSHOT"
    )

    # Compute chained seal hash
    # Exclude seal fields from packet for canonical input
    packet_for_hash = {
        k: v for k, v in packet.items() if k != "seal"
    }
    canonical_packet = _canonical_json(packet_for_hash)
    seal_input = f"{prev_seal_hash}|{policy_hash}|{snapshot_hash}|{canonical_packet}"
    seal_hash = f"sha256:{hashlib.sha256(seal_input.encode()).hexdigest()[:40]}"

    engine.seal_chain_length += 1
    engine.seals_created += 1

    packet["seal"] = {
        "sealed": True,
        "seal_hash": seal_hash,
        "sealed_at": ts,
        "sealed_by": user,
        "role": role,
        "hash_chain_length": engine.seal_chain_length,
        "prev_seal_hash": prev_seal_hash,
        "policy_hash": policy_hash,
        "snapshot_hash": snapshot_hash,
    }

    engine.store.save_packet(packet)

    # Append seal chain record
    chain_entry = {
        "tenant_id": engine.tenant_id,
        "packet_id": packet_id,
        "sealed_at": ts,
        "seal_hash": seal_hash,
        "prev_seal_hash": prev_seal_hash,
        "policy_hash": policy_hash,
        "snapshot_hash": snapshot_hash,
    }
    _append_seal_chain(engine, chain_entry)

    # Audit
    audit_action(
        tenant_id=engine.tenant_id,
        actor_user=user,
        actor_role=role,
        action="PACKET_SEAL",
        target_type="PACKET",
        target_id=packet_id,
        outcome="SUCCESS",
        metadata={
            "seal_hash": seal_hash,
            "prev_seal_hash": prev_seal_hash,
            "chain_length": engine.seal_chain_length,
        },
    )

    return packet


# -- Internal helpers ----------------------------------------------------------

def _build_dlr(engine: CredibilityEngine, packet_id: str) -> dict[str, Any]:
    """Build DLR summary from engine state."""
    findings = [
        f"Credibility Index at {engine.credibility_index} "
        f"({engine.index_band}) \u2014 "
        f"{'within healthy production band' if engine.credibility_index >= 85 else 'below healthy production band'}"
    ]

    unknown_claims = [c for c in engine.claims if c.state == "UNKNOWN"]
    if unknown_claims:
        ids = ", ".join(c.id for c in unknown_claims)
        findings.append(
            f"{len(unknown_claims)} Tier 0 claim(s) in UNKNOWN state: {ids}"
        )

    degraded_claims = [c for c in engine.claims if c.state == "DEGRADED"]
    if degraded_claims:
        ids = ", ".join(c.id for c in degraded_claims)
        findings.append(
            f"{len(degraded_claims)} Tier 0 claim(s) DEGRADED: {ids}"
        )

    critical_clusters = [c for c in engine.clusters if c.coefficient > 0.9]
    for cc in critical_clusters:
        findings.append(
            f"Correlation cluster {cc.id} ({cc.label}) "
            f"at {cc.coefficient:.2f} \u2014 CRITICAL"
        )

    auto_resolved = sum(1 for e in engine.drift_events if e.auto_resolved)
    auto_rate = auto_resolved / max(len(engine.drift_events), 1)
    findings.append(
        f"{len(engine.drift_events)} drift events accumulated \u2014 "
        f"{auto_rate:.0%} auto-resolved"
    )

    return {
        "dlr_id": f"DLR-{packet_id}",
        "title": "Credibility Packet \u2014 Institutional State Assessment",
        "decided_by": "credibility-engine (runtime)",
        "decision_type": "assessment",
        "key_findings": findings,
    }


def _build_rs(engine: CredibilityEngine, packet_id: str) -> dict[str, Any]:
    """Build RS reasoning summary from engine state."""
    idx = engine.credibility_index
    band = engine.index_band

    if idx >= 85:
        assessment = (
            f"Lattice is operationally healthy with "
            f"Credibility Index at {idx} ({band}). "
            "Localized drift signals are within expected bounds."
        )
        recommendation = (
            "Continue monitoring. "
            "Review flagged drift fingerprints on next rotation."
        )
    elif idx >= 70:
        assessment = (
            f"Lattice is under elevated stress. "
            f"Credibility Index at {idx} ({band}). "
            "Multiple subsystems showing degradation."
        )
        recommendation = (
            "Prioritize correlation mitigation for clusters in REVIEW state. "
            "Restore quorum margin on compressed claims."
        )
    elif idx >= 50:
        assessment = (
            f"Lattice is in structural degradation. "
            f"Credibility Index at {idx} ({band}). "
            "Multiple Tier 0 claims compromised."
        )
        recommendation = (
            "Activate remediation protocol. "
            "Restore Tier 0 quorum before allowing dependent decisions."
        )
    else:
        assessment = (
            f"Lattice integrity compromised. "
            f"Credibility Index at {idx} ({band}). "
            "Institutional truth maintenance has failed."
        )
        recommendation = (
            "HALT all dependent decisions. "
            "Activate full recovery protocol."
        )

    # Primary risk
    worst = max(engine.clusters, key=lambda c: c.coefficient) if engine.clusters else None
    if worst and worst.coefficient > 0.9:
        primary = (
            f"{worst.id} ({worst.label}) correlation at {worst.coefficient:.2f} "
            "\u2014 CRITICAL. Structural redundancy illusion."
        )
    elif worst and worst.coefficient > 0.7:
        primary = (
            f"{worst.id} ({worst.label}) correlation at {worst.coefficient:.2f} "
            "approaching critical threshold."
        )
    else:
        primary = "No immediate correlation risk."

    # Secondary risk
    unknown = [c for c in engine.claims if c.state == "UNKNOWN"]
    if unknown:
        secondary = f"{unknown[0].id} in UNKNOWN state \u2014 quorum broken"
    else:
        degraded = [c for c in engine.claims if c.state == "DEGRADED"]
        if degraded:
            secondary = f"{degraded[0].id} DEGRADED with margin {degraded[0].margin}"
        else:
            secondary = "No claim-level risks identified."

    return {
        "rs_id": f"RS-{packet_id}",
        "reasoning": {
            "overall_assessment": assessment,
            "primary_risk": primary,
            "secondary_risk": secondary,
            "recommendation": recommendation,
        },
    }


def _build_ds(engine: CredibilityEngine, packet_id: str) -> dict[str, Any]:
    """Build DS drift signal summary."""
    by_sev = {"low": 0, "medium": 0, "high": 0, "critical": 0}
    for e in engine.drift_events:
        if not e.auto_resolved:
            by_sev[e.severity] = by_sev.get(e.severity, 0) + 1

    active = sum(by_sev.values())

    # Critical signal (most impactful unresolved)
    unresolved = [e for e in engine.drift_events if not e.auto_resolved]
    critical_events = [e for e in unresolved if e.severity == "critical"]
    if not critical_events:
        critical_events = [e for e in unresolved if e.severity == "high"]
    if not critical_events:
        critical_events = unresolved[-1:] if unresolved else []

    if critical_events:
        top = critical_events[0]
        critical_signal = {
            "category": top.category,
            "source": top.fingerprint or top.id,
            "claims_affected": max(1, top.tier_impact * 5),
            "regions": [top.region],
            "description": f"{top.category} drift event ({top.severity})",
        }
    else:
        critical_signal = {
            "category": "none",
            "source": "none",
            "claims_affected": 0,
            "regions": [],
            "description": "No active drift signals",
        }

    return {
        "ds_id": f"DS-{packet_id}",
        "active_signals": active,
        "by_severity": by_sev,
        "critical_signal": critical_signal,
    }
