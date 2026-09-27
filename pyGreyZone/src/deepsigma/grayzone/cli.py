"""Local file assessment CLI. No network, system access or automated action."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import timedelta
from pathlib import Path

from .engine import assess
from .graph import graph_json, ntriples
from .ingest import load_events
from .lattice import LATTICE_EXAMPLE_MAP
from .report import markdown, write_excel, write_json
from .schema import AssessmentConfig, FieldMap


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="grayzone", description="Review candidate patterns in local event files")
    parser.add_argument("input", help=".json, .jsonl, .ndjson or .csv export")
    parser.add_argument("--lattice", action="store_true", help="use the documented synthetic Lattice-like mapping")
    parser.add_argument("--map", dest="field_map", type=Path, help="JSON file of field-name to dot-path mappings")
    parser.add_argument("--window-days", type=int, default=30)
    parser.add_argument("--json", type=Path, help="assessment JSON output")
    parser.add_argument("--markdown", type=Path, help="report Markdown output")
    parser.add_argument("--excel", type=Path, help="C/E/R/P/A workbook output (optional extra)")
    parser.add_argument("--graph", type=Path, help="graph JSON output")
    parser.add_argument("--rdf", type=Path, help="N-Triples output")
    args = parser.parse_args(argv)
    try:
        base = LATTICE_EXAMPLE_MAP if args.lattice else FieldMap()
        if args.field_map:
            overrides = json.loads(args.field_map.read_text(encoding="utf-8"))
            if not isinstance(overrides, dict):
                raise ValueError("--map must contain a JSON object")
            # Overrides retain the documented defaults for omitted keys.
            base = FieldMap.from_mapping({**vars(base), **overrides})
        events = load_events(args.input, base, default_source="lattice-export" if args.lattice else "unknown")
        result = assess(events, AssessmentConfig(window=timedelta(days=args.window_days)))
        if args.json:
            write_json(result, args.json)
        if args.markdown:
            args.markdown.write_text(markdown(result), encoding="utf-8")
        if args.excel:
            write_excel(result, args.excel)
        if args.graph:
            args.graph.write_text(json.dumps(graph_json(result), indent=2) + "\n", encoding="utf-8")
        if args.rdf:
            args.rdf.write_text(ntriples(result), encoding="utf-8")
        print(f"{result.id}: {len(result.events)} observations, {len(result.links)} links, "
              f"{len(result.hypotheses)} unreviewed candidates")
        if not any((args.json, args.markdown, args.excel, args.graph, args.rdf)):
            print(markdown(result))
        return 0
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"grayzone: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
