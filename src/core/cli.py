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


def cmd_feeds_claim_validate(args: argparse.Namespace) -> None:
    from .feeds.canon.claim_validator import ClaimValidator

    p = Path(args.file)
    if not p.exists():
        print(f"Error: {args.file} not found", file=sys.stderr)
        sys.exit(1)

    data = json.loads(p.read_text())
    claims = data if isinstance(data, list) else [data]

    canon_db = getattr(args, "canon_db", None)
    canon_claims: list = []
    if canon_db and Path(canon_db).exists():
        from .feeds.canon.store import CanonStore
        store = CanonStore(canon_db)
        canon_claims = store.list_entries()
        store.close()

    validator = ClaimValidator(canon_claims=canon_claims)
    all_results = []
    for claim in claims:
        issues = validator.validate_claim(claim)
        all_results.append({
            "claimId": claim.get("claimId", "unknown"),
            "valid": len(issues) == 0,
            "issues": issues,
        })

    all_valid = all(r["valid"] for r in all_results)
    if getattr(args, "json", False):
        print(json.dumps({"valid": all_valid, "results": all_results}, indent=2))
    else:
        status = "PASS" if all_valid else "FAIL"
        print(f"Claim Validation: {status}")
        for r in all_results:
            if not r["valid"]:
                for issue in r["issues"]:
                    print(f"  [{r['claimId']}] {issue['type']}: {issue['detail']}")

    sys.exit(0 if all_valid else 1)


def cmd_feeds_claim_submit(args: argparse.Namespace) -> None:
    from .feeds.consumers.claim_trigger import ClaimTriggerPipeline

    p = Path(args.file)
    if not p.exists():
        print(f"Error: {args.file} not found", file=sys.stderr)
        sys.exit(1)

    data = json.loads(p.read_text())
    claims = data if isinstance(data, list) else [data]

    # Optional components
    canon_claims: list = []
    canon_db = getattr(args, "canon_db", None)
    if canon_db and Path(canon_db).exists():
        from .feeds.canon.store import CanonStore
        store = CanonStore(canon_db)
        canon_claims = store.list_entries()
        store.close()

    topics_root = getattr(args, "topics", None)
    if topics_root:
        topics_root = Path(topics_root)

    authority_ledger = None
    ledger_path = getattr(args, "ledger", None)
    if ledger_path and Path(ledger_path).exists():
        from .authority import AuthorityLedger
        authority_ledger = AuthorityLedger(path=Path(ledger_path))

    mg = MemoryGraph()
    ds = DriftSignalCollector()

    pipeline = ClaimTriggerPipeline(
        canon_claims=canon_claims,
        mg=mg,
        ds=ds,
        topics_root=topics_root,
        authority_ledger=authority_ledger,
    )

    episode_id = getattr(args, "episode_id", None)
    result = pipeline.submit(claims, episode_id=episode_id)

    if getattr(args, "json", False):
        print(json.dumps({
            "submitted": result.submitted,
            "accepted": result.accepted,
            "rejected": result.rejected,
            "drift_signals_emitted": result.drift_signals_emitted,
            "results": [
                {
                    "claim_id": r.claim_id,
                    "accepted": r.accepted,
                    "issues": r.issues,
                    "drift_signals": len(r.drift_signals),
                    "graph_node_id": r.graph_node_id,
                    "published_events": r.published_events,
                }
                for r in result.results
            ],
        }, indent=2))
    else:
        print(
            f"Claims: {result.submitted} submitted, "
            f"{result.accepted} accepted, {result.rejected} rejected"
        )
        if result.drift_signals_emitted:
            print(f"  Drift signals: {result.drift_signals_emitted}")
        for r in result.results:
            status = "OK" if r.accepted else "REJECTED"
            print(f"  [{status}] {r.claim_id}")

    sys.exit(0 if result.rejected == 0 else 1)


