"""Security primitives for DISR (Disposable Rotors)."""

from .authority_ledger import append_authority_rotation_entry
from .events import SecurityEvent, append_security_event
from .keyring import Keyring, KeyVersionRecord
from .providers import (
    available_providers,
    create_provider,
    provider_from_policy,
    register_provider,
    resolve_provider_name,
)
from .providers.base import CryptoProvider
from .providers.local_keystore import LocalKeyStoreProvider
from .providers.local_keyring import LocalKeyringProvider

__all__ = [
    "CryptoProvider",
    "Keyring",
    "KeyVersionRecord",
    "SecurityEvent",
    "available_providers",
    "append_security_event",
    "append_authority_rotation_entry",
    "create_provider",
    "LocalKeyStoreProvider",
    "LocalKeyringProvider",
    "provider_from_policy",
    "register_provider",
    "resolve_provider_name",
]
