"""Credibility Engine Simulation - Credibility Packet Generator.

Produces credibility_packet_example.json matching the dashboard schema.
Each packet includes DLR, RS, DS, MG summaries and a seal.

Abstract institutional credibility architecture.
No real-world system modeled.
"""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engine import CredibilityEngine


def generate_packet(engine: CredibilityEngine) -> dict:
    """Generate a complete credibility packet from current engine state."""
    now = engine.sim_time
    ts = now.isoformat().replace("+00:00", "Z")
    packet_id = f"CP-{now.strftime('%Y-%m-%d-%H%M')}"

    # -- DLR summary -----------------------------------------------------------
    findings = _build_findings(engine)

    dlr = {
        "dlr_id": f"DLR-{packet_id}",
        "title": "Credibility Packet \u2014 Institutional State Assessment",
        "decided_by": "credibility-engine (automated)",
        "decision_type": "assessment",
        "key_findings": findings,
    }

    # -- RS summary ------------------------------------------------------------
    rs = {
        "rs_id": f"RS-{packet_id}",
        "reasoning": _build_reasoning(engine),
    }

    # -- DS summary ------------------------------------------------------------
    ds = _build_ds(engine, packet_id)

    # -- MG summary ------------------------------------------------------------
    mg = {
        "mg_id": f"MG-{packet_id}",
        "changes_last_24h": {
            "nodes_added": engine.nodes_added,
            "edges_added": engine.edges_added,
            "nodes_modified": engine.nodes_modified,
            "drift_signals_created": engine.drift_total,
            "patches_applied": engine.patches_applied,
            "seals_created": engine.seals_created,
        },
    }

    # -- Seal ------------------------------------------------------------------
    seal_input = f"{packet_id}:{ts}:{engine.credibility_index}"
    seal_hash = hashlib.sha256(seal_input.encode()).hexdigest()[:40]

    seal = {
        "sealed": True,
        "seal_hash": f"sha256:{seal_hash}",
        "sealed_at": ts,
        "sealed_by": "credibility-engine-sim",
        "role": "Coherence Steward",
        "hash_chain_length": engine.seal_chain_length,
    }

    return {
        "packet_id": packet_id,
        "generated_at": ts,
        "generated_by": "credibility-engine-sim",
        "credibility_index": {
            "score": engine.credibility_index,
            "band": engine.index_band,
            "components": {
                "tier_weighted_integrity": engine.integrity,
                "drift_penalty": engine.drift_penalty,
                "correlation_risk": engine.correlation_penalty,
                "quorum_margin": engine.quorum_penalty,
                "ttl_expiration": engine.ttl_penalty,
                "confirmation_bonus": engine.confirmation_bonus,
            },
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
                "Simulation-generated credibility packet. "
                "Abstract institutional architecture. "
                "No real-world system modeled."
            ),
        },
    }


# -- Internal helpers ----------------------------------------------------------

def _build_findings(engine: CredibilityEngine) -> list[str]:
    """Generate DLR key findings from engine state."""
    findings = [
        f"Credibility Index at {engine.credibility_index} "
        f"({engine.index_band}) \u2014 "
        f"{'within healthy production band' if engine.credibility_index >= 85 else 'below healthy production band'}"
    ]

    unknown_claims = [c for c in engine.claims if c.status == "UNKNOWN"]
    if unknown_claims:
        ids = ", ".join(c.claim_id for c in unknown_claims)
        findings.append(
            f"{len(unknown_claims)} Tier 0 claim(s) in UNKNOWN state: {ids}"
        )

    degraded_claims = [c for c in engine.claims if c.status == "DEGRADED"]
    if degraded_claims:
        ids = ", ".join(c.claim_id for c in degraded_claims)
        findings.append(
            f"{len(degraded_claims)} Tier 0 claim(s) DEGRADED: {ids}"
        )

    critical_clusters = [
        c for c in engine.clusters if c.coefficient > 0.9
    ]
    if critical_clusters:
        for cc in critical_clusters:
            findings.append(
                f"Correlation cluster {cc.cluster_id} ({cc.label}) "
                f"at {cc.coefficient:.2f} \u2014 CRITICAL"
            )

    findings.append(
        f"{engine.drift_total} drift events accumulated \u2014 "
        f"{engine.auto_patch_rate:.0%} auto-resolved, "
        f"{engine.drift_escalated} escalated"
    )

    return findings


