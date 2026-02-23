"""Smoke tests for deepsigma/cli/ — Product CLI."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(1, str(REPO_ROOT))

CSV_FIXTURE = REPO_ROOT / "tests" / "fixtures" / "promptcapabilities_export.csv"
VALID_BOOT = REPO_ROOT / "tests" / "fixtures" / "valid_boot.xlsx"

try:
    import openpyxl  # noqa: F401
    HAS_OPENPYXL = True
except ImportError:
    HAS_OPENPYXL = False


class TestCLIHelp:
    def test_no_args_prints_help(self, capsys):
        from deepsigma.cli.main import main

        rc = main([])
        assert rc == 0
        out = capsys.readouterr().out
        assert "deepsigma" in out.lower() or "usage" in out.lower()

    def test_version_flag(self):
        from deepsigma.cli.main import main

        with pytest.raises(SystemExit) as exc_info:
            main(["--version"])
        assert exc_info.value.code == 0


class TestDoctor:
    def test_doctor_runs(self, capsys):
        from deepsigma.cli.main import main

        main(["doctor"])
        out = capsys.readouterr().out
        assert "PASS" in out or "FAIL" in out

    def test_doctor_json(self, capsys):
        from deepsigma.cli.main import main

        main(["doctor", "--json"])
        out = capsys.readouterr().out
        data = json.loads(out)
        assert "passed" in data
        assert "checks" in data
        assert isinstance(data["checks"], list)


class TestMDPTIndex:
    def test_mdpt_index_runs(self, tmp_path):
        from deepsigma.cli.main import main

        rc = main(["mdpt", "index", "--csv", str(CSV_FIXTURE), "--out", str(tmp_path)])
        assert rc == 0
        assert (tmp_path / "prompt_index.json").exists()
        assert (tmp_path / "prompt_index_summary.md").exists()


class TestValidateBoot:
    @pytest.mark.skipif(not HAS_OPENPYXL, reason="openpyxl not installed")
    @pytest.mark.skipif(not VALID_BOOT.exists(), reason="valid_boot.xlsx fixture missing")
    def test_validate_boot_valid(self, capsys):
        from deepsigma.cli.main import main

        rc = main(["validate", "boot", str(VALID_BOOT)])
        assert rc == 0


class TestDemoExcel:
    @pytest.mark.skipif(not HAS_OPENPYXL, reason="openpyxl not installed")
    def test_demo_excel_runs(self, tmp_path):
        from deepsigma.cli.main import main

        rc = main(["demo", "excel", "--out", str(tmp_path)])
        assert rc == 0
        assert (tmp_path / "workbook.xlsx").exists()


class TestNewConnector:
    def test_new_connector_scaffolds_files(self, tmp_path):
        from deepsigma.cli.main import main

        out_dir = tmp_path / "adapters"
        tests_dir = tmp_path / "tests"

        rc = main(
            [
                "new-connector",
                "sample-api",
                "--out-dir",
                str(out_dir),
                "--tests-dir",
                str(tests_dir),
            ]
        )
        assert rc == 0

        connector_dir = out_dir / "sample_api"
        assert (connector_dir / "__init__.py").exists()
        assert (connector_dir / "connector.py").exists()
        assert (connector_dir / "mcp_tools.py").exists()
        assert (connector_dir / "README.md").exists()
        assert (tests_dir / "test_sample_api_connector.py").exists()


class TestInitProject:
    def test_init_project_scaffolds_quickstart_files(self, tmp_path):
        from deepsigma.cli.main import main

        rc = main(["init", "my-project", "--out-dir", str(tmp_path)])
        assert rc == 0

        project_dir = tmp_path / "my-project"
        assert (project_dir / "README.md").exists()
        assert (project_dir / "Makefile").exists()
        assert (project_dir / "data" / "sample_episodes.json").exists()
        assert (project_dir / "data" / "sample_drift.json").exists()
        assert (project_dir / "data" / "sample_claims.json").exists()
        assert (project_dir / "scenarios" / "drift_scenario.md").exists()
        assert (project_dir / "queries" / "iris_queries.md").exists()


class TestSecurityCLI:
    def test_security_rotate_keys_json(self, tmp_path, capsys, monkeypatch):
        from deepsigma.cli.main import main

        keyring_path = tmp_path / "keyring.json"
        event_path = tmp_path / "events.jsonl"
        authority_ledger_path = tmp_path / "authority_ledger.json"
        monkeypatch.setenv("DEEPSIGMA_AUTHORITY_SIGNING_KEY", "test-signing-key")

        rc = main(
            [
                "security",
                "rotate-keys",
                "--tenant",
                "tenant-alpha",
                "--key-id",
                "credibility",
                "--ttl-days",
                "14",
                "--keyring-path",
                str(keyring_path),
                "--event-log-path",
                str(event_path),
                "--authority-dri",
                "dri.approver",
                "--authority-reason",
                "scheduled policy rotation",
                "--authority-ledger-path",
                str(authority_ledger_path),
                "--json",
            ]
        )
        assert rc == 0
        payload = json.loads(capsys.readouterr().out)
        assert payload["key_id"] == "credibility"
        assert payload["key_version"] == 1
        assert keyring_path.exists()
        assert event_path.exists()
        assert authority_ledger_path.exists()

    def test_security_reencrypt_dry_run_json(self, tmp_path, capsys, monkeypatch):
        from deepsigma.cli.main import main

        data_dir = tmp_path / "cred"
        data_dir.mkdir(parents=True, exist_ok=True)
        (data_dir / "claims.jsonl").write_text('{"claim_id":"C-1"}\\n', encoding="utf-8")
        checkpoint = tmp_path / "checkpoint.json"
        authority_ledger_path = tmp_path / "authority_ledger.json"
        monkeypatch.setenv("DEEPSIGMA_AUTHORITY_SIGNING_KEY", "test-signing-key")

        rc = main(
            [
                "security",
                "reencrypt",
                "--tenant",
                "tenant-alpha",
                "--data-dir",
                str(data_dir),
                "--checkpoint",
                str(checkpoint),
                "--dry-run",
                "--authority-dri",
                "dri.approver",
                "--authority-reason",
                "scheduled drill",
                "--authority-ledger-path",
                str(authority_ledger_path),
                "--json",
            ]
        )
        assert rc == 0
        payload = json.loads(capsys.readouterr().out)
        assert payload["status"] == "dry_run"
        assert payload["records_targeted"] == 1
        assert checkpoint.exists()

    def test_security_provider_changed_and_query(self, tmp_path, capsys, monkeypatch):
        from deepsigma.cli.main import main

        events_path = tmp_path / "security_events.jsonl"
        monkeypatch.setenv("DEEPSIGMA_AUTHORITY_SIGNING_KEY", "test-signing-key")

        rc = main(
            [
                "security",
                "provider-changed",
                "--tenant",
                "tenant-alpha",
                "--previous-provider",
                "gcp-kms",
                "--current-provider",
                "local-keystore",
                "--events-path",
                str(events_path),
                "--json",
            ]
        )
        assert rc == 0
        payload = json.loads(capsys.readouterr().out)
        assert payload["event_type"] == "PROVIDER_CHANGED"

        rc = main(
            [
                "security",
                "events",
                "--events-path",
                str(events_path),
                "--event-type",
                "PROVIDER_CHANGED",
                "--json",
            ]
        )
        assert rc == 0
        listed = json.loads(capsys.readouterr().out)
        assert len(listed) == 1
        assert listed[0]["event_type"] == "PROVIDER_CHANGED"
