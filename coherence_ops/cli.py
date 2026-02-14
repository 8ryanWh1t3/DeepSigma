#!/usr/bin/env python3
"""Coherence Ops CLI — command-line interface for the coherence framework.

Commands:
    coherence audit <path>          Run cross-artifact consistency checks
        coherence score <path>          Compute unified coherence score (0-100)
            coherence mg export <path>      Export Memory Graph (graphml | neo4j-csv | json)
                coherence iris query <args>     IRIS operator query resolution engine
                    coherence demo                  Ship-it demo: score + top drift + "why?" query

                    Usage:
                        python -m coherence_ops.cli audit  ./episodes
                            python -m coherence_ops.cli score  ./episodes
                                python -m coherence_ops.cli mg export --format=graphml ./episodes
                                    python -m coherence_ops.cli iris query --type WHY --target ep-001 ./episodes
                                        python -m coherence_ops.cli iris query --type STATUS ./episodes
                                            python -m coherence_ops.cli iris query --type WHAT_DRIFTED ./episodes
                                                python -m coherence_ops.cli demo
                                                """

from __future__ import annotations

import argparse
import json
import sys
import xml.etree.ElementTree as ET
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List

# ---------------------------------------------------------------------------
# Ensure repo root is importable
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(_REPO_ROOT))

from coherence_ops import (  # noqa: E402
    CoherenceManifest,
    DLRBuilder,
    ReflectionSession,
    DriftSignalCollector,
    MemoryGraph,
    CoherenceAuditor,
    CoherenceScorer,
)
from coherence_ops.iris import (  # noqa: E402
    IRISEngine,
    IRISQuery,
    QueryType,
    IRISConfig,
)
from coherence_ops.manifest import ArtifactDeclaration, ArtifactKind, ComplianceLevel  # noqa: E402


# ===================================================================
# Data loaders
# ===================================================================

def _load_episodes(path: str) -> List[Dict[str, Any]]:
        """Load episodes from a JSON file or directory of JSON files."""
        p = Path(path)
        if p.is_file():
                    return json.loads(p.read_text())
                if p.is_dir():
                            episodes = []
                            for f in sorted(p.glob("*.json")):
                                            data = json.loads(f.read_text())
                                            if isinstance(data, list):
                                                                episodes.extend(data)
                else:
                episodes.append(data)
                            return episodes
    print(f"Error: {path} is not a file or directory", file=sys.stderr)
    sys.exit(1)


def _load_drift(path: str) -> List[Dict[str, Any]]:
        """Load drift events from a drift JSON file, or return empty."""
    p = Path(path)
    drift_file = None
    if p.is_file() and "drift" in p.name:
                drift_file = p
elif p.is_dir():
        candidates = list(p.glob("*drift*.json"))
        if candidates:
                        drift_file = candidates[0]
                if drift_file:
                            data = json.loads(drift_file.read_text())
                            return data if isinstance(data, list) else [data]
                        return []


def _build_pipeline(episodes, drift_events):
        """Run the full DLR -> RS -> DS -> MG pipeline."""
    dlr = DLRBuilder()
    dlr.from_episodes(episodes)

    rs = ReflectionSession("cli-session")
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
        """Create a manifest for CLI operations."""
    m = CoherenceManifest(system_id="cli", version="0.1.0")
    for kind in ArtifactKind:
                m.declare(ArtifactDeclaration(
                    kind=kind,
                    schema_version="1.0.0",
                    compliance=ComplianceLevel.FULL,
                    source="coherence_ops.cli",
    ))
    return m


# ===================================================================
# Commands
# ===================================================================

