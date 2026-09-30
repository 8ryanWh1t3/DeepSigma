from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict

from .module import OntologyModule
from .fabric import SemanticFabric
from .diff import diff_modules


def _load_fabric(paths: list[str]) -> SemanticFabric:
    fabric = SemanticFabric()
    for path in paths:
        fabric.register(OntologyModule.load(path))
    return fabric


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="pyontology", description="Deep Sigma modular ontology fabric")
    sub = p.add_subparsers(dest="cmd", required=True)

    inspect_p = sub.add_parser("inspect")
    inspect_p.add_argument("ontology")

    validate_p = sub.add_parser("validate")
    validate_p.add_argument("ontologies", nargs="+")

    collisions_p = sub.add_parser("collisions")
    collisions_p.add_argument("ontologies", nargs="+")

    bridges_p = sub.add_parser("bridges")
    bridges_p.add_argument("ontologies", nargs="+")
    bridges_p.add_argument("--threshold", type=float, default=0.80)

    search_p = sub.add_parser("search")
    search_p.add_argument("query")
    search_p.add_argument("ontologies", nargs="+")

    gate_p = sub.add_parser("gate-create", help="Fail CI when a proposed concept overlaps existing enterprise meaning")
    gate_p.add_argument("--target-module", required=True)
    gate_p.add_argument("--label", required=True)
    gate_p.add_argument("--kind", default="Class")
    gate_p.add_argument("ontologies", nargs="+")

    diff_p = sub.add_parser("diff")
    diff_p.add_argument("old")
    diff_p.add_argument("new")

    args = p.parse_args(argv)

    if args.cmd == "inspect":
        m = OntologyModule.load(args.ontology)
        print(json.dumps({"manifest": m.manifest.to_dict(), "stats": m.stats(), "imports": m.imports()}, indent=2))
        return 0

    if args.cmd == "diff":
        d = diff_modules(OntologyModule.load(args.old), OntologyModule.load(args.new))
        print(json.dumps(asdict(d), indent=2))
        return 0

    fabric = _load_fabric(args.ontologies)
    if args.cmd == "gate-create":
        if args.target_module not in fabric.modules:
            print(json.dumps({"ok": False, "error": f"target module not registered: {args.target_module}"}, indent=2))
            return 2
        proposal = fabric.propose_concept(args.target_module, args.label, args.kind)
        payload = asdict(proposal)
        payload["ok_to_create"] = proposal.recommended_action == "CREATE"
        print(json.dumps(payload, indent=2))
        return 0 if proposal.recommended_action == "CREATE" else 3
    if args.cmd == "validate":
        report = fabric.validate()
        print(json.dumps({"ok": report.ok, "findings": [asdict(f) for f in report.findings]}, indent=2))
        return 0 if report.ok else 2
    if args.cmd == "collisions":
        print(json.dumps([asdict(c) for c in fabric.detect_collisions()], indent=2))
        return 0
    if args.cmd == "bridges":
        print(json.dumps([asdict(b) for b in fabric.discover_bridges(args.threshold)], indent=2))
        return 0
    if args.cmd == "search":
        print(json.dumps([asdict(c) for c in fabric.search(args.query)], indent=2))
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
