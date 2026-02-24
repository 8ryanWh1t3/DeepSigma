from __future__ import annotations

import json
from pathlib import Path

import pytest

from deepsigma.security.policy import (
    CryptoPolicyError,
    get_envelope_settings,
    load_crypto_policy,
    validate_envelope_metadata,
)


def test_load_crypto_policy_reads_default_file() -> None:
    policy = load_crypto_policy()
    assert policy["policy_version"] == "1.0"
    assert "local-keystore" in policy["allowed_providers"]


def test_get_envelope_settings_returns_current_and_supported() -> None:
    current, supported = get_envelope_settings()
    assert current == "1.0"
    assert "1.0" in supported


def test_validate_envelope_metadata_rejects_unsupported_version(tmp_path: Path) -> None:
    policy_path = tmp_path / "security_crypto_policy.json"
    policy_path.write_text(
        json.dumps(
            {
                "policy_version": "1.0",
                "default_provider": "local-keystore",
                "allowed_providers": ["local-keystore"],
                "allowed_algorithms": ["AES-256-GCM"],
                "min_ttl_days": 1,
                "max_ttl_days": 30,
                "envelope_version_current": "1.0",
                "envelope_versions_supported": ["1.0"],
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(CryptoPolicyError, match="not supported"):
        validate_envelope_metadata(
            {
                "envelope_version": "2.0",
                "provider": "local-keystore",
                "alg": "AES-256-GCM",
            },
            path=policy_path,
        )
