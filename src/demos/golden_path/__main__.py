#!/usr/bin/env python3
"""Golden Path — one command, one outcome, no ambiguity.

Usage:
    # Fixture mode (no credentials needed)
    python -m demos.golden_path --source sharepoint \\
        --fixture demos/golden_path/fixtures/sharepoint_small

    # Live mode (requires env vars)
    python -m demos.golden_path --source sharepoint --list-id Documents
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from demos.golden_path.config import GoldenPathConfig  # noqa: E402
from demos.golden_path.pipeline import GoldenPathPipeline  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="golden-path",
        description="Run the 7-step Golden Path decision governance loop.",
    )
    parser.add_argument(
        "--source", required=True,
        choices=["sharepoint", "snowflake", "dataverse", "asksage"],
        help="Data source connector to use",
    )
    parser.add_argument("--fixture", default=None, help="Path to fixture directory")
    parser.add_argument("--episode-id", default="gp-demo", help="Episode ID")
    parser.add_argument("--decision-type", default="ingest", help="Decision type")
    parser.add_argument("--output", default="./golden_path_output", help="Output directory")
    parser.add_argument("--supervised", action="store_true", help="Pause before patch")
    parser.add_argument("--json", action="store_true", help="Output JSON result")
    # Source-specific
    parser.add_argument("--list-id", default="", help="SharePoint list ID")
    parser.add_argument("--site-id", default="", help="SharePoint site ID")
    parser.add_argument("--table", default="", help="Dataverse table name")
    parser.add_argument("--sql", default="", help="Snowflake SQL query")
    parser.add_argument("--prompt", default="", help="AskSage prompt")

    args = parser.parse_args(argv)

    config = GoldenPathConfig(
        source=args.source,
        fixture_path=args.fixture,
        episode_id=args.episode_id,
        decision_type=args.decision_type,
        output_dir=args.output,
        supervised=args.supervised,
        list_id=args.list_id,
        site_id=args.site_id,
        table_name=args.table,
        sql=args.sql,
        prompt=args.prompt,
    )

    pipeline = GoldenPathPipeline(config)
    result = pipeline.run()

    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        _print_summary(result)

    return 0


def _print_summary(result):
    print()
    print("=" * 60)
    print("  GOLDEN PATH — Complete")
    print("=" * 60)
    print()
    for i, step in enumerate(result.steps_completed, 1):
        print(f"  [{i}] {step.upper():20s} OK")
    print()
    print(f"  Records ingested:    {result.canonical_records}")
    print(f"  Claims extracted:    {result.claims_extracted}")
    print(f"  Episode ID:          {result.episode_id}")
    print()
    print(f"  Baseline score:      {result.baseline_score:.1f} ({result.baseline_grade})")
    print(f"  Drift events:        {result.drift_events}")
    print(f"  Patch applied:       {result.patch_applied}")
    print(f"  Patched score:       {result.patched_score:.1f} ({result.patched_grade})")
    print()
    print("  IRIS Recall:")
    for qtype, status in result.iris_queries.items():
        print(f"    {qtype:20s} {status}")
    print()
    print(f"  Output:              {result.output_dir}")
    print(f"  Elapsed:             {result.elapsed_ms:.0f}ms")
    print()
    print("=" * 60)


if __name__ == "__main__":
    sys.exit(main())
