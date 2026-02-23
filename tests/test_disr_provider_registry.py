from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from deepsigma.security.providers import (
    available_providers,
    create_provider,
    provider_from_policy,
    register_provider,
    resolve_provider_name,
)
from deepsigma.security.providers.base import CryptoProvider


def _now() -> datetime:
    return datetime(2026, 2, 23, tzinfo=timezone.utc)


class _DummyProvider(CryptoProvider):
    @property
    def name(self) -> str:
        return "dummy"

    def create_key_version(self, key_id: str, expires_at: str | None = None):
        return {"key_id": key_id, "expires_at": expires_at}

    def list_key_versions(self, key_id: str | None = None):
        return []

    def current_key_version(self, key_id: str):
        return None

    def disable_key_version(self, key_id: str, key_version: int | None = None):
        return {"key_id": key_id, "key_version": key_version}

    def expire_keys(self, now: datetime | None = None) -> int:
        return 0


def test_default_provider_is_registered() -> None:
    assert "local-keystore" in available_providers()
    assert "local-keyring" in available_providers()
    assert "aws-kms" in available_providers()
    assert "gcp-kms" in available_providers()
    assert "azure-kv" in available_providers()


def test_create_provider_unknown_raises() -> None:
    with pytest.raises(ValueError, match="Unknown provider"):
        create_provider("not-real")


def test_register_provider_and_create_instance() -> None:
    register_provider("dummy", _DummyProvider, overwrite=True)
    provider = create_provider("dummy")
    assert isinstance(provider, _DummyProvider)


def test_register_provider_duplicate_without_overwrite_fails() -> None:
    register_provider("dummy-no-overwrite", _DummyProvider, overwrite=True)
    with pytest.raises(ValueError, match="already registered"):
        register_provider("dummy-no-overwrite", _DummyProvider)


def test_resolve_provider_name_prefers_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEEPSIGMA_CRYPTO_PROVIDER", "dummy")
    resolved = resolve_provider_name({"security": {"crypto_provider": "local-keystore"}})
    assert resolved == "dummy"


def test_resolve_provider_name_from_nested_policy(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DEEPSIGMA_CRYPTO_PROVIDER", raising=False)
    resolved = resolve_provider_name({"security": {"provider": "local-keystore"}})
    assert resolved == "local-keystore"


def test_provider_from_policy_uses_overrides(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.delenv("DEEPSIGMA_CRYPTO_PROVIDER", raising=False)
    provider = provider_from_policy(
        {"security": {"crypto_provider": "local-keystore"}},
        provider_overrides={"local-keystore": {"path": tmp_path / "local_keystore.json", "now_fn": _now}},
    )
    record = provider.create_key_version("credibility")
    assert record.key_version == 1


def test_local_keyring_provider_lifecycle(tmp_path) -> None:
    provider = create_provider("local-keystore", path=tmp_path / "local_keystore.json", now_fn=_now)

    expired_at = (_now() - timedelta(hours=1)).isoformat().replace("+00:00", "Z")
    provider.create_key_version("credibility", expires_at=expired_at)
    provider.create_key_version("credibility")

    changed = provider.expire_keys(now=_now())
    current = provider.current_key_version("credibility")

    assert changed == 1
    assert current is not None
    assert current.key_version == 2
    assert current.status == "active"


def test_local_keystore_file_format_is_deterministic(tmp_path) -> None:
    path = tmp_path / "local_keystore.json"
    provider = create_provider("local-keystore", path=path, now_fn=_now)

    provider.create_key_version("credibility")
    provider.create_key_version("credibility")
    payload = path.read_text(encoding="utf-8")

    assert '"provider": "local-keystore"' in payload
    assert '"schema_version": "1.0"' in payload
    assert payload.count('"key_version"') == 2


@pytest.mark.parametrize("provider_name", ["aws-kms", "gcp-kms", "azure-kv"])
def test_cloud_kms_stubs_fail_closed(provider_name: str) -> None:
    provider = create_provider(provider_name)
    with pytest.raises(NotImplementedError, match="stub"):
        provider.create_key_version("credibility")
