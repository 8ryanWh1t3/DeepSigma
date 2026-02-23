from __future__ import annotations

import importlib.util
import json
from pathlib import Path


def _load_module(repo_root: Path):
    mod_path = repo_root / "scripts" / "security_audit_pack.py"
    spec = importlib.util.spec_from_file_location("security_audit_pack", mod_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_build_security_audit_pack_collects_expected_files(tmp_path: Path):
    repo = tmp_path / "repo"
    (repo / "release_kpis").mkdir(parents=True, exist_ok=True)
    (repo / "governance").mkdir(parents=True, exist_ok=True)
    (repo / "schemas" / "core").mkdir(parents=True, exist_ok=True)
    (repo / "docs" / "docs" / "security").mkdir(parents=True, exist_ok=True)
    (repo / "data" / "security").mkdir(parents=True, exist_ok=True)

    (repo / "release_kpis" / "VERSION.txt").write_text("v2.0.5\n", encoding="utf-8")
    (repo / "release_kpis" / "security_metrics.json").write_text('{"ok":true}\n', encoding="utf-8")
    (repo / "release_kpis" / "SECURITY_GATE_REPORT.md").write_text("# ok\n", encoding="utf-8")
    (repo / "governance" / "security_crypto_policy.json").write_text("{}", encoding="utf-8")
    (repo / "schemas" / "core" / "security_crypto_policy.schema.json").write_text("{}", encoding="utf-8")
    (repo / "schemas" / "core" / "crypto_envelope.schema.json").write_text("{}", encoding="utf-8")
    (repo / "docs" / "docs" / "security" / "DISR.md").write_text("# DISR\n", encoding="utf-8")
    (repo / "docs" / "docs" / "security" / "KEY_LIFECYCLE.md").write_text("# KEY\n", encoding="utf-8")
    (repo / "docs" / "docs" / "security" / "RECOVERY_RUNBOOK.md").write_text("# REC\n", encoding="utf-8")
    (repo / "docs" / "docs" / "security" / "ENVELOPE_VERSIONING.md").write_text("# ENV\n", encoding="utf-8")
    (repo / "data" / "security" / "security_events.jsonl").write_text('{"event":"x"}\n', encoding="utf-8")
    (repo / "data" / "security" / "authority_ledger.json").write_text("[]\n", encoding="utf-8")

    module = _load_module(Path(__file__).resolve().parents[1])
    out_dir = repo / "security_audit_pack"
    manifest = module.build_security_audit_pack(repo, out_dir, strict=False)

    assert (out_dir / "manifest.json").exists()
    assert (out_dir / "versions.json").exists()
    assert (out_dir / "governance" / "security_crypto_policy.json").exists()
    assert manifest["counts"]["included"] > 0


def test_build_security_audit_pack_strict_raises_on_missing(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir(parents=True, exist_ok=True)
    module = _load_module(Path(__file__).resolve().parents[1])
    out_dir = repo / "security_audit_pack"
    try:
        module.build_security_audit_pack(repo, out_dir, strict=True)
        assert False, "expected strict mode to fail on missing files"
    except RuntimeError as exc:
        assert "Missing required audit pack sources" in str(exc)

    manifest = json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["counts"]["missing"] >= 1
