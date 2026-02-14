#!/usr/bin/env python3
"""End-to-end examples: sealed DecisionEpisode -> CoherenceReport (JSON).

Three scenarios demonstrating the full coherence_ops pipeline:
  1. Happy path  — all episodes healthy, score ~90+
  2. Mixed path   — some drift, partial outcomes, score ~60-75
  3. Stress path  — recurring red drift, verification failures, score <50

Each example loads sample data, runs the full DLR -> RS -> DS -> MG -> Score
pipeline, and prints the CoherenceReport as pretty JSON.

Usage:
    python -m coherence_ops.examples.e2e_seal_to_report
"""
from __future__ import annotations

import json
import sys
from dataclasses import asdict
from pathlib import Path

# ---------------------------------------------------------------------------
# Ensure the repo root is on sys.path so `coherence_ops` is importable
# when running from the examples/ directory.
# ---------------------------------------------------------------------------
_REPO_ROOT = Path(__file__).resolve().parents[2]
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
from coherence_ops.manifest import ArtifactDeclaration, ArtifactKind, ComplianceLevel  # noqa: E402
from coherence_ops.scoring import CoherenceReport  # noqa: E402


# ===================================================================
# Helpers
# ===================================================================

def _load_json(name: str) -> list:
    """Load a JSON file from the same directory as this script."""
    return json.loads((Path(__file__).parent / name).read_text())


def _build_manifest() -> CoherenceManifest:
    """Create a full-coverage manifest for the demo system."""
    m = CoherenceManifest(system_id="demo-system", version="0.1.0")
    for kind in ArtifactKind:
        m.declare(ArtifactDeclaration(
            kind=kind,
            schema_version="1.0.0",
            compliance=ComplianceLevel.FULL,
            source="coherence_ops.examples",
            description=f"Demo {kind.value.upper()} artifact",
        ))
    return m


def _print_report(title: str, report: CoherenceReport) -> None:
    """Pretty-print a CoherenceReport with a header."""
    border = "=" * 60
    print(f"\n{border}")
    print(f"  {title}")
    print(f"{border}")
    raw = asdict(report)
    # Include seal/version metadata
    raw["metadata"]["seal_status"] = "sealed"
    raw["metadata"]["framework_version"] = "0.1.0"
    raw["metadata"]["pipeline"] = "DLR -> RS -> DS -> MG -> Score"
    print(json.dumps(raw, indent=2))
    print(f"\n  Overall: {report.overall_score}/100  Grade: {report.grade}")
    print(border)


def _run_pipeline(episodes, drift_events, session_id="rs-demo"):
    """Run the full coherence pipeline and return the report."""
    # 1. DLR — build Decision Log Records
    dlr = DLRBuilder()
    dlr.from_episodes(episodes)

    # 2. RS — run a Reflection Session
    rs = ReflectionSession(session_id)
    rs.ingest(episodes)

    # 3. DS — collect Drift Signals
    ds = DriftSignalCollector()
    if drift_events:
        ds.ingest(drift_events)

    # 4. MG — build the Memory Graph
    mg = MemoryGraph()
    for ep in episodes:
        mg.add_episode(ep)
    for d in drift_events:
        mg.add_drift(d)

    # 5. Score — compute coherence
    scorer = CoherenceScorer(dlr_builder=dlr, rs=rs, ds=ds, mg=mg)
    report = scorer.score()

    return report, dlr, rs, ds, mg


# ===================================================================
# Example 1: Happy Path
# ===================================================================

def example_happy_path():
    """All episodes succeed, verification passes, no red drift."""
    episodes = _load_json("sample_episodes.json")
    # Use only the two healthy episodes (deploy + scale)
    healthy = [ep for ep in episodes if ep["outcome"]["code"] == "success"]

    # No drift for the happy path
    drift_events = []

    report, dlr, rs, ds, mg = _run_pipeline(
        healthy, drift_events, session_id="rs-happy-001"
    )
    _print_report("Example 1: Happy Path (all green)", report)

    # Show DLR entries
    print(f"\n  DLR entries: {len(dlr.entries)}")
    for e in dlr.entries:
        print(f"    {e.dlr_id}  episode={e.episode_id}  "
              f"policy={'stamped' if e.policy_stamp else 'MISSING'}  "
              f"outcome={e.outcome_code}")

    # Show RS summary
    summary = rs.summarise()
    print("\n  RS takeaways:")
    for t in summary.takeaways:
        print(f"    - {t}")

    return report


