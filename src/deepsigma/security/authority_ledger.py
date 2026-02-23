"""Authority ledger entries for signed key rotation approvals."""

from __future__ import annotations

import hashlib
import hmac
import json
from pathlib import Path
from typing import Any

LEDGER_SCHEMA_VERSION = "authority-ledger-v1"
TIER_SYSTEM = "SYSTEM"
TIER_APPROVER = "APPROVER"
TIER_DRI = "DRI"
_TIER_RANK = {
    TIER_SYSTEM: 1,
    TIER_APPROVER: 2,
    TIER_DRI: 3,
}


def _canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _entry_hash(payload: dict[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def _event_signature(payload: dict[str, Any], signing_key: str) -> str:
    return hmac.new(
        signing_key.encode("utf-8"),
        _canonical_json(payload).encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def _authority_tier(authority_role: str) -> str:
    role = authority_role.strip().lower()
    if role in {"system", "automation", "service", "bot"}:
        return TIER_SYSTEM
    if role in {"approver", "dri_approver", "reviewer", "coherence_steward"} or "approver" in role:
        return TIER_APPROVER
    if role in {"dri", "decision_dri", "program_dri"} or role.endswith("_dri") or "dri" in role:
        return TIER_DRI
    return TIER_APPROVER


def _snapshot_path(ledger_path: Path) -> Path:
    if ledger_path.suffix:
        return ledger_path.with_name(f"{ledger_path.stem}.snapshot{ledger_path.suffix}")
    return ledger_path.with_name(f"{ledger_path.name}.snapshot.json")


def _write_snapshot(
    *,
    ledger_path: Path,
    entries: list[dict[str, Any]],
    provenance: dict[str, Any],
) -> dict[str, Any]:
    snapshot_path = _snapshot_path(ledger_path)
    version = 1
    if snapshot_path.exists():
        try:
            previous = json.loads(snapshot_path.read_text(encoding="utf-8"))
            version = int(previous.get("snapshot_version", 0)) + 1
        except (json.JSONDecodeError, TypeError, ValueError):
            version = 1
    digest = _entry_hash({"entries": entries})
    snapshot = {
        "schema_version": LEDGER_SCHEMA_VERSION,
        "snapshot_version": version,
        "snapshot_id": f"AUTHSNAP-{digest[:12]}",
        "source_ledger_path": str(ledger_path),
        "entry_count": len(entries),
        "latest_entry_hash": entries[-1]["entry_hash"] if entries else None,
        "ledger_hash": digest,
        "provenance": provenance,
    }
    snapshot_path.write_text(json.dumps(snapshot, indent=2) + "\n", encoding="utf-8")
    return snapshot


def append_authority_rotation_entry(
    *,
    ledger_path: str | Path,
    rotation_event: dict[str, Any],
    authority_dri: str,
    authority_role: str,
    authority_reason: str,
    signing_key: str,
) -> dict[str, Any]:
    return append_authority_action_entry(
        ledger_path=ledger_path,
        authority_event=rotation_event,
        authority_dri=authority_dri,
        authority_role=authority_role,
        authority_reason=authority_reason,
        signing_key=signing_key,
        action_type="AUTHORIZED_KEY_ROTATION",
    )


def append_authority_action_entry(
    *,
    ledger_path: str | Path,
    authority_event: dict[str, Any],
    authority_dri: str,
    authority_role: str,
    authority_reason: str,
    signing_key: str,
    action_type: str,
    action_contract: dict[str, Any] | None = None,
) -> dict[str, Any]:
    path = Path(ledger_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    entries: list[dict[str, Any]] = []
    if path.exists():
        raw = path.read_text(encoding="utf-8").strip()
        if raw:
            obj = json.loads(raw)
            if isinstance(obj, list):
                entries = [item for item in obj if isinstance(item, dict)]

    tier = _authority_tier(authority_role)
    if tier == TIER_SYSTEM:
        raise ValueError("authority_role precedence too low: system cannot authorize privileged actions")
    if action_contract:
        contract_dri = action_contract.get("dri")
        contract_approver = action_contract.get("approver")
        if authority_dri == contract_dri and authority_dri != contract_approver and tier != TIER_DRI:
            raise ValueError("authority_role must be DRI when signer is contract.dri")
        if authority_dri == contract_approver and _TIER_RANK[tier] < _TIER_RANK[TIER_APPROVER]:
            raise ValueError("authority_role must be APPROVER or higher when signer is contract.approver")
        if authority_dri not in {contract_dri, contract_approver}:
            raise ValueError("authority_dri must match action contract approver or dri")

    prev_hash = entries[-1]["entry_hash"] if entries else None
    payload = authority_event.get("payload", {})
    unsigned = {
        "schema_version": LEDGER_SCHEMA_VERSION,
        "entry_type": action_type,
        "event_id": authority_event["event_id"],
        "event_hash": authority_event["event_hash"],
        "tenant_id": authority_event["tenant_id"],
        "key_id": payload.get("key_id"),
        "key_version": payload.get("key_version"),
        "authority_dri": authority_dri,
        "authority_role": authority_role,
        "authority_tier": tier,
        "authority_precedence": _TIER_RANK[tier],
        "authority_reason": authority_reason,
        "recorded_at": authority_event["occurred_at"],
        "prev_entry_hash": prev_hash,
        "action_contract_id": (action_contract or {}).get("action_id"),
        "action_contract_dri": (action_contract or {}).get("dri"),
        "action_contract_approver": (action_contract or {}).get("approver"),
    }
    signature = _event_signature(unsigned, signing_key)
    entry = dict(unsigned)
    entry["event_signature"] = signature
    entry["signature_alg"] = "HMAC-SHA256"
    prefix = "AUTHROT" if action_type == "AUTHORIZED_KEY_ROTATION" else "AUTHACT"
    entry["entry_id"] = f"{prefix}-{authority_event['event_hash'][:12]}"
    entry["entry_hash"] = _entry_hash({**entry, "entry_hash": ""})

    entries.append(entry)
    path.write_text(json.dumps(entries, indent=2) + "\n", encoding="utf-8")
    _write_snapshot(
        ledger_path=path,
        entries=entries,
        provenance={
            "action_type": action_type,
            "event_id": authority_event.get("event_id"),
            "event_hash": authority_event.get("event_hash"),
            "authority_dri": authority_dri,
            "authority_role": authority_role,
            "entry_id": entry["entry_id"],
        },
    )
    return entry
