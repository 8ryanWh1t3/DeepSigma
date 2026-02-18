#!/usr/bin/env python3
"""Coherence Ops CLI — governance framework entrypoint.

This CLI is intended as a practical control surface around the core
coherence pipeline:

- Decision Log Record (DLR)
- Reflection Session (RS)
- Drift Signals (DS)
- Memory Graph (MG)

Commands:
  coherence audit <path>
  coherence score <path> [--json]
  coherence mg export <path> [--format json]
  coherence iris query --type WHY|STATUS ... <path> [--json]

Usage:
  python -m coherence_ops.cli score ./episodes
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
import sys
from pathlib import Path
from typing import Any, Dict, List

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from coherence_ops import (  # noqa: E402
    CoherenceAuditor,
    CoherenceManifest,
    CoherenceScorer,
    DLRBuilder,
    DriftSignalCollector,
    MemoryGraph,
    ReflectionSession,
)
from coherence_ops.iris import (  # noqa: E402
    IRISConfig,
    IRISEngine,
    IRISQuery,
    QueryType,
)
from coherence_ops.manifest import ArtifactDeclaration, ArtifactKind, ComplianceLevel  # noqa: E402


def _load_json_like(text: str) -> List[Dict[str, Any]]:
    data = json.loads(text)
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return [data]
    raise ValueError("Expected JSON object or list")


def _load_episodes(path: str) -> List[Dict[str, Any]]:
    p = Path(path)
    if p.is_file():
        return _load_json_like(p.read_text())
    if p.is_dir():
        episodes: List[Dict[str, Any]] = []
        for f in sorted(p.glob("*.json")):
            episodes.extend(_load_json_like(f.read_text()))
        return episodes

    print(f"Error: {path} is not a file or directory", file=sys.stderr)
    sys.exit(1)


def _load_drift(path: str) -> List[Dict[str, Any]]:
    p = Path(path)
    drift_file: Path | None = None

    if p.is_file() and "drift" in p.name:
        drift_file = p
    elif p.is_dir():
        candidates = list(p.glob("*drift*.json"))
        if candidates:
            drift_file = candidates[0]

    if drift_file and drift_file.exists():
        return _load_json_like(drift_file.read_text())

    return []


def _build_pipeline(
    episodes: List[Dict[str, Any]], drift_events: List[Dict[str, Any]]
):
    dlr = DLRBuilder()
    dlr.from_episodes(episodes)

    rs = ReflectionSession("cli")
    rs.ingest(episodes)

    ds = DriftSignalCollector()
    if drift_events:
        ds.ingest(drift_events)

    mg = MemoryGraph()
    for ep in episodes:
        mg.add_episode(ep)
    for d in drift_events:
        mg.add_drift(d)

    return dlr, rs, ds, mg


def _build_manifest() -> CoherenceManifest:
    manifest = CoherenceManifest(system_id="coherence-cli", version="0.1.0")
    for kind in ArtifactKind:
        manifest.declare(
            ArtifactDeclaration(
                kind=kind,
                schema_version="1.0.0",
                compliance=ComplianceLevel.FULL,
                source="coherence_ops.cli",
            )
        )
    return manifest


def cmd_audit(args: argparse.Namespace) -> None:
    episodes = _load_episodes(args.path)
    drift_events = _load_drift(args.path)
    dlr, rs, ds, mg = _build_pipeline(episodes, drift_events)

    manifest = _build_manifest()
    auditor = CoherenceAuditor(
        manifest=manifest,
        dlr_builder=dlr,
        rs=rs,
        ds=ds,
        mg=mg,
    )
    report = auditor.run(run_id="cli-audit")

    print(f"Coherence Audit | system: {report.manifest_system_id}")
    print(f"Result: {'PASSED' if report.passed else 'FAILED'}")
    print(f"Findings: {report.summary}")
    print()


def cmd_score(args: argparse.Namespace) -> None:
    episodes = _load_episodes(args.path)
    drift_events = _load_drift(args.path)
    dlr, rs, ds, mg = _build_pipeline(episodes, drift_events)

    scorer = CoherenceScorer(dlr_builder=dlr, rs=rs, ds=ds, mg=mg)
    report = scorer.score()

    if getattr(args, "json", False):
        print(json.dumps(asdict(report), indent=2))
        return

    print(f"Coherence Score: {report.overall_score}/100  Grade: {report.grade}")
    print()



def cmd_mg_export(args: argparse.Namespace) -> None:
    episodes = _load_episodes(args.path)
    drift_events = _load_drift(args.path)
    _, _, _, mg = _build_pipeline(episodes, drift_events)

    fmt = args.format

    if fmt == "json":
        print(mg.to_json(indent=2))
        return

    print(f"Export format '{fmt}' not implemented in this CLI build.", file=sys.stderr)
    sys.exit(2)


_IRIS_QUERY_TYPE_MAP = {
    "WHY": QueryType.WHY,
    "WHAT_CHANGED": QueryType.WHAT_CHANGED,
    "WHAT_DRIFTED": QueryType.WHAT_DRIFTED,
    "RECALL": QueryType.RECALL,
    "STATUS": QueryType.STATUS,
}


def cmd_iris_query(args: argparse.Namespace) -> None:
    episodes = _load_episodes(args.path)
    drift_events = _load_drift(args.path)
    dlr, rs, ds, mg = _build_pipeline(episodes, drift_events)

    engine = IRISEngine(
        config=IRISConfig(),
        memory_graph=mg,
        dlr_entries=dlr.entries,
        rs=rs,
        ds=ds,
    )

    qtype = _IRIS_QUERY_TYPE_MAP.get(args.type.upper())
    if qtype is None:
        valid = ", ".join(sorted(_IRIS_QUERY_TYPE_MAP))
        print(f"Unknown query type '{args.type}'. Valid types: {valid}", file=sys.stderr)
        sys.exit(1)

    if qtype in (QueryType.WHY, QueryType.RECALL) and not args.target:
        print("--target is required for WHY and RECALL queries", file=sys.stderr)
        sys.exit(1)

    query = IRISQuery(
        query_type=qtype,
        episode_id=args.target or "",
        text=args.text or "",
    )

    response = engine.resolve(query)

    if getattr(args, "json", False):
        print(json.dumps(response.to_dict(), indent=2))
        return

    print(response.summary)


def cmd_demo(args: argparse.Namespace) -> None:  # noqa: ARG001
    parser = argparse.ArgumentParser(
        prog="coherence demo",
        description="Demo: score and IRIS status query",
    )
    parser.add_argument("path", help="Path to episodes file or directory")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    parsed = parser.parse_args(args.remaining or [])

    score_args = argparse.Namespace(path=parsed.path, json=parsed.json)
    cmd_score(score_args)



def main() -> None:
    parser = argparse.ArgumentParser(
        prog="coherence",
        description="Coherence Ops CLI",
    )
    parser.set_defaults(func=None)
    subparsers = parser.add_subparsers(dest="command", required=False)

    p_audit = subparsers.add_parser("audit", help="Run coherence audit")
    p_audit.add_argument("path", help="Path to episodes file or directory")
    p_audit.set_defaults(func=cmd_audit)

    p_score = subparsers.add_parser("score", help="Compute coherence score")
    p_score.add_argument("path", help="Path to episodes file or directory")
    p_score.add_argument("--json", action="store_true", help="Output JSON")
    p_score.set_defaults(func=cmd_score)

    p_mg = subparsers.add_parser("mg", help="Memory Graph operations")
    mg_sub = p_mg.add_subparsers(dest="mg_command", required=True)

    p_export = mg_sub.add_parser("export", help="Export Memory Graph")
    p_export.add_argument("path", help="Path to episodes file or directory")
    p_export.add_argument(
        "--format",
        default="json",
        choices=["json"],
        help="Export format",
    )
    p_export.set_defaults(func=cmd_mg_export)

    p_iris = subparsers.add_parser("iris", help="IRIS operator query resolution")
    iris_sub = p_iris.add_subparsers(dest="iris_command", required=True)

    p_iris_query = iris_sub.add_parser(
        "query",
        help="Resolve an IRIS operator query",
    )
    p_iris_query.add_argument("path", help="Path to episodes file or directory")
    p_iris_query.add_argument(
        "--type",
        "-t",
        required=True,
        metavar="QUERY_TYPE",
        choices=list(_IRIS_QUERY_TYPE_MAP.keys()),
    )
    p_iris_query.add_argument(
        "--target",
        default="",
        metavar="EPISODE_ID",
    )
    p_iris_query.add_argument(
        "--text",
        default="",
        metavar="QUERY_TEXT",
    )
    p_iris_query.add_argument(
        "--limit",
        default=20,
        type=int,
    )
    p_iris_query.add_argument(
        "--json",
        action="store_true",
    )
    p_iris_query.set_defaults(func=cmd_iris_query)

    p_demo = subparsers.add_parser(
        "demo",
        help="Demo: coherence score",
    )
    p_demo.set_defaults(func=cmd_demo)
    p_demo.add_argument("remaining", nargs=argparse.REMAINDER)

    args = parser.parse_args()

    if args.func is None:
        parser.print_help()
        sys.exit(0)

    args.func(args)


if __name__ == "__main__":
    main()
