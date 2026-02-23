"""File-backed keyring model for rotatable keys.

Provides a lightweight JSON persistence layer with key version records and
TTL/status lifecycle controls suitable for pilot workflows.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Callable, Iterable

VALID_STATUSES = {"active", "disabled", "expired"}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _to_iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_iso(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


@dataclass(frozen=True)
class KeyVersionRecord:
    key_id: str
    key_version: int
    created_at: str
    expires_at: str | None
    status: str

    @classmethod
    def from_dict(cls, payload: dict) -> "KeyVersionRecord":
        status = str(payload.get("status", "")).lower()
        if status not in VALID_STATUSES:
            raise ValueError(f"Invalid key status: {status}")
        return cls(
            key_id=str(payload["key_id"]),
            key_version=int(payload["key_version"]),
            created_at=str(payload["created_at"]),
            expires_at=(str(payload["expires_at"]) if payload.get("expires_at") else None),
            status=status,
        )


class Keyring:
    """Manage key versions and lifecycle state in a JSON keyring file."""

    def __init__(
        self,
        path: str | Path = "data/security/keyring.json",
        now_fn: Callable[[], datetime] = _utc_now,
    ) -> None:
        self.path = Path(path)
        self._now_fn = now_fn
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._write([])

    def list(self, key_id: str | None = None) -> list[KeyVersionRecord]:
        records = self._read()
        if key_id is None:
            return records
        return [record for record in records if record.key_id == key_id]

    def create(
        self,
        key_id: str,
        expires_at: str | None = None,
    ) -> KeyVersionRecord:
        if not key_id or not key_id.strip():
            raise ValueError("key_id is required")
        if expires_at:
            _parse_iso(expires_at)

        records = self._read()
        current_versions = [r.key_version for r in records if r.key_id == key_id]
        next_version = (max(current_versions) + 1) if current_versions else 1
        created = _to_iso(self._now_fn())

        new_record = KeyVersionRecord(
            key_id=key_id.strip(),
            key_version=next_version,
            created_at=created,
            expires_at=expires_at,
            status="active",
        )
        records.append(new_record)
        self._write(records)
        return new_record

    def disable(self, key_id: str, key_version: int | None = None) -> KeyVersionRecord:
        records = self._read()
        target = self._find_target(records, key_id, key_version)
        updated = self._replace_status(records, target, "disabled")
        self._write(updated)
        return self._find_target(updated, key_id, target.key_version)

    def expire(self, now: datetime | None = None) -> int:
        current_time = now or self._now_fn()
        records = self._read()
        changed = 0
        updated: list[KeyVersionRecord] = []
        for record in records:
            if (
                record.status == "active"
                and record.expires_at
                and _parse_iso(record.expires_at) <= current_time
            ):
                updated.append(
                    KeyVersionRecord(
                        key_id=record.key_id,
                        key_version=record.key_version,
                        created_at=record.created_at,
                        expires_at=record.expires_at,
                        status="expired",
                    )
                )
                changed += 1
            else:
                updated.append(record)
        if changed:
            self._write(updated)
        return changed

    def current(self, key_id: str) -> KeyVersionRecord | None:
        records = self.list(key_id)
        if not records:
            return None
        ordered = sorted(records, key=lambda r: r.key_version, reverse=True)
        for record in ordered:
            if record.status == "active":
                if record.expires_at and _parse_iso(record.expires_at) <= self._now_fn():
                    continue
                return record
        return None

    def _find_target(
        self,
        records: Iterable[KeyVersionRecord],
        key_id: str,
        key_version: int | None,
    ) -> KeyVersionRecord:
        candidates = [r for r in records if r.key_id == key_id]
        if not candidates:
            raise ValueError(f"Unknown key_id: {key_id}")
        if key_version is not None:
            for record in candidates:
                if record.key_version == key_version:
                    return record
            raise ValueError(f"Unknown key version: {key_id}@v{key_version}")
        return sorted(candidates, key=lambda r: r.key_version)[-1]

    def _replace_status(
        self,
        records: list[KeyVersionRecord],
        target: KeyVersionRecord,
        status: str,
    ) -> list[KeyVersionRecord]:
        if status not in VALID_STATUSES:
            raise ValueError(f"Invalid key status: {status}")
        output: list[KeyVersionRecord] = []
        for record in records:
            if record.key_id == target.key_id and record.key_version == target.key_version:
                output.append(
                    KeyVersionRecord(
                        key_id=record.key_id,
                        key_version=record.key_version,
                        created_at=record.created_at,
                        expires_at=record.expires_at,
                        status=status,
                    )
                )
            else:
                output.append(record)
        return output

    def _read(self) -> list[KeyVersionRecord]:
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        if not isinstance(raw, list):
            raise ValueError("Keyring file must contain a JSON array")
        return [KeyVersionRecord.from_dict(item) for item in raw]

    def _write(self, records: list[KeyVersionRecord]) -> None:
        payload = [asdict(record) for record in records]
        self.path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
