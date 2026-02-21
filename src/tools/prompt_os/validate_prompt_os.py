#!/usr/bin/env python3
"""Prompt OS v2 — CSV ↔ Schema parity validator.

Validates every CSV in artifacts/sample_data/prompt_os_v2 against
schemas/prompt_os/prompt_os_schema_v2.json.

Checks:
  1. Required columns present
  2. No unexpected columns (not defined in schema)
  3. Enum fields match allowed values exactly
  4. Type checks (integers, numbers, date-like strings)
  5. Range checks (minimum / maximum)
  6. Required fields are non-empty

Exit code: 0 = all pass, 1 = any failure.

Usage:
    python src/tools/prompt_os/validate_prompt_os.py
    python src/tools/prompt_os/validate_prompt_os.py --csv-dir artifacts/sample_data/prompt_os_v2
    python src/tools/prompt_os/validate_prompt_os.py --schema schemas/prompt_os/prompt_os_schema_v2.json
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

# Map CSV filenames → schema table keys
CSV_TABLE_MAP = {
    "decision_log.csv": "DecisionLogTable",
    "atomic_claims.csv": "AtomicClaimsTable",
    "assumptions.csv": "AssumptionsTable",
    "prompt_library.csv": "PromptLibraryTable",
    "patch_log.csv": "PatchLogTable",
    "llm_output.csv": "LLMOutputTable",
    "dashboard_trends.csv": "DashboardTrendsTable",
}

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def load_schema(path: Path) -> dict:
    with open(path) as f:
        return json.load(f)


def get_item_schema(schema: dict, table_key: str) -> dict | None:
    table_def = schema.get("properties", {}).get(table_key)
    if not table_def:
        return None
    return table_def.get("items", {})


def validate_csv(csv_path: Path, item_schema: dict) -> list[str]:
    """Return list of error strings. Empty list = pass."""
    errors: list[str] = []
    properties = item_schema.get("properties", {})
    required = set(item_schema.get("required", []))
    allowed_cols = set(properties.keys())

    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            return ["  Empty CSV file"]

        csv_cols = set(reader.fieldnames)

        # 1) Missing required columns
        missing = sorted(required - csv_cols)
        if missing:
            errors.append(f"  Missing required columns: {missing}")

        # 2) Unexpected columns
        unexpected = sorted(csv_cols - allowed_cols)
        if unexpected:
            errors.append(f"  Unexpected columns (not in schema): {unexpected}")

        for row_num, row in enumerate(reader, start=2):
            for col in required:
                val = row.get(col, "").strip()
                if not val:
                    errors.append(f"  Row {row_num}, {col}: required field is empty")

            for col, raw in row.items():
                if col not in properties:
                    continue
                val = raw.strip()
                if not val:
                    continue  # optional empty

                col_schema = properties[col]
                col_type = col_schema.get("type", "string")

                # 4a) Integer type check
                if col_type == "integer":
                    try:
                        int(float(val))
                    except (ValueError, TypeError):
                        errors.append(
                            f"  Row {row_num}, {col}: '{val}' is not a valid integer"
                        )
                        continue

                # 4b) Number type check
                elif col_type == "number":
                    try:
                        float(val)
                    except (ValueError, TypeError):
                        errors.append(
                            f"  Row {row_num}, {col}: '{val}' is not a valid number"
                        )
                        continue

                # 4c) Date format check
                if col_schema.get("format") == "date":
                    if not DATE_RE.match(val):
                        errors.append(
                            f"  Row {row_num}, {col}: '{val}' does not match YYYY-MM-DD"
                        )

                # 3) Enum validation
                if "enum" in col_schema:
                    if val not in col_schema["enum"]:
                        errors.append(
                            f"  Row {row_num}, {col}: '{val}' not in {col_schema['enum']}"
                        )

                # 5) Range validation
                if "minimum" in col_schema or "maximum" in col_schema:
                    try:
                        num = float(val)
                    except (ValueError, TypeError):
                        pass
                    else:
                        lo = col_schema.get("minimum")
                        hi = col_schema.get("maximum")
                        if lo is not None and num < lo:
                            errors.append(
                                f"  Row {row_num}, {col}: {num} < minimum {lo}"
                            )
                        if hi is not None and num > hi:
                            errors.append(
                                f"  Row {row_num}, {col}: {num} > maximum {hi}"
                            )

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate Prompt OS v2 sample CSVs against JSON schema"
    )
    parser.add_argument(
        "--csv-dir",
        type=Path,
        default=Path("artifacts/sample_data/prompt_os_v2"),
    )
    parser.add_argument(
        "--schema",
        type=Path,
        default=Path("schemas/prompt_os/prompt_os_schema_v2.json"),
    )
    args = parser.parse_args()

    if not args.schema.exists():
        print(f"ERROR: Schema not found: {args.schema}")
        return 1
    if not args.csv_dir.exists():
        print(f"ERROR: CSV directory not found: {args.csv_dir}")
        return 1

    schema = load_schema(args.schema)
    total_errors = 0
    files_checked = 0
    files_passed = 0

    print("Prompt OS v2 — CSV ↔ Schema Parity Validator")
    print("=" * 50)

    for csv_name, table_key in sorted(CSV_TABLE_MAP.items()):
        csv_path = args.csv_dir / csv_name
        if not csv_path.exists():
            print(f"SKIP  {csv_name} (file not found)")
            continue

        item_schema = get_item_schema(schema, table_key)
        if not item_schema:
            print(f"SKIP  {csv_name} (no schema for {table_key})")
            continue

        errors = validate_csv(csv_path, item_schema)
        files_checked += 1
        row_count = sum(1 for _ in open(csv_path)) - 1

        if errors:
            print(f"FAIL  {csv_name} ({row_count} rows, {len(errors)} errors)")
            for err in errors:
                print(err)
            total_errors += len(errors)
        else:
            print(f"PASS  {csv_name} ({row_count} rows)")
            files_passed += 1

    print("=" * 50)
    print(f"Files: {files_passed}/{files_checked} passed")
    if total_errors:
        print(f"Total errors: {total_errors}")
        return 1
    print("All validations passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