def cmd_audit(args):
        """Run a coherence audit and print findings."""
    episodes = _load_episodes(args.path)
    drift_events = _load_drift(args.path)
    dlr, rs, ds, mg = _build_pipeline(episodes, drift_events)

    manifest = _build_manifest()
    auditor = CoherenceAuditor(
                manifest=manifest, dlr_builder=dlr, rs=rs, ds=ds, mg=mg
    )
    report = auditor.run("cli-audit-001")

    print(f"Coherence Audit | system: {report.manifest_system_id}")
    print(f"Run at: {report.run_at}")
    print(f"Result: {'PASSED' if report.passed else 'FAILED'}")
    print(f"Findings: {report.summary}")
    print()
    for f in report.findings:
                sev = f.severity.value.upper()
                print(f"  [{sev:8s}] {f.check_name}: {f.message}")
            print()
    # Seal stub in output
    print("Seal: stub-sha256 (v0.1.0)")
    print(f"Pipeline: episodes={len(episodes)} drift={len(drift_events)}")


def cmd_score(args):
        """Compute and print the coherence score."""
        episodes = _load_episodes(args.path)
        drift_events = _load_drift(args.path)
        dlr, rs, ds, mg = _build_pipeline(episodes, drift_events)

    scorer = CoherenceScorer(dlr_builder=dlr, rs=rs, ds=ds, mg=mg)
    report = scorer.score()

    raw = asdict(report)
    # Inject seal / version / patch metadata (C requirement)
    raw["metadata"]["seal"] = "stub-sha256"
    raw["metadata"]["version"] = "0.1.0"
    raw["metadata"]["patch_level"] = 0
    raw["metadata"]["pipeline"] = "DLR -> RS -> DS -> MG -> Score"

    if args.json:
                print(json.dumps(raw, indent=2))
else:
            print(f"Coherence Score: {report.overall_score}/100  Grade: {report.grade}")
            print(f"Computed at: {report.computed_at}")
            print()
            for dim in report.dimensions:
                            bar = "#" * int(dim.score / 5) + "-" * (20 - int(dim.score / 5))
                            print(f"  {dim.name:25s} {dim.score:6.1f} [{bar}] (w={dim.weight})")
                        print()
        print("Seal: stub-sha256 | Version: 0.1.0 | Patch: 0")


def cmd_mg_export(args):
        """Export the Memory Graph in the requested format."""
    episodes = _load_episodes(args.path)
    drift_events = _load_drift(args.path)
    _, _, _, mg = _build_pipeline(episodes, drift_events)

    fmt = args.format.lower()
    if fmt == "json":
                print(mg.to_json(indent=2))
    elif fmt == "graphml":
        _export_graphml(mg)
elif fmt in ("neo4j-csv", "neo4j"):
        _export_neo4j_csv(mg)
else:
        print(f"Unknown format: {fmt}. Use: json | graphml | neo4j-csv", file=sys.stderr)
        sys.exit(1)


def _export_graphml(mg: MemoryGraph):
        """Export MG as GraphML XML."""
    ns = "http://graphml.graphdrawing.org/xmlns"
    root = ET.Element("graphml", xmlns=ns)

    # Key definitions
    ET.SubElement(root, "key", id="kind",
                                    attrib={"for": "node", "attr.name": "kind", "attr.type": "string"})
    ET.SubElement(root, "key", id="label",
                                    attrib={"for": "node", "attr.name": "label", "attr.type": "string"})
    ET.SubElement(root, "key", id="timestamp",
                                    attrib={"for": "node", "attr.name": "timestamp", "attr.type": "string"})
    ET.SubElement(root, "key", id="edge_kind",
                                    attrib={"for": "edge", "attr.name": "kind", "attr.type": "string"})

    graph = ET.SubElement(root, "graph", id="MemoryGraph", edgedefault="directed")

    data = json.loads(mg.to_json())
    for node in data["nodes"]:
                n = ET.SubElement(graph, "node", id=node["node_id"])
                d1 = ET.SubElement(n, "data", key="kind")
                d1.text = node["kind"]
                d2 = ET.SubElement(n, "data", key="label")
                d2.text = node.get("label", "")
                d3 = ET.SubElement(n, "data", key="timestamp")
                d3.text = node.get("timestamp", "")

    for i, edge in enumerate(data["edges"]):
                e = ET.SubElement(graph, "edge", id=f"e{i}",
                                                            source=edge["source_id"], target=edge["target_id"])
                d = ET.SubElement(e, "data", key="edge_kind")
                d.text = edge["kind"]

    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ")
    print('<?xml version="1.0" encoding="UTF-8"?>')
    ET.dump(root)


