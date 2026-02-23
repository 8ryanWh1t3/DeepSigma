"""Runtime crypto policy loading and enforcement helpers."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

DEFAULT_POLICY_PATH = Path("governance/security_crypto_policy.json")


class CryptoPolicyError(ValueError):
    """Raised when runtime crypto policy validation fails."""


def _coerce_path(path: str | Path | None) -> Path:
    if path is not None:
        return Path(path)
    from_env = os.getenv("DEEPSIGMA_CRYPTO_POLICY_PATH")
    if from_env:
        return Path(from_env)
    return DEFAULT_POLICY_PATH


def load_crypto_policy(path: str | Path | None = None) -> dict[str, Any]:
    """Load policy JSON from explicit path, env override, or default location."""
    policy_path = _coerce_path(path)
    if not policy_path.exists():
        raise CryptoPolicyError(f"Crypto policy file not found: {policy_path}")

    try:
        payload = json.loads(policy_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise CryptoPolicyError(f"Invalid crypto policy JSON at {policy_path}: {exc}") from exc

    if not isinstance(payload, dict):
        raise CryptoPolicyError(f"Crypto policy must be a JSON object: {policy_path}")

    required = {
        "policy_version",
        "default_provider",
        "allowed_providers",
        "allowed_algorithms",
        "min_ttl_days",
        "max_ttl_days",
        "envelope_version_current",
        "envelope_versions_supported",
    }
    missing = sorted(required - set(payload.keys()))
    if missing:
        raise CryptoPolicyError(f"Crypto policy missing required keys: {', '.join(missing)}")
    return payload


def get_envelope_settings(path: str | Path | None = None) -> tuple[str, set[str]]:
    policy = load_crypto_policy(path)
    current = str(policy["envelope_version_current"])
    supported = {str(item) for item in policy["envelope_versions_supported"]}
    if current not in supported:
        raise CryptoPolicyError("envelope_version_current must be included in envelope_versions_supported")
    return current, supported


def validate_provider_allowed(provider_name: str, path: str | Path | None = None) -> None:
    policy = load_crypto_policy(path)
    allowed = {str(item) for item in policy["allowed_providers"]}
    if provider_name not in allowed:
        raise CryptoPolicyError(
            f"Provider '{provider_name}' blocked by crypto policy. Allowed providers: {sorted(allowed)}"
        )


def validate_algorithm_allowed(algorithm: str, path: str | Path | None = None) -> None:
    policy = load_crypto_policy(path)
    allowed = {str(item) for item in policy["allowed_algorithms"]}
    if algorithm not in allowed:
        raise CryptoPolicyError(
            f"Algorithm '{algorithm}' blocked by crypto policy. Allowed algorithms: {sorted(allowed)}"
        )


def validate_rotation_ttl_days(ttl_days: int, path: str | Path | None = None) -> None:
    policy = load_crypto_policy(path)
    min_days = int(policy["min_ttl_days"])
    max_days = int(policy["max_ttl_days"])
    if ttl_days < min_days or ttl_days > max_days:
        raise CryptoPolicyError(
            f"ttl_days={ttl_days} violates crypto policy bounds [{min_days}, {max_days}]"
        )


def validate_envelope_metadata(envelope: dict[str, Any], path: str | Path | None = None) -> None:
    current, supported = get_envelope_settings(path)
    version = str(envelope.get("envelope_version", ""))
    if version not in supported:
        raise CryptoPolicyError(
            f"Envelope version '{version}' is not supported by crypto policy: {sorted(supported)}"
        )
    if version != current:
        # Migration path remains backward compatible, but new writes must use current.
        raise CryptoPolicyError(
            f"Envelope version '{version}' is not current policy version '{current}' for new writes"
        )

    provider = str(envelope.get("provider", ""))
    validate_provider_allowed(provider, path=path)

    algorithm = str(envelope.get("alg", ""))
    validate_algorithm_allowed(algorithm, path=path)
