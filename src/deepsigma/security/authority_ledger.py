"""Authority ledger entries for signed key rotation approvals."""

from __future__ import annotations

import hashlib
import hmac
import json
from pathlib import Path
from typing import Any


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


def append_authority_rotation_entry(
    *,
    ledger_path: str | Path,
    rotation_event: dict[str, Any],
    authority_dri: str,
    authority_role: str,
    authority_reason: str,
    signing_key: str,
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

    prev_hash = entries[-1]["entry_hash"] if entries else None
    unsigned = {
        "entry_type": "AUTHORIZED_KEY_ROTATION",
        "event_id": rotation_event["event_id"],
        "event_hash": rotation_event["event_hash"],
        "tenant_id": rotation_event["tenant_id"],
        "key_id": rotation_event["payload"]["key_id"],
        "key_version": rotation_event["payload"]["key_version"],
        "authority_dri": authority_dri,
        "authority_role": authority_role,
        "authority_reason": authority_reason,
        "recorded_at": rotation_event["occurred_at"],
        "prev_entry_hash": prev_hash,
    }
    signature = _event_signature(unsigned, signing_key)
    entry = dict(unsigned)
    entry["event_signature"] = signature
    entry["signature_alg"] = "HMAC-SHA256"
    entry["entry_id"] = f"AUTHROT-{rotation_event['event_hash'][:12]}"
    entry["entry_hash"] = _entry_hash({**entry, "entry_hash": ""})

    entries.append(entry)
    path.write_text(json.dumps(entries, indent=2) + "\n", encoding="utf-8")
    return entry