def _export_neo4j_csv(mg: MemoryGraph):
        """Export MG as Neo4j-importable CSV (nodes + relationships)."""
    data = json.loads(mg.to_json())

    print("=== NODES (nodes.csv) ===")
    print("nodeId:ID,kind:LABEL,label,timestamp")
    for node in data["nodes"]:
                nid = node["node_id"]
                kind = node["kind"]
                label = node.get("label", "").replace(",", ";")
                ts = node.get("timestamp", "")
                print(f"{nid},{kind},{label},{ts}")

    print()
    print("=== RELATIONSHIPS (relationships.csv) ===")
    print(":START_ID,:END_ID,:TYPE")
    for edge in data["edges"]:
                print(f"{edge['source_id']},{edge['target_id']},{edge['kind']}")


# ===================================================================
# IRIS Command — operator query resolution
# ===================================================================

_IRIS_QUERY_TYPE_MAP = {
        "WHY": QueryType.WHY,
        "WHAT_CHANGED": QueryType.WHAT_CHANGED,
        "WHAT_DRIFTED": QueryType.WHAT_DRIFTED,
        "RECALL": QueryType.RECALL,
        "STATUS": QueryType.STATUS,
}


def cmd_iris_query(args):
        """Run an IRIS operator query and print the structured answer.

            Builds the full DLR -> RS -> DS -> MG pipeline, wires it into the
                IRISEngine, and resolves the requested query type.
                    """
    episodes = _load_episodes(args.path)
    drift_events = _load_drift(args.path)
    dlr, rs, ds, mg = _build_pipeline(episodes, drift_events)

    engine = IRISEngine(
                dlr_builder=dlr,
                rs=rs,
                ds=ds,
                mg=mg,
                config=IRISConfig(),
    )

    query_type_str = args.type.upper()
    query_type = _IRIS_QUERY_TYPE_MAP.get(query_type_str)
    if query_type is None:
                valid = ", ".join(sorted(_IRIS_QUERY_TYPE_MAP.keys()))
                print(f"Error: unknown query type '{args.type}'. Valid types: {valid}",
                      file=sys.stderr)
                sys.exit(1)

    # Build the query
    query = IRISQuery(
                query_type=query_type,
                episode_id=args.target or "",
                text=args.text or "",
                limit=args.limit,
    )

    # Validate required fields
    if query_type in (QueryType.WHY, QueryType.RECALL) and not args.target:
                print(f"Error: --target <episode_id> is required for {query_type_str} queries",
                                    file=sys.stderr)
                sys.exit(1)

    response = engine.resolve(query)

    if args.json:
                print(response.to_json(indent=2))
    else:
        _print_iris_response(response)


