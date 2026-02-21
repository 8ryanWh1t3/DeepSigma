#!/usr/bin/env python3
"""Export a single sealed run from LLM_OUTPUT CSV to JSON.

Reads sample_data/prompt_os_v2/llm_output.csv (by default) and exports
the specified RunID as an immutable JSON snapshot.

Usage:
    python scripts/prompt_os/export_sealed_run.py --run-id RUN-001
    python scripts/prompt_os/export_sealed_run.py --run-id RUN-001 --out artifacts/sealed_runs/custom.json
    python scripts/prompt_os/export_sealed_run.py --run-id RUN-001 --csv sample_data/prompt_os_v2/llm_output.csv
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


def parse_semicolon_list(raw: str) -> list[str]:
    """Split '1) Foo; 2) Bar; 3) Baz' into ['Foo', 'Bar', 'Baz']."""
    if not raw:
        return []
    parts = re.split(r";\s*", raw)
    cleaned = []
    for part in parts:
        # Strip leading numbering like "1) " or "2. "
        part = re.sub(r"^\d+[).]\s*", "", part).strip()
        if part:
            cleaned.append(part)
    return cleaned


def find_run(csv_path: Path, run_id: str) -> dict | None:
    """Find a row by RunID in the LLM output CSV."""
    with open(csv_path, newline="") as f:
        for row in csv.DictReader(f):
            if row.get("RunID") == run_id:
                return row
    return None


def build_sealed_run(row: dict) -> dict:
    """Build the sealed run JSON structure from a CSV row."""
    now = datetime.now(timezone.utc)

    sealed = {
        "schema_version": "1.0",
        "meta": {
            "run_id": row["RunID"],
            "session_date": row["SessionDate"],
            "operator": row.get("Operator", ""),
            "model": row.get("Model", ""),
            "workbook_version": "v2",
            "export_timestamp": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        },
        "top_risks": parse_semicolon_list(row.get("TopRisks", "")),
        "top_actions": parse_semicolon_list(row.get("TopActions", "")),
        "system_observations": [],
        "suggested_updates": parse_semicolon_list(row.get("SuggestedUpdates", "")),
        "kpis": {
            "summary_confidence_pct": int(row.get("SummaryConfidence_pct", 0)),
            "next_review_date": row.get("NextReviewDate", ""),
        },
        "hash": "",
    }

    # Compute hash over content (with hash field as empty string)
    canonical = json.dumps(sealed, sort_keys=True)
    sealed["hash"] = "sha256:" + hashlib.sha256(canonical.encode()).hexdigest()

    return sealed


def default_output_path(run_id: str) -> Path:
    """Generate default output path per naming convention."""
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return Path(f"artifacts/sealed_runs/{run_id}_{ts}.json")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Export a sealed run from LLM_OUTPUT CSV to JSON"
    )
    parser.add_argument(
        "--run-id",
        required=True,
        help="RunID to export (e.g. RUN-001)",
    )
    parser.add_argument(
        "--csv",
        type=Path,
        default=Path("sample_data/prompt_os_v2/llm_output.csv"),
        help="Path to LLM output CSV",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Output JSON path (default: artifacts/sealed_runs/<RunID>_<timestamp>.json)",
    )
    args = parser.parse_args()

    if not args.csv.exists():
        print(f"ERROR: CSV not found: {args.csv}")
        return 1

    row = find_run(args.csv, args.run_id)
    if not row:
        print(f"ERROR: RunID '{args.run_id}' not found in {args.csv}")
        return 1

    sealed = build_sealed_run(row)

    out_path = args.out or default_output_path(args.run_id)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with open(out_path, "w") as f:
        json.dump(sealed, f, indent=2)

    print(f"Sealed run exported: {out_path}")
    print(f"  RunID:      {sealed['meta']['run_id']}")
    print(f"  Session:    {sealed['meta']['session_date']}")
    print(f"  Operator:   {sealed['meta']['operator']}")
    print(f"  Model:      {sealed['meta']['model']}")
    print(f"  Confidence: {sealed['kpis']['summary_confidence_pct']}%")
    print(f"  Hash:       {sealed['hash']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
