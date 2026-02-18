#!/usr/bin/env python3
"""Golden Path CLI — first-class entrypoint.

Usage:
    deepsigma golden-path sharepoint --fixture demos/golden_path/fixtures/sharepoint_small
    deepsigma golden-path sharepoint --fixture demos/golden_path/fixtures/sharepoint_small --json
    deepsigma golden-path sharepoint --fixture demos/golden_path/fixtures/sharepoint_small --clean --verbose
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


def _run_golden_path(args: argparse.Namespace) -> int:
    from demos.golden_path.config import GoldenPathConfig
    from demos.golden_path.pipeline import GoldenPathPipeline

    out_dir = Path(args.output)

    # --clean: wipe output directory before running
    if args.clean and out_dir.exists():
        if args.verbose:
            print(f"Cleaning output directory: {out_dir}")
        shutil.rmtree(out_dir)

    config = GoldenPathConfig(
        source=args.source,
        fixture_path=args.fixture,
        episode_id=args.episode_id,
        decision_type=args.decision_type,
        output_dir=str(out_dir),
        supervised=args.supervised,
        list_id=args.list_id,
        site_id=args.site_id,
        table_name=args.table,
        sql=args.sql,
        prompt=args.prompt,
    )

    if args.verbose:
        mode = "fixture" if config.fixture_path else "live"
        print(f"Source: {config.source}  Mode: {mode}  Output: {config.output_dir}")

    try:
        pipeline = GoldenPathPipeline(config)
        result = pipeline.run()
    except Exception as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
        return 0

    # Step-by-step summary
    steps_expected = ["connect", "normalize", "extract", "seal", "drift", "patch", "recall"]
    print()
    print("=" * 60)
    print("  GOLDEN PATH")
    print("=" * 60)
    for i, step in enumerate(steps_expected, 1):
        ok = step in result.steps_completed
        tag = "PASS" if ok else "FAIL"
        print(f"  [{i}] {step.upper():20s} {tag}")
    print()
    print(f"  Records:    {result.canonical_records}")
    print(f"  Claims:     {result.claims_extracted}")
    print(f"  Baseline:   {result.baseline_score:.1f} ({result.baseline_grade})")
    print(f"  Drift:      {result.drift_events} events")
    print(f"  Patch:      {'applied' if result.patch_applied else 'none'}")
    print(f"  Patched:    {result.patched_score:.1f} ({result.patched_grade})")
    print(f"  IRIS:       {', '.join(f'{k}={v}' for k, v in result.iris_queries.items())}")
    print(f"  Output:     {result.output_dir}")
    print(f"  Elapsed:    {result.elapsed_ms:.0f}ms")
    print("=" * 60)

    all_passed = len(result.steps_completed) == 7
    return 0 if all_passed else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="deepsigma",
        description="Sigma OVERWATCH CLI",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    gp = subparsers.add_parser(
        "golden-path",
        help="Run the 7-step Golden Path decision governance loop",
    )
    gp.add_argument(
        "source",
        choices=["sharepoint", "snowflake", "dataverse", "asksage"],
        help="Data source connector",
    )
    gp.add_argument("--fixture", default=None, help="Path to fixture directory (offline mode)")
    gp.add_argument("--output", "--out", default="./golden_path_output", help="Output directory")
    gp.add_argument("--clean", action="store_true", help="Wipe output directory before running")
    gp.add_argument("--verbose", action="store_true", help="Print extra diagnostic output")
    gp.add_argument("--json", action="store_true", help="Output JSON result instead of table")
    gp.add_argument("--episode-id", default="gp-demo", help="Episode ID")
    gp.add_argument("--decision-type", default="ingest", help="Decision type")
    gp.add_argument("--supervised", action="store_true", help="Pause before patch step")
    gp.add_argument("--list-id", default="", help="SharePoint list ID")
    gp.add_argument("--site-id", default="", help="SharePoint site ID")
    gp.add_argument("--table", default="", help="Dataverse table name")
    gp.add_argument("--sql", default="", help="Snowflake SQL query")
    gp.add_argument("--prompt", default="", help="AskSage prompt")
    gp.set_defaults(func=_run_golden_path)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
