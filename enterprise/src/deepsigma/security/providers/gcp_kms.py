"""Google Cloud KMS provider stub (optional dependency, not enabled by default)."""

from __future__ import annotations

from datetime import datetime

from deepsigma.security.keyring import KeyVersionRecord

from .base import CryptoProvider


class GCPKMSProvider(CryptoProvider):
    """Stub provider for future Google Cloud KMS integration."""

    @property
    def name(self) -> str:
        return "gcp-kms"

    def create_key_version(self, key_id: str, expires_at: str | None = None) -> KeyVersionRecord:
        self._not_configured()

    def list_key_versions(self, key_id: str | None = None) -> list[KeyVersionRecord]:
        self._not_configured()

    def current_key_version(self, key_id: str) -> KeyVersionRecord | None:
        self._not_configured()

    def disable_key_version(self, key_id: str, key_version: int | None = None) -> KeyVersionRecord:
        self._not_configured()

    def expire_keys(self, now: datetime | None = None) -> int:
        self._not_configured()

    def _not_configured(self) -> None:
        raise NotImplementedError(
            "gcp-kms provider is a stub. Configure cloud adapter + credentials in deployment, "
            "then replace this stub with runtime implementation."
        )
