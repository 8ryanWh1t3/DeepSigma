"""Authority Drift Detection -- scan authority state for trust decay.

Detects expired delegations, revoked roles still active, scope mismatches,
policy version drift, orphaned privileges, signature custody mismatches,
authority chain breaks, and actor-to-role inconsistencies.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from .delegation_chain import _parse_iso, check_expiry, validate_chain
from .models import Actor, Delegation, RevocationEvent
from .seal_and_hash import compute_hash, verify_chain, verify_seal


# ── Drift Signal Builder ─────────────────────────────────────────


def _drift_signal(
    drift_type: str,
    severity: str,
    evidence_refs: List[str],
    target_type: str = "",
    target_id: str = "",
    notes: str = "",
) -> Dict[str, Any]:
    """Build a drift signal dict matching the FranOps FRAN-F11 format."""
    return {
        "driftId": f"DS-auth-{uuid.uuid4().hex[:8]}",
        "driftType": drift_type,
        "severity": severity,
        "detectedAt": datetime.now(timezone.utc).isoformat(),
        "evidenceRefs": evidence_refs,
        "fingerprint": {"key": f"{drift_type}:{target_id}", "version": "1"},
        "targetType": target_type,
        "targetId": target_id,
        "notes": notes,
    }


# ── AUTH-F13: Master Drift Scan ──────────────────────────────────


def scan_authority_drift(
    actors: List[Dict[str, Any]],
    delegations: List[Dict[str, Any]],
    grants: List[Dict[str, Any]],
    revocations: List[Dict[str, Any]],
    policies: List[Dict[str, Any]],
    now: Optional[datetime] = None,
) -> List[Dict[str, Any]]:
    """Master authority drift scan (AUTH-F13).

    Orchestrates sub-detectors and adds cross-cutting checks:
    - Revoked role still active on an actor
    - Scope mismatch between grants and delegations
    - Actor-to-role inconsistency

    Returns:
        List of drift signal dicts.
    """
    if now is None:
        now = datetime.now(timezone.utc)

    signals: List[Dict[str, Any]] = []

    # 1. Delegation health sub-scan
    signals.extend(check_delegation_health(delegations, actors, now=now))

    # 2. Privilege expiry sub-scan
    signals.extend(check_privilege_expiry(grants, delegations, now=now))

    # 3. Integrity sub-scan (if policies provided)
    if policies:
        signals.extend(check_authority_integrity(
            ledger_snapshot={}, grants=grants, policies=policies,
        ))

    # 4. Cross-cutting: revoked role still active
    revocation_targets = set()
    for rev in revocations:
        if isinstance(rev, RevocationEvent):
            if rev.target_type == "role":
                revocation_targets.add(rev.target_id)
        elif isinstance(rev, dict):
            if rev.get("targetType", rev.get("target_type")) == "role":
                revocation_targets.add(
                    rev.get("targetId", rev.get("target_id", ""))
                )

    for actor in actors:
        actor_id = actor.get("actorId", actor.get("actor_id", ""))
        roles = actor.get("roles", [])
        for role in roles:
            role_id = role.get("roleId", role.get("role_id", ""))
            if role_id in revocation_targets:
                signals.append(_drift_signal(
                    drift_type="revoked_role_active",
                    severity="red",
                    evidence_refs=[f"actor:{actor_id}", f"role:{role_id}"],
                    target_type="actor",
                    target_id=actor_id,
                    notes=f"Revoked role {role_id} still active on actor {actor_id}",
                ))

    # 5. Cross-cutting: scope mismatch between grants and delegations
    for grant in grants:
        grant_scope = grant.get("scope", "")
        grant_id = grant.get("authorityId", grant.get("authority_id", ""))
        for deleg in delegations:
            deleg_scope = deleg.get("scope", "")
            deleg_id = deleg.get("delegationId", deleg.get("delegation_id", ""))
            # If grant scope extends beyond delegation scope
            if (
                grant_scope
                and deleg_scope
                and not grant_scope.startswith(deleg_scope)
                and grant_scope != deleg_scope
            ):
                to_actor = deleg.get("toActorId", deleg.get("to_actor_id", ""))
                # Only flag if the grant is associated with this delegation's actor
                if to_actor and to_actor == grant.get("actorId", grant.get("actor_id", "")):
                    signals.append(_drift_signal(
                        drift_type="delegation_scope_violated",
                        severity="orange",
                        evidence_refs=[f"grant:{grant_id}", f"delegation:{deleg_id}"],
                        target_type="delegation",
                        target_id=deleg_id,
                        notes=f"Grant scope '{grant_scope}' exceeds delegation scope '{deleg_scope}'",
                    ))

    # 6. Cross-cutting: actor-to-role inconsistency
    for actor in actors:
        actor_id = actor.get("actorId", actor.get("actor_id", ""))
        actor_type = actor.get("actorType", actor.get("actor_type", ""))
        roles = actor.get("roles", [])
        for role in roles:
            role_scope = role.get("scope", "")
            # Agent actors should not have admin-level roles without delegation
            if actor_type == "agent" and role_scope == "global" and not actor.get("delegatedFrom"):
                signals.append(_drift_signal(
                    drift_type="actor_role_inconsistency",
                    severity="yellow",
                    evidence_refs=[f"actor:{actor_id}"],
                    target_type="actor",
                    target_id=actor_id,
                    notes=f"Agent actor {actor_id} has global scope without delegation source",
                ))

    return signals


# ── AUTH-F14: Delegation Health Monitor ──────────────────────────


def check_delegation_health(
    delegations: List[Dict[str, Any]],
    actors: List[Dict[str, Any]],
    now: Optional[datetime] = None,
    near_expiry_hours: int = 72,
) -> List[Dict[str, Any]]:
    """Focused delegation chain health check (AUTH-F14).

    For each delegation:
    - Check expired → ORANGE
    - Check near-expiry → YELLOW
    - Check revoked → RED

    For chain validation (if actors provided):
    - Build Delegation models and validate chains
    """
    if now is None:
        now = datetime.now(timezone.utc)

    signals: List[Dict[str, Any]] = []
    near_threshold = timedelta(hours=near_expiry_hours)

    for d in delegations:
        deleg_id = d.get("delegationId", d.get("delegation_id", ""))

        # Build model for expiry check
        delegation = Delegation(
            delegation_id=deleg_id,
            from_actor_id=d.get("fromActorId", d.get("from_actor_id", "")),
            to_actor_id=d.get("toActorId", d.get("to_actor_id", "")),
            scope=d.get("scope", ""),
            max_depth=d.get("maxDepth", d.get("max_depth", 3)),
            effective_at=d.get("effectiveAt", d.get("effective_at", "")),
            expires_at=d.get("expiresAt", d.get("expires_at")),
            revoked_at=d.get("revokedAt", d.get("revoked_at")),
        )

        # Revoked
        if delegation.revoked_at is not None:
            signals.append(_drift_signal(
                drift_type="authority_chain_broken",
                severity="red",
                evidence_refs=[f"delegation:{deleg_id}"],
                target_type="delegation",
                target_id=deleg_id,
                notes=f"Delegation {deleg_id} has been revoked",
            ))
            continue

        # Expired
        if delegation.expires_at:
            try:
                exp = _parse_iso(delegation.expires_at)
                if exp.tzinfo is None:
                    exp = exp.replace(tzinfo=timezone.utc)
                if now >= exp:
                    signals.append(_drift_signal(
                        drift_type="grant_expired",
                        severity="orange",
                        evidence_refs=[f"delegation:{deleg_id}"],
                        target_type="delegation",
                        target_id=deleg_id,
                        notes=f"Delegation {deleg_id} expired at {delegation.expires_at}",
                    ))
                    continue
                # Near expiry
                if exp - now <= near_threshold:
                    signals.append(_drift_signal(
                        drift_type="delegation_near_expiry",
                        severity="yellow",
                        evidence_refs=[f"delegation:{deleg_id}"],
                        target_type="delegation",
                        target_id=deleg_id,
                        notes=f"Delegation {deleg_id} expires in {exp - now}",
                    ))
            except (ValueError, TypeError):
                pass

    # Chain validation per actor
    for actor_dict in actors:
        actor_id = actor_dict.get("actorId", actor_dict.get("actor_id", ""))
        delegated_from = actor_dict.get("delegatedFrom", actor_dict.get("delegated_from"))
        if not delegated_from:
            continue  # No delegation chain for this actor

        # Find delegations targeting this actor
        chain_delegations = []
        for d in delegations:
            to_id = d.get("toActorId", d.get("to_actor_id", ""))
            if to_id == actor_id:
                chain_delegations.append(Delegation(
                    delegation_id=d.get("delegationId", d.get("delegation_id", "")),
                    from_actor_id=d.get("fromActorId", d.get("from_actor_id", "")),
                    to_actor_id=to_id,
                    scope=d.get("scope", ""),
                    max_depth=d.get("maxDepth", d.get("max_depth", 3)),
                    effective_at=d.get("effectiveAt", d.get("effective_at", "")),
                    expires_at=d.get("expiresAt", d.get("expires_at")),
                    revoked_at=d.get("revokedAt", d.get("revoked_at")),
                ))

        if chain_delegations:
            actor_model = Actor(
                actor_id=actor_id,
                actor_type=actor_dict.get("actorType", actor_dict.get("actor_type", "agent")),
            )
            valid, issues = validate_chain(chain_delegations, actor_model, now=now)
            if not valid:
                for issue in issues:
                    severity = "red" if "revoked" in issue else "orange"
                    signals.append(_drift_signal(
                        drift_type="authority_chain_broken",
                        severity=severity,
                        evidence_refs=[f"actor:{actor_id}", f"chain_issue:{issue}"],
                        target_type="actor",
                        target_id=actor_id,
                        notes=f"Delegation chain issue for {actor_id}: {issue}",
                    ))

    return signals


# ── AUTH-F15: Privilege Expiry Scanner ───────────────────────────


def check_privilege_expiry(
    grants: List[Dict[str, Any]],
    delegations: List[Dict[str, Any]],
    now: Optional[datetime] = None,
    near_expiry_hours: int = 72,
) -> List[Dict[str, Any]]:
    """Scan grants and delegations for expired or near-expiry privileges (AUTH-F15).

    Detects:
    - Expired grants → ORANGE
    - Near-expiry grants → YELLOW
    - Orphaned grants (source delegation expired/revoked) → RED
    """
    if now is None:
        now = datetime.now(timezone.utc)

    signals: List[Dict[str, Any]] = []
    near_threshold = timedelta(hours=near_expiry_hours)

    # Build set of invalid delegation IDs (expired or revoked)
    invalid_delegation_ids = set()
    for d in delegations:
        deleg_id = d.get("delegationId", d.get("delegation_id", ""))
        if d.get("revokedAt", d.get("revoked_at")) is not None:
            invalid_delegation_ids.add(deleg_id)
            continue
        expires_at = d.get("expiresAt", d.get("expires_at"))
        if expires_at:
            try:
                exp = _parse_iso(expires_at)
                if exp.tzinfo is None:
                    exp = exp.replace(tzinfo=timezone.utc)
                if now >= exp:
                    invalid_delegation_ids.add(deleg_id)
            except (ValueError, TypeError):
                pass

    for grant in grants:
        grant_id = grant.get("authorityId", grant.get("authority_id", ""))
        expires_at = grant.get("expiresAt", grant.get("expires_at"))

        if expires_at:
            try:
                exp = _parse_iso(expires_at)
                if exp.tzinfo is None:
                    exp = exp.replace(tzinfo=timezone.utc)
                if now >= exp:
                    signals.append(_drift_signal(
                        drift_type="grant_expired",
                        severity="orange",
                        evidence_refs=[f"grant:{grant_id}"],
                        target_type="authority",
                        target_id=grant_id,
                        notes=f"Authority grant {grant_id} expired at {expires_at}",
                    ))
                    continue
                if exp - now <= near_threshold:
                    signals.append(_drift_signal(
                        drift_type="delegation_near_expiry",
                        severity="yellow",
                        evidence_refs=[f"grant:{grant_id}"],
                        target_type="authority",
                        target_id=grant_id,
                        notes=f"Authority grant {grant_id} expires in {exp - now}",
                    ))
            except (ValueError, TypeError):
                pass

        # Check for orphaned grants (source delegation is invalid)
        source_delegation = grant.get("sourceDelegation", grant.get("source_delegation", ""))
        if source_delegation and source_delegation in invalid_delegation_ids:
            signals.append(_drift_signal(
                drift_type="privilege_orphaned",
                severity="red",
                evidence_refs=[f"grant:{grant_id}", f"delegation:{source_delegation}"],
                target_type="authority",
                target_id=grant_id,
                notes=f"Grant {grant_id} source delegation {source_delegation} is invalid",
            ))

    return signals


# ── AUTH-F16: Authority Integrity Checker ────────────────────────


def check_authority_integrity(
    ledger_snapshot: Dict[str, Any],
    grants: List[Dict[str, Any]],
    policies: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Verify seal/hash/chain integrity (AUTH-F16).

    Checks:
    - Ledger chain validity (if entries provided)
    - Policy seal hash verification
    - Policy hash consistency
    """
    signals: List[Dict[str, Any]] = []

    # Ledger chain integrity
    entries = ledger_snapshot.get("entries", [])
    if entries:
        if not verify_chain(entries):
            signals.append(_drift_signal(
                drift_type="authority_chain_broken",
                severity="red",
                evidence_refs=["ledger:chain_integrity"],
                target_type="authority",
                target_id="ledger",
                notes="Authority ledger hash chain is broken",
            ))

    # Policy seal verification
    for policy in policies:
        policy_id = policy.get("policyPackId", policy.get("policy_pack_id", ""))
        seal_hash = policy.get("sealHash", policy.get("seal_hash", ""))
        policy_hash = policy.get("policyHash", policy.get("policy_hash", ""))

        if seal_hash:
            # Reconstruct hashable payload for verification
            hashable = {
                k: v for k, v in policy.items()
                if k not in ("sealHash", "seal_hash", "sealVersion", "seal_version")
            }
            actual = compute_hash(hashable)
            if actual != seal_hash:
                signals.append(_drift_signal(
                    drift_type="signature_custody_mismatch",
                    severity="red",
                    evidence_refs=[f"policy:{policy_id}"],
                    target_type="policy",
                    target_id=policy_id,
                    notes=f"Policy {policy_id} seal hash mismatch: expected {seal_hash}",
                ))

        if policy_hash:
            expected = policy.get("expectedPolicyHash", policy.get("expected_policy_hash", ""))
            if expected and expected != policy_hash:
                signals.append(_drift_signal(
                    drift_type="policy_drift_detected",
                    severity="yellow",
                    evidence_refs=[f"policy:{policy_id}"],
                    target_type="policy",
                    target_id=policy_id,
                    notes=f"Policy {policy_id} hash drift: current={policy_hash}, expected={expected}",
                ))

    return signals
