"""Tests for deepsigma compliance export command."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from credibility_engine.store import CredibilityStore
from deepsigma.cli.main import main
from deepsigma.cli import compliance_export as compliance_mod
from governance import audit as audit_mod
from tenancy import policies as policy_mod


def _iso(days_ago: int) -> str:
    now = datetime.now(timezone.utc)
    return (now - timedelta(days=days_ago)).isoformat().replace("+00:00", "Z")


def _seed_tenant_registry(tmp_path) -> None:
    registry_path = tmp_path / "tenants.json"
    compliance_mod.TENANT_REGISTRY_PATH = registry_path
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry_path.write_text(
        json.dumps(
            [
                {
                    "tenant_id": "tenant-alpha",
                    "display_name": "Tenant Alpha",
                    "status": "ACTIVE",
                    "created_at": _iso(1),
                }
            ],
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def test_compliance_export_generates_required_artifacts(tmp_path, monkeypatch):
    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True)
    (repo_root / "src" / "adapters" / "sharepoint").mkdir(parents=True)
    (repo_root / "src" / "adapters" / "sharepoint" / "connector.py").write_text(
        "# connector\n",
        encoding="utf-8",
    )
    (repo_root / "trust_scorecard.json").write_text(
        json.dumps({"timestamp": _iso(1), "metrics": {"baseline_score": 90}}, indent=2),
        encoding="utf-8",
    )

    monkeypatch.setattr(compliance_mod, "REPO_ROOT", repo_root)
    monkeypatch.setattr(policy_mod, "_BASE_POLICY_DIR", tmp_path / "policies")
    monkeypatch.setattr(audit_mod, "_BASE_AUDIT_DIR", tmp_path / "audit")
    _seed_tenant_registry(tmp_path)

    tenant_id = "tenant-alpha"
    policy = policy_mod.default_policy(tenant_id)
    policy["updated_at"] = _iso(1)
    policy["updated_by"] = "owner@example.com"
    policy_mod.save_policy(tenant_id, policy)

    audit_mod.audit_action(
        tenant_id=tenant_id,
        actor_user="owner@example.com",
        actor_role="coherence_steward",
        action="POLICY_UPDATE",
        target_type="POLICY",
        target_id=tenant_id,
        outcome="SUCCESS",
        metadata={"updated_keys": ["retention_policy"]},
    )

    store = CredibilityStore(data_dir=tmp_path / "cred", tenant_id=tenant_id)
    store.append_record(
        "seal_chain.jsonl",
        {
            "packet_id": "CP-1",
            "sealed_at": _iso(1),
            "seal_hash": "sha256:abc",
            "prev_seal_hash": "GENESIS",
            "policy_hash": "123",
            "snapshot_hash": "456",
        },
    )
    store.save_packet(
        {
            "packet_id": "CP-1",
            "seal": {"sealed": True, "sealed_at": _iso(1)},
        }
    )

    out_dir = tmp_path / "report"
    rc = main(
        [
            "compliance",
            "export",
            "--tenant",
            tenant_id,
            "--from",
            (datetime.now(timezone.utc) - timedelta(days=7)).date().isoformat(),
            "--to",
            datetime.now(timezone.utc).date().isoformat(),
            "--out",
            str(out_dir),
        ]
    )
    assert rc == 0

    expected = [
        "audit_log.json",
        "audit_log.csv",
        "sealed_packet_chain.json",
        "policy_snapshots.json",
        "trust_scorecard_history.json",
        "tenant_configuration.json",
        "data_flow_diagram.mmd",
        "compliance_summary.md",
    ]
    for file_name in expected:
        assert (out_dir / file_name).exists(), file_name

    summary = (out_dir / "compliance_summary.md").read_text(encoding="utf-8")
    assert "Control Mapping" in summary
    assert "Gap Analysis" in summary


def test_compliance_export_redact_strips_user_identifiers(tmp_path, monkeypatch):
    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True)
    monkeypatch.setattr(compliance_mod, "REPO_ROOT", repo_root)
    monkeypatch.setattr(policy_mod, "_BASE_POLICY_DIR", tmp_path / "policies")
    monkeypatch.setattr(audit_mod, "_BASE_AUDIT_DIR", tmp_path / "audit")
    _seed_tenant_registry(tmp_path)

    tenant_id = "tenant-alpha"
    policy = policy_mod.default_policy(tenant_id)
    policy["updated_at"] = _iso(1)
    policy["updated_by"] = "person@example.com"
    policy_mod.save_policy(tenant_id, policy)

    audit_mod.audit_action(
        tenant_id=tenant_id,
        actor_user="person@example.com",
        actor_role="exec",
        action="PACKET_GENERATE",
        target_type="PACKET",
        target_id="CP-2",
        outcome="SUCCESS",
        metadata={"owner": "person@example.com"},
    )

    out_dir = tmp_path / "report_redacted"
    rc = main(
        [
            "compliance",
            "export",
            "--tenant",
            tenant_id,
            "--from",
            (datetime.now(timezone.utc) - timedelta(days=7)).date().isoformat(),
            "--to",
            datetime.now(timezone.utc).date().isoformat(),
            "--out",
            str(out_dir),
            "--redact",
        ]
    )
    assert rc == 0

    audit_json = (out_dir / "audit_log.json").read_text(encoding="utf-8")
    assert "person@example.com" not in audit_json
    assert "[REDACTED]" in audit_json