def _print_iris_response(response):
        """Pretty-print an IRIS response for terminal output."""
    W = 60
    print()
    print("+" + "-" * W + "+")
    print("|" + f" IRIS — {response.query_type.value} ".center(W) + "|")
    print("+" + "-" * W + "+")
    print()

    # Status and confidence
    status_icon = {
                "RESOLVED": "[OK]",
                "PARTIAL": "[??]",
                "NOT_FOUND": "[--]",
                "ERROR": "[!!]",
    }.get(response.status.value, "[??]")

    print(f"  Status:     {status_icon} {response.status.value}")
    conf_bar_len = 30
    conf_filled = int(response.confidence * conf_bar_len)
    conf_bar = "=" * conf_filled + "-" * (conf_bar_len - conf_filled)
    print(f"  Confidence: {response.confidence:.1%} [{conf_bar}]")
    print(f"  Query ID:   {response.query_id}")
    print(f"  Resolved:   {response.resolved_at}")
    print(f"  Elapsed:    {response.elapsed_ms:.1f} ms")
    print()

    # Summary
    print("  Summary:")
    # Word-wrap the summary at ~70 chars
    words = response.summary.split()
    line = "    "
    for word in words:
                if len(line) + len(word) + 1 > 72:
                                print(line)
                                line = "    "
                            line += word + " "
    if line.strip():
                print(line)
    print()

    # Provenance chain
    if response.provenance_chain:
                print(f"  Provenance Chain ({len(response.provenance_chain)} links):")
        for i, link in enumerate(response.provenance_chain):
                        role_tag = link.get("role", "?") if isinstance(link, dict) else link.role
                        artifact = link.get("artifact", "?") if isinstance(link, dict) else link.artifact
                        ref_id = link.get("ref_id", "?") if isinstance(link, dict) else link.ref_id
                        detail = link.get("detail", "") if isinstance(link, dict) else link.detail
                        print(f"    {i + 1}. [{artifact:5s}] {ref_id}")
                        print(f"       role={role_tag}  {detail}")
                    print()

    # Data highlights (query-type specific)
    data = response.data if isinstance(response.data, dict) else {}

    if response.query_type == QueryType.WHY:
                _print_why_data(data)
elif response.query_type == QueryType.WHAT_CHANGED:
        _print_what_changed_data(data)
elif response.query_type == QueryType.WHAT_DRIFTED:
        _print_what_drifted_data(data)
elif response.query_type == QueryType.RECALL:
        _print_recall_data(data)
elif response.query_type == QueryType.STATUS:
        _print_status_data(data)

    # Warnings
    warnings = response.warnings if isinstance(response.warnings, list) else []
    if warnings:
                print("  Warnings:")
        for w in warnings:
                        print(f"    ! {w}")
                    print()

    # Footer
    print("+" + "-" * W + "+")
    print("|" + " Seal: stub-sha256 | v0.1.0 | IRIS ".center(W) + "|")
    print("+" + "-" * W + "+")
    print()


def _print_why_data(data: Dict[str, Any]):
        """Print WHY-specific data highlights."""
    dlr = data.get("dlr_entry")
    if dlr:
                print("  DLR Record:")
        print(f"    DLR ID:        {dlr.get('dlr_id', '?')}")
        print(f"    Decision Type: {dlr.get('decision_type', '?')}")
        print(f"    Outcome:       {dlr.get('outcome_code', '?')}")
        stamp = dlr.get("policy_stamp")
        if stamp:
                        print(f"    Policy Pack:   {stamp.get('policyPackId', '?')} "
                                                f"v{stamp.get('policyPackVersion', '?')}")
                    degrade = dlr.get("degrade_step")
        if degrade and degrade != "none":
                        print(f"    Degrade Step:  {degrade}")
                    print()

    mg_prov = data.get("mg_provenance")
    if mg_prov:
                node = mg_prov.get("node")
        if node:
                        print("  MG Node:")
                        print(f"    Label:    {node.get('label', '?')}")
                        print(f"    Kind:     {node.get('kind', '?')}")
                    evidence = mg_prov.get("evidence_refs", [])
        if evidence:
                        print(f"    Evidence: {', '.join(evidence)}")
                    actions = mg_prov.get("actions", [])
        if actions:
                        print(f"    Actions:  {', '.join(actions)}")
                    print()

    drift = data.get("mg_drift", [])
    if drift:
                print(f"  Linked Drift Events: {len(drift)}")
        for d in drift[:5]:
                        label = d.get("label", "?")
                        sev = d.get("properties", {}).get("severity", "?")
                        print(f"    - {label} (severity={sev})")
                    print()


