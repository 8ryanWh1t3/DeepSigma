"""CLI for the Deep Sigma OpenShell bridge."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml

from .compiler import OpenShellPolicyCompiler, diff_policies
from .loader import load_contract


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="deepsigma-openshell")
    sub = p.add_subparsers(dest="command", required=True)

    c = sub.add_parser("compile", help="compile a mission contract to OpenShell policy YAML")
    c.add_argument("contract")
    c.add_argument("--out", required=True)
    c.add_argument("--dko-out")

    d = sub.add_parser("diff", help="classify an OpenShell policy delta")
    d.add_argument("old")
    d.add_argument("new")

    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "compile":
        contract = load_contract(args.contract)
        projection = OpenShellPolicyCompiler().compile(contract)
        Path(args.out).write_text(projection.yaml_text, encoding="utf-8")
        if args.dko_out:
            Path(args.dko_out).write_text(
                json.dumps(contract.to_dko(), indent=2, sort_keys=True),
                encoding="utf-8",
            )
        print(json.dumps({
            "contract_id": contract.contract_id,
            "contract_hash": projection.contract_hash,
            "policy_hash": projection.policy_hash,
            "out": str(Path(args.out)),
        }, indent=2))
        return 0

    if args.command == "diff":
        old = yaml.safe_load(Path(args.old).read_text(encoding="utf-8")) or {}
        new = yaml.safe_load(Path(args.new).read_text(encoding="utf-8")) or {}
        delta = diff_policies(old, new)
        print(json.dumps({
            "static_changed": delta.static_changed,
            "dynamic_changed": delta.dynamic_changed,
            "expands_access": delta.expands_access,
            "requires_recreate": delta.requires_recreate,
            "reasons": delta.reasons,
        }, indent=2))
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
