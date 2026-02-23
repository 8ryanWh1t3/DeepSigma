"""Security primitives for DISR (Disposable Rotors)."""

from .authority_ledger import append_authority_rotation_entry
from .action_contract import ActionContract, create_action_contract, validate_action_contract
from .events import (
    EVENT_KEY_ROTATED,
    EVENT_NONCE_REUSE_DETECTED,
    EVENT_PROVIDER_CHANGED,
    EVENT_REENCRYPT_DONE,
    SecurityEvent,
    append_security_event,
    query_security_events,
)
from .keyring import Keyring, KeyVersionRecord
from .providers import (
    available_providers,
    create_provider,
    provider_from_policy,
    register_provider,
    resolve_provider_name,
)
from .providers.base import CryptoProvider
from .providers.aws_kms import AWSKMSProvider
from .providers.azure_kv import AzureKeyVaultProvider
from .providers.gcp_kms import GCPKMSProvider
from .providers.local_keystore import LocalKeyStoreProvider
from .providers.local_keyring import LocalKeyringProvider

__all__ = [
    "CryptoProvider",
    "Keyring",
    "KeyVersionRecord",
    "SecurityEvent",
    "available_providers",
    "append_security_event",
    "query_security_events",
    "EVENT_KEY_ROTATED",
    "EVENT_NONCE_REUSE_DETECTED",
    "EVENT_REENCRYPT_DONE",
    "EVENT_PROVIDER_CHANGED",
    "append_authority_rotation_entry",
    "ActionContract",
    "create_action_contract",
    "validate_action_contract",
    "AWSKMSProvider",
    "AzureKeyVaultProvider",
    "create_provider",
    "GCPKMSProvider",
    "LocalKeyStoreProvider",
    "LocalKeyringProvider",
    "provider_from_policy",
    "register_provider",
    "resolve_provider_name",
]
