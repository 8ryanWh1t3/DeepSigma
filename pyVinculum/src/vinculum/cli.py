from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .authority import AuthorityGrant
from .constraints import Constraint
from .engine import VinculumEngine
from .evidence import EvidenceRecord
from .governance import GovernanceContext, GovernancePolicy
from .models import Hypothesis
from .provenance import ProvenanceRecord


def _policy_from_dict(data: dict[str, Any] | None) -> GovernancePolicy:
    if not data:
        return GovernancePolicy.compatibility()
    if data.get("mode") == "strict":
        base = GovernancePolicy.strict().to_dict()
        base.update({k: v for k, v in data.items() if k != "mode"})
        return GovernancePolicy(**base)
    cleaned = {k: v for k, v in data.items() if k != "mode"}
    return GovernancePolicy(**cleaned)


def _load_scenario(
    path: Path,
) -> tuple[list[Hypothesis], list[Constraint], GovernanceContext, GovernancePolicy]:
    data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    hypotheses = [Hypothesis(**item) for item in data.get("hypotheses", [])]
    constraints = [Constraint(**item) for item in data.get("constraints", [])]
    evidence = [EvidenceRecord(**item) for item in data.get("evidence", [])]
    provenance = []
    for item in data.get("provenance", []):
        item = dict(item)
        if "payload" in item:
            payload = item.pop("payload")
            provenance.append(ProvenanceRecord.from_payload(payload=payload, **item))
        else:
            provenance.append(ProvenanceRecord(**item))
    authorities = [AuthorityGrant(**item) for item in data.get("authorities", [])]
    ctx_meta = data.get("context", {})
    context = GovernanceContext(
        evidence=evidence,
        provenance=provenance,
        authorities=authorities,
        context_id=str(ctx_meta.get("id", "")),
        metadata=ctx_meta.get("metadata", {}),
    )
    policy = _policy_from_dict(data.get("governance_policy"))
    return hypotheses, constraints, context, policy


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="vinculum",
        description="Evaluate bounded-coherence scenarios with optional evidence/provenance/authority governance.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    evaluate = sub.add_parser("evaluate", help="Evaluate a JSON scenario")
    evaluate.add_argument("scenario", type=Path)
    evaluate.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
    evaluate.add_argument(
        "--strict-governance",
        action="store_true",
        help="Override scenario policy with STRICT_V0_2 governance gates",
    )

    args = parser.parse_args(argv)

    if args.command == "evaluate":
        hypotheses, constraints, context, policy = _load_scenario(args.scenario)
        if args.strict_governance:
            policy = GovernancePolicy.strict()
        report = VinculumEngine(governance_policy=policy).bind(
            hypotheses, constraints, context=context
        )
        output = report.to_dict()
        output["sha256"] = report.sha256()
        print(json.dumps(output, indent=2 if args.pretty else None, sort_keys=True))
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
