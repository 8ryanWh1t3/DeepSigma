"""Deterministic local keystore provider for DISR key lifecycle operations."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Callable

from deepsigma.security.keyring import KeyVersionRecord

from .base import CryptoProvider

_STORE_SCHEMA_VERSION = "1.0"
_STORE_PROVIDER_NAME = "local-keystore"
_VALID_STATUSES = {"active", "disabled", "expired"}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _to_iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_iso(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


class LocalKeyStoreProvider(CryptoProvider):
    """File-backed key provider with deterministic canonical storage."""

    def __init__(
        self,
        *,
        path: str | Path = "data/security/local_keystore.json",
        now_fn: Callable[[], datetime] = _utc_now,
    ) -> None:
        self.path = Path(path)
        self._now_fn = now_fn
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._write_store([])
        else:
            # Validate/normalize existing file on startup for deterministic shape.
            self._write_store(self._read_records())

    @property
    def name(self) -> str:
        return _STORE_PROVIDER_NAME

    def create_key_version(self, key_id: str, expires_at: str | None = None) -> KeyVersionRecord:
        if not key_id or not key_id.strip():
            raise ValueError("key_id is required")
        if expires_at:
            _parse_iso(expires_at)
        key_id = key_id.strip()

        records = self._read_records()
        current_versions = [r.key_version for r in records if r.key_id == key_id]
        next_version = (max(current_versions) + 1) if current_versions else 1

        created = _to_iso(self._now_fn())
        record = KeyVersionRecord(
            key_id=key_id,
            key_version=next_version,
            created_at=created,
            expires_at=expires_at,
            status="active",
        )
        records.append(record)
        self._write_store(records)
        return record

    def list_key_versions(self, key_id: str | None = None) -> list[KeyVersionRecord]:
        records = self._read_records()
        if key_id is None:
            return records
        return [record for record in records if record.key_id == key_id]

    def current_key_version(self, key_id: str) -> KeyVersionRecord | None:
        records = self.list_key_versions(key_id=key_id)
        if not records:
            return None
        ordered = sorted(records, key=lambda r: r.key_version, reverse=True)
        now = self._now_fn()
        for record in ordered:
            if record.status != "active":
                continue
            if record.expires_at and _parse_iso(record.expires_at) <= now:
                continue
            return record
        return None

    def disable_key_version(self, key_id: str, key_version: int | None = None) -> KeyVersionRecord:
        records = self._read_records()
        candidates = [record for record in records if record.key_id == key_id]
        if not candidates:
            raise ValueError(f"Unknown key_id: {key_id}")

        target = None
        if key_version is None:
            target = sorted(candidates, key=lambda r: r.key_version)[-1]
        else:
            for candidate in candidates:
                if candidate.key_version == key_version:
                    target = candidate
                    break
            if target is None:
                raise ValueError(f"Unknown key version: {key_id}@v{key_version}")

        updated: list[KeyVersionRecord] = []
        for record in records:
            if record.key_id == target.key_id and record.key_version == target.key_version:
                updated.append(
                    KeyVersionRecord(
                        key_id=record.key_id,
                        key_version=record.key_version,
                        created_at=record.created_at,
                        expires_at=record.expires_at,
                        status="disabled",
                    )
                )
            else:
                updated.append(record)
        self._write_store(updated)
        return [r for r in updated if r.key_id == target.key_id and r.key_version == target.key_version][0]

    def expire_keys(self, now: datetime | None = None) -> int:
        current_time = now or self._now_fn()
        records = self._read_records()
        updated: list[KeyVersionRecord] = []
        changed = 0
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
            self._write_store(updated)
        return changed

    def _read_records(self) -> list[KeyVersionRecord]:
        raw = json.loads(self.path.read_text(encoding="utf-8"))

        # Backward compatibility: old keyring format was a flat list.
        if isinstance(raw, list):
            payload = raw
        else:
            payload = raw.get("keys", [])
            provider = raw.get("provider")
            if provider and str(provider) not in {_STORE_PROVIDER_NAME, "local-keyring"}:
                raise ValueError(f"Unexpected keystore provider: {provider}")

        if not isinstance(payload, list):
            raise ValueError("Keystore keys payload must be a list")

        records = [KeyVersionRecord.from_dict(item) for item in payload]
        return sorted(records, key=lambda r: (r.key_id, r.key_version))

    def _write_store(self, records: list[KeyVersionRecord]) -> None:
        for record in records:
            if record.status not in _VALID_STATUSES:
                raise ValueError(f"Invalid key status: {record.status}")

        payload = {
            "schema_version": _STORE_SCHEMA_VERSION,
            "provider": _STORE_PROVIDER_NAME,
            "keys": [asdict(record) for record in sorted(records, key=lambda r: (r.key_id, r.key_version))],
        }
        self.path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