def cmd_demo(args: argparse.Namespace) -> None:
    """Run the deterministic drift-patch demo using bundled sample data.

    Three-state cycle: BASELINE (sealed) -> DRIFT (injected) -> PATCH (resolved).
    Produces identical output on every run.
    """
    # Load bundled sample episodes
    sample_path = Path(__file__).parent / "examples" / "sample_episodes.json"
    if not sample_path.exists():
        print("Error: bundled sample_episodes.json not found", file=sys.stderr)
        sys.exit(1)
    episodes = json.loads(sample_path.read_text(encoding="utf-8"))

    ep_id = episodes[0].get("episodeId", "ep-demo-001")
    NOW = "2026-02-16T15:00:00Z"
    DRIFT_ID = "drift-cycle-001"
    PATCH_ID = "patch-cycle-001"

    # ── BASELINE ──
    dlr_b, rs_b, ds_b, mg_b = _build_pipeline(episodes, [])
    report_base = CoherenceScorer(dlr_builder=dlr_b, rs=rs_b, ds=ds_b, mg=mg_b).score()

    # ── DRIFT ──
    drift_event = {
        "driftId": DRIFT_ID,
        "episodeId": ep_id,
        "driftType": "bypass",
        "severity": "red",
        "detectedAt": NOW,
        "fingerprint": {"key": "bypass-gate-cycle"},
        "recommendedPatchType": "RETCON",
    }
    dlr_d, rs_d, ds_d, mg_d = _build_pipeline(episodes, [drift_event])
    scorer_drift = CoherenceScorer(dlr_builder=dlr_d, rs=rs_d, ds=ds_d, mg=mg_d)
    report_drift = scorer_drift.score()

    # ── PATCH ──
    dlr_p, rs_p, ds_p, mg_p = _build_pipeline(episodes, [])
    mg_p.add_drift(drift_event)
    mg_p.add_patch({
        "patchId": PATCH_ID,
        "driftId": DRIFT_ID,
        "patchType": "RETCON",
        "appliedAt": NOW,
        "description": "Retcon: bypass gate drift resolved by re-evaluation",
        "changes": [{"field": "verification.result", "from": "bypass", "to": "pass"}],
    })
    scorer_patch = CoherenceScorer(dlr_builder=dlr_p, rs=rs_p, ds=ds_p, mg=mg_p)
    report_after = scorer_patch.score()

    if getattr(args, "json", False):
        from dataclasses import asdict as _asdict
        result = {
            "baseline": _asdict(report_base),
            "drift": _asdict(report_drift),
            "patch": _asdict(report_after),
        }
        print(json.dumps(result, indent=2))
        return

    # Write artifacts if requested
    artifacts_dir = getattr(args, "artifacts", None)
    if artifacts_dir:
        out = Path(artifacts_dir)
        out.mkdir(parents=True, exist_ok=True)
        from dataclasses import asdict as _asdict
        for name, report in [("baseline", report_base), ("drift", report_drift), ("patch", report_after)]:
            (out / f"report_{name}.json").write_text(
                json.dumps(_asdict(report), indent=2) + "\n"
            )
        (out / "memory_graph.json").write_text(mg_p.to_json(indent=2) + "\n")
        print(f"Artifacts written to {out}/")

    print(f"BASELINE  {report_base.overall_score:6.2f} ({report_base.grade})")
    print(f"DRIFT     {report_drift.overall_score:6.2f} ({report_drift.grade})   red=1")
    print(
        f"PATCH     {report_after.overall_score:6.2f} ({report_after.grade})"
        f"   patch=RETCON  drift_resolved=true"
    )



# ── agent commands ────────────────────────────────────────────
_DEFAULT_SESSION_DIR = Path.home() / ".deepsigma" / "agent"


def cmd_agent_log(args: argparse.Namespace) -> None:
    from .agent import AgentSession

    p = Path(args.file)
    if not p.exists():
        print(f"Error: {args.file} not found", file=sys.stderr)
        sys.exit(1)

    decision = json.loads(p.read_text())
    session_dir = getattr(args, "session_dir", None) or _DEFAULT_SESSION_DIR
    session = AgentSession(agent_id="cli", storage_dir=session_dir)
    episode = session.log_decision(decision)

    if getattr(args, "json", False):
        print(json.dumps(episode, indent=2))
    else:
        print(f"Logged: {episode['episodeId']}  seal={episode['seal']['sealHash'][:30]}...")


def cmd_agent_audit(args: argparse.Namespace) -> None:
    from .agent import AgentSession

    session_dir = getattr(args, "session_dir", None) or _DEFAULT_SESSION_DIR
    session = AgentSession(agent_id="cli", storage_dir=session_dir)

    if not session._episodes:
        print("No decisions logged yet.", file=sys.stderr)
        sys.exit(1)

    report = session.audit()

    if getattr(args, "json", False):
        print(json.dumps(report, indent=2))
    else:
        passed = report.get("passed", False)
        summary = report.get("summary", "")
        print(f"Audit: {'PASSED' if passed else 'FAILED'}")
        print(f"  {summary}")


