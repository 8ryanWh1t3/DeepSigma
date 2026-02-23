from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path

from deepsigma.security.keyring import Keyring
from deepsigma.security.reencrypt import run_reencrypt_job
from deepsigma.security.rotate_keys import rotate_keys


def _now() -> datetime:
    return datetime(2026, 2, 23, 0, 0, tzinfo=timezone.utc)


def test_keyring_ttl_expiry_boundary(tmp_path: Path):
    keyring = Keyring(path=tmp_path / "keyring.json", now_fn=_now)
    boundary = _now().isoformat().replace("+00:00", "Z")
    keyring.create("credibility", expires_at=boundary)

    changed = keyring.expire(now=_now())
    record = keyring.list("credibility")[0]

    assert changed == 1
    assert record.status == "expired"


def test_rotate_keys_increments_versions_with_authority_context(tmp_path: Path):
    keyring_path = tmp_path / "keyring.json"
    event_log_path = tmp_path / "events.jsonl"
    authority_ledger_path = tmp_path / "authority_ledger.json"

    first = rotate_keys(
        tenant_id="tenant-alpha",
        key_id="credibility",
        ttl_days=14,
        actor_user="dri",
        actor_role="coherence_steward",
        authority_dri="dri.approver",
        authority_role="dri_approver",
        authority_reason="scheduled rotation",
        authority_signing_key="test-signing-key",
        keyring_path=keyring_path,
        event_log_path=event_log_path,
        authority_ledger_path=authority_ledger_path,
    )
    second = rotate_keys(
        tenant_id="tenant-alpha",
        key_id="credibility",
        ttl_days=14,
        actor_user="dri",
        actor_role="coherence_steward",
        authority_dri="dri.approver",
        authority_role="dri_approver",
        authority_reason="scheduled rotation",
        authority_signing_key="test-signing-key",
        keyring_path=keyring_path,
        event_log_path=event_log_path,
        authority_ledger_path=authority_ledger_path,
    )

    assert first.key_version == 1
    assert second.key_version == 2

    ledger = json.loads(authority_ledger_path.read_text(encoding="utf-8"))
    assert len(ledger) == 2
    assert ledger[1]["prev_entry_hash"] == ledger[0]["entry_hash"]


def test_reencrypt_dry_run_then_resume_completed(tmp_path: Path):
    data_dir = tmp_path / "cred"
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "claims.jsonl").write_text('{"claim_id":"C-1"}\n', encoding="utf-8")
    checkpoint = tmp_path / "checkpoint.json"

    first = run_reencrypt_job(
        tenant_id="tenant-alpha",
        dry_run=True,
        resume=False,
        data_dir=data_dir,
        checkpoint_path=checkpoint,
    )
    assert first.status == "dry_run"

    checkpoint.write_text(
        json.dumps(
            {
                "tenant_id": "tenant-alpha",
                "status": "completed",
                "files_targeted": 1,
                "records_targeted": 1,
                "files_rewritten": 1,
                "records_reencrypted": 1,
            }
        ),
        encoding="utf-8",
    )

    resumed = run_reencrypt_job(
        tenant_id="tenant-alpha",
        dry_run=False,
        resume=True,
        data_dir=data_dir,
        checkpoint_path=checkpoint,
    )
    assert resumed.resumed is True
    assert resumed.status == "completed"
    assert resumed.records_reencrypted == 1
