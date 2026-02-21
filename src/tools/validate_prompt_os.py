#!/usr/bin/env python3
"""Validate Prompt OS v2 sample CSV data against the JSON schema.

Usage:
    python -m tools.validate_prompt_os
    python -m tools.validate_prompt_os --csv-dir artifacts/sample_data/prompt_os_v2
    python -m tools.validate_prompt_os --schema schemas/prompt_os/prompt_os_schema_v2.json
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

# Map CSV filenames to their schema table key
CSV_TABLE_MAP = {
    "decision_log.csv": "DecisionLogTable",
    "atomic_claims.csv": "AtomicClaimsTable",
    "assumptions.csv": "AssumptionsTable",
    "prompt_library.csv": "PromptLibraryTable",
    "patch_log.csv": "PatchLogTable",
    "llm_output.csv": "LLMOutputTable",
    "dashboard_trends.csv": "DashboardTrendsTable",
}

# Schema type → Python coercion for validation
TYPE_COERCERS = {
    "string": str,
    "integer": int,
    "number": float,
}


def load_schema(schema_path: Path) -> dict:
    with open(schema_path) as f:
        return json.load(f)


def get_table_schema(schema: dict, table_key: str) -> dict | None:
    table_def = schema.get("properties", {}).get(table_key)
    if not table_def:
        return None
    return table_def.get("items", {})


def validate_enum(value: str, allowed: list[str], col: str, row_num: int) -> str | None:
    if value and value not in allowed:
        return f"  Row {row_num}, {col}: '{value}' not in enum {allowed}"
    return None


def validate_type(value: str, expected_type: str, col: str, row_num: int) -> str | None:
    if not value:
        return None  # empty values handled by required check
    if expected_type == "integer":
        try:
            int(float(value))  # handle "42.0" from Excel
        except (ValueError, TypeError):
            return f"  Row {row_num}, {col}: '{value}' is not a valid integer"
    elif expected_type == "number":
        try:
            float(value)
        except (ValueError, TypeError):
            return f"  Row {row_num}, {col}: '{value}' is not a valid number"
    return None


def validate_range(
    value: str, minimum: float | None, maximum: float | None, col: str, row_num: int
) -> str | None:
    if not value:
        return None
    try:
        num = float(value)
    except (ValueError, TypeError):
        return None  # type check handles this
    if minimum is not None and num < minimum:
        return f"  Row {row_num}, {col}: {num} < minimum {minimum}"
    if maximum is not None and num > maximum:
        return f"  Row {row_num}, {col}: {num} > maximum {maximum}"
    return None


def validate_csv(csv_path: Path, item_schema: dict) -> list[str]:
    errors = []
    properties = item_schema.get("properties", {})
    required = set(item_schema.get("required", []))

    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            return [f"  Empty CSV file: {csv_path.name}"]

        # Check for missing required columns
        csv_cols = set(reader.fieldnames)
        missing_cols = required - csv_cols
        if missing_cols:
            errors.append(f"  Missing required columns: {sorted(missing_cols)}")

        for row_num, row in enumerate(reader, start=2):
            # Check required fields have values
            for req_col in required:
                if req_col in row and not row[req_col].strip():
                    errors.append(f"  Row {row_num}, {req_col}: required field is empty")

            # Validate each column against schema
            for col, value in row.items():
                if col not in properties:
                    continue
                col_schema = properties[col]
                col_type = col_schema.get("type", "string")

                # Type validation
                err = validate_type(value, col_type, col, row_num)
                if err:
                    errors.append(err)

                # Enum validation
                if "enum" in col_schema:
                    err = validate_enum(value, col_schema["enum"], col, row_num)
                    if err:
                        errors.append(err)

                # Range validation
                if "minimum" in col_schema or "maximum" in col_schema:
                    err = validate_range(
                        value,
                        col_schema.get("minimum"),
                        col_schema.get("maximum"),
                        col,
                        row_num,
                    )
                    if err:
                        errors.append(err)

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Prompt OS v2 CSV data against schema")
    parser.add_argument(
        "--csv-dir",
        type=Path,
        default=Path("artifacts/sample_data/prompt_os_v2"),
        help="Directory containing CSV files (default: artifacts/sample_data/prompt_os_v2)",
    )
    parser.add_argument(
        "--schema",
        type=Path,
        default=Path("schemas/prompt_os/prompt_os_schema_v2.json"),
        help="Path to JSON schema (default: schemas/prompt_os/prompt_os_schema_v2.json)",
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

    for csv_name, table_key in CSV_TABLE_MAP.items():
        csv_path = args.csv_dir / csv_name
        if not csv_path.exists():
            print(f"SKIP: {csv_name} (not found)")
            continue

        item_schema = get_table_schema(schema, table_key)
        if not item_schema:
            print(f"SKIP: {csv_name} (no schema for {table_key})")
            continue

        errors = validate_csv(csv_path, item_schema)
        files_checked += 1

        if errors:
            print(f"FAIL: {csv_name} ({len(errors)} errors)")
            for err in errors:
                print(err)
            total_errors += len(errors)
        else:
            row_count = sum(1 for _ in open(csv_path)) - 1
            print(f"PASS: {csv_name} ({row_count} rows)")

    print(f"\n{'='*40}")
    print(f"Files checked: {files_checked}/{len(CSV_TABLE_MAP)}")
    if total_errors:
        print(f"Total errors: {total_errors}")
        return 1
    print("All validations passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
