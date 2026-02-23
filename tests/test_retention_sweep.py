"""Tests for deepsigma retention sweep command."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from credibility_engine.store import CredibilityStore
from deepsigma.cli.main import main
from governance import audit as audit_mod
from tenancy import policies as policy_mod


def _iso(days_ago: int) -> str:
    now = datetime.now(timezone.utc)
    return (now - timedelta(days=days_ago)).isoformat().replace("+00:00", "Z")


def _write_policy(tenant_id: str) -> None:
    policy = policy_mod.default_policy(tenant_id)
    policy_mod.save_policy(tenant_id, policy)


def test_retention_sweep_dry_run_no_deletes(tmp_path, monkeypatch, capsys):
    tenant_id = "tenant-alpha"
    monkeypatch.setattr(policy_mod, "_BASE_POLICY_DIR", tmp_path / "policies")
    monkeypatch.setattr(audit_mod, "_BASE_AUDIT_DIR", tmp_path / "audit")

    _write_policy(tenant_id)

    store = CredibilityStore(data_dir=tmp_path / "cred", tenant_id=tenant_id)
    store.write_cold(
        store.CLAIMS_FILE,
        [
            {"id": "old", "timestamp": _iso(500)},
            {"id": "new", "timestamp": _iso(10)},
        ],
    )

    rc = main(
        [
            "retention",
            "sweep",
            "--tenant",
            tenant_id,
            "--data-dir",
            str(tmp_path / "cred"),
            "--dry-run",
            "--json",
        ]
    )
    assert rc == 0

    out = json.loads(capsys.readouterr().out)
    assert out["dry_run"] is True
    assert out["cold_purge"]["deleted_total"] == 1

    # Dry run must not mutate cold records.
    assert len(store.load_cold(store.CLAIMS_FILE)) == 2


def test_retention_sweep_applies_purge_and_audits(tmp_path, monkeypatch, capsys):
    tenant_id = "tenant-alpha"
    monkeypatch.setattr(policy_mod, "_BASE_POLICY_DIR", tmp_path / "policies")
    monkeypatch.setattr(audit_mod, "_BASE_AUDIT_DIR", tmp_path / "audit")

    policy = policy_mod.default_policy(tenant_id)
    policy["retention_policy"]["cold_retention_days"] = 30
    policy["retention_policy"]["audit_retention_days"] = 30
    policy_mod.save_policy(tenant_id, policy)

    store = CredibilityStore(data_dir=tmp_path / "cred", tenant_id=tenant_id)
    store.write_cold(
        store.CLAIMS_FILE,
        [
            {"id": "delete-me", "timestamp": _iso(60)},
            {"id": "keep-me", "timestamp": _iso(5)},
        ],
    )

    audit_path = audit_mod._audit_path(tenant_id)
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    old_evt = {"timestamp": _iso(90), "action": "OLD"}
    new_evt = {"timestamp": _iso(2), "action": "NEW"}
    audit_path.write_text(json.dumps(old_evt) + "\n" + json.dumps(new_evt) + "\n", encoding="utf-8")

    rc = main(
        [
            "retention",
            "sweep",
            "--tenant",
            tenant_id,
            "--data-dir",
            str(tmp_path / "cred"),
            "--json",
        ]
    )
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["cold_purge"]["deleted_total"] == 1
    assert out["audit_purge"]["deleted"] == 1

    all_claims = (
        store.load_all(store.CLAIMS_FILE)
        + store.load_warm(store.CLAIMS_FILE)
        + store.load_cold(store.CLAIMS_FILE)
    )
    ids = {r["id"] for r in all_claims}
    assert "keep-me" in ids
    assert "delete-me" not in ids

    # Purge operations must emit audit entries.
    lines = [json.loads(x) for x in audit_path.read_text(encoding="utf-8").splitlines() if x.strip()]
    purge_events = [x for x in lines if x.get("action") == "RETENTION_PURGE"]
    assert purge_events


def test_default_policy_contains_retention_policy():
    policy = policy_mod.default_policy("tenant-alpha")
    retention = policy.get("retention_policy", {})
    assert retention["hot_retention_hours"] == 24
    assert retention["warm_retention_days"] == 30
    assert retention["cold_retention_days"] == 365
    assert retention["audit_retention_days"] == 2555
