from __future__ import annotations

import json
from pathlib import Path

import pytest

from deepsigma.security.authority_ledger import append_authority_action_entry


def _event(event_id: str = "evt-1", event_hash: str = "abc123") -> dict[str, object]:
    return {
        "event_id": event_id,
        "event_hash": event_hash,
        "tenant_id": "tenant-alpha",
        "occurred_at": "2026-02-23T00:00:00Z",
        "payload": {"key_id": "credibility", "key_version": 2},
    }


def test_authority_ledger_writes_versioned_snapshot_with_provenance(tmp_path: Path) -> None:
    ledger_path = tmp_path / "authority_ledger.json"
    entry = append_authority_action_entry(
        ledger_path=ledger_path,
        authority_event=_event(),
        authority_dri="dri.approver",
        authority_role="dri_approver",
        authority_reason="incident recovery",
        signing_key="test-signing-key",
        action_type="AUTHORIZED_REENCRYPT",
        action_contract={
            "action_id": "ACT-12345678",
            "dri": "dri.owner",
            "approver": "dri.approver",
        },
    )

    snapshot_path = tmp_path / "authority_ledger.snapshot.json"
    assert snapshot_path.exists()
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    assert snapshot["schema_version"] == "authority-ledger-v1"
    assert snapshot["snapshot_version"] == 1
    assert snapshot["latest_entry_hash"] == entry["entry_hash"]
    assert snapshot["provenance"]["entry_id"] == entry["entry_id"]


def test_authority_ledger_rejects_system_precedence(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="precedence too low"):
        append_authority_action_entry(
            ledger_path=tmp_path / "authority_ledger.json",
            authority_event=_event(),
            authority_dri="system.bot",
            authority_role="system",
            authority_reason="automation fallback",
            signing_key="test-signing-key",
            action_type="AUTHORIZED_REENCRYPT",
        )


def test_authority_ledger_enforces_contract_identity_match(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="must match action contract approver or dri"):
        append_authority_action_entry(
            ledger_path=tmp_path / "authority_ledger.json",
            authority_event=_event(),
            authority_dri="unknown.actor",
            authority_role="dri_approver",
            authority_reason="incident recovery",
            signing_key="test-signing-key",
            action_type="AUTHORIZED_REENCRYPT",
            action_contract={
                "action_id": "ACT-12345678",
                "dri": "dri.owner",
                "approver": "dri.approver",
            },
        )