def _print_what_changed_data(data: Dict[str, Any]):
        """Print WHAT_CHANGED-specific data highlights."""
    total = data.get("total_entries", 0)
    outcomes = data.get("outcome_distribution", {})
    degraded = data.get("degraded_episodes", [])
    missing = data.get("policy_missing", [])

    print(f"  DLR Entries Analysed: {total}")
    if outcomes:
                print("  Outcome Distribution:")
        for code, count in outcomes.items():
                        print(f"    {code:12s} {count}")
                if degraded:
                            print(f"  Degraded Episodes:    {len(degraded)}")
                        if missing:
                                    print(f"  Missing Policy Stamp: {len(missing)}")

    patch_count = data.get("patch_count")
    if patch_count is not None:
                print(f"  MG Patches:           {patch_count}")

    drift_sum = data.get("drift_summary")
    if drift_sum:
                sev = drift_sum.get("by_severity", {})
        print(f"  Drift Signals:        {drift_sum.get('total_signals', 0)} "
                            f"(red={sev.get('red', 0)})")
    print()


def _print_what_drifted_data(data: Dict[str, Any]):
        """Print WHAT_DRIFTED-specific data highlights."""
    total = data.get("total_signals", 0)
    by_sev = data.get("by_severity", {})
    print(f"  Total Signals:  {total}")
    print(f"  Severity:       red={by_sev.get('red', 0)} "
                    f"yellow={by_sev.get('yellow', 0)} "
                    f"green={by_sev.get('green', 0)}")

    buckets = data.get("top_buckets", [])
    if buckets:
                print()
        print("  Top Drift Fingerprints:")
        for i, b in enumerate(buckets[:10], 1):
                        sev = b.get("worst_severity", "?").upper()
                        key = b.get("fingerprint_key", "?")
                        count = b.get("count", 0)
                        print(f"    {i}. [{sev:6s}] {key} (x{count})")
                        patches = b.get("recommended_patches", [])
                        if patches:
                                            print(f"       Patch: {', '.join(patches)}")

                ratio = data.get("resolution_ratio")
    if ratio is not None:
                pct = f"{ratio:.0%}"
        mg_d = data.get("mg_drift_nodes", "?")
        mg_p = data.get("mg_patch_nodes", "?")
        print(f"\n  Resolution Ratio: {pct} ({mg_p}/{mg_d} resolved)")
    print()


def _print_recall_data(data: Dict[str, Any]):
        """Print RECALL-specific data highlights."""
    prov = data.get("provenance", {})
    node = prov.get("node") if prov else None
    if node:
                print("  Recalled Episode:")
        print(f"    Label:    {node.get('label', '?')}")
        print(f"    Kind:     {node.get('kind', '?')}")
        props = node.get("properties", {})
        if props:
                        for k, v in props.items():
                                            print(f"    {k:10s} {v}")
                                evidence = prov.get("evidence_refs", []) if prov else []
    actions = prov.get("actions", []) if prov else []
    drift = data.get("drift_events", [])
    patches = data.get("patches", [])
    print(f"  Evidence Refs: {len(evidence)}")
    print(f"  Actions:       {len(actions)}")
    print(f"  Drift Events:  {len(drift)}")
    print(f"  Patches:       {len(patches)}")

    dlr = data.get("dlr_entry")
    if dlr:
                print(f"  DLR Confirms:  {dlr.get('decision_type', '?')} "
                                    f"-> {dlr.get('outcome_code', '?')}")
    print()


