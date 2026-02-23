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
