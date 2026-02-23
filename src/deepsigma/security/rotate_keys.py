"""Key rotation primitive for DISR workflows."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
from typing import Callable

from governance.audit import audit_action

from .events import append_security_event
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
    keyring_path: str | Path = "data/security/keyring.json",
    event_log_path: str | Path = "data/security/key_rotation_events.jsonl",
    now_fn: Callable[[], datetime] = _utc_now,
) -> RotationResult:
    if ttl_days <= 0:
        raise ValueError("ttl_days must be > 0")

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

    append_security_event(
        event_type="KEY_ROTATED",
        tenant_id=tenant_id,
        payload={
            "key_id": record.key_id,
            "key_version": record.key_version,
            "expires_at": record.expires_at,
            "actor_user": actor_user,
            "actor_role": actor_role,
        },
    )

    audit_action(
        tenant_id=tenant_id,
        actor_user=actor_user,
        actor_role=actor_role,
        action="KEY_ROTATED",
        target_type="KEYRING",
        target_id=f"{record.key_id}@v{record.key_version}",
        outcome="SUCCESS",
        metadata={
            "key_id": record.key_id,
            "key_version": record.key_version,
            "expires_at": record.expires_at,
            "event_hash": digest,
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
    )


def rotation_result_to_dict(result: RotationResult) -> dict:
    return asdict(result)
