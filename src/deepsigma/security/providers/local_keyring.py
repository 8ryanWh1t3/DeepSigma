"""Local file-backed crypto provider built on the DISR keyring."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from deepsigma.security.keyring import Keyring, KeyVersionRecord

from .base import CryptoProvider


class LocalKeyringProvider(CryptoProvider):
    """Default provider using the existing JSON keyring implementation."""

    def __init__(
        self,
        *,
        keyring_path: str | Path = "data/security/keyring.json",
        now_fn: Callable[[], datetime] | None = None,
    ) -> None:
        self._keyring = Keyring(path=keyring_path, now_fn=now_fn or _utc_now)

    @property
    def name(self) -> str:
        return "local-keyring"

    def create_key_version(self, key_id: str, expires_at: str | None = None) -> KeyVersionRecord:
        return self._keyring.create(key_id=key_id, expires_at=expires_at)

    def list_key_versions(self, key_id: str | None = None) -> list[KeyVersionRecord]:
        return self._keyring.list(key_id=key_id)

    def current_key_version(self, key_id: str) -> KeyVersionRecord | None:
        return self._keyring.current(key_id=key_id)

    def disable_key_version(self, key_id: str, key_version: int | None = None) -> KeyVersionRecord:
        return self._keyring.disable(key_id=key_id, key_version=key_version)

    def expire_keys(self, now: datetime | None = None) -> int:
        return self._keyring.expire(now=now)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)
