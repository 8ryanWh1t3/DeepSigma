"""Provider interface for DISR key management backends."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from deepsigma.security.keyring import KeyVersionRecord


class CryptoProvider(ABC):
    """Abstract interface for key lifecycle operations."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Stable provider identifier used in policy selection."""

    @abstractmethod
    def create_key_version(self, key_id: str, expires_at: str | None = None) -> KeyVersionRecord:
        """Create a new active key version for a logical key."""

    @abstractmethod
    def list_key_versions(self, key_id: str | None = None) -> list[KeyVersionRecord]:
        """List key versions, optionally filtered by logical key."""

    @abstractmethod
    def current_key_version(self, key_id: str) -> KeyVersionRecord | None:
        """Return the latest active non-expired key version."""

    @abstractmethod
    def disable_key_version(self, key_id: str, key_version: int | None = None) -> KeyVersionRecord:
        """Disable a specific or latest key version for a logical key."""

    @abstractmethod
    def expire_keys(self, now: datetime | None = None) -> int:
        """Expire active keys whose TTL has elapsed; return updated record count."""
