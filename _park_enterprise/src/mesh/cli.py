"""Mesh CLI — Command-line interface for mesh operations.

Usage:
    python -m mesh.cli init --tenant tenant-alpha
    python -m mesh.cli run --tenant tenant-alpha --scenario healthy
    python -m mesh.cli scenario --tenant tenant-alpha --mode day3
    python -m mesh.cli verify --tenant tenant-alpha

Abstract institutional credibility architecture.
No real-world system modeled.
"""

from __future__ import annotations

import argparse
import sys

from mesh.crypto import BACKEND, DEMO_MODE
from mesh.scenarios import MeshScenario
from mesh.verify import full_verification


def cmd_init(args: argparse.Namespace) -> None:
    """Initialize mesh nodes for a tenant."""
    tenant_id = args.tenant
    print(f"Initializing mesh for tenant: {tenant_id}")
    print(f"  Crypto backend: {BACKEND}" + (" (DEMO MODE)" if DEMO_MODE else ""))

    scenario = MeshScenario(tenant_id=tenant_id)
    nodes = scenario.init_nodes()

    print(f"  Created {len(nodes)} nodes:")
    for n in nodes:
        print(f"    {n['node_id']:20s} region={n['region_id']:12s} role={n['role']}")
    print("  Init complete.")


def cmd_run(args: argparse.Namespace) -> None:
    """Run mesh with a specific scenario phase."""
    tenant_id = args.tenant
    scenario_name = args.scenario or "healthy"
    cycles = args.cycles or 3

    phase_map = {
        "healthy": 0,
        "partition": 1,
        "correlated_failure": 2,
        "correlated-failure": 2,
        "recovery": 3,
    }
    phase = phase_map.get(scenario_name)
    if phase is None:
        print(f"Unknown scenario: {scenario_name}")
        print(f"Available: {', '.join(phase_map.keys())}")
        sys.exit(1)

    print(f"Running mesh scenario: {scenario_name} (phase {phase})")
    print(f"  Tenant: {tenant_id}")
    print(f"  Cycles: {cycles}")
    print(f"  Crypto: {BACKEND}" + (" (DEMO)" if DEMO_MODE else ""))

    scenario = MeshScenario(tenant_id=tenant_id)
    scenario.init_nodes()

    results = scenario.run_phase(phase, cycles=cycles)
    _print_phase_results(scenario_name, results)


def cmd_scenario(args: argparse.Namespace) -> None:
    """Run the full day-3 scenario (all 4 phases)."""
    tenant_id = args.tenant
    cycles = args.cycles or 3

    print("Running full mesh scenario (4 phases)")
    print(f"  Tenant: {tenant_id}")
    print(f"  Cycles per phase: {cycles}")
    print(f"  Crypto: {BACKEND}" + (" (DEMO)" if DEMO_MODE else ""))
    print()

    scenario = MeshScenario(tenant_id=tenant_id)
    scenario.init_nodes()

    report = scenario.run_all_phases(cycles_per_phase=cycles)

    for phase_name, phase_data in report["phases"].items():
        print(f"--- Phase: {phase_name} ---")
        _print_phase_results(phase_name, phase_data["results"])
        print()

    print(f"Scenario complete. Total events: {report['total_events']}")
    print(f"  Started: {report['started_at']}")
    print(f"  Completed: {report['completed_at']}")


def cmd_verify(args: argparse.Namespace) -> None:
    """Run verification checks."""
    tenant_id = args.tenant
    print(f"Verifying mesh integrity for tenant: {tenant_id}")
    print()

    report = full_verification(tenant_id)

    # Envelope signatures
    sig = report["envelope_signatures"]
    print(f"Envelope Signatures: {sig['status']}")
    print(f"  Checked: {sig['total_checked']}")
    print(f"  Passed:  {sig['total_passed']}")
    print(f"  Failed:  {sig['total_failed']}")
    if sig.get("nodes"):
        for node in sig["nodes"]:
            status = "OK" if node["failed"] == 0 else "FAIL"
            print(f"    {node['node_id']:20s} {status} ({node['envelopes_checked']} envelopes)")
    print()

    # Seal chain
    chain = report["seal_chain"]
    print(f"Seal Chain: {chain['status']}")
    print(f"  Total seals: {chain['total_seals']}")
    print(f"  Chain breaks: {chain['chain_breaks']}")
    print(f"  Missing fields: {chain['missing_fields']}")
    if chain.get("chains"):
        for ch in chain["chains"]:
            status = "INTACT" if ch["chain_intact"] else "BROKEN"
            print(f"    {ch['node_id']:20s} {status} ({ch['seal_count']} seals)")
    print()

    print(f"Overall: {report['overall']}")


def _print_phase_results(phase_name: str, results: list[dict]) -> None:
    """Print phase cycle results."""
    for cycle_data in results:
        cycle = cycle_data.get("cycle", 0)
        node_results = cycle_data.get("node_results", [])

        # Find key results
        agg_result = None
        seal_result = None
        for nr in node_results:
            if nr.get("action") == "aggregate":
                agg_result = nr
            elif nr.get("action") == "seal":
                seal_result = nr

        line = f"  cycle {cycle}: "
        if agg_result:
            line += (
                f"index={agg_result.get('index_score', '?')} "
                f"band={agg_result.get('index_band', '?')} "
                f"claim={agg_result.get('claim_state', '?')} "
                f"envs={agg_result.get('envelopes_processed', 0)} "
            )
        if seal_result:
            line += f"seal={seal_result.get('seal_hash', '?')[:20]}..."
        elif seal_result is None:
            # Check for skipped seals
            for nr in node_results:
                if nr.get("action") == "seal_skip":
                    line += f"seal=skipped({nr.get('reason', '')})"

        offline = [nr["node_id"] for nr in node_results if nr.get("reason") == "offline"]
        if offline:
            line += f" offline=[{','.join(offline)}]"

        print(line)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="mesh",
        description="Distributed Credibility Mesh CLI",
    )
    sub = parser.add_subparsers(dest="command")

    # init
    p_init = sub.add_parser("init", help="Initialize mesh nodes")
    p_init.add_argument("--tenant", required=True, help="Tenant ID")

    # run
    p_run = sub.add_parser("run", help="Run a single scenario phase")
    p_run.add_argument("--tenant", required=True, help="Tenant ID")
    p_run.add_argument("--scenario", default="healthy", help="Phase name")
    p_run.add_argument("--cycles", type=int, default=3, help="Cycles to run")

    # scenario (full day3)
    p_sc = sub.add_parser("scenario", help="Run full 4-phase scenario")
    p_sc.add_argument("--tenant", required=True, help="Tenant ID")
    p_sc.add_argument("--mode", default="day3", help="Scenario mode")
    p_sc.add_argument("--cycles", type=int, default=3, help="Cycles per phase")

    # verify
    p_ver = sub.add_parser("verify", help="Verify mesh integrity")
    p_ver.add_argument("--tenant", required=True, help="Tenant ID")

    args = parser.parse_args()

    if args.command == "init":
        cmd_init(args)
    elif args.command == "run":
        cmd_run(args)
    elif args.command == "scenario":
        cmd_scenario(args)
    elif args.command == "verify":
        cmd_verify(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