def cmd_agent_score(args: argparse.Namespace) -> None:
    from .agent import AgentSession

    session_dir = getattr(args, "session_dir", None) or _DEFAULT_SESSION_DIR
    session = AgentSession(agent_id="cli", storage_dir=session_dir)

    if not session._episodes:
        print("No decisions logged yet.", file=sys.stderr)
        sys.exit(1)

    report = session.score()

    if getattr(args, "json", False):
        print(json.dumps(report, indent=2))
    else:
        print(f"Score: {report['overall_score']}/100  Grade: {report['grade']}")
        print(f"  Episodes: {len(session._episodes)}")


# ── metrics commands ──────────────────────────────────────────


def cmd_metrics(args: argparse.Namespace) -> None:
    from .metrics import MetricsCollector

    episodes = _load_episodes(args.path)
    drift_events = _load_drift(args.path)
    dlr, rs, ds, mg = _build_pipeline(episodes, drift_events)

    authority_ledger = None
    ledger_path = getattr(args, "ledger", None)
    if ledger_path and Path(ledger_path).exists():
        from .authority import AuthorityLedger
        authority_ledger = AuthorityLedger(path=Path(ledger_path))

    collector = MetricsCollector(
        dlr_builder=dlr, rs=rs, ds=ds, mg=mg,
        authority_ledger=authority_ledger,
    )
    report = collector.collect()

    if getattr(args, "json", False):
        print(report.to_json())
    else:
        for m in report.metrics:
            if m.unit == "score":
                grade = m.details.get("grade", "")
                print(f"  {m.name}: {m.value:.1f}/100  ({grade})")
            elif m.unit == "ratio":
                print(f"  {m.name}: {m.value:.4f}")
            else:
                print(f"  {m.name}: {m.value}")


def cmd_agent_metrics(args: argparse.Namespace) -> None:
    from .agent import AgentSession
    from .metrics import MetricsCollector

    session_dir = getattr(args, "session_dir", None) or _DEFAULT_SESSION_DIR
    session = AgentSession(agent_id="cli", storage_dir=session_dir)

    if not session._episodes:
        print("No decisions logged yet.", file=sys.stderr)
        sys.exit(1)

    dlr, rs, ds, mg = session._build_pipeline()

    authority_ledger = None
    ledger_path = getattr(args, "ledger", None)
    if ledger_path and Path(ledger_path).exists():
        from .authority import AuthorityLedger
        authority_ledger = AuthorityLedger(path=Path(ledger_path))

    collector = MetricsCollector(
        dlr_builder=dlr, rs=rs, ds=ds, mg=mg,
        authority_ledger=authority_ledger,
    )
    report = collector.collect()

    if getattr(args, "json", False):
        print(report.to_json())
    else:
        print(f"Agent Metrics ({len(session._episodes)} episodes):")
        for m in report.metrics:
            if m.unit == "score":
                grade = m.details.get("grade", "")
                print(f"  {m.name}: {m.value:.1f}/100  ({grade})")
            elif m.unit == "ratio":
                print(f"  {m.name}: {m.value:.4f}")
            else:
                print(f"  {m.name}: {m.value}")


# ── authority commands ──────────────────────────────────────────
_DEFAULT_LEDGER_PATH = Path.home() / ".deepsigma" / "authority_ledger.json"


def cmd_authority_grant(args: argparse.Namespace) -> None:
    from .authority import AuthorityEntry, AuthorityLedger

    p = Path(args.file)
    if not p.exists():
        print(f"Error: {args.file} not found", file=sys.stderr)
        sys.exit(1)
    data = json.loads(p.read_text())
    ledger_path = Path(getattr(args, "ledger", None) or _DEFAULT_LEDGER_PATH)
    ledger = AuthorityLedger(path=ledger_path)
    entry = AuthorityEntry(
        entry_id=data.get("entry_id", ""),
        entry_type="grant",
        authority_source=data["authority_source"],
        authority_role=data["authority_role"],
        scope=data["scope"],
        claims_blessed=data["claims_blessed"],
        effective_at=data["effective_at"],
        expires_at=data.get("expires_at"),
        entry_hash="",
        prev_entry_hash=None,
    )
    ledger.append(entry)
    if getattr(args, "json", False):
        from dataclasses import asdict
        print(json.dumps(asdict(entry), indent=2))
    else:
        print(
            f"Grant appended: {entry.entry_id}  "
            f"hash={entry.entry_hash[:40]}..."
        )


