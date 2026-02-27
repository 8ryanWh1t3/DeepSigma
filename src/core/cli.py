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
  python -m core.cli score ./episodes
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
import sys
from pathlib import Path
from typing import Any, Dict, List

from core import __version__
from . import (
    CoherenceAuditor,
    CoherenceManifest,
    CoherenceScorer,
    DLRBuilder,
    DriftSignalCollector,
    MemoryGraph,
    ReflectionSession,
)
from .iris import (
    IRISConfig,
    IRISEngine,
    IRISQuery,
    QueryType,
)
from .manifest import ArtifactDeclaration, ArtifactKind, ComplianceLevel
from .normalize import normalize_keys


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
        return normalize_keys(_load_json_like(p.read_text()))
    if p.is_dir():
        episodes: List[Dict[str, Any]] = []
        for f in sorted(p.glob("*.json")):
            episodes.extend(_load_json_like(f.read_text()))
        return normalize_keys(episodes)

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
        return normalize_keys(_load_json_like(drift_file.read_text()))

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
                source="core.cli",
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
    report = auditor.run(audit_id="cli-audit")

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


def cmd_reconcile(args: argparse.Namespace) -> None:
    episodes = _load_episodes(args.path)
    drift_events = _load_drift(args.path)
    dlr, _rs, ds, mg = _build_pipeline(episodes, drift_events)

    from .reconciler import Reconciler
    reconciler = Reconciler(dlr_builder=dlr, ds=ds, mg=mg)
    result = reconciler.reconcile()

    if getattr(args, "auto_fix", False):
        reconciler.apply_auto_fixes()
        result = reconciler.reconcile()  # re-run after fixes

    if getattr(args, "json", False):
        print(json.dumps(asdict(result), indent=2, default=str))
        return

    print(f"Reconciliation | {len(result.proposals)} proposal(s)")
    print(f"  Auto-fixable: {result.auto_fixable_count}")
    print(f"  Manual:       {result.manual_count}")
    for p in result.proposals:
        fix = " [auto-fixable]" if p.auto_fixable else ""
        print(f"  - [{p.kind.value}] {p.description}{fix}")
    print()


def cmd_schema_validate(args: argparse.Namespace) -> None:
    p = Path(args.file)
    if not p.exists():
        print(f"Error: {args.file} not found", file=sys.stderr)
        sys.exit(1)

    data = json.loads(p.read_text())
    items = data if isinstance(data, list) else [data]

    from .schema_validator import validate
    all_valid = True
    results = []
    for i, item in enumerate(items):
        result = validate(item, args.schema)
        results.append({"index": i, "valid": result.valid, "errors": [
            {"path": e.path, "message": e.message} for e in result.errors
        ]})
        if not result.valid:
            all_valid = False

    if getattr(args, "json", False):
        print(json.dumps({"valid": all_valid, "results": results}, indent=2))
    else:
        status = "PASS" if all_valid else "FAIL"
        print(f"Schema Validation: {status} ({args.schema})")
        for r in results:
            if not r["valid"]:
                for e in r["errors"]:
                    print(f"  [{r['index']}] {e['path']}: {e['message']}")

    sys.exit(0 if all_valid else 1)


def cmd_dte_check(args: argparse.Namespace) -> None:
    episodes = _load_episodes(args.path)

    dte_path = Path(args.dte)
    if not dte_path.exists():
        print(f"Error: DTE spec not found: {args.dte}", file=sys.stderr)
        sys.exit(1)

    dte_spec = json.loads(dte_path.read_text())

    from .dte_enforcer import DTEEnforcer
    enforcer = DTEEnforcer(dte_spec)

    results = []
    for ep in episodes:
        ep_id = ep.get("episodeId", "unknown")
        telem = ep.get("telemetry", {})
        elapsed = telem.get("endToEndMs", 0)
        stage_elapsed = telem.get("stageMs", {})
        counts = {
            "hops": telem.get("hopCount", 0),
            "tool_calls": telem.get("toolCallCount", 0),
        }
        violations = enforcer.enforce(
            elapsed_ms=elapsed,
            stage_elapsed=stage_elapsed,
            counts=counts,
        )
        if violations:
            results.append({
                "episodeId": ep_id,
                "violations": [
                    {
                        "gate": v.gate,
                        "field": v.field,
                        "limit": v.limit_value,
                        "actual": v.actual_value,
                        "severity": v.severity,
                        "message": v.message,
                    }
                    for v in violations
                ],
            })

    if getattr(args, "json", False):
        print(json.dumps({"total_episodes": len(episodes), "violations": results}, indent=2))
    else:
        if results:
            print(f"DTE Check: {len(results)}/{len(episodes)} episode(s) with violations")
            for r in results:
                for v in r["violations"]:
                    print(f"  [{r['episodeId']}] {v['message']}")
        else:
            print(f"DTE Check: CLEAN — {len(episodes)} episode(s) within envelope")

    sys.exit(1 if results else 0)


