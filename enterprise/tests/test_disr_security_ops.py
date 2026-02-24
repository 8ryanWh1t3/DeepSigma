from __future__ import annotations

import json
from pathlib import Path

import pytest

from credibility_engine.store import CredibilityStore
from deepsigma.security.reencrypt import run_reencrypt_job
from deepsigma.security.rotate_keys import rotate_keys


@pytest.fixture
def temp_store_dir(tmp_path: Path) -> Path:
    data_dir = tmp_path / "cred"
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "claims.jsonl").write_text(
        '{"enc":"AES-256-GCM","tenant_id":"tenant-alpha","nonce":"AAAAAAAAAAAAAAAA","encrypted_payload":"BBBB"}\n',
        encoding="utf-8",
    )
    return data_dir


def test_rotate_keys_emits_event_and_keyring(tmp_path: Path):
    keyring_path = tmp_path / "keyring.json"
    event_log_path = tmp_path / "events.jsonl"
    authority_ledger_path = tmp_path / "authority_ledger.json"

    result = rotate_keys(
        tenant_id="tenant-alpha",
        key_id="credibility",
        ttl_days=14,
        actor_user="dri",
        actor_role="coherence_steward",
        authority_dri="dri.approver",
        authority_role="dri_approver",
        authority_reason="quarterly rotation cadence",
        authority_signing_key="test-signing-key",
        keyring_path=keyring_path,
        event_log_path=event_log_path,
        authority_ledger_path=authority_ledger_path,
    )

    assert result.key_version == 1
    keyring = json.loads(keyring_path.read_text(encoding="utf-8"))
    assert keyring[0]["key_id"] == "credibility"
    events = [json.loads(line) for line in event_log_path.read_text(encoding="utf-8").splitlines()]
    assert events[0]["event_type"] == "KEY_ROTATED"
    assert events[0]["event_hash"]
    ledger = json.loads(authority_ledger_path.read_text(encoding="utf-8"))
    assert ledger[0]["entry_type"] == "AUTHORIZED_KEY_ROTATION"
    assert ledger[0]["authority_dri"] == "dri.approver"


def test_reencrypt_dry_run_writes_checkpoint(tmp_path: Path):
    checkpoint = tmp_path / "checkpoint.json"
    data_dir = tmp_path / "cred"
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "claims.jsonl").write_text('{"k":"v"}\n', encoding="utf-8")

    summary = run_reencrypt_job(
        tenant_id="tenant-alpha",
        dry_run=True,
        resume=False,
        data_dir=data_dir,
        checkpoint_path=checkpoint,
        batch_size=25,
        idempotency_key="ik-dry-001",
        authority_dri="dri.approver",
        authority_reason="planned drill",
        authority_signing_key="test-signing-key",
    )

    assert summary.status == "dry_run"
    assert summary.records_targeted == 1
    cp = json.loads(checkpoint.read_text(encoding="utf-8"))
    assert cp["status"] == "dry_run"
    assert cp["batch_size"] == 25
    assert cp["idempotency_key"] == "ik-dry-001"


def test_reencrypt_resume_completed_returns_without_changes(tmp_path: Path):
    checkpoint = tmp_path / "checkpoint.json"
    checkpoint.write_text(
        json.dumps(
            {
                "tenant_id": "tenant-alpha",
                "status": "completed",
                "idempotency_key": "ik-001",
                "files_targeted": 3,
                "records_targeted": 9,
                "files_rewritten": 3,
                "records_reencrypted": 9,
            }
        ),
        encoding="utf-8",
    )

    summary = run_reencrypt_job(
        tenant_id="tenant-alpha",
        dry_run=False,
        resume=True,
            data_dir=tmp_path / "cred",
            checkpoint_path=checkpoint,
            idempotency_key="ik-001",
            authority_dri="dri.approver",
            authority_reason="resume run",
            authority_signing_key="test-signing-key",
        )

    assert summary.resumed is True
    assert summary.status == "completed"
    assert summary.records_reencrypted == 9


