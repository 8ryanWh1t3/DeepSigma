#!/usr/bin/env python3
"""Credibility Engine Simulation - Runner.

Drives the simulation engine in a tick loop, writing JSON snapshots
to the dashboard directory for live visualization.

Usage:
    python runner.py --scenario day0
    python runner.py --scenario day2 --interval 2 --output-dir ../../dashboard/credibility-engine-demo

Abstract institutional credibility architecture.
No real-world system modeled.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import time
from pathlib import Path

# Ensure sim package is importable
sys.path.insert(0, str(Path(__file__).parent))

from engine import CredibilityEngine
from packet import generate_packet
from scenarios import SCENARIOS

# Default output directory (relative to this file)
DEFAULT_OUTPUT = str(
    Path(__file__).parent.parent.parent / "dashboard" / "credibility-engine-demo"
)

# Scenario hot-reload file (optional)
SCENARIO_FILE = "scenario.json"


def write_atomic(filepath: str, data: dict) -> None:
    """Write JSON atomically: write temp file, then rename."""
    dir_path = os.path.dirname(filepath)
    fd, tmp_path = tempfile.mkstemp(dir=dir_path, suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(data, f, indent=2)
            f.write("\n")
        os.replace(tmp_path, filepath)
    except Exception:
        # Clean up temp file on error
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def check_scenario_switch(engine: CredibilityEngine, output_dir: str) -> None:
    """Check for scenario.json hot-reload file."""
    scenario_path = os.path.join(output_dir, SCENARIO_FILE)
    if os.path.exists(scenario_path):
        try:
            with open(scenario_path) as f:
                data = json.load(f)
            new_scenario = data.get("scenario", "").strip()
            if new_scenario and new_scenario in SCENARIOS:
                if new_scenario != engine.scenario_name:
                    print(f"\n  Switching scenario: {engine.scenario_name} -> {new_scenario}")
                    engine.set_scenario(new_scenario)
            os.unlink(scenario_path)
        except (json.JSONDecodeError, KeyError, OSError):
            pass


def print_status(engine: CredibilityEngine, tick: int) -> None:
    """Print a compact status line."""
    idx = engine.credibility_index
    band = engine.index_band

    # Color codes
    if idx >= 95:
        color = "\033[92m"  # green
    elif idx >= 85:
        color = "\033[93m"  # yellow
    elif idx >= 70:
        color = "\033[91m"  # red
    elif idx >= 50:
        color = "\033[91m"  # red
    else:
        color = "\033[91;1m"  # bold red
    reset = "\033[0m"

    unknown = sum(1 for c in engine.claims if c.status == "UNKNOWN")
    degraded = sum(1 for c in engine.claims if c.status == "DEGRADED")
    max_corr = max(c.coefficient for c in engine.clusters)
    drift = engine.drift_total

    claims_str = ""
    if unknown:
        claims_str += f" UNK:{unknown}"
    if degraded:
        claims_str += f" DEG:{degraded}"
    if not claims_str:
        claims_str = " ALL OK"

    print(
        f"  [{tick:4d}] "
        f"CI: {color}{idx:3d}{reset} ({band:<24s}) "
        f"| Drift: {drift:5d} "
        f"| Corr: {max_corr:.2f} "
        f"| Claims:{claims_str} "
        f"| Sim: {engine.sim_time.strftime('%H:%M')}",
        flush=True,
    )


def _sync_to_runtime(sim_engine, runtime_engine) -> None:
    """Push simulation state into the runtime credibility engine."""
    from credibility_engine.packet import generate_credibility_packet

    # Sync claims
    for sim_claim in sim_engine.claims:
        runtime_engine.update_claim_state(
            sim_claim.claim_id,
            state=sim_claim.status,
            confidence=sim_claim.confidence,
            margin=sim_claim.margin,
            ttl_remaining=sim_claim.ttl_remaining_minutes,
        )

    # Sync correlations
    for sim_cluster in sim_engine.clusters:
        runtime_engine.update_correlation(
            sim_cluster.cluster_id,
            coefficient=sim_cluster.coefficient,
        )

    # Sync sync regions
    for sim_sr in sim_engine.sync_regions:
        runtime_engine.update_sync(
            sim_sr.region,
            time_skew_ms=sim_sr.time_skew_ms,
            watermark_lag_s=sim_sr.watermark_lag_s,
            replay_flags=sim_sr.replay_flags_count,
        )

    # Recalculate and persist
    runtime_engine.recalculate_index()
    runtime_engine.generate_snapshot()
    generate_credibility_packet(runtime_engine)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Credibility Engine Simulation Runner",
    )
    parser.add_argument(
        "--scenario",
        choices=list(SCENARIOS.keys()),
        default="day0",
        help="Scenario to run (default: day0)",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=2.0,
        help="Seconds between ticks (default: 2)",
    )
    parser.add_argument(
        "--output-dir",
        default=DEFAULT_OUTPUT,
        help="Directory to write JSON snapshots",
    )
    parser.add_argument(
        "--mode",
        choices=["json", "engine"],
        default="json",
        help="Output mode: 'json' writes files (default), 'engine' drives runtime engine",
    )
    args = parser.parse_args()

    output_dir = os.path.abspath(args.output_dir)
    if args.mode == "json" and not os.path.isdir(output_dir):
        print(f"Error: output directory does not exist: {output_dir}")
        sys.exit(1)

    # Initialize runtime engine if in engine mode
    runtime_engine = None
    if args.mode == "engine":
        try:
            from credibility_engine.engine import CredibilityEngine as RuntimeEngine
            from credibility_engine.store import CredibilityStore

            store = CredibilityStore()
            runtime_engine = RuntimeEngine(store=store)
            runtime_engine.initialize_default_state()
        except ImportError:
            print("Error: credibility_engine module not found. Use --mode json instead.")
            sys.exit(1)

    engine = CredibilityEngine(args.scenario)
    scenario_desc = engine.scenario["description"]

    mode_label = "ENGINE (runtime)" if args.mode == "engine" else "JSON (file)"

    print()
    print("  ╔══════════════════════════════════════════════════════╗")
    print("  ║   Σ OVERWATCH — Credibility Engine Simulation       ║")
    print("  ╚══════════════════════════════════════════════════════╝")
    print()
    print(f"  Scenario:  {args.scenario} — {scenario_desc}")
    print(f"  Mode:      {mode_label}")
    print(f"  Interval:  {args.interval}s per tick (15 min sim time)")
    print(f"  Output:    {output_dir}")
    print("  Dashboard: http://localhost:8000/dashboard/credibility-engine-demo/")
    print()
    print("  Press Ctrl+C to stop.")
    print()
    print(
        f"  {'Tick':>6s}  {'CI':>3s}  {'Band':<24s}  "
        f"{'Drift':>5s}  {'Corr':>5s}  {'Claims':<12s}  {'SimTime':<6s}"
    )
    print("  " + "-" * 80)

    try:
        while True:
            # Check for hot-reload scenario switch
            check_scenario_switch(engine, output_dir)

            # Advance simulation
            engine.tick()

            if args.mode == "engine" and runtime_engine is not None:
                # Drive runtime engine with simulation state
                _sync_to_runtime(engine, runtime_engine)
            else:
                # Generate all snapshots
                snapshots = engine.all_snapshots()
                packet = generate_packet(engine)

                # Write all files atomically
                for name, data in snapshots.items():
                    filepath = os.path.join(output_dir, f"{name}.json")
                    write_atomic(filepath, data)
                write_atomic(
                    os.path.join(output_dir, "credibility_packet_example.json"),
                    packet,
                )

            # Print status
            print_status(engine, engine.tick_num)

            # Sleep
            time.sleep(args.interval)

    except KeyboardInterrupt:
        print("\n")
        print("  Simulation stopped.")
        print(f"  Final CI: {engine.credibility_index} ({engine.index_band})")
        print(f"  Total ticks: {engine.tick_num}")
        print(f"  Total drift: {engine.drift_total}")
        print()


if __name__ == "__main__":
    main()
