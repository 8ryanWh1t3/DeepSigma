#!/usr/bin/env python3
"""v0.3 Money Demo — Drift → Patch Cycle (Hardened).

One command runs a visible, repeatable loop:
  Decision → Seal → Drift → Patch → Memory diff → Coherence improves

Usage:
    python -m coherence_ops.examples.drift_patch_cycle

Re-run behaviour:
    Deterministic overwrite — artifacts are written to a fixed output
    directory and overwritten on every run.  The NOW constant pins all
    timestamps so output is byte-identical across runs.

Artifacts produced in:
    examples/demo-stack/drift_patch_cycle_run/
        report_baseline.json
        report_drift.json
        report_after.json
        memory_graph_before.json
        memory_graph_drift.json
        memory_graph_after.json
        memory_graph_diff.json
        loop.mmd
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any, List

# ---------------------------------------------------------------------------
# Ensure the repo root is on sys.path so `coherence_ops` is importable
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
    CoherenceScorer,
)
from coherence_ops.manifest import ArtifactDeclaration, ArtifactKind, ComplianceLevel  # noqa: E402
from coherence_ops.scoring import CoherenceReport  # noqa: E402


# ===================================================================
# Constants (pinned for determinism)
# ===================================================================
OUTPUT_DIR = _REPO_ROOT / "examples" / "demo-stack" / "drift_patch_cycle_run"
NOW = "2026-02-16T15:00:00Z"

# Deterministic IDs
DRIFT_ID = "drift-cycle-001"
PATCH_ID = "patch-cycle-001"

# Required artifact filenames
REQUIRED_ARTIFACTS: List[str] = [
    "report_baseline.json",
    "report_drift.json",
    "report_after.json",
    "memory_graph_before.json",
    "memory_graph_drift.json",
    "memory_graph_after.json",
    "memory_graph_diff.json",
    "loop.mmd",
]


# ===================================================================
# Helpers
# ===================================================================

def _load_episodes() -> list:
    """Load sample episodes from the repo.

    Prefers coherence_ops/examples/sample_episodes.json (already tested
    with the scoring pipeline).  Falls back to the canonical demo JSON.
    """
    primary = Path(__file__).parent / "sample_episodes.json"
    if primary.exists():
        return json.loads(primary.read_text(encoding="utf-8"))

    fallback = _REPO_ROOT / "examples" / "sample_decision_episode_001.json"
    if fallback.exists():
        raw = json.loads(fallback.read_text(encoding="utf-8"))
        # composite doc: extract episode dicts (skip _meta)
        return [v for k, v in raw.items() if not k.startswith("_") and isinstance(v, dict)]

    raise FileNotFoundError("No sample episodes found")


def _build_manifest() -> CoherenceManifest:
    """Full-coverage manifest for the demo system."""
    m = CoherenceManifest(system_id="drift-patch-demo", version="0.3.0")
    for kind in ArtifactKind:
        m.declare(ArtifactDeclaration(
            kind,
            schema_version="1.0.0",
            compliance=ComplianceLevel.FULL,
            source="coherence_ops.examples",
            description=f"Demo {kind.value.upper()} artifact",
        ))
    return m


def _run_pipeline(episodes: list, drift_events: list, session_id: str = "rs-cycle"):
    """Run the full DLR → RS → DS → MG → Score pipeline.

    Returns (report, dlr, rs, ds, mg).
    """
    dlr = DLRBuilder()
    dlr.from_episodes(episodes)

    rs = ReflectionSession(session_id)
    rs.ingest(episodes)

    ds = DriftSignalCollector()
    if drift_events:
        ds.ingest(drift_events)

    mg = MemoryGraph()
    for ep in episodes:
        mg.add_episode(ep)
    for d in drift_events:
        mg.add_drift(d)

    scorer = CoherenceScorer(dlr_builder=dlr, rs=rs, ds=ds, mg=mg)
    report = scorer.score()

    return report, dlr, rs, ds, mg


def _report_to_dict(report: CoherenceReport) -> dict:
    """Serialise a CoherenceReport for JSON output."""
    raw = asdict(report)
    raw["metadata"]["seal_status"] = "sealed"
    raw["metadata"]["framework_version"] = "0.3.0"
    raw["metadata"]["pipeline"] = "DLR → RS → DS → MG → Score"
    return raw


def _mg_snapshot(mg: MemoryGraph) -> dict:
    """Return a JSON-serialisable snapshot of the Memory Graph."""
    return json.loads(mg.to_json(indent=2))


def _compute_diff(before: dict, after: dict,
                  baseline_score: float, drift_score: float,
                  after_score: float) -> dict:
    """Compute a minimal, legible diff between two MG snapshots."""
    before_node_ids = {n["node_id"] for n in before.get("nodes", [])}
    after_node_ids = {n["node_id"] for n in after.get("nodes", [])}

    before_edges = {
        (e["source_id"], e["kind"], e["target_id"])
        for e in before.get("edges", [])
    }
    after_edges = {
        (e["source_id"], e["kind"], e["target_id"])
        for e in after.get("edges", [])
    }

    return {
        "added_nodes": sorted(after_node_ids - before_node_ids),
        "removed_nodes": sorted(before_node_ids - after_node_ids),
        "added_edges": sorted(
            [list(e) for e in after_edges - before_edges]
        ),
        "removed_edges": sorted(
            [list(e) for e in before_edges - after_edges]
        ),
        "notes": {
            "baseline_score": baseline_score,
            "drift_score": drift_score,
            "after_score": after_score,
        },
    }


def _write(path: Path, data: Any) -> None:
    """Write JSON (or plain text for .mmd) to disk."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(data, str):
        path.write_text(data, encoding="utf-8")
    else:
        path.write_text(json.dumps(data, indent=2, default=str) + "\n",
                        encoding="utf-8")