def cmd_feeds_validate(args: argparse.Namespace) -> None:
    p = Path(args.path)
    if not p.exists():
        print(f"Error: {args.path} not found", file=sys.stderr)
        sys.exit(1)

    items: list = []
    if p.is_file():
        items = _load_json_like(p.read_text())
    elif p.is_dir():
        for f in sorted(p.glob("*.json")):
            items.extend(_load_json_like(f.read_text()))

    from .feeds.validate import validate_feed_event

    all_valid = True
    results = []
    for i, item in enumerate(items):
        result = validate_feed_event(item)
        results.append({"index": i, "valid": result.valid, "errors": [
            {"path": e.path, "message": e.message} for e in result.errors
        ]})
        if not result.valid:
            all_valid = False

    if getattr(args, "json", False):
        print(json.dumps({"valid": all_valid, "results": results}, indent=2))
    else:
        status = "PASS" if all_valid else "FAIL"
        print(f"FEEDS Validation: {status}")
        for r in results:
            if not r["valid"]:
                for e in r["errors"]:
                    print(f"  [{r['index']}] {e['path']}: {e['message']}")

    sys.exit(0 if all_valid else 1)


def cmd_feeds_ingest(args: argparse.Namespace) -> None:
    from .feeds.ingest import IngestOrchestrator
    from .feeds.types import Classification

    classification = getattr(args, "classification", "LEVEL_0")
    orchestrator = IngestOrchestrator(
        topics_root=args.topics,
        producer="coherence-cli",
        classification=classification,
    )
    result = orchestrator.ingest(args.packet_dir)

    if getattr(args, "json", False):
        from dataclasses import asdict
        print(json.dumps(asdict(result), indent=2))
    else:
        status = "OK" if result.success else "FAIL"
        print(f"Ingest {status}: packet={result.packet_id}, events={result.events_published}")
        if result.errors:
            for err in result.errors:
                print(f"  ERROR: {err}")
        if result.drift_signal_id:
            print(f"  PROCESS_GAP drift: {result.drift_signal_id}")

    sys.exit(0 if result.success else 1)


def cmd_feeds_triage_list(args: argparse.Namespace) -> None:
    from .feeds.consumers.triage import TriageStore

    store = TriageStore(args.db)
    state = getattr(args, "state", None)
    entries = store.list_entries(state=state)
    store.close()

    if getattr(args, "json", False):
        print(json.dumps([{
            "driftId": e.drift_id, "state": e.state.value,
            "severity": e.severity, "driftType": e.drift_type,
            "packetId": e.packet_id, "updatedAt": e.updated_at,
            "notes": e.notes,
        } for e in entries], indent=2))
    else:
        if not entries:
            print("No triage entries found.")
        else:
            for e in entries:
                print(f"  [{e.state.value}] {e.drift_id}  sev={e.severity}  type={e.drift_type}")


