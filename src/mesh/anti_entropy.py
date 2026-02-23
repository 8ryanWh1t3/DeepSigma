"""Mesh anti-entropy and delta synchronization helpers.

Protocol selected for this repo:
- Digest exchange for quick divergence checks
- Cursor + ID-based delta sync (no full-log replay)
- Replay-safe apply using seen record IDs
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any


def _stable_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def _record_id(record: dict[str, Any]) -> str:
    rid = str(record.get("id") or record.get("envelope_id") or record.get("record_id") or "")
    if rid:
        return rid
    payload = _stable_json(record)
    return "anon:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def _record_ts(record: dict[str, Any]) -> str:
    return str(record.get("timestamp") or record.get("ts") or "")


def record_hash(record: dict[str, Any]) -> str:
    """Hash record content deterministically."""
    return hashlib.sha256(_stable_json(record).encode("utf-8")).hexdigest()


def digest(records: list[dict[str, Any]]) -> str:
    """Compute deterministic digest for a record set."""
    tuples = sorted((_record_id(r), record_hash(r)) for r in records)
    blob = _stable_json(tuples).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


@dataclass
class DeltaCursor:
    """Cursor state for replay-safe delta synchronization."""

    last_timestamp: str = ""
    seen_ids: set[str] = field(default_factory=set)


@dataclass
class ApplyResult:
    applied: list[dict[str, Any]]
    skipped_replay: list[dict[str, Any]]
    cursor: DeltaCursor


def build_delta_offer(
    local_records: list[dict[str, Any]],
    remote_known_ids: set[str],
    since_timestamp: str = "",
) -> list[dict[str, Any]]:
    """Return only records remote does not already know and newer than cursor."""
    out: list[dict[str, Any]] = []
    for rec in local_records:
        rid = _record_id(rec)
        rts = _record_ts(rec)
        if rid in remote_known_ids:
            continue
        if since_timestamp and rts and rts <= since_timestamp:
            continue
        out.append(rec)
    out.sort(key=lambda r: (_record_ts(r), _record_id(r)))
    return out


def apply_delta_replay_safe(
    incoming_delta: list[dict[str, Any]],
    cursor: DeltaCursor,
) -> ApplyResult:
    """Apply delta with replay safety.

    Any record with an ID already present in cursor.seen_ids is skipped.
    """
    applied: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    last_ts = cursor.last_timestamp
    seen = set(cursor.seen_ids)

    for rec in incoming_delta:
        rid = _record_id(rec)
        rts = _record_ts(rec)
        if rid in seen:
            skipped.append(rec)
            continue
        seen.add(rid)
        applied.append(rec)
        if rts and rts > last_ts:
            last_ts = rts

    return ApplyResult(
        applied=applied,
        skipped_replay=skipped,
        cursor=DeltaCursor(last_timestamp=last_ts, seen_ids=seen),
    )


def reconcile_sets(
    local_records: list[dict[str, Any]],
    remote_records: list[dict[str, Any]],
) -> dict[str, Any]:
    """Reconcile local and remote record sets by ID and content hash."""
    local_map = {_record_id(r): record_hash(r) for r in local_records}
    remote_map = {_record_id(r): record_hash(r) for r in remote_records}

    local_ids = set(local_map)
    remote_ids = set(remote_map)

    missing_on_local = sorted(remote_ids - local_ids)
    missing_on_remote = sorted(local_ids - remote_ids)
    shared = local_ids & remote_ids
    mismatched = sorted(rid for rid in shared if local_map[rid] != remote_map[rid])

    return {
        "local_digest": digest(local_records),
        "remote_digest": digest(remote_records),
        "in_sync": not missing_on_local and not missing_on_remote and not mismatched,
        "missing_on_local": missing_on_local,
        "missing_on_remote": missing_on_remote,
        "mismatched_records": mismatched,
    }


def estimate_bandwidth_profile(
    full_records: int,
    delta_records: int,
    avg_record_bytes: int = 512,
) -> dict[str, float]:
    """Estimate transfer bytes for full-log replication vs delta sync."""
    full_bytes = max(full_records, 0) * max(avg_record_bytes, 1)
    delta_bytes = max(delta_records, 0) * max(avg_record_bytes, 1)
    if full_bytes == 0:
        saved = 0.0
    else:
        saved = max(0.0, 100.0 * (1.0 - (delta_bytes / full_bytes)))
    return {
        "full_bytes": float(full_bytes),
        "delta_bytes": float(delta_bytes),
        "saved_percent": round(saved, 2),
    }
