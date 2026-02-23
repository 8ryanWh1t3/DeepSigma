"""Security primitives for DISR (Disposable Rotors)."""

from .authority_ledger import append_authority_rotation_entry, export_authority_ledger, load_authority_ledger
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
from .policy import (
    CryptoPolicyError,
    get_envelope_settings,
    load_crypto_policy,
    validate_algorithm_allowed,
    validate_envelope_metadata,
    validate_provider_allowed,
    validate_rotation_ttl_days,
)
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
    "load_crypto_policy",
    "get_envelope_settings",
    "validate_algorithm_allowed",
    "validate_envelope_metadata",
    "validate_provider_allowed",
    "validate_rotation_ttl_days",
    "CryptoPolicyError",
    "EVENT_KEY_ROTATED",
    "EVENT_NONCE_REUSE_DETECTED",
    "EVENT_REENCRYPT_DONE",
    "EVENT_PROVIDER_CHANGED",
    "append_authority_rotation_entry",
    "load_authority_ledger",
    "export_authority_ledger",
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
