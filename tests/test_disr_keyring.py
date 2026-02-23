from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from deepsigma.security.keyring import Keyring


def _now() -> datetime:
    return datetime(2026, 2, 23, 0, 0, tzinfo=timezone.utc)


def test_create_increments_version(tmp_path):
    path = tmp_path / "keyring.json"
    keyring = Keyring(path=path, now_fn=_now)

    first = keyring.create("credibility")
    second = keyring.create("credibility")

    assert first.key_version == 1
    assert second.key_version == 2
    assert second.status == "active"


def test_disable_latest_when_version_unspecified(tmp_path):
    path = tmp_path / "keyring.json"
    keyring = Keyring(path=path, now_fn=_now)
    keyring.create("credibility")
    keyring.create("credibility")

    disabled = keyring.disable("credibility")

    assert disabled.key_version == 2
    assert disabled.status == "disabled"


def test_expire_marks_active_records(tmp_path):
    path = tmp_path / "keyring.json"
    keyring = Keyring(path=path, now_fn=_now)

    expired_at = (_now() - timedelta(hours=1)).isoformat().replace("+00:00", "Z")
    active_at = (_now() + timedelta(days=1)).isoformat().replace("+00:00", "Z")
    keyring.create("credibility", expires_at=expired_at)
    keyring.create("credibility", expires_at=active_at)

    changed = keyring.expire(now=_now())
    records = keyring.list("credibility")

    assert changed == 1
    assert records[0].status == "expired"
    assert records[1].status == "active"


def test_current_ignores_expired_entries(tmp_path):
    path = tmp_path / "keyring.json"
    keyring = Keyring(path=path, now_fn=_now)

    expired_at = (_now() - timedelta(days=1)).isoformat().replace("+00:00", "Z")
    keyring.create("credibility", expires_at=expired_at)
    keyring.create("credibility")

    current = keyring.current("credibility")

    assert current is not None
    assert current.key_version == 2
    assert current.status == "active"


def test_disable_unknown_key_raises(tmp_path):
    keyring = Keyring(path=tmp_path / "keyring.json", now_fn=_now)

    with pytest.raises(ValueError):
        keyring.disable("missing")