def test_reencrypt_resume_rejects_mismatched_idempotency_key(tmp_path: Path):
    checkpoint = tmp_path / "checkpoint.json"
    checkpoint.write_text(
        json.dumps(
            {
                "tenant_id": "tenant-alpha",
                "status": "completed",
                "idempotency_key": "ik-001",
                "files_targeted": 1,
                "records_targeted": 1,
                "files_rewritten": 1,
                "records_reencrypted": 1,
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="idempotency_key"):
        run_reencrypt_job(
            tenant_id="tenant-alpha",
            dry_run=False,
            resume=True,
            data_dir=tmp_path / "cred",
            checkpoint_path=checkpoint,
            idempotency_key="ik-002",
            authority_dri="dri.approver",
            authority_reason="resume run",
            authority_signing_key="test-signing-key",
        )


def test_reencrypt_rejects_invalid_batch_size(tmp_path: Path):
    data_dir = tmp_path / "cred"
    data_dir.mkdir(parents=True, exist_ok=True)
    with pytest.raises(ValueError, match="batch_size must be > 0"):
        run_reencrypt_job(
            tenant_id="tenant-alpha",
            dry_run=True,
            resume=False,
            data_dir=data_dir,
            checkpoint_path=tmp_path / "checkpoint.json",
            batch_size=0,
            authority_dri="dri.approver",
            authority_reason="policy",
            authority_signing_key="test-signing-key",
        )


def test_rotate_keys_rejects_invalid_ttl(tmp_path: Path):
    with pytest.raises(ValueError):
        rotate_keys(
            tenant_id="tenant-alpha",
            key_id="credibility",
            ttl_days=0,
            actor_user="dri",
            actor_role="coherence_steward",
            authority_dri="dri.approver",
            authority_role="dri_approver",
            authority_reason="policy",
            authority_signing_key="test-signing-key",
            keyring_path=tmp_path / "keyring.json",
            event_log_path=tmp_path / "events.jsonl",
        )


def test_rotate_keys_rejects_ttl_above_policy_max(tmp_path: Path):
    with pytest.raises(ValueError, match="violates crypto policy bounds"):
        rotate_keys(
            tenant_id="tenant-alpha",
            key_id="credibility",
            ttl_days=45,
            actor_user="dri",
            actor_role="coherence_steward",
            authority_dri="dri.approver",
            authority_role="dri_approver",
            authority_reason="policy",
            authority_signing_key="test-signing-key",
            keyring_path=tmp_path / "keyring.json",
            event_log_path=tmp_path / "events.jsonl",
        )


def test_rotate_keys_requires_authority_context(tmp_path: Path):
    with pytest.raises(ValueError, match="authority_dri is required"):
        rotate_keys(
            tenant_id="tenant-alpha",
            key_id="credibility",
            ttl_days=14,
            actor_user="dri",
            actor_role="coherence_steward",
            authority_dri=None,
            authority_role="dri_approver",
            authority_reason="policy",
            authority_signing_key="test-signing-key",
            keyring_path=tmp_path / "keyring.json",
            event_log_path=tmp_path / "events.jsonl",
        )


def test_reencrypt_requires_authority_context(tmp_path: Path):
    data_dir = tmp_path / "cred"
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "claims.jsonl").write_text('{"claim_id":"C-1"}\n', encoding="utf-8")

    with pytest.raises(ValueError, match="authority_dri is required"):
        run_reencrypt_job(
            tenant_id="tenant-alpha",
            dry_run=True,
            resume=False,
            data_dir=data_dir,
            checkpoint_path=tmp_path / "checkpoint.json",
            authority_dri=None,
            authority_reason="planned drill",
            authority_signing_key="test-signing-key",
        )


def test_reencrypt_completed_writes_authority_ledger(tmp_path: Path, monkeypatch):
    data_dir = tmp_path / "cred"
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "claims.jsonl").write_text('{"claim_id":"C-1"}\n', encoding="utf-8")

    monkeypatch.setenv("DEEPSIGMA_MASTER_KEY", "old-master-key")
    old_store = CredibilityStore(data_dir=data_dir, tenant_id="tenant-alpha", encrypt_at_rest=True)
    old_store.append_claim({"claim_id": "C-2"})

    monkeypatch.setenv("DEEPSIGMA_MASTER_KEY", "new-master-key")
    monkeypatch.setenv("DEEPSIGMA_PREVIOUS_MASTER_KEY", "old-master-key")
    summary = run_reencrypt_job(
        tenant_id="tenant-alpha",
        dry_run=False,
        resume=False,
        data_dir=data_dir,
        checkpoint_path=tmp_path / "checkpoint.json",
        authority_dri="dri.approver",
        authority_reason="incident recovery",
        authority_signing_key="test-signing-key",
        authority_ledger_path=tmp_path / "authority_ledger.json",
    )

    assert summary.status == "completed"
    ledger = json.loads((tmp_path / "authority_ledger.json").read_text(encoding="utf-8"))
    assert ledger[-1]["entry_type"] == "AUTHORIZED_REENCRYPT"
