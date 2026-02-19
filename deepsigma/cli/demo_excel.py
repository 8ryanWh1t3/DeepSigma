"""deepsigma demo excel — run the Excel-first Money Demo."""
from __future__ import annotations

import argparse


def register(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser("demo", help="Run demos")
    demo_sub = p.add_subparsers(dest="demo_command", required=True)

    excel = demo_sub.add_parser("excel", help="Excel-first Money Demo")
    excel.add_argument(
        "--out", default="out/excel_money_demo",
        help="Output directory (default: out/excel_money_demo)",
    )
    excel.set_defaults(func=run_excel)


def run_excel(args: argparse.Namespace) -> int:
    from demos.excel_first.__main__ import main as excel_main

    return excel_main(["--out", args.out])
