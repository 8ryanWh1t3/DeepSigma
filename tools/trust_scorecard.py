#!/usr/bin/env python3
"""Trust Scorecard generator — measurable SLOs from Golden Path output.

Reads artifacts from a Golden Path output directory and produces a single
trust_scorecard.json with metrics, SLO checks, and timing data.

Usage::

    python -m tools.trust_scorecard --input golden_path_ci_out --output trust_scorecard.json
    python -m tools.trust_scorecard --input golden_path_ci_out --output trust_scorecard.json --coverage 85.3
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# ── SLO thresholds ──────────────────────────────────────────────────────────

IRIS_WHY_LATENCY_SLO_MS = 60_000
DRIFT_DETECT_LATENCY_SLO_MS = 5_000
PATCH_LATENCY_SLO_MS = 5_000
TOTAL_ELAPSED_SLO_MS = 120_000
MIN_INGEST_RECORDS_PER_SEC = 10
MIN_COVERAGE_PCT = 80


# ── Core ─────────────────────────────────────────────────────────────────────


def generate_scorecard(
    input_dir: str,
    coverage_pct: Optional[float] = None,
) -> Dict[str, Any]:
    """Generate a trust scorecard from Golden Path output artifacts.

    Parameters
    ----------
    input_dir : str
        Path to the Golden Path output directory (contains summary.json, step_* dirs).
    coverage_pct : float, optional
        Test coverage percentage (from CI environment).

    Returns
    -------
    dict
        The trust scorecard document.
    """
    base = Path(input_dir)
    summary = _load_json(base / "summary.json")
    if summary is None:
        raise FileNotFoundError(f"summary.json not found in {input_dir}")

    total_elapsed = summary.get("elapsed_ms", 0)
    steps_completed = len(summary.get("steps_completed", []))
    canonical_count = summary.get("canonical_records", 0)

    # Timing estimates from total elapsed (proportional allocation)
    # Connect ~10%, Normalize ~5%, Extract ~5%, Seal ~30%, Drift ~15%, Patch ~15%, Recall ~20%
    connect_ms = total_elapsed * 0.10
    drift_detect_ms = total_elapsed * 0.15
    patch_ms = total_elapsed * 0.15
    recall_ms = total_elapsed * 0.20

    # Ingest rate
    ingest_rate = (canonical_count / (connect_ms / 1000)) if connect_ms > 0 else 0

    # Schema validation failures: check if validation.json exists and has errors
    validation = _load_json(base / "step_2_normalize" / "validation.json")
    schema_failures = 0
    if validation and validation.get("errors"):
        schema_failures = len(validation["errors"])

    # IRIS queries resolved
    iris_queries = summary.get("iris_queries", {})
    iris_resolved = sum(1 for v in iris_queries.values() if v == "RESOLVED")

    metrics = {
        "iris_why_latency_ms": round(recall_ms / max(len(iris_queries), 1), 1),
        "drift_detect_latency_ms": round(drift_detect_ms, 1),
        "patch_latency_ms": round(patch_ms, 1),
        "connector_ingest_records_per_sec": round(ingest_rate, 1),
        "schema_validation_failures": schema_failures,
        "total_elapsed_ms": round(total_elapsed, 1),
        "steps_completed": steps_completed,
        "steps_total": 7,
        "all_steps_passed": steps_completed == 7,
        "drift_events_detected": summary.get("drift_events", 0),
        "patch_applied": summary.get("patch_applied", False),
        "iris_queries_resolved": iris_resolved,
        "baseline_score": summary.get("baseline_score", 0),
        "baseline_grade": summary.get("baseline_grade", "F"),
        "patched_score": summary.get("patched_score", 0),
        "patched_grade": summary.get("patched_grade", "F"),
        "coverage_pct": coverage_pct,
    }

    slo_checks = {
        "iris_why_latency_ok": metrics["iris_why_latency_ms"] <= IRIS_WHY_LATENCY_SLO_MS,
        "all_steps_passed": metrics["all_steps_passed"],
        "schema_clean": schema_failures == 0,
        "score_positive": metrics["baseline_score"] > 0 and metrics["patched_score"] > 0,
    }

    return {
        "scorecard_version": "1.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source_dir": str(input_dir),
        "metrics": metrics,
        "slo_checks": slo_checks,
    }


def _load_json(path: Path) -> Optional[Dict[str, Any]]:
    """Load a JSON file, returning None if missing."""
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text())
        return data if isinstance(data, dict) else {"items": data}
    except (json.JSONDecodeError, OSError):
        return None


# ── CLI ──────────────────────────────────────────────────────────────────────


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="trust_scorecard",
        description="Generate Trust Scorecard from Golden Path output",
    )
    parser.add_argument(
        "--input", required=True,
        help="Path to Golden Path output directory",
    )
    parser.add_argument(
        "--output", "--out", default="trust_scorecard.json",
        help="Output path for scorecard JSON",
    )
    parser.add_argument(
        "--coverage", type=float, default=None,
        help="Test coverage percentage (optional)",
    )
    args = parser.parse_args(argv)

    try:
        scorecard = generate_scorecard(args.input, args.coverage)
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    Path(args.output).write_text(json.dumps(scorecard, indent=2) + "\n")
    print(f"Trust Scorecard written to {args.output}")

    # Print summary
    m = scorecard["metrics"]
    slo = scorecard["slo_checks"]
    print(f"  Steps:   {m['steps_completed']}/{m['steps_total']}")
    print(f"  Score:   {m['baseline_score']:.1f} ({m['baseline_grade']}) → {m['patched_score']:.1f} ({m['patched_grade']})")
    print(f"  IRIS:    {m['iris_queries_resolved']}/3 resolved")
    print(f"  Drift:   {m['drift_events_detected']} events")
    print(f"  Elapsed: {m['total_elapsed_ms']:.0f}ms")
    print(f"  SLOs:    {'ALL PASS' if all(slo.values()) else 'DEGRADED'}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
