"""Command-line analysis. No command publishes authority or performs CERPA APPLY."""
from __future__ import annotations

import argparse
import sys
import sqlite3

from .adapters import vinculum_projection
from .assessment import assess
from .atlas import Atlas
from .editions import EditionStore, compare
from .exports import export_csv, export_jsonl, export_jsonld, export_ntriples, write_json
from .folding import fold
from .navigation import dependencies, impact, trace
from .sample import run_demo
from .util import VERSION, CartographyError, canonical_json


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="sigma-cartography", description="Deep Sigma semantic cartography. Inspection and proposals only.")
    p.add_argument("--version", action="version", version=VERSION)
    commands = p.add_subparsers(dest="command", required=True)
    validate = commands.add_parser("validate", help="Validate canonical atlas JSON")
    validate.add_argument("input")
    for command in ("assess", "trace", "dependencies", "impact", "fold", "export"):
        sub = commands.add_parser(command)
        sub.add_argument("input")
        sub.add_argument("--as-of", required=True, help="ISO 8601 timestamp with timezone")
        sub.add_argument("--scope", action="append", help="Analytical scope filter; NOT access control")
        sub.add_argument("--exclude-inferred", action="store_true")
        if command == "trace":
            sub.add_argument("source")
            sub.add_argument("target")
            sub.add_argument("--direction", choices=("out", "in", "both", "dependencies", "impact"), default="out")
        if command in ("dependencies", "impact"):
            sub.add_argument("start")
        if command in ("trace", "dependencies", "impact"):
            sub.add_argument("--max-depth", type=int)
        if command == "fold":
            sub.add_argument("--by", choices=("layer", "kind", "scope"), default="layer")
        if command == "export":
            sub.add_argument("--format", choices=("json", "jsonl", "csv", "jsonld", "nt", "vinculum", "xlsx"), required=True)
            sub.add_argument("--out", required=True)
        else:
            sub.add_argument("--out")
    diff = commands.add_parser("diff")
    diff.add_argument("before")
    diff.add_argument("after")
    diff.add_argument("--out")
    demo = commands.add_parser("demo")
    demo.add_argument("--out", default="cartography-demo")
    demo.add_argument("--xlsx", action="store_true")
    archive = commands.add_parser("archive")
    archive_commands = archive.add_subparsers(dest="archive_command", required=True)
    init = archive_commands.add_parser("init")
    init.add_argument("database")
    init.add_argument("--atlas-id", required=True)
    append = archive_commands.add_parser("append")
    append.add_argument("database")
    append.add_argument("input")
    append.add_argument("--recorded-at", required=True)
    append.add_argument("--expected-parent", required=True, help="Current head SHA-256, or GENESIS for the first edition")
    show = archive_commands.add_parser("show")
    show.add_argument("database")
    show.add_argument("sequence", type=int)
    verify = archive_commands.add_parser("verify")
    verify.add_argument("database")
    verify.add_argument("--expected-head")
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        result = None
        if args.command == "demo":
            result = run_demo(args.out, xlsx=args.xlsx)
        elif args.command == "archive":
            if args.archive_command == "init":
                with EditionStore.create(args.database, atlas_id=args.atlas_id):
                    result = {"created": args.database, "atlas_id": args.atlas_id}
            else:
                with EditionStore.open(args.database) as store:
                    if args.archive_command == "append":
                        result = store.append(Atlas.load(args.input), recorded_at=args.recorded_at,
                                              expected_parent=None if args.expected_parent == "GENESIS" else args.expected_parent)
                    elif args.archive_command == "show":
                        result = store.get(args.sequence)
                    else:
                        result = {"head_sha256": store.verify(expected_head=args.expected_head), "verified": True,
                                  "authentication": "not_evaluated"}
        elif args.command == "diff":
            result = compare(Atlas.load(args.before), Atlas.load(args.after))
        else:
            atlas = Atlas.load(args.input)
            if args.command == "validate":
                result = {"valid": True, "atlas_id": atlas.id, "sha256": atlas.fingerprint,
                          "nodes": len(atlas.nodes), "edges": len(atlas.edges)}
            else:
                view = atlas.view(as_of=args.as_of, scopes=tuple(args.scope) if args.scope is not None else None,
                                  include_inferred=not args.exclude_inferred)
                if args.command == "assess":
                    result = assess(view)
                elif args.command == "trace":
                    result = trace(view, args.source, args.target, direction=args.direction, max_depth=args.max_depth)
                elif args.command == "dependencies":
                    result = dependencies(view, args.start, max_depth=args.max_depth)
                elif args.command == "impact":
                    result = impact(view, args.start, max_depth=args.max_depth)
                elif args.command == "fold":
                    result = fold(view, by=args.by)
                elif args.command == "export":
                    if args.format == "json":
                        view.atlas.save(args.out)
                    elif args.format == "jsonl":
                        export_jsonl(view.atlas, args.out)
                    elif args.format == "csv":
                        export_csv(view.atlas, args.out)
                    elif args.format == "jsonld":
                        export_jsonld(view, args.out)
                    elif args.format == "nt":
                        export_ntriples(view, args.out)
                    elif args.format == "vinculum":
                        write_json(vinculum_projection(view, assess(view)), args.out)
                    else:
                        from .workbook import export_workbook
                        export_workbook(view, args.out)
                    result = {"exported": args.out, "format": args.format, "view_sha256": view.fingerprint}
        if getattr(args, "out", None) and args.command not in ("demo", "export"):
            write_json(result, args.out)
        else:
            print(canonical_json(result))
        return 0
    except (CartographyError, OSError, ImportError, sqlite3.Error) as exc:
        print(f"sigma-cartography: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
