"""Provider registry and policy-based resolution for DISR crypto backends."""

from __future__ import annotations

import os
from typing import Any, Callable

from .aws_kms import AWSKMSProvider
from .azure_kv import AzureKeyVaultProvider
from .base import CryptoProvider
from .gcp_kms import GCPKMSProvider
from .local_keystore import LocalKeyStoreProvider
from .local_keyring import LocalKeyringProvider

ProviderFactory = Callable[..., CryptoProvider]

_PROVIDER_REGISTRY: dict[str, ProviderFactory] = {}


def register_provider(name: str, factory: ProviderFactory, *, overwrite: bool = False) -> None:
    """Register a provider factory under a stable name."""
    normalized = _normalize_name(name)
    if normalized in _PROVIDER_REGISTRY and not overwrite:
        raise ValueError(f"Provider already registered: {normalized}")
    _PROVIDER_REGISTRY[normalized] = factory


def available_providers() -> list[str]:
    """Return registered provider names sorted for deterministic display."""
    return sorted(_PROVIDER_REGISTRY.keys())


def create_provider(name: str, **kwargs: Any) -> CryptoProvider:
    """Instantiate a provider by name."""
    normalized = _normalize_name(name)
    factory = _PROVIDER_REGISTRY.get(normalized)
    if factory is None:
        choices = ", ".join(available_providers()) or "(none)"
        raise ValueError(f"Unknown provider '{normalized}'. Available: {choices}")
    return factory(**kwargs)


def resolve_provider_name(policy: dict[str, Any] | None = None, *, default: str = "local-keystore") -> str:
    """Resolve provider name from env first, then policy, then default."""
    env_name = os.getenv("DEEPSIGMA_CRYPTO_PROVIDER")
    if env_name:
        return _normalize_name(env_name)

    payload = policy or {}
    nested_security = payload.get("security")
    if isinstance(nested_security, dict):
        for key in ("crypto_provider", "provider", "cryptoProvider"):
            value = nested_security.get(key)
            if value:
                return _normalize_name(str(value))

    for key in ("crypto_provider", "provider", "cryptoProvider"):
        value = payload.get(key)
        if value:
            return _normalize_name(str(value))

    return _normalize_name(default)


def provider_from_policy(
    policy: dict[str, Any] | None = None,
    *,
    default: str = "local-keystore",
    provider_overrides: dict[str, Any] | None = None,
    emit_change_event: bool = False,
    previous_provider: str | None = None,
    tenant_id: str = "tenant-alpha",
    events_path: str = "data/security/security_events.jsonl",
    signer_id: str | None = None,
    signing_key: str | None = None,
) -> CryptoProvider:
    """Create provider selected by policy name, with optional per-provider kwargs."""
    name = resolve_provider_name(policy, default=default)
    overrides = provider_overrides or {}
    kwargs = overrides.get(name, {})
    if not isinstance(kwargs, dict):
        raise ValueError(f"provider_overrides[{name}] must be a mapping")

    if emit_change_event and previous_provider and _normalize_name(previous_provider) != name:
        from ..events import EVENT_PROVIDER_CHANGED, append_security_event

        append_security_event(
            event_type=EVENT_PROVIDER_CHANGED,
            tenant_id=tenant_id,
            payload={
                "previous_provider": _normalize_name(previous_provider),
                "current_provider": name,
                "source": "policy_resolution",
            },
            events_path=events_path,
            signer_id=signer_id,
            signing_key=signing_key,
        )

    return create_provider(name, **kwargs)


def _normalize_name(name: str) -> str:
    normalized = name.strip().lower()
    if not normalized:
        raise ValueError("Provider name cannot be empty")
    return normalized


register_provider("local-keystore", LocalKeyStoreProvider)
register_provider("local-keyring", LocalKeyringProvider)
register_provider("aws-kms", AWSKMSProvider)
register_provider("gcp-kms", GCPKMSProvider)
register_provider("azure-kv", AzureKeyVaultProvider)
