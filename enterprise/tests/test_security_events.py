from __future__ import annotations

import json
from pathlib import Path

import pytest

from deepsigma.security.events import (
    EVENT_KEY_ROTATED,
    EVENT_REENCRYPT_DONE,
    append_security_event,
    query_security_events,
)


def test_security_events_are_hash_chained(tmp_path: Path):
    events_path = tmp_path / "security_events.jsonl"

    first = append_security_event(
        event_type=EVENT_KEY_ROTATED,
        tenant_id="tenant-alpha",
        payload={"key_id": "credibility", "key_version": 1},
        events_path=events_path,
    )
    second = append_security_event(
        event_type=EVENT_REENCRYPT_DONE,
        tenant_id="tenant-alpha",
        payload={"records_reencrypted": 42},
        events_path=events_path,
    )

    rows = [json.loads(line) for line in events_path.read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 2
    assert rows[0]["event_hash"] == first.event_hash
    assert rows[1]["prev_hash"] == first.event_hash
    assert rows[1]["event_hash"] == second.event_hash


def test_query_security_events_filters(tmp_path: Path):
    events_path = tmp_path / "security_events.jsonl"
    append_security_event(
        event_type=EVENT_KEY_ROTATED,
        tenant_id="tenant-alpha",
        payload={"key_id": "credibility", "key_version": 1},
        events_path=events_path,
    )
    append_security_event(
        event_type=EVENT_REENCRYPT_DONE,
        tenant_id="tenant-beta",
        payload={"records_reencrypted": 42},
        events_path=events_path,
    )
    alpha = query_security_events(events_path=events_path, tenant_id="tenant-alpha")
    done = query_security_events(events_path=events_path, event_type=EVENT_REENCRYPT_DONE)
    assert len(alpha) == 1
    assert alpha[0].tenant_id == "tenant-alpha"
    assert len(done) == 1
    assert done[0].event_type == EVENT_REENCRYPT_DONE


def test_append_security_event_rejects_unknown_type(tmp_path: Path):
    with pytest.raises(ValueError, match="Unsupported security event type"):
        append_security_event(
            event_type="UNKNOWN_EVENT",
            tenant_id="tenant-alpha",
            payload={"x": 1},
            events_path=tmp_path / "security_events.jsonl",
        )
