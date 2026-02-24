#!/usr/bin/env python3
"""Deterministic input ordering for CSV files and file lists.

Ensures that the same set of input files and rows always produce the same
canonical representation, regardless of OS-level ordering.
"""
from __future__ import annotations

import csv
from pathlib import Path

# Primary key columns for known CSV types
PRIMARY_KEYS: dict[str, str] = {
    "decision_log": "DecisionID",
    "decision": "Decision_ID",
    "claims": "Claim_ID",
    "claim": "Claim_ID",
    "assumptions": "Assumption_ID",
    "assumption": "Assumption_ID",
    "patches": "Patch_ID",
    "patch": "Patch_ID",
    "patch_log": "Patch_ID",
    "runs": "Run_ID",
    "run": "Run_ID",
    "llm_output": "RunID",
    "telemetry": "EventID",
    "telemetry_events": "EventID",
}


def _normalize_cell(value: str) -> str:
    """Normalize a single CSV cell: strip whitespace, normalize empty strings."""
    if value is None:
        return ""
    return value.strip()


def _normalize_row(row: dict[str, str]) -> dict[str, str]:
    """Normalize all cells in a row."""
    return {k.strip(): _normalize_cell(v) for k, v in row.items()}


def _row_sort_key(row: dict[str, str]) -> str:
    """Full-row canonical string for sorting when no primary key is available."""
    from canonical_json import canonical_dumps

    return canonical_dumps(row)


def read_csv_deterministic(path: Path) -> list[dict[str, str]]:
    """Read a CSV file and return rows in deterministic order.

    Rows are normalized (stripped whitespace, normalized line endings)
    and sorted by primary key if known, otherwise by full-row canonical string.
    """
    with open(path, newline="", encoding="utf-8") as f:
        content = f.read()

    # Normalize line endings
    content = content.replace("\r\n", "\n").replace("\r", "\n")

    rows = list(csv.DictReader(content.splitlines()))
    rows = [_normalize_row(r) for r in rows]

    if not rows:
        return rows

    # Detect primary key from filename
    stem = path.stem.lower()
    pk_col = PRIMARY_KEYS.get(stem)

    # Also check if a known PK column exists in headers
    if pk_col is None:
        headers = set(rows[0].keys())
        for _name, col in PRIMARY_KEYS.items():
            if col in headers:
                pk_col = col
                break

    if pk_col and pk_col in rows[0]:
        rows.sort(key=lambda r: r.get(pk_col, ""))
    else:
        rows.sort(key=_row_sort_key)

    return rows


def list_files_deterministic(directory: Path, glob_pattern: str = "*") -> list[Path]:
    """List files in a directory in deterministic (lexicographic) order."""
    if not directory.exists():
        return []
    return sorted(p for p in directory.glob(glob_pattern) if p.is_file())
