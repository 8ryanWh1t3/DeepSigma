"""Key rotation primitive for DISR workflows."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
from typing import Callable

from governance.audit import audit_action

from .action_contract import create_action_contract, validate_action_contract
from .authority_ledger import append_authority_action_entry
from .events import EVENT_KEY_ROTATED, append_security_event
from .keyring import Keyring, KeyVersionRecord


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _to_iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True)
class RotationResult:
    tenant_id: str
    key_id: str
    key_version: int
    expires_at: str | None
    actor_user: str
    actor_role: str
    event_hash: str
    security_event_id: str
    authority_entry_id: str



def _event_hash(payload: dict) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def rotate_keys(
    *,
    tenant_id: str,
    key_id: str,
    ttl_days: int,
    actor_user: str,
    actor_role: str,
    authority_dri: str | None,
    authority_role: str,
    authority_reason: str | None,
    authority_signing_key: str | None,
    action_contract: dict | None = None,
    keyring_path: str | Path = "data/security/keyring.json",
    event_log_path: str | Path = "data/security/key_rotation_events.jsonl",
    authority_ledger_path: str | Path = "data/security/authority_ledger.json",
    security_events_path: str | Path = "data/security/security_events.jsonl",
    now_fn: Callable[[], datetime] = _utc_now,
) -> RotationResult:
    if ttl_days <= 0:
        raise ValueError("ttl_days must be > 0")
    if not authority_dri:
        raise ValueError("authority_dri is required for rotation approval")
    if not authority_reason:
        raise ValueError("authority_reason is required for rotation approval")
    if not authority_signing_key:
        raise ValueError("authority_signing_key is required to sign rotation approval")
    if action_contract is None:
        action_contract = create_action_contract(
            action_type="ROTATE_KEYS",
            requested_by=actor_user,
            dri=authority_dri,
            approver=authority_dri,
            signing_key=authority_signing_key,
        ).to_dict()
    validated_contract = validate_action_contract(
        action_contract,
        expected_action_type="ROTATE_KEYS",
        signing_key=authority_signing_key,
        now=now_fn(),
    )

    now = now_fn()
    expires_at = _to_iso(now + timedelta(days=ttl_days))

    keyring = Keyring(path=keyring_path, now_fn=now_fn)
    record: KeyVersionRecord = keyring.create(key_id=key_id, expires_at=expires_at)

    payload = {
        "event_type": "KEY_ROTATED",
        "tenant_id": tenant_id,
        "key_id": record.key_id,
        "key_version": record.key_version,
        "expires_at": record.expires_at,
        "actor_user": actor_user,
        "actor_role": actor_role,
        "rotated_at": _to_iso(now),
    }
    digest = _event_hash(payload)
    payload["event_hash"] = digest

    event_path = Path(event_log_path)
    event_path.parent.mkdir(parents=True, exist_ok=True)
    with event_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")

    security_event = append_security_event(
        event_type=EVENT_KEY_ROTATED,
        tenant_id=tenant_id,
        payload={
            "key_id": record.key_id,
            "key_version": record.key_version,
            "expires_at": record.expires_at,
            "actor_user": actor_user,
            "actor_role": actor_role,
            "authority_dri": authority_dri,
            "authority_role": authority_role,
            "authority_reason": authority_reason,
            "action_contract_id": validated_contract.action_id,
        },
        events_path=security_events_path,
        signer_id=authority_dri,
        signing_key=authority_signing_key,
    )
    authority_entry = append_authority_action_entry(
        ledger_path=authority_ledger_path,
        authority_event={
            "event_id": security_event.event_id,
            "event_hash": security_event.event_hash,
            "tenant_id": tenant_id,
            "occurred_at": security_event.occurred_at,
            "payload": security_event.payload,
        },
        authority_dri=authority_dri,
        authority_role=authority_role,
        authority_reason=authority_reason,
        signing_key=authority_signing_key,
        action_type="AUTHORIZED_KEY_ROTATION",
        action_contract=validated_contract.to_dict(),
    )

    audit_action(
        tenant_id=tenant_id,
        actor_user=authority_dri,
        actor_role=authority_role,
        action="AUTHORIZED_KEY_ROTATION",
        target_type="KEYRING",
        target_id=f"{record.key_id}@v{record.key_version}",
        outcome="SUCCESS",
        metadata={
            "key_id": record.key_id,
            "key_version": record.key_version,
            "expires_at": record.expires_at,
            "event_hash": digest,
            "security_event_id": security_event.event_id,
            "authority_entry_id": authority_entry["entry_id"],
            "authority_reason": authority_reason,
            "approved_by": authority_dri,
            "action_contract_id": validated_contract.action_id,
        },
    )

    return RotationResult(
        tenant_id=tenant_id,
        key_id=record.key_id,
        key_version=record.key_version,
        expires_at=record.expires_at,
        actor_user=actor_user,
        actor_role=actor_role,
        event_hash=digest,
        security_event_id=security_event.event_id,
        authority_entry_id=authority_entry["entry_id"],
    )


def rotation_result_to_dict(result: RotationResult) -> dict:
    return asdict(result)