def cmd_authority_revoke(args: argparse.Namespace) -> None:
    from .authority import AuthorityEntry, AuthorityLedger

    p = Path(args.file)
    if not p.exists():
        print(f"Error: {args.file} not found", file=sys.stderr)
        sys.exit(1)
    data = json.loads(p.read_text())
    ledger_path = Path(getattr(args, "ledger", None) or _DEFAULT_LEDGER_PATH)
    ledger = AuthorityLedger(path=ledger_path)
    entry = AuthorityEntry(
        entry_id=data.get("entry_id", ""),
        entry_type="revocation",
        authority_source=data["authority_source"],
        authority_role=data["authority_role"],
        scope=data["scope"],
        claims_blessed=data["claims_blessed"],
        effective_at=data["effective_at"],
        expires_at=data.get("expires_at"),
        entry_hash="",
        prev_entry_hash=None,
    )
    ledger.append(entry)
    if getattr(args, "json", False):
        from dataclasses import asdict
        print(json.dumps(asdict(entry), indent=2))
    else:
        print(
            f"Revocation appended: {entry.entry_id}  "
            f"hash={entry.entry_hash[:40]}..."
        )


def cmd_authority_list(args: argparse.Namespace) -> None:
    from .authority import AuthorityLedger

    ledger_path = Path(getattr(args, "ledger", None) or _DEFAULT_LEDGER_PATH)
    ledger = AuthorityLedger(path=ledger_path)
    if getattr(args, "json", False):
        from dataclasses import asdict
        print(json.dumps([asdict(e) for e in ledger.entries], indent=2))
    else:
        if not ledger.entries:
            print("No authority entries.")
        else:
            for e in ledger.entries:
                print(
                    f"  [{e.entry_type}] {e.entry_id}  "
                    f"claims={len(e.claims_blessed)}  scope={e.scope}"
                )


def cmd_authority_verify(args: argparse.Namespace) -> None:
    from .authority import AuthorityLedger

    ledger_path = Path(getattr(args, "ledger", None) or _DEFAULT_LEDGER_PATH)
    ledger = AuthorityLedger(path=ledger_path)
    valid = ledger.verify_chain()
    snapshot = ledger.snapshot()
    if getattr(args, "json", False):
        print(json.dumps({**snapshot, "chain_valid": valid}, indent=2))
    else:
        status = "VALID" if valid else "BROKEN"
        print(f"Authority Chain: {status}  entries={snapshot['entry_count']}")
    sys.exit(0 if valid else 1)