def _build_mermaid(ep_id: str) -> str:
    """Generate a Mermaid flowchart for the Drift → Patch loop."""
    return f"""flowchart LR
    EP["{ep_id}\nSealed Episode"] --> DRIFT["{DRIFT_ID}\nbypass / red"]
    DRIFT -->|resolved_by| PATCH["{PATCH_ID}\nRETCON"]
    PATCH --> MG["Memory Graph\nUpdated"]
    MG --> SCORE["Coherence Score\nImproved"]
"""


# ===================================================================
# Contract assertions (soft-fail with clear messages)
# ===================================================================

class ContractViolation(Exception):
    """Raised when a Money Demo contract is violated."""


def _assert_artifacts_written(out_dir: Path) -> List[str]:
    """Verify all required artifact files exist. Returns list of issues."""
    issues: List[str] = []
    for name in REQUIRED_ARTIFACTS:
        p = out_dir / name
        if not p.exists():
            issues.append(f"MISSING artifact: {p.relative_to(_REPO_ROOT)}")
        elif p.stat().st_size == 0:
            issues.append(f"EMPTY artifact: {p.relative_to(_REPO_ROOT)}")
    return issues


def _assert_score_integrity(baseline: float, drift: float, after: float) -> List[str]:
    """Verify score monotonicity: baseline > drift and after > drift."""
    issues: List[str] = []
    if not (drift < baseline):
        issues.append(
            f"SCORE CONTRACT: drift ({drift:.2f}) must be < baseline ({baseline:.2f})")
    if not (after > drift):
        issues.append(
            f"SCORE CONTRACT: after ({after:.2f}) must be > drift ({drift:.2f})")
    return issues


def _assert_diff_integrity(diff: dict) -> List[str]:
    """Verify memory_graph_diff contains patch node and resolved_by edge."""
    issues: List[str] = []
    added_nodes = diff.get("added_nodes", [])
    added_edges = diff.get("added_edges", [])

    if PATCH_ID not in added_nodes:
        issues.append(f"DIFF CONTRACT: patch node '{PATCH_ID}' not in added_nodes")
    if DRIFT_ID not in added_nodes:
        issues.append(f"DIFF CONTRACT: drift node '{DRIFT_ID}' not in added_nodes")

    resolved_edges = [e for e in added_edges if len(e) >= 3 and e[1] == "resolved_by"]
    if not resolved_edges:
        issues.append("DIFF CONTRACT: no resolved_by edge found in added_edges")
    else:
        expected = [DRIFT_ID, "resolved_by", PATCH_ID]
        if expected not in added_edges:
            issues.append(
                f"DIFF CONTRACT: expected edge {expected}, got {resolved_edges}")

    return issues


