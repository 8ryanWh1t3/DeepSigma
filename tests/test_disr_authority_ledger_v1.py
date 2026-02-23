from __future__ import annotations

import json
from pathlib import Path

import pytest

from deepsigma.security.authority_ledger import (
    append_authority_action_entry,
    export_authority_ledger,
    load_authority_ledger,
)


def _event(event_id: str, event_hash: str) -> dict:
    return {
        "event_id": event_id,
        "event_hash": event_hash,
        "tenant_id": "tenant-alpha",
        "occurred_at": "2026-02-23T00:00:00Z",
        "payload": {"key_id": "credibility", "key_version": 1},
    }


def test_snapshot_version_increments_and_chain_is_preserved(tmp_path: Path):
    ledger_path = tmp_path / "authority_ledger.json"
    append_authority_action_entry(
        ledger_path=ledger_path,
        authority_event=_event("evt-1", "a" * 64),
        authority_dri="demo.dri",
        authority_role="dri_approver",
        authority_reason="rotation approval",
        signing_key="test-signing-key",
        action_type="AUTHORIZED_KEY_ROTATION",
        action_contract={"action_id": "act-1", "dri": "demo.dri", "approver": "demo.dri"},
    )
    append_authority_action_entry(
        ledger_path=ledger_path,
        authority_event=_event("evt-2", "b" * 64),
        authority_dri="demo.dri",
        authority_role="dri_approver",
        authority_reason="reencrypt approval",
        signing_key="test-signing-key",
        action_type="AUTHORIZED_REENCRYPT",
        action_contract={"action_id": "act-2", "dri": "demo.dri", "approver": "demo.dri"},
    )

    entries = load_authority_ledger(ledger_path)
    assert len(entries) == 2
    assert entries[1]["prev_entry_hash"] == entries[0]["entry_hash"]

    snapshot_path = tmp_path / "authority_ledger.snapshot.json"
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    assert snapshot["snapshot_version"] == 2
    assert snapshot["entry_count"] == 2
    assert snapshot["provenance"]["event_id"] == "evt-2"


def test_system_tier_cannot_authorize_privileged_actions(tmp_path: Path):
    with pytest.raises(ValueError, match="precedence too low"):
        append_authority_action_entry(
            ledger_path=tmp_path / "authority_ledger.json",
            authority_event=_event("evt-1", "c" * 64),
            authority_dri="svc.account",
            authority_role="system",
            authority_reason="should fail",
            signing_key="test-signing-key",
            action_type="AUTHORIZED_KEY_ROTATION",
            action_contract={"action_id": "act-1", "dri": "demo.dri", "approver": "demo.dri"},
        )


def test_export_authority_ledger_ndjson(tmp_path: Path):
    ledger_path = tmp_path / "authority_ledger.json"
    append_authority_action_entry(
        ledger_path=ledger_path,
        authority_event=_event("evt-1", "d" * 64),
        authority_dri="demo.dri",
        authority_role="dri_approver",
        authority_reason="export validation",
        signing_key="test-signing-key",
        action_type="AUTHORIZED_KEY_ROTATION",
        action_contract={"action_id": "act-1", "dri": "demo.dri", "approver": "demo.dri"},
    )

    out_path = tmp_path / "authority_ledger.ndjson"
    export_authority_ledger(ledger_path=ledger_path, out_path=out_path, export_format="ndjson")
    rows = [line for line in out_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(rows) == 1
    parsed = json.loads(rows[0])
    assert parsed["entry_type"] == "AUTHORIZED_KEY_ROTATION"
