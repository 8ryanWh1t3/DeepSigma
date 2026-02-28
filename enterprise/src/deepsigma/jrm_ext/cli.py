"""JRM enterprise CLI — federation, gate, hub, advisory commands."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import List


def register(subparsers: argparse._SubParsersAction) -> None:
    """Register JRM enterprise subcommands on the ``deepsigma`` CLI."""
    p_jrm = subparsers.add_parser("jrm", help="JRM enterprise operations")
    jrm_sub = p_jrm.add_subparsers(dest="jrm_ext_command", required=True)

    # ── jrm federate ─────────────────────────────────────────────
    p_fed = jrm_sub.add_parser("federate", help="Federate JRM-X packets")
    p_fed.add_argument("--packets", nargs="+", required=True,
                       help="Paths to JRM-X packet zips")
    p_fed.add_argument("--out", default="federation_report.json",
                       help="Output federation report path")
    p_fed.add_argument("--json", action="store_true", dest="json_output")
    p_fed.set_defaults(func=cmd_federate)

    # ── jrm gate ─────────────────────────────────────────────────
    p_gate = jrm_sub.add_parser("gate", help="JRM gate operations")
    gate_sub = p_gate.add_subparsers(dest="gate_command", required=True)

    p_gate_validate = gate_sub.add_parser("validate", help="Validate packet")
    p_gate_validate.add_argument("--packet", required=True, help="Packet zip path")
    p_gate_validate.add_argument("--json", action="store_true", dest="json_output")
    p_gate_validate.set_defaults(func=cmd_gate_validate)

    # ── jrm hub ──────────────────────────────────────────────────
    p_hub = jrm_sub.add_parser("hub", help="JRM hub operations")
    hub_sub = p_hub.add_subparsers(dest="hub_command", required=True)

    p_hub_replay = hub_sub.add_parser("replay", help="Replay packets through hub")
    p_hub_replay.add_argument("--packets", nargs="+", required=True)
    p_hub_replay.add_argument("--out", default="hub_state.json")
    p_hub_replay.add_argument("--json", action="store_true", dest="json_output")
    p_hub_replay.set_defaults(func=cmd_hub_replay)

    # ── jrm advisory ─────────────────────────────────────────────
    p_adv = jrm_sub.add_parser("advisory", help="JRM advisory operations")
    adv_sub = p_adv.add_subparsers(dest="advisory_command", required=True)

    p_adv_pub = adv_sub.add_parser("publish", help="Publish advisories from report")
    p_adv_pub.add_argument("--from", dest="from_file", required=True,
                           help="Federation report path")
    p_adv_pub.add_argument("--out", default="advisories.json")
    p_adv_pub.add_argument("--json", action="store_true", dest="json_output")
    p_adv_pub.set_defaults(func=cmd_advisory_publish)


def cmd_federate(args: argparse.Namespace) -> int:
    from .federation.hub import JRMHub

    hub = JRMHub()
    hub.ingest(args.packets)
    report = hub.produce_report()

    out_path = Path(args.out)
    out_path.write_text(json.dumps(report, indent=2, default=str))

    if args.json_output:
        print(json.dumps(report, indent=2, default=str))
    else:
        print(f"Federation report: {out_path}")
        print(f"  Environments: {report['environments']}")
        print(f"  Packets ingested: {report['packetsIngested']}")
        print(f"  Cross-env drifts: {len(report['crossEnvDrifts'])}")
    return 0


def cmd_gate_validate(args: argparse.Namespace) -> int:
    from .federation.gate import JRMGate

    gate = JRMGate()
    result = gate.validate(args.packet)

    output = {
        "packet": args.packet,
        "accepted": result.accepted,
        "reasonCode": result.reason_code,
        "violations": result.violations,
    }

    if args.json_output:
        print(json.dumps(output, indent=2))
    else:
        status = "ACCEPTED" if result.accepted else "REJECTED"
        print(f"Gate: {status} — {args.packet}")
        for v in result.violations:
            print(f"  - {v}")
    return 0 if result.accepted else 1


def cmd_hub_replay(args: argparse.Namespace) -> int:
    from .federation.hub import JRMHub

    hub = JRMHub()
    hub.ingest(args.packets)
    report = hub.produce_report()

    out_path = Path(args.out)
    out_path.write_text(json.dumps(report, indent=2, default=str))

    if args.json_output:
        print(json.dumps(report, indent=2, default=str))
    else:
        print(f"Hub state: {out_path}")
    return 0


def cmd_advisory_publish(args: argparse.Namespace) -> int:
    from .federation.advisory import AdvisoryEngine
    from .types import CrossEnvDrift, CrossEnvDriftType
    from dataclasses import asdict

    report_path = Path(args.from_file)
    if not report_path.exists():
        print(f"Error: {report_path} not found", file=sys.stderr)
        return 1

    report = json.loads(report_path.read_text())
    drifts = []
    for d in report.get("crossEnvDrifts", []):
        drifts.append(CrossEnvDrift(
            drift_id=d["driftId"],
            drift_type=CrossEnvDriftType(d["driftType"]),
            severity=d["severity"],
            environments=d["environments"],
            signature_id=d.get("signatureId", ""),
            detail=d.get("detail", ""),
        ))

    engine = AdvisoryEngine()
    advisories = engine.publish(drifts)

    output = [asdict(a) for a in advisories]
    out_path = Path(args.out)
    out_path.write_text(json.dumps(output, indent=2, default=str))

    if args.json_output:
        print(json.dumps(output, indent=2, default=str))
    else:
        print(f"Published {len(advisories)} advisories -> {out_path}")
        for a in advisories:
            print(f"  [{a.advisory_id}] {a.drift_type}: {a.recommendation[:60]}")
    return 0
