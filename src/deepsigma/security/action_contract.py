"""Authority action contract for signed rotate/reencrypt operations."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import json
from typing import Any


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _to_iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_iso(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


@dataclass(frozen=True)
class ActionContract:
    action_id: str
    action_type: str
    requested_by: str
    dri: str
    approver: str
    timestamp: str
    ttl: int
    signature: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def create_action_contract(
    *,
    action_type: str,
    requested_by: str,
    dri: str,
    approver: str,
    signing_key: str,
    ttl: int = 900,
    now: datetime | None = None,
) -> ActionContract:
    if ttl <= 0:
        raise ValueError("ttl must be > 0")
    if not signing_key:
        raise ValueError("signing_key is required")
    if not action_type or not requested_by or not dri or not approver:
        raise ValueError("action_type, requested_by, dri, and approver are required")

    issued = now or _now_utc()
    timestamp = _to_iso(issued)
    unsigned = {
        "action_type": action_type,
        "requested_by": requested_by,
        "dri": dri,
        "approver": approver,
        "timestamp": timestamp,
        "ttl": ttl,
    }
    action_id = f"ACT-{hashlib.sha256(_canonical_json(unsigned).encode('utf-8')).hexdigest()[:12]}"
    sign_payload = {"action_id": action_id, **unsigned}
    signature = hmac.new(
        signing_key.encode("utf-8"),
        _canonical_json(sign_payload).encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return ActionContract(
        action_id=action_id,
        action_type=action_type,
        requested_by=requested_by,
        dri=dri,
        approver=approver,
        timestamp=timestamp,
        ttl=ttl,
        signature=signature,
    )


def validate_action_contract(
    contract: dict[str, Any],
    *,
    expected_action_type: str,
    signing_key: str,
    now: datetime | None = None,
) -> ActionContract:
    required = {
        "action_id",
        "action_type",
        "requested_by",
        "dri",
        "approver",
        "timestamp",
        "ttl",
        "signature",
    }
    missing = [key for key in required if key not in contract]
    if missing:
        raise ValueError(f"Missing action contract fields: {', '.join(sorted(missing))}")

    if not signing_key:
        raise ValueError("signing_key is required")

    parsed = ActionContract(
        action_id=str(contract["action_id"]),
        action_type=str(contract["action_type"]),
        requested_by=str(contract["requested_by"]),
        dri=str(contract["dri"]),
        approver=str(contract["approver"]),
        timestamp=str(contract["timestamp"]),
        ttl=int(contract["ttl"]),
        signature=str(contract["signature"]),
    )
    if parsed.action_type != expected_action_type:
        raise ValueError(
            f"Invalid action_type in contract: {parsed.action_type} (expected {expected_action_type})"
        )
    if parsed.ttl <= 0:
        raise ValueError("Invalid contract ttl: must be > 0")

    sign_payload = {
        "action_id": parsed.action_id,
        "action_type": parsed.action_type,
        "requested_by": parsed.requested_by,
        "dri": parsed.dri,
        "approver": parsed.approver,
        "timestamp": parsed.timestamp,
        "ttl": parsed.ttl,
    }
    expected_sig = hmac.new(
        signing_key.encode("utf-8"),
        _canonical_json(sign_payload).encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(expected_sig, parsed.signature):
        raise ValueError("Invalid action contract signature")

    ts = _parse_iso(parsed.timestamp)
    expires_at = ts + timedelta(seconds=parsed.ttl)
    current = now or _now_utc()
    if current > expires_at:
        raise ValueError("Action contract is expired")
    return parsed
