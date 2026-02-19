"""deepsigma validate boot <xlsx> — validate BOOT contract."""
from __future__ import annotations

import argparse


def register(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser("validate", help="Validation commands")
    val_sub = p.add_subparsers(dest="validate_command", required=True)

    boot = val_sub.add_parser("boot", help="Validate workbook BOOT contract")
    boot.add_argument("xlsx", help="Path to .xlsx workbook")
    boot.add_argument(
        "--boot-only", action="store_true",
        help="Only validate BOOT sheet (skip table checks)",
    )
    boot.set_defaults(func=run_boot)


def run_boot(args: argparse.Namespace) -> int:
    from tools.validate_workbook_boot import main as boot_main

    cli_args = [args.xlsx]
    if args.boot_only:
        cli_args.append("--boot-only")
    return boot_main(cli_args)
