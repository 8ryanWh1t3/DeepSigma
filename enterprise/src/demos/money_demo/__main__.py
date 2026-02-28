"""CLI entry point for the Money Demo pipeline."""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Ensure src is on path
_repo_root = Path(__file__).resolve().parents[4]
_src_root = _repo_root / "src"
if str(_src_root) not in sys.path:
    sys.path.insert(0, str(_src_root))

from .pipeline import run_pipeline


def main() -> None:
    fixture_dir = None
    if len(sys.argv) > 1:
        fixture_dir = sys.argv[1]

    result = run_pipeline(fixture_dir)

    print(json.dumps(result.to_dict(), indent=2))

    # Summary line
    print(f"\n--- Money Demo Complete ---")
    print(f"Steps: {len(result.steps)}/10")
    print(f"Baseline claims: {result.baseline_claims}")
    print(f"Delta claims: {result.delta_claims}")
    print(f"Drift signals: {result.drift_signals_total}")
    print(f"Retcon executed: {result.retcon_executed}")
    print(f"Cascade rules: {result.cascade_rules_triggered}")
    print(f"Coherence score: {result.coherence_score:.0f}")
    print(f"Episode sealed: {result.episode_sealed}")
    print(f"Audit entries: {result.audit_entries}")
    print(f"Elapsed: {result.elapsed_ms:.1f}ms")


if __name__ == "__main__":
    main()
