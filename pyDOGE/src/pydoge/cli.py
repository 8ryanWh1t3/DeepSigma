from __future__ import annotations

import argparse
import json
from pathlib import Path

from .core import WorkSystem


def _print(obj) -> None:
    print(json.dumps(obj, indent=2, sort_keys=True))


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="pydoge", description="Diagnose work before workforce.")
    sub = p.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("analyze", help="Run full work-system analysis")
    a.add_argument("dataset")

    e = sub.add_parser("explain", help="Explain why a work item exists")
    e.add_argument("dataset")
    e.add_argument("work_id")

    b = sub.add_parser("blast-radius", help="Show downstream work affected by a work item")
    b.add_argument("dataset")
    b.add_argument("work_id")

    m = sub.add_parser("map", help="Emit the normalized work/dependency map")
    m.add_argument("dataset")

    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    ws = WorkSystem.load(Path(args.dataset))
    if args.cmd == "analyze":
        _print(ws.optimize())
    elif args.cmd == "explain":
        _print(ws.explain(args.work_id))
    elif args.cmd == "blast-radius":
        _print(ws.calculate_blast_radius(args.work_id))
    elif args.cmd == "map":
        _print(ws.map_work())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
