"""deepsigma golden-path — preserved 7-step governance loop.

Delegates to the existing tools.golden_path_cli module to preserve
backward compatibility.
"""
from __future__ import annotations

import argparse


def register(subparsers: argparse._SubParsersAction) -> None:
    gp = subparsers.add_parser(
        "golden-path",
        help="Run the 7-step Golden Path decision governance loop",
    )
    gp.add_argument(
        "source",
        choices=["sharepoint", "snowflake", "dataverse", "asksage"],
        help="Data source connector",
    )
    gp.add_argument("--fixture", default=None, help="Path to fixture directory (offline mode)")
    gp.add_argument("--output", "--out", default="./golden_path_output", help="Output directory")
    gp.add_argument("--clean", action="store_true", help="Wipe output directory before running")
    gp.add_argument("--verbose", action="store_true", help="Print extra diagnostic output")
    gp.add_argument("--json", action="store_true", help="Output JSON result instead of table")
    gp.add_argument("--episode-id", default="gp-demo", help="Episode ID")
    gp.add_argument("--decision-type", default="ingest", help="Decision type")
    gp.add_argument("--supervised", action="store_true", help="Pause before patch step")
    gp.add_argument("--list-id", default="", help="SharePoint list ID")
    gp.add_argument("--site-id", default="", help="SharePoint site ID")
    gp.add_argument("--table", default="", help="Dataverse table name")
    gp.add_argument("--sql", default="", help="Snowflake SQL query")
    gp.add_argument("--prompt", default="", help="AskSage prompt")
    gp.set_defaults(func=run)


def run(args: argparse.Namespace) -> int:
    from tools.golden_path_cli import _run_golden_path

    return _run_golden_path(args)
