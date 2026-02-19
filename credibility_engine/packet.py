"""Credibility Engine — Credibility Packet Generator.

Produces sealed credibility packets containing DLR, RS, DS, MG summaries.
Persists the latest packet to data/credibility/packet_latest.json.

Abstract institutional credibility architecture.
No real-world system modeled.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from credibility_engine.engine import CredibilityEngine


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def generate_credibility_packet(engine: CredibilityEngine) -> dict[str, Any]:
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

    # Seal
    seal_input = f"{packet_id}:{ts}:{engine.credibility_index}"
    seal_hash = hashlib.sha256(seal_input.encode()).hexdigest()[:40]
    engine.seal_chain_length += 1

    seal = {
        "sealed": True,
        "seal_hash": f"sha256:{seal_hash}",
        "sealed_at": ts,
        "sealed_by": "credibility-engine-runtime",
        "role": "Coherence Steward",
        "hash_chain_length": engine.seal_chain_length,
    }

    packet = {
        "packet_id": packet_id,
        "generated_at": ts,
        "generated_by": "credibility-engine-runtime",
        "credibility_index": {
            "score": engine.credibility_index,
            "band": engine.index_band,
            "components": engine.index_components,
        },
        "dlr_summary": dlr,
        "rs_summary": rs,
        "ds_summary": ds,
        "mg_summary": mg,
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