# ===================================================================
# Example 2: Mixed Path
# ===================================================================

def example_mixed_path():
    """Mix of success and partial, some yellow drift."""
    episodes = _load_json("sample_episodes.json")  # all 3 episodes
    all_drift = _load_json("sample_drift.json")
    # Use only the green + yellow drift (not the red ones)
    mild_drift = [d for d in all_drift if d["severity"] != "red"]

    report, dlr, rs, ds, mg = _run_pipeline(
        episodes, mild_drift, session_id="rs-mixed-001"
    )
    _print_report("Example 2: Mixed Path (yellow drift, partial outcomes)", report)

    # Show drift summary
    ds_summary = ds.summarise()
    print(f"\n  Drift signals: {ds_summary.total_signals}")
    print(f"  By severity: {ds_summary.by_severity}")
    print(f"  By type: {ds_summary.by_type}")

    # Show MG stats
    mg_stats = mg.query("stats")
    print(f"\n  Memory Graph: {mg_stats['total_nodes']} nodes, "
          f"{mg_stats['total_edges']} edges")

    return report


# ===================================================================
# Example 3: Stress Path
# ===================================================================

def example_stress_path():
    """Recurring red drift, verification failure, degradation."""
    episodes = _load_json("sample_episodes.json")  # all 3 episodes
    drift_events = _load_json("sample_drift.json")  # all 5 drift events

    report, dlr, rs, ds, mg = _run_pipeline(
        episodes, drift_events, session_id="rs-stress-001"
    )
    _print_report("Example 3: Stress Path (red drift, verification fail)", report)

    # Show the top recurring drift fingerprints
    ds_summary = ds.summarise()
    print("\n  Top recurring drift fingerprints:")
    for fp in ds_summary.top_recurring:
        bucket = next(b for b in ds_summary.buckets if b.fingerprint_key == fp)
        print(f"    {fp}  count={bucket.count}  "
              f"severity={bucket.worst_severity}  "
              f"patches={bucket.recommended_patches}")

    # Show "why did we do this?" for the rollback episode
    why = mg.query("why", episode_id="ep-demo-003")
    print("\n  Why did we do ep-demo-003 (rollback)?")
    print(f"    Evidence refs: {why['evidence_refs']}")
    print(f"    Actions taken: {why['actions']}")

    # Show audit findings
    manifest = _build_manifest()
    auditor = CoherenceAuditor(
        manifest=manifest, dlr_builder=dlr, rs=rs, ds=ds, mg=mg
    )
    audit_report = auditor.run("audit-stress-001")
    print(f"\n  Audit: {'PASSED' if audit_report.passed else 'FAILED'}")
    print(f"  Findings: {audit_report.summary}")
    for f in audit_report.findings:
        print(f"    [{f.severity.value}] {f.check_name}: {f.message}")

    return report


# ===================================================================
# Main
# ===================================================================

if __name__ == "__main__":
    print("Coherence Ops — End-to-End Examples")
    print("Sealed DecisionEpisode -> CoherenceReport (JSON)")
    print()

    r1 = example_happy_path()
    r2 = example_mixed_path()
    r3 = example_stress_path()

    print("\n" + "=" * 60)
    print("  Summary")
    print("=" * 60)
    print(f"  Happy path:  {r1.overall_score}/100  ({r1.grade})")
    print(f"  Mixed path:  {r2.overall_score}/100  ({r2.grade})")
    print(f"  Stress path: {r3.overall_score}/100  ({r3.grade})")
    print("=" * 60)
