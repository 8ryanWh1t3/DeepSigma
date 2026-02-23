#!/usr/bin/env python3
"""Export authority ledger to shareable JSON or NDJSON artifacts."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from deepsigma.security.authority_ledger import export_authority_ledger, load_authority_ledger  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Export authority ledger artifact")
    parser.add_argument(
        "--ledger-path",
        default="data/security/authority_ledger.json",
        help="Path to authority ledger JSON",
    )
    parser.add_argument(
        "--out",
        default="artifacts/security/authority_ledger_export.json",
        help="Destination path",
    )
    parser.add_argument(
        "--format",
        default="json",
        choices=["json", "ndjson"],
        help="Export format",
    )
    args = parser.parse_args()

    ledger_path = (ROOT / args.ledger_path).resolve()
    out_path = (ROOT / args.out).resolve()
    destination = export_authority_ledger(
        ledger_path=ledger_path,
        out_path=out_path,
        export_format=args.format,
    )
    print(f"Exported {len(load_authority_ledger(ledger_path))} entries to {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
