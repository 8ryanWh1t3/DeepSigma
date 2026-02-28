from __future__ import annotations

import json
from pathlib import Path

import pytest

from deepsigma.security.authority_ledger import (
    append_authority_action_entry,
    detect_replay,
    export_authority_ledger,
    load_authority_ledger,
    verify_chain,
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


def test_verify_chain_passes_on_valid_ledger(tmp_path: Path):
    ledger_path = tmp_path / "authority_ledger.json"
    for i in range(3):
        append_authority_action_entry(
            ledger_path=ledger_path,
            authority_event=_event(f"evt-{i}", f"{chr(ord('a') + i)}" * 64),
            authority_dri="demo.dri",
            authority_role="dri_approver",
            authority_reason=f"entry {i}",
            signing_key="test-signing-key",
            action_type="AUTHORIZED_KEY_ROTATION",
            action_contract={"action_id": f"act-{i}", "dri": "demo.dri", "approver": "demo.dri"},
        )
    entries = load_authority_ledger(ledger_path)
    errors = verify_chain(entries)
    assert errors == [], f"valid chain should have no errors: {errors}"


def test_verify_chain_detects_tampered_hash(tmp_path: Path):
    ledger_path = tmp_path / "authority_ledger.json"
    append_authority_action_entry(
        ledger_path=ledger_path,
        authority_event=_event("evt-1", "a" * 64),
        authority_dri="demo.dri",
        authority_role="dri_approver",
        authority_reason="test",
        signing_key="test-signing-key",
        action_type="AUTHORIZED_KEY_ROTATION",
        action_contract={"action_id": "act-1", "dri": "demo.dri", "approver": "demo.dri"},
    )
    entries = load_authority_ledger(ledger_path)
    entries[0]["entry_hash"] = "tampered"
    errors = verify_chain(entries)
    assert len(errors) == 1
    assert errors[0]["error"] == "entry_hash tampered"


def test_detect_replay_finds_duplicates(tmp_path: Path):
    ledger_path = tmp_path / "authority_ledger.json"
    append_authority_action_entry(
        ledger_path=ledger_path,
        authority_event=_event("evt-1", "a" * 64),
        authority_dri="demo.dri",
        authority_role="dri_approver",
        authority_reason="first",
        signing_key="test-signing-key",
        action_type="AUTHORIZED_KEY_ROTATION",
        action_contract={"action_id": "act-1", "dri": "demo.dri", "approver": "demo.dri"},
    )
    entries = load_authority_ledger(ledger_path)
    entries.append(dict(entries[0]))  # simulate replay
    dups = detect_replay(entries)
    assert len(dups) == 1
    assert dups[0]["event_id"] == "evt-1"


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
