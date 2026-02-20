"""Tests for Healthcare and FinServ CDS workbook generators.

Validates BOOT protocol compliance and table structure.

Run:  pytest tests/test_workbook_boot.py -v
"""
from __future__ import annotations

import sys
from pathlib import Path

import openpyxl

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.validate_workbook_boot import validate  # noqa: E402

REPO = Path(__file__).resolve().parents[1]

REQUIRED_TABLES = [
    "tblTimeline", "tblDeliverables", "tblDLR",
    "tblClaims", "tblAssumptions", "tblPatchLog",
    "tblCanonGuardrails",
]


def _generate_healthcare(out: Path) -> Path:
    from tools.generate_healthcare_cds_workbook import (
        generate_workbook,
    )
    generate_workbook(out)
    return out


def _generate_finserv(out: Path) -> Path:
    from tools.generate_finserv_cds_workbook import (
        generate_workbook,
    )
    generate_workbook(out)
    return out


def _get_tables(path: Path) -> dict[str, int]:
    """Return {table_name: row_count} for all tables."""
    wb = openpyxl.load_workbook(
        str(path), read_only=False, data_only=True,
    )
    tables = {}
    for ws in wb.worksheets:
        for t in ws.tables.values():
            # Count data rows (total rows - header)
            rows = ws.max_row - 1  # subtract header
            tables[t.displayName] = rows
    wb.close()
    return tables


class TestHealthcareBoot:
    """Healthcare workbook BOOT compliance."""

    def test_boot_valid(self, tmp_path):
        p = _generate_healthcare(tmp_path / "hc.xlsx")
        errors = validate(str(p))
        assert errors == [], f"BOOT errors: {errors}"

    def test_has_7_tables(self, tmp_path):
        p = _generate_healthcare(tmp_path / "hc.xlsx")
        tables = _get_tables(p)
        for name in REQUIRED_TABLES:
            assert name in tables, (
                f"Missing table {name}"
            )

    def test_25_rows_per_table(self, tmp_path):
        p = _generate_healthcare(tmp_path / "hc.xlsx")
        tables = _get_tables(p)
        for name in REQUIRED_TABLES:
            assert tables[name] == 25, (
                f"{name} has {tables[name]} rows, "
                f"expected 25"
            )


class TestFinServBoot:
    """FinServ workbook BOOT compliance."""

    def test_boot_valid(self, tmp_path):
        p = _generate_finserv(tmp_path / "fs.xlsx")
        errors = validate(str(p))
        assert errors == [], f"BOOT errors: {errors}"

    def test_has_7_tables(self, tmp_path):
        p = _generate_finserv(tmp_path / "fs.xlsx")
        tables = _get_tables(p)
        for name in REQUIRED_TABLES:
            assert name in tables, (
                f"Missing table {name}"
            )

    def test_25_rows_per_table(self, tmp_path):
        p = _generate_finserv(tmp_path / "fs.xlsx")
        tables = _get_tables(p)
        for name in REQUIRED_TABLES:
            assert tables[name] == 25, (
                f"{name} has {tables[name]} rows, "
                f"expected 25"
            )