def _print_status_data(data: Dict[str, Any]):
        """Print STATUS-specific data highlights."""
    score = data.get("overall_score", 0)
    grade = data.get("grade", "?")
    dims = data.get("dimensions", [])

    bar_len = 30
    filled = int(score / 100 * bar_len)
    bar = "=" * filled + "-" * (bar_len - filled)
    print(f"  Coherence: {score}/100 [{bar}] {grade}")
    print()

    if dims:
                print("  Dimensions:")
        for dim in dims:
                        name = dim.get("name", "?")
            s = dim.get("score", 0)
            w = dim.get("weight", 0)
            mini = "=" * int(s / 10) + "-" * (10 - int(s / 10))
            print(f"    {name:25s} {s:5.1f} [{mini}] (w={w})")
        print()

    headline = data.get("drift_headline")
    if headline:
                print(f"  Drift: {headline.get('total', 0)} signals "
                                    f"(red={headline.get('red', 0)}, "
                                    f"recurring={headline.get('recurring', 0)})")

    mg_stats = data.get("mg_stats")
    if mg_stats:
                print(f"  Graph: {mg_stats.get('total_nodes', 0)} nodes, "
                                    f"{mg_stats.get('total_edges', 0)} edges")
    print()


# ===================================================================
# Demo Command — the Stark/Jobs "ship it" moment
# ===================================================================

def cmd_demo(args):
        """Ship-it demo: coherence score, top 3 drift fingerprints, why query.

            This is the one command that turns coherence_ops from framework into
                product. Run it and see the system speak.
                    """
    # Load bundled sample data
    examples_dir = Path(__file__).parent / "examples"
    if not examples_dir.exists():
                print("Error: examples/ directory not found. Run from repo root.",
                                    file=sys.stderr)
        sys.exit(1)

    episodes = json.loads(
                (examples_dir / "sample_episodes.json").read_text()
    )
    drift_events = json.loads(
                (examples_dir / "sample_drift.json").read_text()
    )

    dlr, rs, ds, mg = _build_pipeline(episodes, drift_events)
    scorer = CoherenceScorer(dlr_builder=dlr, rs=rs, ds=ds, mg=mg)
    report = scorer.score()

    # ---------------------------------------------------------------
    # Output: the product speaks
    # ---------------------------------------------------------------
    W = 56
    print()
    print("+" + "-" * W + "+")
    print("|" + " COHERENCE OPS — SYSTEM STATUS ".center(W) + "|")
    print("+" + "-" * W + "+")
    print()

    # 1. Coherence Score
    grade_emoji = {"A": "A", "B": "B", "C": "C", "D": "D", "F": "F"}
    g = grade_emoji.get(report.grade, "?")
    bar_len = 40
    filled = int(report.overall_score / 100 * bar_len)
    bar = "=" * filled + "-" * (bar_len - filled)
    print(f"  Coherence Score: {report.overall_score}/100 [{bar}] {g}")
    print()
    for dim in report.dimensions:
                mini = "=" * int(dim.score / 10) + "-" * (10 - int(dim.score / 10))
        print(f"    {dim.name:25s} {dim.score:5.1f} [{mini}]")
    print()

    # 2. Top 3 Drift Fingerprints
    ds_summary = ds.summarise()
    print("  Top 3 Drift Fingerprints:")
    top_buckets = sorted(
                ds_summary.buckets,
                key=lambda b: b.count, reverse=True
    )[:3]
    for i, bucket in enumerate(top_buckets, 1):
                sev = bucket.worst_severity.upper()
        print(f"    {i}. [{sev:6s}] {bucket.fingerprint_key} "
                            f"(x{bucket.count})")
        if bucket.recommended_patches:
                        print(f"         Patch: {', '.join(bucket.recommended_patches)}")
    print()

    # 3. "Why did we do this?" query
    # Pick the most interesting episode — the rollback
    target_ep = "ep-demo-003"
    why = mg.query("why", episode_id=target_ep)
    drift_q = mg.query("drift", episode_id=target_ep)
    mg.query("patches", episode_id=target_ep)  # patches data not displayed yet

    print(f'  "Why did we do this?" (episode: {target_ep})')
    node = why.get("node", {})
    if node:
                props = node.get("properties", {})
        print(f"    Decision:   {node.get('label', 'unknown')}")
        print(f"    Outcome:    {props.get('outcome', 'unknown')}")
        print(f"    Seal:       {props.get('seal_hash', 'none')}")
        print(f"    Evidence:   {why.get('evidence_refs', [])}")
        print(f"    Actions:    {why.get('actions', [])}")
        drift_nodes = drift_q.get("drift_events", [])
        if drift_nodes:
                        print(f"    Drift signals: {len(drift_nodes)}")
            for dn in drift_nodes[:3]:
                                print(f"      - {dn['label']} "
                                                            f"(severity={dn['properties'].get('severity')})")
                    print()

    # Footer
    print("+" + "-" * W + "+")
    print("|" + " Seal: stub-sha256 | v0.1.0 | patch=0 ".center(W) + "|")
    print("|" + f" {len(episodes)} episodes | {len(drift_events)} drift events ".center(W) + "|")
    print("+" + "-" * W + "+")
    print()


