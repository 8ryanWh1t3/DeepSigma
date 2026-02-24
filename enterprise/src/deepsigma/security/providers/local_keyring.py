"""Backward-compatible local-keyring provider alias."""

from __future__ import annotations

from .local_keystore import LocalKeyStoreProvider


class LocalKeyringProvider(LocalKeyStoreProvider):
    """Compatibility alias for older policy values."""

    @property
    def name(self) -> str:
        return "local-keyring"
