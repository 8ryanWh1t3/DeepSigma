from __future__ import annotations

import json
from pathlib import Path

from deepsigma.security.events import append_security_event


def test_security_events_are_hash_chained(tmp_path: Path):
    events_path = tmp_path / "security_events.jsonl"

    first = append_security_event(
        event_type="KEY_ROTATED",
        tenant_id="tenant-alpha",
        payload={"key_id": "credibility", "key_version": 1},
        events_path=events_path,
    )
    second = append_security_event(
        event_type="REENCRYPT_COMPLETED",
        tenant_id="tenant-alpha",
        payload={"records_reencrypted": 42},
        events_path=events_path,
    )

    rows = [json.loads(line) for line in events_path.read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 2
    assert rows[0]["event_hash"] == first.event_hash
    assert rows[1]["prev_hash"] == first.event_hash
    assert rows[1]["event_hash"] == second.event_hash