def cmd_authority_prove(args: argparse.Namespace) -> None:
    from .authority import AuthorityLedger

    ledger_path = Path(getattr(args, "ledger", None) or _DEFAULT_LEDGER_PATH)
    ledger = AuthorityLedger(path=ledger_path)
    proof = ledger.prove_authority(args.claim_id)
    if proof is None:
        print(f"No authority found for {args.claim_id}", file=sys.stderr)
        sys.exit(1)
    if getattr(args, "json", False):
        print(json.dumps(proof, indent=2))
    else:
        print(
            f"Authority proof: {proof['entry_id']}  "
            f"source={proof['authority_source']}  "
            f"role={proof['authority_role']}"
        )


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

    # ── metrics ──────────────────────────────────────────────────
    p_metrics = subparsers.add_parser("metrics", help="Collect coherence metrics")
    p_metrics.add_argument("path", help="Path to episodes file or directory")
    p_metrics.add_argument("--ledger", default=None, help="Authority ledger path")
    p_metrics.add_argument("--json", action="store_true", help="Output JSON")
    p_metrics.set_defaults(func=cmd_metrics)

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

    # ── claim ──
    p_claim = feeds_sub.add_parser("claim", help="Claim trigger operations")
    claim_sub = p_claim.add_subparsers(dest="claim_command", required=True)

    p_claim_validate = claim_sub.add_parser("validate", help="Validate claim(s)")
    p_claim_validate.add_argument("file", help="Path to claim JSON file")
    p_claim_validate.add_argument("--canon-db", default=None, help="Canon DB for contradiction check")
    p_claim_validate.add_argument("--json", action="store_true", help="Output JSON")
    p_claim_validate.set_defaults(func=cmd_feeds_claim_validate)

    p_claim_submit = claim_sub.add_parser("submit", help="Submit claim(s) through trigger pipeline")
    p_claim_submit.add_argument("file", help="Path to claim JSON file")
    p_claim_submit.add_argument("--episode-id", default=None, help="Episode ID to link claims to")
    p_claim_submit.add_argument("--topics", default=None, help="Topics root for FEEDS publishing")
    p_claim_submit.add_argument("--canon-db", default=None, help="Canon DB for contradiction check")
    p_claim_submit.add_argument("--ledger", default=None, help="Authority ledger for authorization check")
    p_claim_submit.add_argument("--json", action="store_true", help="Output JSON")
    p_claim_submit.set_defaults(func=cmd_feeds_claim_submit)

    # ── agent ─────────────────────────────────────────────────────
    p_agent = subparsers.add_parser("agent", help="Agent decision logging")
    agent_sub = p_agent.add_subparsers(dest="agent_command", required=True)

    p_agent_log = agent_sub.add_parser("log", help="Log a decision")
    p_agent_log.add_argument("file", help="Path to decision JSON file")
    p_agent_log.add_argument("--session-dir", default=None, help="Session storage directory")
    p_agent_log.add_argument("--json", action="store_true", help="Output JSON")
    p_agent_log.set_defaults(func=cmd_agent_log)

    p_agent_audit = agent_sub.add_parser("audit", help="Audit logged decisions")
    p_agent_audit.add_argument("--session-dir", default=None, help="Session storage directory")
    p_agent_audit.add_argument("--json", action="store_true", help="Output JSON")
    p_agent_audit.set_defaults(func=cmd_agent_audit)

    p_agent_score = agent_sub.add_parser("score", help="Score logged decisions")
    p_agent_score.add_argument("--session-dir", default=None, help="Session storage directory")
    p_agent_score.add_argument("--json", action="store_true", help="Output JSON")
    p_agent_score.set_defaults(func=cmd_agent_score)

    p_agent_metrics = agent_sub.add_parser("metrics", help="Collect coherence metrics")
    p_agent_metrics.add_argument("--session-dir", default=None, help="Session storage directory")
    p_agent_metrics.add_argument("--ledger", default=None, help="Authority ledger path")
    p_agent_metrics.add_argument("--json", action="store_true", help="Output JSON")
    p_agent_metrics.set_defaults(func=cmd_agent_metrics)

    # ── authority ──────────────────────────────────────────────────
    p_authority = subparsers.add_parser("authority", help="Authority ledger operations")
    authority_sub = p_authority.add_subparsers(dest="authority_command", required=True)

    p_auth_grant = authority_sub.add_parser("grant", help="Append a grant entry")
    p_auth_grant.add_argument("file", help="Path to grant JSON file")
    p_auth_grant.add_argument("--ledger", default=None, help="Ledger file path")
    p_auth_grant.add_argument("--json", action="store_true", help="Output JSON")
    p_auth_grant.set_defaults(func=cmd_authority_grant)

    p_auth_revoke = authority_sub.add_parser("revoke", help="Append a revocation entry")
    p_auth_revoke.add_argument("file", help="Path to revocation JSON file")
    p_auth_revoke.add_argument("--ledger", default=None, help="Ledger file path")
    p_auth_revoke.add_argument("--json", action="store_true", help="Output JSON")
    p_auth_revoke.set_defaults(func=cmd_authority_revoke)

    p_auth_list = authority_sub.add_parser("list", help="List authority entries")
    p_auth_list.add_argument("--ledger", default=None, help="Ledger file path")
    p_auth_list.add_argument("--json", action="store_true", help="Output JSON")
    p_auth_list.set_defaults(func=cmd_authority_list)

    p_auth_verify = authority_sub.add_parser("verify", help="Verify hash chain integrity")
    p_auth_verify.add_argument("--ledger", default=None, help="Ledger file path")
    p_auth_verify.add_argument("--json", action="store_true", help="Output JSON")
    p_auth_verify.set_defaults(func=cmd_authority_verify)

    p_auth_prove = authority_sub.add_parser("prove", help="Prove authority for a claim")
    p_auth_prove.add_argument("claim_id", help="Claim ID to prove authority for")
    p_auth_prove.add_argument("--ledger", default=None, help="Ledger file path")
    p_auth_prove.add_argument("--json", action="store_true", help="Output JSON")
    p_auth_prove.set_defaults(func=cmd_authority_prove)

    # ── demo ─────────────────────────────────────────────────────
    p_demo = subparsers.add_parser(
        "demo",
        help="Run deterministic drift-patch demo",
    )
    p_demo.add_argument("--json", action="store_true", help="Output JSON")
    p_demo.add_argument("--artifacts", default=None, metavar="DIR",
                        help="Write artifact files to directory")
    p_demo.set_defaults(func=cmd_demo)

    args = parser.parse_args()

    if args.func is None:
        parser.print_help()
        sys.exit(0)

    args.func(args)


if __name__ == "__main__":
    main()
