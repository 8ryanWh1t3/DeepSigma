#!/usr/bin/env python3
"""v0.3 Money Demo — Drift → Patch Cycle.

One command runs a visible, repeatable loop:
  Decision → Seal → Drift → Patch → Memory diff → Coherence improves

Usage:
    python -m coherence_ops.examples.drift_patch_cycle

Produces deterministic artifacts in:
    examples/demo-stack/drift_patch_cycle_run/
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

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
# Constants
# ===================================================================
OUTPUT_DIR = _REPO_ROOT / "examples" / "demo-stack" / "drift_patch_cycle_run"
NOW = "2026-02-16T15:00:00Z"


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


def _write(path: Path, data: dict) -> None:
    """Write JSON to disk."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, default=str) + "\n",
                    encoding="utf-8")


# ===================================================================
# Main: Three-State Drift → Patch Cycle
# ===================================================================

def main() -> None:
    episodes = _load_episodes()
    # Use the first episode's ID for the drift/patch cycle
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
        "driftId": "drift-cycle-001",
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
        "patchId": "patch-cycle-001",
        "driftId": "drift-cycle-001",
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
    # Apply patch to the MG so the diff shows the patch node + resolved_by edge
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

    # ----- Write Artifacts -----
    _write(OUTPUT_DIR / "report_baseline.json", _report_to_dict(report_base))
    _write(OUTPUT_DIR / "report_drift.json", _report_to_dict(report_drift))
    _write(OUTPUT_DIR / "report_after.json", _report_to_dict(report_after))
    _write(OUTPUT_DIR / "memory_graph_before.json", mg_before_snap)
    _write(OUTPUT_DIR / "memory_graph_drift.json", mg_drift_snap)
    _write(OUTPUT_DIR / "memory_graph_after.json", mg_after_snap)
    _write(OUTPUT_DIR / "memory_graph_diff.json", diff)

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


if __name__ == "__main__":
    main()
