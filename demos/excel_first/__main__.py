"""Excel-first Money Demo CLI.

One command. Deterministic Drift→Patch proof — no LLM, no network.

Usage:
    python -m demos.excel_first --out out/excel_money_demo
    excel-demo --out out/excel_money_demo
"""

from __future__ import annotations

import argparse
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="excel-demo",
        description="Excel-first Money Demo — deterministic Drift→Patch proof",
    )
    parser.add_argument(
        "--out",
        default="out/excel_money_demo",
        help="Output directory (default: out/excel_money_demo)",
    )
    args = parser.parse_args(argv)

    from demos.excel_first.pipeline import run_demo

    result = run_demo(args.out)

    print()
    print("=" * 60)
    print("  Excel-first Money Demo — COMPLETE")
    print("=" * 60)
    print(f"  Output:         {result['output_dir']}")
    print(f"  Workbook:       workbook.xlsx")
    print(f"  BOOT valid:     {result['boot_valid']}")
    print(f"  Drift detected: {result['drift_detected']}")
    print(f"  Patch proposed: {result['patch_proposed']}")
    print(f"  Before score:   {result['before_score']:.1f}")
    print(f"  After score:    {result['after_score']:.1f}")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