def cmd_feeds_triage_set_state(args: argparse.Namespace) -> None:
    from .feeds.consumers.triage import TriageStore

    store = TriageStore(args.db)
    try:
        entry = store.set_state(args.drift_id, args.new_state, notes=getattr(args, "notes", ""))
        print(f"Updated {entry.drift_id} -> {entry.state.value}")
    except (KeyError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
    finally:
        store.close()


def cmd_feeds_triage_stats(args: argparse.Namespace) -> None:
    from .feeds.consumers.triage import TriageStore

    store = TriageStore(args.db)
    stats = store.stats()
    store.close()

    if getattr(args, "json", False):
        print(json.dumps(stats, indent=2))
    else:
        print(f"Total: {stats['total']}")
        print("  By state:")
        for s, c in stats.get("by_state", {}).items():
            print(f"    {s}: {c}")
        print("  By severity:")
        for s, c in stats.get("by_severity", {}).items():
            print(f"    {s}: {c}")


def cmd_feeds_canon_list(args: argparse.Namespace) -> None:
    from .feeds.canon.store import CanonStore

    store = CanonStore(args.db)
    domain = getattr(args, "domain", None)
    entries = store.list_entries(domain=domain)
    store.close()

    if getattr(args, "json", False):
        print(json.dumps(entries, indent=2))
    else:
        if not entries:
            print("No canon entries found.")
        else:
            for e in entries:
                sup = f"  supersededBy={e['supersededBy']}" if e.get("supersededBy") else ""
                print(f"  [{e['version']}] {e['canonId']}  domain={e['domain']}{sup}")


def cmd_feeds_canon_add(args: argparse.Namespace) -> None:
    from .feeds.canon.store import CanonStore

    p = Path(args.file)
    if not p.exists():
        print(f"Error: {args.file} not found", file=sys.stderr)
        sys.exit(1)

    canon_entry = json.loads(p.read_text())
    # Accept either a bare payload or an envelope
    if "payload" in canon_entry and "topic" in canon_entry:
        canon_entry = canon_entry["payload"]

    topics_root = getattr(args, "topics", None)
    store = CanonStore(args.db, topics_root=topics_root)
    canon_id = store.add(canon_entry)
    store.close()
    print(f"Added canon entry: {canon_id}")


def cmd_feeds_graph_build(args: argparse.Namespace) -> None:
    from .feeds.canon.mg_writer import MGWriter

    topics_root = Path(args.topics)
    packet_id = args.packet_id

    # Collect all events from ack/ dirs that match the packet_id
    events: list = []
    for topic_dir in topics_root.iterdir():
        if not topic_dir.is_dir() or topic_dir.name.startswith("."):
            continue
        for sub in ("ack", "inbox"):
            sub_dir = topic_dir / sub
            if not sub_dir.is_dir():
                continue
            for f in sub_dir.glob("*.json"):
                try:
                    event = json.loads(f.read_text())
                    if event.get("packetId") == packet_id:
                        events.append(event)
                except (json.JSONDecodeError, KeyError):
                    continue

    if not events:
        print(f"No events found for packet {packet_id}", file=sys.stderr)
        sys.exit(1)

    writer = MGWriter()
    output = getattr(args, "output", ".")
    path = writer.write_graph(packet_id, events, output)
    print(f"Graph written: {path}")


def cmd_feeds_bus_init(args: argparse.Namespace) -> None:
    from .feeds.bus import init_topic_layout
    root = init_topic_layout(args.topics_root)
    print(f"FEEDS bus initialized at {root}")


def cmd_feeds_publish(args: argparse.Namespace) -> None:
    p = Path(args.file)
    if not p.exists():
        print(f"Error: {args.file} not found", file=sys.stderr)
        sys.exit(1)

    event = json.loads(p.read_text())
    from .feeds.bus import Publisher
    pub = Publisher(args.topics)
    try:
        written = pub.publish(args.topic, event)
        print(f"Published: {written.name}")
    except (ValueError, FileNotFoundError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


def cmd_feeds_poll(args: argparse.Namespace) -> None:
    from .feeds.bus import Subscriber
    sub = Subscriber(args.topics, args.topic)

    processed: list = []
    def _handler(event: dict) -> None:
        processed.append(event.get("eventId", "unknown"))

    acked = sub.poll(_handler, batch_size=args.batch)
    if getattr(args, "json", False):
        print(json.dumps({"acked": acked, "eventIds": processed}, indent=2))
    else:
        print(f"Polled {acked} event(s) from {args.topic}")
        for eid in processed:
            print(f"  - {eid}")


def cmd_feeds_replay_dlq(args: argparse.Namespace) -> None:
    from .feeds.bus import DLQManager
    dlq = DLQManager(args.topics, args.topic)

    event_id = getattr(args, "event_id", None)
    replayed = dlq.replay(event_id=event_id)

    if getattr(args, "json", False):
        print(json.dumps({"replayed": replayed}, indent=2))
    else:
        print(f"Replayed {replayed} event(s) from {args.topic} DLQ")


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
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}",
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

    # ── reconcile ─────────────────────────────────────────────────
    p_reconcile = subparsers.add_parser("reconcile", help="Detect cross-artifact inconsistencies")
    p_reconcile.add_argument("path", help="Path to episodes file or directory")
    p_reconcile.add_argument("--auto-fix", action="store_true", help="Apply auto-fixable repairs")
    p_reconcile.add_argument("--json", action="store_true", help="Output JSON")
    p_reconcile.set_defaults(func=cmd_reconcile)

    # ── schema validate ──────────────────────────────────────────
    p_schema = subparsers.add_parser("schema", help="Schema operations")
    schema_sub = p_schema.add_subparsers(dest="schema_command", required=True)

    p_schema_validate = schema_sub.add_parser("validate", help="Validate JSON against a schema")
    p_schema_validate.add_argument("file", help="Path to JSON file to validate")
    p_schema_validate.add_argument("--schema", required=True, help="Schema name (e.g., episode, drift, dte)")
    p_schema_validate.add_argument("--json", action="store_true", help="Output JSON")
    p_schema_validate.set_defaults(func=cmd_schema_validate)

    # ── dte check ────────────────────────────────────────────────
    p_dte = subparsers.add_parser("dte", help="DTE operations")
    dte_sub = p_dte.add_subparsers(dest="dte_command", required=True)

    p_dte_check = dte_sub.add_parser("check", help="Check episodes against DTE constraints")
    p_dte_check.add_argument("path", help="Path to episodes file or directory")
    p_dte_check.add_argument("--dte", required=True, help="Path to DTE spec JSON")
    p_dte_check.add_argument("--json", action="store_true", help="Output JSON")
    p_dte_check.set_defaults(func=cmd_dte_check)

    # ── feeds ─────────────────────────────────────────────────────
    p_feeds = subparsers.add_parser("feeds", help="FEEDS operations")
    feeds_sub = p_feeds.add_subparsers(dest="feeds_command", required=True)

    p_feeds_validate = feeds_sub.add_parser("validate", help="Validate FEEDS event(s)")
    p_feeds_validate.add_argument("path", help="Path to FEEDS event JSON file or directory")
    p_feeds_validate.add_argument("--json", action="store_true", help="Output JSON")
    p_feeds_validate.set_defaults(func=cmd_feeds_validate)

    p_feeds_bus_init = feeds_sub.add_parser("bus-init", help="Initialize FEEDS topic layout")
    p_feeds_bus_init.add_argument("topics_root", help="Root directory for FEEDS topics")
    p_feeds_bus_init.set_defaults(func=cmd_feeds_bus_init)

    p_feeds_publish = feeds_sub.add_parser("publish", help="Publish a FEEDS event")
    p_feeds_publish.add_argument("topic", help="Target FEEDS topic")
    p_feeds_publish.add_argument("file", help="Path to event JSON file")
    p_feeds_publish.add_argument("--topics", required=True, help="Topics root directory")
    p_feeds_publish.set_defaults(func=cmd_feeds_publish)

    p_feeds_poll = feeds_sub.add_parser("poll", help="Poll a FEEDS topic inbox")
    p_feeds_poll.add_argument("topic", help="FEEDS topic to poll")
    p_feeds_poll.add_argument("--topics", required=True, help="Topics root directory")
    p_feeds_poll.add_argument("--batch", type=int, default=10, help="Batch size")
    p_feeds_poll.add_argument("--json", action="store_true", help="Output JSON")
    p_feeds_poll.set_defaults(func=cmd_feeds_poll)

    p_feeds_replay = feeds_sub.add_parser("replay-dlq", help="Replay DLQ events")
    p_feeds_replay.add_argument("topic", help="FEEDS topic")
    p_feeds_replay.add_argument("--topics", required=True, help="Topics root directory")
    p_feeds_replay.add_argument("--event-id", default=None, help="Specific event ID to replay")
    p_feeds_replay.add_argument("--json", action="store_true", help="Output JSON")
    p_feeds_replay.set_defaults(func=cmd_feeds_replay_dlq)

    p_feeds_ingest = feeds_sub.add_parser("ingest", help="Ingest a coherence packet")
    p_feeds_ingest.add_argument("packet_dir", help="Path to packet directory")
    p_feeds_ingest.add_argument("--topics", required=True, help="Topics root directory")
    p_feeds_ingest.add_argument("--classification", default="LEVEL_0", help="Classification level")
    p_feeds_ingest.add_argument("--json", action="store_true", help="Output JSON")
    p_feeds_ingest.set_defaults(func=cmd_feeds_ingest)

    # ── triage ──
    p_triage = feeds_sub.add_parser("triage", help="Drift triage operations")
    triage_sub = p_triage.add_subparsers(dest="triage_command", required=True)

    p_triage_list = triage_sub.add_parser("list", help="List triage entries")
    p_triage_list.add_argument("--state", default=None, help="Filter by state")
    p_triage_list.add_argument("--db", default="drift_triage.db", help="Triage DB path")
    p_triage_list.add_argument("--json", action="store_true", help="Output JSON")
    p_triage_list.set_defaults(func=cmd_feeds_triage_list)

    p_triage_set = triage_sub.add_parser("set-state", help="Transition triage entry state")
    p_triage_set.add_argument("drift_id", help="Drift signal ID")
    p_triage_set.add_argument("new_state", help="Target state")
    p_triage_set.add_argument("--notes", default="", help="Transition notes")
    p_triage_set.add_argument("--db", default="drift_triage.db", help="Triage DB path")
    p_triage_set.set_defaults(func=cmd_feeds_triage_set_state)

    p_triage_stats = triage_sub.add_parser("stats", help="Triage statistics")
    p_triage_stats.add_argument("--db", default="drift_triage.db", help="Triage DB path")
    p_triage_stats.add_argument("--json", action="store_true", help="Output JSON")
    p_triage_stats.set_defaults(func=cmd_feeds_triage_stats)

    # ── canon ──
    p_canon = feeds_sub.add_parser("canon", help="Canon store operations")
    canon_sub = p_canon.add_subparsers(dest="canon_command", required=True)

    p_canon_list = canon_sub.add_parser("list", help="List canon entries")
    p_canon_list.add_argument("--domain", default=None, help="Filter by domain")
    p_canon_list.add_argument("--db", default="canon_store.db", help="Canon DB path")
    p_canon_list.add_argument("--json", action="store_true", help="Output JSON")
    p_canon_list.set_defaults(func=cmd_feeds_canon_list)

    p_canon_add = canon_sub.add_parser("add", help="Add a canon entry")
    p_canon_add.add_argument("file", help="Path to canon entry JSON file")
    p_canon_add.add_argument("--db", default="canon_store.db", help="Canon DB path")
    p_canon_add.add_argument("--topics", default=None, help="Topics root for cache invalidation")
    p_canon_add.set_defaults(func=cmd_feeds_canon_add)

    # ── graph ──
    p_graph = feeds_sub.add_parser("graph", help="Memory graph operations")
    graph_sub = p_graph.add_subparsers(dest="graph_command", required=True)

    p_graph_build = graph_sub.add_parser("build", help="Build per-packet memory graph")
    p_graph_build.add_argument("packet_id", help="Coherence packet ID")
    p_graph_build.add_argument("--topics", required=True, help="Topics root directory")
    p_graph_build.add_argument("--output", default=".", help="Output directory")
    p_graph_build.set_defaults(func=cmd_feeds_graph_build)

    # ── demo ─────────────────────────────────────────────────────
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
