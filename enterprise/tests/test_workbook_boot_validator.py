"""Tests for tools/validate_workbook_boot.py — BOOT contract validation."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

FIXTURES = REPO_ROOT / "tests" / "fixtures"
TEMPLATE = (
    REPO_ROOT
    / "templates"
    / "creative_director_suite"
    / "Creative_Director_Suite_CoherenceOps_v2.xlsx"
)

try:
    import openpyxl  # noqa: F401
    HAS_OPENPYXL = True
except ImportError:
    HAS_OPENPYXL = False

pytestmark = pytest.mark.skipif(not HAS_OPENPYXL, reason="openpyxl not installed")


def _validate(path, **kwargs):
    from tools.validate_workbook_boot import validate
    return validate(str(path), **kwargs)


def _main(args):
    from tools.validate_workbook_boot import main
    return main(args)


class TestBootSheetPresence:
    def test_missing_boot_sheet_fails(self):
        errors = _validate(FIXTURES / "missing_boot_sheet.xlsx")
        assert errors
        assert any("Missing required sheet: BOOT" in e for e in errors)

    def test_nonexistent_file_fails(self):
        errors = _validate(FIXTURES / "does_not_exist.xlsx")
        assert errors
        assert any("File not found" in e for e in errors)


class TestBootKeyValidation:
    def test_missing_required_keys_fails(self):
        errors = _validate(FIXTURES / "missing_keys.xlsx", boot_only=True)
        assert errors
        missing_key_errors = [e for e in errors if "missing required key" in e.lower()]
        # Should be missing at least ttl_hours_default, risk_lane_default, schema_ref, owner
        assert len(missing_key_errors) >= 4

    def test_all_keys_present_passes(self):
        errors = _validate(FIXTURES / "valid_boot.xlsx")
        key_errors = [e for e in errors if "missing required key" in e.lower()]
        assert len(key_errors) == 0


class TestNamedTables:
    def test_missing_tables_without_boot_only_fails(self):
        errors = _validate(FIXTURES / "boot_only.xlsx", boot_only=False)
        table_errors = [e for e in errors if "Missing named table" in e]
        assert len(table_errors) == 7  # all 7 tables missing

    def test_boot_only_mode_skips_table_check(self):
        errors = _validate(FIXTURES / "boot_only.xlsx", boot_only=True)
        table_errors = [e for e in errors if "Missing named table" in e]
        assert len(table_errors) == 0


class TestValidWorkbook:
    def test_full_valid_workbook_passes(self):
        errors = _validate(FIXTURES / "valid_boot.xlsx")
        assert errors == []

    def test_cli_exit_code_zero_on_pass(self):
        rc = _main([str(FIXTURES / "valid_boot.xlsx")])
        assert rc == 0

    def test_cli_exit_code_one_on_fail(self):
        rc = _main([str(FIXTURES / "missing_boot_sheet.xlsx")])
        assert rc == 1


class TestExistingTemplate:
    @pytest.mark.skipif(not TEMPLATE.exists(), reason="Template not yet generated")
    def test_template_workbook_validates(self):
        errors = _validate(TEMPLATE)
        assert errors == [], f"Template validation failed: {errors}"