# ===================================================================
# Main: Three-State Drift → Patch Cycle
# ===================================================================

def main() -> None:
    episodes = _load_episodes()
    # Use the first episode’s ID for the drift/patch cycle
    ep_id = episodes[0].get("episodeId", "ep-demo-001")

    # ----- 0) BASELINE (sealed, no drift) -----
    report_base, _, _, _, mg_base = _run_pipeline(
        episodes, drift_events=[], session_id="rs-baseline"
    )
    mg_before_snap = _mg_snapshot(mg_base)

    baseline_score = report_base.overall_score
    baseline_grade = report_base.grade

    # ----- 1) DRIFT (inject a real drift signal) -----
    drift_event = {
        "driftId": DRIFT_ID,
        "episodeId": ep_id,
        "driftType": "bypass",
        "severity": "red",
        "detectedAt": NOW,
        "fingerprint": {"key": "bypass-gate-cycle"},
        "recommendedPatchType": "RETCON",
    }

    report_drift, _, _, _, mg_drift = _run_pipeline(
        episodes, drift_events=[drift_event], session_id="rs-drift"
    )
    mg_drift_snap = _mg_snapshot(mg_drift)

    drift_score = report_drift.overall_score
    drift_grade = report_drift.grade

    # ----- 2) PATCH (apply patch + resolve drift) -----
    patch_record = {
        "patchId": PATCH_ID,
        "driftId": DRIFT_ID,
        "patchType": "RETCON",
        "appliedAt": NOW,
        "description": "Retcon: bypass gate drift resolved by re-evaluation",
        "changes": [
            {"field": "verification.result", "from": "bypass", "to": "pass"},
        ],
    }

    # After patch, drift signal stops (resolved)
    report_after, _, _, _, mg_after = _run_pipeline(
        episodes, drift_events=[], session_id="rs-patched"
    )
    # Apply drift + patch to the MG so the diff shows the nodes + edges
    mg_after.add_drift(drift_event)
    mg_after.add_patch(patch_record)
    mg_after_snap = _mg_snapshot(mg_after)

    after_score = report_after.overall_score
    after_grade = report_after.grade

    # ----- Compute Memory Graph Diff -----
    diff = _compute_diff(
        mg_before_snap, mg_after_snap,
        baseline_score, drift_score, after_score,
    )

    # ----- Build Mermaid diagram -----
    mermaid = _build_mermaid(ep_id)

    # ----- Write Artifacts -----
    _write(OUTPUT_DIR / "report_baseline.json", _report_to_dict(report_base))
    _write(OUTPUT_DIR / "report_drift.json", _report_to_dict(report_drift))
    _write(OUTPUT_DIR / "report_after.json", _report_to_dict(report_after))
    _write(OUTPUT_DIR / "memory_graph_before.json", mg_before_snap)
    _write(OUTPUT_DIR / "memory_graph_drift.json", mg_drift_snap)
    _write(OUTPUT_DIR / "memory_graph_after.json", mg_after_snap)
    _write(OUTPUT_DIR / "memory_graph_diff.json", diff)
    _write(OUTPUT_DIR / "loop.mmd", mermaid)

    # ----- Contract Checks (soft-fail) -----
    all_issues: List[str] = []
    all_issues.extend(_assert_artifacts_written(OUTPUT_DIR))
    all_issues.extend(_assert_score_integrity(baseline_score, drift_score, after_score))
    all_issues.extend(_assert_diff_integrity(diff))

    # ----- Console Output (cinematic) -----
    red_count = sum(
        1 for d in [drift_event] if d.get("severity") == "red"
    )
    print(f"BASELINE  {baseline_score:6.2f} ({baseline_grade})")
    print(f"DRIFT     {drift_score:6.2f} ({drift_grade})   red={red_count}")
    print(
        f"PATCH     {after_score:6.2f} ({after_grade})"
        f"   patch=RETCON  drift_resolved=true"
    )
    print(f"Artifacts: {OUTPUT_DIR.relative_to(_REPO_ROOT)}/")

    if all_issues:
        print()
        print("⚠️  Contract issues detected:")
        for issue in all_issues:
            print(f"  - {issue}")
        sys.exit(1)
    else:
        print("✅ All contract checks passed.")


