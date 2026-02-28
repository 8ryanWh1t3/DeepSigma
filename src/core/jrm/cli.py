"""JRM CLI command handlers — wire into ``coherence jrm`` subparser group."""

from __future__ import annotations

import argparse
import json
import sys
import zipfile
from pathlib import Path
from typing import Any, Dict, List


def register_jrm_commands(subparsers: argparse._SubParsersAction) -> None:
    """Register JRM subcommands on the core CLI."""
    p_jrm = subparsers.add_parser("jrm", help="Judgment Refinement Module operations")
    jrm_sub = p_jrm.add_subparsers(dest="jrm_command", required=True)

    # ── jrm ingest ───────────────────────────────────────────────
    p_ingest = jrm_sub.add_parser("ingest", help="Normalize raw events via adapter")
    p_ingest.add_argument("--adapter", required=True,
                          help="Adapter name (suricata_eve, snort_fastlog, copilot_agent)")
    p_ingest.add_argument("--in", dest="input_file", required=True,
                          help="Path to raw event file")
    p_ingest.add_argument("--out", dest="output_file", required=True,
                          help="Path to write normalized NDJSON")
    p_ingest.add_argument("--env", default="default", help="Environment ID")
    p_ingest.add_argument("--json", action="store_true", dest="json_output",
                          help="Output summary as JSON")
    p_ingest.set_defaults(func=cmd_jrm_ingest)

    # ── jrm run ──────────────────────────────────────────────────
    p_run = jrm_sub.add_parser("run", help="Run JRM pipeline on normalized events")
    p_run.add_argument("--in", dest="input_file", required=True,
                       help="Path to normalized NDJSON file")
    p_run.add_argument("--env", default="default", help="Environment ID")
    p_run.add_argument("--packet-out", dest="packet_out", default="./jrm_packets",
                       help="Output directory for packets")
    p_run.add_argument("--roll-events", type=int, default=50000,
                       help="Max events per packet part")
    p_run.add_argument("--roll-mb", type=int, default=25,
                       help="Max zip size in MB per packet part")
    p_run.add_argument("--json", action="store_true", dest="json_output",
                       help="Output summary as JSON")
    p_run.set_defaults(func=cmd_jrm_run)

    # ── jrm validate ─────────────────────────────────────────────
    p_validate = jrm_sub.add_parser("validate", help="Validate a JRM-X packet")
    p_validate.add_argument("packet", help="Path to JRM-X packet zip")
    p_validate.add_argument("--json", action="store_true", dest="json_output",
                            help="Output as JSON")
    p_validate.set_defaults(func=cmd_jrm_validate)

    # ── jrm adapters ─────────────────────────────────────────────
    p_adapters = jrm_sub.add_parser("adapters", help="List available adapters")
    p_adapters.add_argument("--json", action="store_true", dest="json_output",
                            help="Output as JSON")
    p_adapters.set_defaults(func=cmd_jrm_adapters)

    # ── Extension hooks ──────────────────────────────────────────
    try:
        from .hooks.registry import get_cli_hooks
        for hook in get_cli_hooks():
            hook(jrm_sub)
    except ImportError:
        pass


# ── Command implementations ──────────────────────────────────────


