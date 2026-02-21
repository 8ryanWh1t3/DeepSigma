#!/usr/bin/env python3
"""Mermaid diagram drift guardrail.

Ensures docs/mermaid/ contains only the 5 canonical diagrams + README.
Fails (exit 1) if new diagrams have been added outside the archive.

Usage:
    python src/tools/mermaid_audit.py
    python -m tools.mermaid_audit
"""

from __future__ import annotations

import pathlib
import re
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
MERMAID_DIR = REPO_ROOT / "docs" / "mermaid"
ARCHIVE_DIR = REPO_ROOT / "docs" / "archive" / "mermaid"

CANONICAL = {
    "README.md",
    "01-system-architecture.md",
    "05-drift-to-patch.md",
    "06-coherence-ops-pipeline.md",
    "10-integration-map.md",
    "11-seal-and-prove.md",
}

MAX_CANONICAL = 5  # diagrams (excludes README)

MERMAID_BLOCK_RE = re.compile(r"^```mermaid", re.MULTILINE)


def _count_embedded(root: pathlib.Path) -> tuple[int, list[tuple[str, int]]]:
    """Count ```mermaid blocks in all .md files under *root*, excluding archive."""
    total = 0
    details: list[tuple[str, int]] = []
    for md in sorted(root.rglob("*.md")):
        rel = md.relative_to(root)
        if "archive" in rel.parts or "node_modules" in rel.parts:
            continue
        count = len(MERMAID_BLOCK_RE.findall(md.read_text(encoding="utf-8", errors="replace")))
        if count:
            total += count
            details.append((str(rel), count))
    return total, details


def main() -> int:
    errors: list[str] = []

    # --- Check docs/mermaid/ contents ---
    if not MERMAID_DIR.is_dir():
        errors.append(f"Missing directory: {MERMAID_DIR.relative_to(REPO_ROOT)}")
    else:
        actual = {f.name for f in MERMAID_DIR.iterdir() if f.is_file()}
        unexpected = actual - CANONICAL
        if unexpected:
            errors.append(
                f"Unexpected files in docs/mermaid/ (archive or remove): {sorted(unexpected)}"
            )
        missing = CANONICAL - actual
        if missing:
            errors.append(f"Missing canonical files: {sorted(missing)}")

    # --- Count standalone .mmd files outside archive ---
    mmd_files = []
    for ext in ("*.mmd", "*.mermaid"):
        for f in sorted(REPO_ROOT.rglob(ext)):
            rel = f.relative_to(REPO_ROOT)
            if "archive" not in rel.parts and "node_modules" not in rel.parts:
                mmd_files.append(str(rel))

    # --- Count embedded blocks ---
    embedded_total, embedded_details = _count_embedded(REPO_ROOT)

    # --- Report ---
    print("=== Mermaid Audit ===")
    print(f"Canonical diagrams: {len(CANONICAL) - 1}/{MAX_CANONICAL}")
    print(f"Standalone .mmd files (outside archive): {len(mmd_files)}")
    print(f"Embedded mermaid blocks (outside archive): {embedded_total}")
    if ARCHIVE_DIR.is_dir():
        archived = len(list(ARCHIVE_DIR.iterdir()))
        print(f"Archived diagrams: {archived}")
    print()

    if errors:
        print("ERRORS:")
        for e in errors:
            print(f"  - {e}")
        print()
        print("To fix: move new diagrams to docs/archive/mermaid/ or update CANONICAL set.")
        return 1

    print("PASS — diagram set is canonical.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
