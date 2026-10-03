"""New CLI; the legacy `vinculum score` CLI remains unchanged."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
from .codec import CodecEvaluator
from .rdf import from_turtle, to_turtle
from .report import write_csv, write_html, write_json
from .serialization import load_scenario, representation_from_dict, save_scenario
from .utils import primitive, read_json


def main(argv=None):
    parser = argparse.ArgumentParser(prog='vinculum-lattice', description='VINCULUM 0.7.0 — explicit cross-order hinge evaluation')
    parser.add_argument('--version', action='version', version='VINCULUM pyLib 0.7.0')
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('evaluate', help='evaluate a JSON/Turtle scenario; no implicit all-pairs scoring')
    p.add_argument('input')
    p.add_argument('--out-dir')
    p.add_argument('--summary', action='store_true')
    p.add_argument('--strict-exit', action='store_true', help='exit 2 unless fully aligned and gap-free')
    p = sub.add_parser('convert', help='lossless native scenario JSON/Turtle conversion')
    p.add_argument('input')
    p.add_argument('output')
    p = sub.add_parser('monitor', help='read normalized representation JSONL and emit pairing proposals only')
    p.add_argument('input')
    p.add_argument('--max-nodes', type=int, default=10000)
    args = parser.parse_args(argv)
    try:
        if args.command == 'monitor':
            from .monitor import PairingMonitor
            monitor = PairingMonitor(max_nodes=args.max_nodes)
            with Path(args.input).open(encoding='utf-8') as f:
                for lineno, line in enumerate(f, 1):
                    if line.strip():
                        for proposal in monitor.ingest(representation_from_dict(read_json(line))):
                            print(json.dumps({'line': lineno, 'proposal': primitive(proposal)}, ensure_ascii=False))
            return 0
        path = Path(args.input)
        scenario = from_turtle(path.read_text(encoding='utf-8')) if path.suffix.lower() == '.ttl' else load_scenario(path)
        if args.command == 'convert':
            if Path(args.output).suffix.lower() == '.ttl':
                Path(args.output).write_text(to_turtle(scenario), encoding='utf-8')
            else:
                save_scenario(scenario, args.output)
            return 0
        report = scenario.evaluate()
        codecs = tuple(CodecEvaluator(scenario.units).evaluate(scenario.graph, report, t) for t in scenario.transformations)
        if args.out_dir:
            out = Path(args.out_dir)
            out.mkdir(parents=True, exist_ok=True)
            write_json(report, out / 'report.json')
            write_json([c.to_dict() for c in codecs], out / 'codec.json')
            write_html(report, out / 'report.html', context=scenario.graph.context, codec_reports=codecs)
            write_csv(report, out / 'excel_csv')
        print(json.dumps(report.summary if args.summary else report.to_dict(), ensure_ascii=False, indent=2, allow_nan=False))
        return 2 if args.strict_exit and (report.summary['status'] != 'ALIGNED' or report.summary['has_gaps']) else 0
    except (OSError, ValueError, TypeError, KeyError, OverflowError) as exc:
        print(f'vinculum-lattice: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