def cmd_jrm_ingest(args: argparse.Namespace) -> None:
    from core.jrm.adapters.registry import get_adapter
    from core.jrm.types import JRMEvent

    AdapterCls = get_adapter(args.adapter)
    adapter = AdapterCls()

    input_path = Path(args.input_file)
    if not input_path.exists():
        print(f"Error: {input_path} not found", file=sys.stderr)
        sys.exit(1)

    output_path = Path(args.output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    count = 0
    with open(input_path, "r", encoding="utf-8", errors="replace") as fin, \
         open(output_path, "w", encoding="utf-8") as fout:
        for event in adapter.parse_stream(fin, environment_id=args.env):
            fout.write(json.dumps(event.to_dict(), sort_keys=True) + "\n")
            count += 1

    summary = {"adapter": args.adapter, "input": str(input_path),
               "output": str(output_path), "events": count}
    if args.json_output:
        print(json.dumps(summary, indent=2))
    else:
        print(f"Ingested {count} events from {input_path} -> {output_path}")


def cmd_jrm_run(args: argparse.Namespace) -> None:
    from .types import EventType, JRMEvent, Severity
    from .pipeline.runner import PipelineRunner
    from .packet.builder import RollingPacketBuilder

    input_path = Path(args.input_file)
    if not input_path.exists():
        print(f"Error: {input_path} not found", file=sys.stderr)
        sys.exit(1)

    runner = PipelineRunner(environment_id=args.env)
    builder = RollingPacketBuilder(
        environment_id=args.env,
        output_dir=args.packet_out,
        max_events=args.roll_events,
        max_zip_bytes=args.roll_mb * 1024 * 1024,
    )

    # Read normalized NDJSON and reconstruct JRMEvent objects
    events: List[JRMEvent] = []
    with open(input_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            events.append(JRMEvent(
                event_id=d["eventId"],
                source_system=d["sourceSystem"],
                event_type=EventType(d["eventType"]),
                timestamp=d["timestamp"],
                severity=Severity(d["severity"]),
                actor=d["actor"],
                object=d["object"],
                action=d["action"],
                confidence=d["confidence"],
                evidence_hash=d["evidenceHash"],
                raw_pointer=d["rawPointer"],
                environment_id=d["environmentId"],
                assumptions=d.get("assumptions", []),
                metadata=d.get("metadata", {}),
            ))

    packets_built: List[str] = []

    # Process in batches matching roll-events
    batch_size = args.roll_events
    for i in range(0, len(events), batch_size):
        batch = events[i : i + batch_size]
        result = runner.run(batch)
        packet_path = builder.add(result)
        if packet_path:
            packets_built.append(str(packet_path))

    # Final flush
    final = builder.flush()
    if final:
        packets_built.append(str(final))

    summary = {
        "environment": args.env,
        "totalEvents": len(events),
        "packetsBuilt": len(packets_built),
        "packets": packets_built,
    }
    if args.json_output:
        print(json.dumps(summary, indent=2))
    else:
        print(f"Processed {len(events)} events for env={args.env}")
        for p in packets_built:
            print(f"  Packet: {p}")


def cmd_jrm_validate(args: argparse.Namespace) -> None:
    from .packet.manifest import compute_file_hash

    packet_path = Path(args.packet)
    if not packet_path.exists():
        print(f"Error: {packet_path} not found", file=sys.stderr)
        sys.exit(1)

    required_files = {
        "truth_snapshot.json",
        "authority_slice.json",
        "decision_lineage.jsonl",
        "drift_signal.jsonl",
        "memory_graph.json",
        "canon_entry.json",
        "manifest.json",
    }

    errors: List[str] = []

    try:
        with zipfile.ZipFile(packet_path, "r") as zf:
            names = set(zf.namelist())

            # Check required files
            missing = required_files - names
            if missing:
                errors.append(f"Missing files: {sorted(missing)}")

            # Validate manifest hashes
            if "manifest.json" in names:
                manifest = json.loads(zf.read("manifest.json"))
                file_hashes = manifest.get("files", {})
                for fname, expected_hash in file_hashes.items():
                    if fname in names:
                        actual = compute_file_hash(zf.read(fname))
                        if actual != expected_hash:
                            errors.append(
                                f"Hash mismatch for {fname}: "
                                f"expected {expected_hash}, got {actual}"
                            )
                    else:
                        errors.append(f"File listed in manifest but missing: {fname}")
    except zipfile.BadZipFile:
        errors.append("Not a valid zip file")

    result = {
        "packet": str(packet_path),
        "valid": len(errors) == 0,
        "errors": errors,
    }

    if args.json_output:
        print(json.dumps(result, indent=2))
    else:
        if errors:
            print(f"INVALID: {packet_path}")
            for e in errors:
                print(f"  - {e}")
        else:
            print(f"VALID: {packet_path}")


def cmd_jrm_adapters(args: argparse.Namespace) -> None:
    from core.jrm.adapters.registry import list_adapters

    adapters = list_adapters()
    if args.json_output:
        print(json.dumps({"adapters": adapters}))
    else:
        print("Available JRM adapters:")
        for name in adapters:
            print(f"  - {name}")
