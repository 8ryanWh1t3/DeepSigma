"""deepsigma mdpt index --csv <file> [--out <dir>] — generate MDPT Prompt Index."""
from __future__ import annotations

import argparse


def register(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser("mdpt", help="MDPT operations")
    mdpt_sub = p.add_subparsers(dest="mdpt_command", required=True)

    idx = mdpt_sub.add_parser("index", help="Generate Prompt Index from CSV export")
    idx.add_argument("--csv", required=True, help="Path to PromptCapabilities CSV export")
    idx.add_argument(
        "--out", default="out/mdpt",
        help="Output directory (default: out/mdpt)",
    )
    idx.add_argument(
        "--include-nonapproved", action="store_true",
        help="Include non-Approved rows (default: Approved only)",
    )
    idx.set_defaults(func=run_index)


def run_index(args: argparse.Namespace) -> int:
    from mdpt.tools.generate_prompt_index import generate

    return generate(args.csv, args.out, args.include_nonapproved)