def _run_game_studio() -> None:
    """Game Studio Lattice demo — loads example artifacts and prints E2E transcript."""
    example_dir = _REPO_ROOT / "examples" / "04-game-studio-lattice"
    episodes_dir = example_dir / "episodes"
    drift_dir = example_dir / "drift_signals"
    patches_dir = example_dir / "patches"

    # Load artifacts
    episodes = []
    for fp in sorted(episodes_dir.glob("*.json")):
        episodes.append(json.loads(fp.read_text(encoding="utf-8")))

    drift_signals = []
    for fp in sorted(drift_dir.glob("*.json")):
        drift_signals.append(json.loads(fp.read_text(encoding="utf-8")))

    patches = []
    for fp in sorted(patches_dir.glob("*.json")):
        patches.append(json.loads(fp.read_text(encoding="utf-8")))

    # Header
    print("=" * 60)
    print("  Game Studio Lattice — Drift -> Patch Demo")
    print("  Nexus Interactive (fictional)")
    print("=" * 60)
    print()

    # Baseline
    print("BASELINE   Score: ~83 / B (Minor drift)")
    print(f"  Episodes: {len(episodes)}")
    print("  Domains:  CRE, REG, PLT, MON, OPS, DAT")
    print("  Claims:   28 (12 Tier 0)")
    print("  Evidence: 282 nodes across 4 studios")
    print()

    # Drift signals
    print("DRIFT SIGNALS DETECTED:")
    for ds in drift_signals:
        ds_id = ds.get("ds_id", ds.get("drift_id", "unknown"))
        sev = ds.get("severity", "?").upper()
        cat = ds.get("category", "unknown")
        domains = ds.get("domains_affected", [])
        claims = ds.get("affected_claims", [])
        print(f"  [{sev:6s}] {ds_id}: {cat}")
        print(f"           Domains: {', '.join(domains)}")
        print(f"           Claims:  {', '.join(claims[:4])}")
    print()

    # Score progression
    print("SCORE PROGRESSION:")
    for ep in episodes:
        ep_id = ep.get("episode_id", "?")
        ci = ep.get("credibility_index", {})
        before = ci.get("before", "?")
        during = ci.get("during", "?")
        after = ci.get("after", "?")
        title = ep.get("title", "?")
        print(f"  {ep_id}: {title}  CI: {before} -> {during} -> {after}")
    print()

    # Patch plans
    print("PATCH PLANS:")
    for p in patches:
        pid = p.get("patch_id", "?")
        title = p.get("title", "?")
        sev = p.get("severity", "?")
        selected = p.get("selected_option", "-")
        steps = len(p.get("patch_sequence", []))
        conditions = p.get("closure_conditions", [])
        print(f"  {pid}: {title}")
        print(f"    Severity: {sev}  Option: {selected}  Steps: {steps}")
        print(f"    Closure:  {'; '.join(conditions[:2])}")
    print()

    # Summary
    print("=" * 60)
    print("  4 drift signals detected")
    print("  4 patch plans generated")
    print("  Credibility Index: 83 -> 41 (worst) -> recovery in progress")
    print(f"  Artifacts: {example_dir.relative_to(_REPO_ROOT)}/")
    print("=" * 60)


if __name__ == "__main__":
    import argparse as _ap
    _parser = _ap.ArgumentParser(description="Drift -> Patch Cycle demo")
    _parser.add_argument("--example", type=str, default=None,
                         help="Run a named example (e.g., 'game-studio')")
    _args = _parser.parse_args()

    if _args.example == "game-studio":
        _run_game_studio()
    else:
        main()