# ===================================================================
# Argument Parser
# ===================================================================

def main():
        """Entry point for the coherence CLI."""
    parser = argparse.ArgumentParser(
                prog="coherence",
                description="Coherence Ops CLI — governance framework for agentic AI",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # audit
    p_audit = subparsers.add_parser("audit", help="Run coherence audit")
    p_audit.add_argument("path", help="Path to episodes file or directory")
    p_audit.set_defaults(func=cmd_audit)

    # score
    p_score = subparsers.add_parser("score", help="Compute coherence score")
    p_score.add_argument("path", help="Path to episodes file or directory")
    p_score.add_argument("--json", action="store_true", help="Output as JSON")
    p_score.set_defaults(func=cmd_score)

    # mg (with sub-subparser for export)
    p_mg = subparsers.add_parser("mg", help="Memory Graph operations")
    mg_sub = p_mg.add_subparsers(dest="mg_command")
    p_export = mg_sub.add_parser("export", help="Export Memory Graph")
    p_export.add_argument("path", help="Path to episodes file or directory")
    p_export.add_argument(
                "--format", default="json",
                choices=["json", "graphml", "neo4j-csv"],
                help="Export format (default: json)",
    )
    p_export.set_defaults(func=cmd_mg_export)

    # iris (with sub-subparser for query)
    p_iris = subparsers.add_parser(
                "iris",
                help="IRIS operator query resolution engine",
    )
    iris_sub = p_iris.add_subparsers(dest="iris_command")

    p_iris_query = iris_sub.add_parser(
                "query",
                help="Resolve an operator query (WHY / WHAT_CHANGED / WHAT_DRIFTED / RECALL / STATUS)",
    )
    p_iris_query.add_argument(
                "path",
                help="Path to episodes file or directory",
    )
    p_iris_query.add_argument(
                "--type", "-t",
                required=True,
                metavar="QUERY_TYPE",
                choices=["WHY", "WHAT_CHANGED", "WHAT_DRIFTED", "RECALL", "STATUS"],
                help="Query type: WHY, WHAT_CHANGED, WHAT_DRIFTED, RECALL, STATUS",
    )
    p_iris_query.add_argument(
                "--target",
                metavar="EPISODE_ID",
                default="",
                help="Target episode ID (required for WHY and RECALL queries)",
    )
    p_iris_query.add_argument(
                "--text",
                metavar="QUERY_TEXT",
                default="",
                help="Free-text query description",
    )
    p_iris_query.add_argument(
                "--limit",
                type=int,
                default=20,
                help="Maximum number of results (default: 20)",
    )
    p_iris_query.add_argument(
                "--json",
                action="store_true",
                help="Output as JSON instead of formatted text",
    )
    p_iris_query.set_defaults(func=cmd_iris_query)

    # demo
    p_demo = subparsers.add_parser(
                "demo",
                help="Ship-it demo: score + top drift + why query",
    )
    p_demo.set_defaults(func=cmd_demo)

    args = parser.parse_args()
    if not args.command:
                parser.print_help()
        sys.exit(0)

    if hasattr(args, "func"):
                args.func(args)
else:
        parser.print_help()


if __name__ == "__main__":
        main()
