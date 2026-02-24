"""Security event emission/query with hash-chained envelopes."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import hmac
import json
from pathlib import Path
from typing import Any

EVENT_KEY_ROTATED = "KEY_ROTATED"
EVENT_NONCE_REUSE_DETECTED = "NONCE_REUSE_DETECTED"
EVENT_REENCRYPT_DONE = "REENCRYPT_DONE"
EVENT_PROVIDER_CHANGED = "PROVIDER_CHANGED"
EVENT_AUTHORIZED_KEY_ROTATION = "AUTHORIZED_KEY_ROTATION"
EVENT_REENCRYPT_COMPLETED_LEGACY = "REENCRYPT_COMPLETED"

ALLOWED_EVENT_TYPES = {
    EVENT_KEY_ROTATED,
    EVENT_NONCE_REUSE_DETECTED,
    EVENT_REENCRYPT_DONE,
    EVENT_PROVIDER_CHANGED,
    EVENT_AUTHORIZED_KEY_ROTATION,
    EVENT_REENCRYPT_COMPLETED_LEGACY,
}


@dataclass(frozen=True)
class SecurityEvent:
    event_id: str
    event_type: str
    tenant_id: str
    occurred_at: str
    payload: dict[str, Any]
    prev_hash: str | None
    event_hash: str
    signer_id: str | None
    signature: str | None
    signature_alg: str | None


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _hash_payload(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _event_signature(payload: dict[str, Any], signing_key: str) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hmac.new(signing_key.encode("utf-8"), encoded, hashlib.sha256).hexdigest()


def _last_hash(path: Path) -> str | None:
    if not path.exists():
        return None
    lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not lines:
        return None
    try:
        last = json.loads(lines[-1])
        return str(last.get("event_hash")) if last.get("event_hash") else None
    except Exception:
        return None


def query_security_events(
    *,
    events_path: str | Path = "data/security/security_events.jsonl",
    event_type: str | None = None,
    tenant_id: str | None = None,
) -> list[SecurityEvent]:
    path = Path(events_path)
    if not path.exists():
        return []
    rows: list[SecurityEvent] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        raw = json.loads(line)
        if event_type and raw.get("event_type") != event_type:
            continue
        if tenant_id and raw.get("tenant_id") != tenant_id:
            continue
        rows.append(SecurityEvent(**raw))
    return rows


def append_security_event(
    *,
    event_type: str,
    tenant_id: str,
    payload: dict[str, Any],
    events_path: str | Path = "data/security/security_events.jsonl",
    occurred_at: str | None = None,
    signer_id: str | None = None,
    signing_key: str | None = None,
) -> SecurityEvent:
    if event_type not in ALLOWED_EVENT_TYPES:
        allowed = ", ".join(sorted(ALLOWED_EVENT_TYPES))
        raise ValueError(f"Unsupported security event type '{event_type}'. Allowed: {allowed}")

    path = Path(events_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    timestamp = occurred_at or _utc_now_iso()
    prev_hash = _last_hash(path)

    base = {
        "event_type": event_type,
        "tenant_id": tenant_id,
        "occurred_at": timestamp,
        "payload": payload,
        "prev_hash": prev_hash,
    }
    event_hash = _hash_payload(base)
    signature = _event_signature(base, signing_key) if signing_key else None

    event = SecurityEvent(
        event_id=f"SE-{event_hash[:12]}",
        event_type=event_type,
        tenant_id=tenant_id,
        occurred_at=timestamp,
        payload=payload,
        prev_hash=prev_hash,
        event_hash=event_hash,
        signer_id=signer_id,
        signature=signature,
        signature_alg="HMAC-SHA256" if signature else None,
    )

    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(asdict(event), sort_keys=True) + "\n")

    return event
