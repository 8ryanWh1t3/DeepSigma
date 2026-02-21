#!/usr/bin/env python3
"""Export Prompt OS v2 workbook to a JSON sealed snapshot.

Reads all named tables from the Excel workbook, exports each as a JSON array,
computes a SHA-256 seal hash, and writes the sealed snapshot to a JSON file.

Usage:
    python -m tools.export_sealed_snapshot
    python -m tools.export_sealed_snapshot --input artifacts/excel/Coherence_Prompt_OS_v2.xlsx
    python -m tools.export_sealed_snapshot --input workbook.xlsx --output snapshot.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    import openpyxl
except ImportError:
    print("ERROR: openpyxl is required. Install with: pip install openpyxl")
    sys.exit(1)

# Named tables to export (table display name → expected sheet)
NAMED_TABLES = [
    "DecisionLogTable",
    "AtomicClaimsTable",
    "PromptLibraryTable",
    "AssumptionsTable",
    "PatchLogTable",
    "LLMOutputTable",
    "DashboardTrendsTable",
]


def extract_table_data(wb: openpyxl.Workbook, table_name: str) -> list[dict] | None:
    """Extract rows from a named table as a list of dicts."""
    for ws in wb.worksheets:
        for tbl in ws.tables.values():
            if tbl.displayName == table_name:
                ref = tbl.ref  # e.g. "A1:Q4"
                rows = list(ws[ref])
                if len(rows) < 2:
                    return []
                headers = [cell.value for cell in rows[0]]
                data = []
                for row in rows[1:]:
                    record = {}
                    for header, cell in zip(headers, row):
                        if header is None:
                            continue
                        value = cell.value
                        # Convert dates and numbers to strings for JSON
                        if hasattr(value, "isoformat"):
                            value = value.isoformat()
                        elif isinstance(value, float) and value == int(value):
                            value = int(value)
                        record[header] = value
                    data.append(record)
                return data
    return None


def compute_seal_hash(tables_json: str) -> str:
    """Compute SHA-256 hash of the tables JSON string."""
    return "sha256:" + hashlib.sha256(tables_json.encode("utf-8")).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description="Export Prompt OS v2 workbook to sealed JSON snapshot")
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("artifacts/excel/Coherence_Prompt_OS_v2.xlsx"),
        help="Path to workbook (default: artifacts/excel/Coherence_Prompt_OS_v2.xlsx)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output JSON path (default: sealed_snapshot_YYYY-MM-DD.json)",
    )
    parser.add_argument(
        "--operator",
        type=str,
        default="system",
        help="Operator name for the seal record (default: system)",
    )
    args = parser.parse_args()

    if not args.input.exists():
        print(f"ERROR: Workbook not found: {args.input}")
        return 1

    if args.output is None:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        args.output = Path(f"sealed_snapshot_{today}.json")

    print(f"Reading workbook: {args.input}")
    wb = openpyxl.load_workbook(args.input, data_only=True)

    tables = {}
    for table_name in NAMED_TABLES:
        data = extract_table_data(wb, table_name)
        if data is None:
            print(f"  WARN: Table '{table_name}' not found in workbook")
            tables[table_name] = []
        else:
            print(f"  {table_name}: {len(data)} rows")
            tables[table_name] = data

    # Compute seal hash from deterministic JSON
    tables_json = json.dumps(tables, sort_keys=True, default=str)
    seal_hash = compute_seal_hash(tables_json)

    # Build sealed snapshot
    snapshot = {
        "seal_version": "2.0",
        "sealed_at": datetime.now(timezone.utc).isoformat(),
        "seal_hash": seal_hash,
        "operator": args.operator,
        "source_workbook": str(args.input),
        "tables": tables,
    }

    with open(args.output, "w") as f:
        json.dump(snapshot, f, indent=2, default=str)

    print(f"\nSealed snapshot written: {args.output}")
    print(f"Seal hash: {seal_hash}")
    print(f"Tables exported: {len([t for t in tables.values() if t])}/{len(NAMED_TABLES)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
