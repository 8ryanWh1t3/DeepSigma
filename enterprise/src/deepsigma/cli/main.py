#!/usr/bin/env python3
"""DeepSigma unified CLI — product entrypoint.

Commands:
    deepsigma init <project-name>            Scaffold a 5-minute starter project
    deepsigma doctor                          Environment health check
    deepsigma demo excel [--out DIR]          Excel-first Money Demo
    deepsigma retention sweep --tenant <id>   TTL retention sweep + compaction
    deepsigma new-connector <name>           Scaffold ConnectorV1 plugin
    deepsigma validate boot <xlsx>            BOOT contract validation
    deepsigma mdpt index --csv <file>         Generate MDPT Prompt Index
    deepsigma golden-path <source> [opts]     7-step Golden Path loop
    deepsigma compact --input <dir>           Compact JSONL evidence files
    deepsigma rekey --tenant <id>             Rekey encrypted evidence at rest
    deepsigma security rotate-keys ...        Rotate key versions with audit events
    deepsigma security reencrypt ...          Re-encrypt with checkpoint/resume
    deepsigma compliance export --tenant ...  Export SOC 2 evidence package
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


def _get_version() -> str:
    try:
        from core import __version__
        return __version__
    except ImportError:
        return "unknown"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="deepsigma",
        description="Sigma OVERWATCH — Institutional Decision Infrastructure CLI",
    )
    parser.add_argument(
        "--version", action="version",
        version=f"%(prog)s {_get_version()}",
    )
    subparsers = parser.add_subparsers(dest="command")

    from deepsigma.cli import (
        compliance_export,
        compact,
        demo_excel,
        doctor,
        golden_path,
        init_project,
        mdpt_index,
        security,
        retention,
        rekey,
        new_connector,
        validate_boot,
    )

    init_project.register(subparsers)
    doctor.register(subparsers)
    demo_excel.register(subparsers)
    validate_boot.register(subparsers)
    mdpt_index.register(subparsers)
    retention.register(subparsers)
    golden_path.register(subparsers)
    compact.register(subparsers)
    rekey.register(subparsers)
    security.register(subparsers)
    compliance_export.register(subparsers)
    new_connector.register(subparsers)

    from deepsigma.jrm_ext import cli as jrm_ext_cli
    jrm_ext_cli.register(subparsers)

    args = parser.parse_args(argv)

    if not hasattr(args, "func") or args.func is None:
        parser.print_help()
        return 0

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