def _build_reasoning(engine: CredibilityEngine) -> dict:
    """Generate RS reasoning narrative from engine state."""
    idx = engine.credibility_index
    band = engine.index_band

    if idx >= 85:
        assessment = (
            "Lattice is operationally healthy with "
            f"Credibility Index at {idx} ({band}). "
            "Localized drift signals are within expected bounds."
        )
    elif idx >= 70:
        assessment = (
            f"Lattice is under elevated stress. "
            f"Credibility Index at {idx} ({band}). "
            "Multiple subsystems showing degradation. "
            "Coordinated response required."
        )
    elif idx >= 50:
        assessment = (
            f"Lattice is in structural degradation. "
            f"Credibility Index at {idx} ({band}). "
            "Multiple Tier 0 claims compromised. "
            "Dependent decisions should be suspended pending recovery."
        )
    else:
        assessment = (
            f"Lattice integrity compromised. "
            f"Credibility Index at {idx} ({band}). "
            "Institutional truth maintenance has failed. "
            "All dependent decisions must halt. "
            "Full recovery protocol required."
        )

    # Primary risk
    worst_cluster = max(engine.clusters, key=lambda c: c.coefficient)
    if worst_cluster.coefficient > 0.9:
        primary = (
            f"{worst_cluster.cluster_id} ({worst_cluster.label}) "
            f"correlation at {worst_cluster.coefficient:.2f} \u2014 "
            f"affects {worst_cluster.claims_affected} claims across "
            f"{', '.join(worst_cluster.regions)}. "
            "Structural redundancy illusion."
        )
    elif worst_cluster.coefficient > 0.7:
        primary = (
            f"{worst_cluster.cluster_id} ({worst_cluster.label}) "
            f"correlation at {worst_cluster.coefficient:.2f} approaching "
            "critical threshold. Monitor closely."
        )
    else:
        primary = "No immediate correlation risk. All clusters below review threshold."

    # Secondary risk
    unknown_claims = [c for c in engine.claims if c.status == "UNKNOWN"]
    if unknown_claims:
        c = unknown_claims[0]
        secondary = (
            f"{c.claim_id} in UNKNOWN state \u2014 "
            f"{c.degradation_reason or 'quorum broken'}"
        )
    else:
        degraded = [c for c in engine.claims if c.status == "DEGRADED"]
        if degraded:
            c = degraded[0]
            secondary = (
                f"{c.claim_id} DEGRADED with margin {c.margin} \u2014 "
                f"{c.degradation_reason or 'confidence below threshold'}"
            )
        else:
            secondary = "No claim-level risks identified."

    # Recommendation
    if idx >= 85:
        recommendation = (
            "Continue monitoring. "
            "Review flagged drift fingerprints on next rotation."
        )
    elif idx >= 70:
        recommendation = (
            "Prioritize correlation mitigation for clusters in REVIEW state. "
            "Restore quorum margin on compressed claims. "
            "Investigate sync plane anomalies."
        )
    elif idx >= 50:
        recommendation = (
            "Activate remediation protocol. "
            "Restore Tier 0 quorum before allowing dependent decisions. "
            "Isolate correlated failure domains. "
            "Engage sync plane recovery."
        )
    else:
        recommendation = (
            "HALT all dependent decisions. "
            "Activate full recovery protocol. "
            "Restore sync plane integrity before quorum. "
            "Independent verification required before index can be trusted."
        )

    return {
        "overall_assessment": assessment,
        "primary_risk": primary,
        "secondary_risk": secondary,
        "recommendation": recommendation,
    }


def _build_ds(engine: CredibilityEngine, packet_id: str) -> dict:
    """Generate DS summary from engine state."""
    by_sev = {
        "low": 0, "medium": 0, "high": 0, "critical": 0,
    }
    for fp in engine.fingerprints:
        if not fp.auto_resolved and fp.recurrence_count > 0:
            by_sev[fp.severity] += 1

    active = sum(by_sev.values())

    # Find the most critical signal
    critical_fps = [
        fp for fp in engine.fingerprints
        if fp.severity == "critical" and not fp.auto_resolved
    ]
    if not critical_fps:
        critical_fps = [
            fp for fp in engine.fingerprints
            if fp.severity == "high" and not fp.auto_resolved
        ]
    if not critical_fps:
        critical_fps = sorted(
            engine.fingerprints,
            key=lambda f: f.recurrence_count,
            reverse=True,
        )

    top = critical_fps[0] if critical_fps else engine.fingerprints[0]

    # Map fingerprint to cluster/region
    regions = ["East", "Central", "West"]
    if "WEST" in top.fingerprint:
        regions = ["West"]
    elif "C2" in top.fingerprint or "CENTRAL" in top.fingerprint.upper():
        regions = ["Central"]
    elif "S003" in top.fingerprint:
        regions = ["East", "Central", "West"]

    return {
        "ds_id": f"DS-{packet_id}",
        "active_signals": max(active, engine.active_drift_signals),
        "by_severity": by_sev,
        "critical_signal": {
            "category": _fp_to_category(top.fingerprint),
            "source": top.fingerprint,
            "claims_affected": max(1, top.tier_impact * 5 + top.recurrence_count // 3),
            "regions": regions,
            "description": top.description,
        },
    }


def _fp_to_category(fingerprint: str) -> str:
    """Map fingerprint ID to drift category."""
    fp = fingerprint.upper()
    if "TTL" in fp:
        return "ttl_compression"
    if "CONF" in fp:
        return "confidence_volatility"
    if "CORR" in fp:
        return "correlation_drift"
    if "TIMING" in fp or "LAG" in fp:
        return "timing_entropy"
    if "SYNC" in fp or "BEACON" in fp:
        return "external_mismatch"
    return "timing_entropy"
