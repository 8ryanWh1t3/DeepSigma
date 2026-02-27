#!/usr/bin/env python3
"""Generate static site data files from CLI output.

Runs ``coherence demo --json`` and ``coherence metrics`` to produce
JSON data files consumed by the static demo site.

Output:
    docs/site/data/demo.json
    docs/site/data/metrics.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# Ensure the src directory is importable
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))


def generate_demo_json(output_dir: Path) -> Path:
    """Run the demo pipeline and write demo.json."""
    import argparse
    import io
    from contextlib import redirect_stdout
    from core.cli import cmd_demo

    # Simulate `coherence demo --json`
    args = argparse.Namespace(json=True, artifacts=None)
    buf = io.StringIO()
    with redirect_stdout(buf):
        cmd_demo(args)

    data = json.loads(buf.getvalue())
    path = output_dir / "demo.json"
    path.write_text(json.dumps(data, indent=2, default=str) + "\n")
    return path


def generate_metrics_json(output_dir: Path) -> Path:
    """Run the metrics collector on sample episodes and write metrics.json."""
    from core.decision_log import DLRBuilder
    from core.drift_signal import DriftSignalCollector
    from core.memory_graph import MemoryGraph
    from core.reflection import ReflectionSession
    from core.metrics import MetricsCollector

    # Load sample episodes (JSON files may contain arrays or single objects)
    examples_dir = REPO_ROOT / "src" / "core" / "examples"
    episodes = []
    for f in sorted(examples_dir.glob("*.json")):
        try:
            data_raw = json.loads(f.read_text())
            if isinstance(data_raw, list):
                episodes.extend(data_raw)
            elif isinstance(data_raw, dict):
                episodes.append(data_raw)
        except (json.JSONDecodeError, OSError):
            continue
    # Filter to only episode dicts (must have episodeId)
    episodes = [ep for ep in episodes if isinstance(ep, dict) and "episodeId" in ep]

    if not episodes:
        data = {"error": "no sample episodes found"}
    else:
        dlr = DLRBuilder()
        dlr.from_episodes(episodes)

        rs = ReflectionSession("site-content")
        rs.ingest(episodes)

        ds = DriftSignalCollector()
        mg = MemoryGraph()
        for ep in episodes:
            mg.add_episode(ep)

        collector = MetricsCollector(
            dlr_builder=dlr, rs=rs, ds=ds, mg=mg,
        )
        report = collector.collect()
        data = json.loads(report.to_json())

    path = output_dir / "metrics.json"
    path.write_text(json.dumps(data, indent=2, default=str) + "\n")
    return path


def main() -> None:
    output_dir = REPO_ROOT / "docs" / "site" / "data"
    output_dir.mkdir(parents=True, exist_ok=True)

    demo_path = generate_demo_json(output_dir)
    print(f"  demo.json    -> {demo_path}")

    metrics_path = generate_metrics_json(output_dir)
    print(f"  metrics.json -> {metrics_path}")


if __name__ == "__main__":
    main()
