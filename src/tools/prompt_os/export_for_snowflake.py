#!/usr/bin/env python3
"""Export Prompt OS v2 CSVs as a Snowflake-ready bundle.

Reads all CSVs from artifacts/sample_data/prompt_os_v2/ and produces a
timestamped export bundle with uppercased table names, a MANIFEST.json,
and any sealed run JSONs.

Usage:
    python src/tools/prompt_os/export_for_snowflake.py
    python src/tools/prompt_os/export_for_snowflake.py --data-dir artifacts/sample_data/prompt_os_v2
"""
from __future__ import annotations

import argparse
import csv
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_DATA_DIR = Path("artifacts/sample_data/prompt_os_v2")
DEFAULT_SEALED_DIR = Path("artifacts/sealed_runs")
DEFAULT_EXPORT_ROOT = Path("artifacts/snowflake_exports")

# Map source CSV → Snowflake table name
TABLE_MAP = {
    "decision_log.csv": "PROMPT_OS_DECISION_LOG.csv",
    "atomic_claims.csv": "PROMPT_OS_ATOMIC_CLAIMS.csv",
    "assumptions.csv": "PROMPT_OS_ASSUMPTIONS.csv",
    "patch_log.csv": "PROMPT_OS_PATCH_LOG.csv",
    "prompt_library.csv": "PROMPT_OS_PROMPT_LIBRARY.csv",
    "llm_output.csv": "PROMPT_OS_LLM_OUTPUT.csv",
    "dashboard_trends.csv": "PROMPT_OS_DASHBOARD_TRENDS.csv",
}


def count_csv_rows(path: Path) -> int:
    """Count data rows in a CSV file (excluding header)."""
    with open(path, newline="") as f:
        reader = csv.reader(f)
        next(reader, None)  # skip header
        return sum(1 for _ in reader)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Export Prompt OS CSVs as a Snowflake-ready bundle"
    )
    parser.add_argument(
        "--data-dir", type=Path, default=DEFAULT_DATA_DIR,
        help="Directory containing prompt_os_v2 CSVs",
    )
    parser.add_argument(
        "--sealed-dir", type=Path, default=DEFAULT_SEALED_DIR,
        help="Directory containing sealed run JSONs",
    )
    parser.add_argument(
        "--export-root", type=Path, default=DEFAULT_EXPORT_ROOT,
        help="Root directory for exports",
    )
    args = parser.parse_args()

    data_dir: Path = args.data_dir
    sealed_dir: Path = args.sealed_dir
    export_root: Path = args.export_root

    if not data_dir.exists():
        print(f"ERROR: Data directory not found: {data_dir}", file=sys.stderr)
        return 1

    # Create timestamped export folder
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    export_dir = export_root / f"prompt_os_export_{ts}"
    export_dir.mkdir(parents=True, exist_ok=True)

    manifest_files: list[dict] = []
    total_rows = 0

    # Copy and rename CSVs
    for src_name, dest_name in TABLE_MAP.items():
        src_path = data_dir / src_name
        if not src_path.exists():
            print(f"  SKIP: {src_name} (not found)")
            continue
        dest_path = export_dir / dest_name
        shutil.copy2(src_path, dest_path)
        rows = count_csv_rows(dest_path)
        total_rows += rows
        manifest_files.append({
            "file": dest_name,
            "source": src_name,
            "rows": rows,
        })

    # Copy sealed runs if any exist
    sealed_count = 0
    if sealed_dir.exists():
        json_files = list(sealed_dir.glob("*.json"))
        if json_files:
            sealed_dest = export_dir / "SEALED_RUNS"
            sealed_dest.mkdir(exist_ok=True)
            for jf in json_files:
                shutil.copy2(jf, sealed_dest / jf.name)
                sealed_count += 1
            manifest_files.append({
                "file": "SEALED_RUNS/",
                "source": str(sealed_dir),
                "rows": sealed_count,
            })

    # Write manifest
    manifest = {
        "schema_version": "1.0",
        "export_timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source_dir": str(data_dir),
        "files": manifest_files,
        "total_csv_rows": total_rows,
        "sealed_run_count": sealed_count,
    }
    manifest_path = export_dir / "MANIFEST.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    # Print summary
    print("=" * 50)
    print("  Snowflake Export Bundle")
    print("=" * 50)
    print(f"  Export folder: {export_dir}")
    print()
    for entry in manifest_files:
        label = entry["file"]
        rows = entry["rows"]
        unit = "files" if label.endswith("/") else "rows"
        print(f"    {label:<40s} {rows:>5d} {unit}")
    print(f"  {'─' * 48}")
    print(f"    {'Total CSV rows':<40s} {total_rows:>5d}")
    print(f"    {'Sealed runs':<40s} {sealed_count:>5d}")
    print("=" * 50)

    return 0


if __name__ == "__main__":
    sys.exit(main())
