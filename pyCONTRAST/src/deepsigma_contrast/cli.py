from __future__ import annotations

import argparse
import json
from pathlib import Path

from .cerpa import to_cerpa_handoff
from .compare import ContrastEngine
from .memory import episode_from_dict
from .models import Assumption, Episode, EvidenceRef, Outcome


def _load(path: str) -> Episode:
    return episode_from_dict(json.loads(Path(path).read_text(encoding="utf-8")))


def _demo() -> tuple[Episode, Episode]:
    prior = Episode(
        id="EP-001",
        title="Stable coverage",
        claim="Sensor coverage is sufficient.",
        decision="Maintain current posture.",
        rationale="Observed coverage and uptime met threshold.",
        assumptions=[
            Assumption(id="A1", statement="Sensor A is continuously available", confidence=0.90),
        ],
        outcome=Outcome(status="SUCCESS", summary="Coverage remained stable.", metrics={"coverage": 0.96}),
        evidence=[EvidenceRef(id="EV-1", uri="memory://ev-1", weight=0.9)],
        tags={"C-UAS", "coverage"},
        entities=["Sensor-A", "Sector-1"],
        metadata={"weather": "clear"},
    )
    current = Episode(
        id="EP-002",
        title="Coverage degradation",
        claim="Sensor coverage is sufficient.",
        decision="Maintain current posture.",
        rationale="Historical coverage had been stable.",
        assumptions=[
            Assumption(id="A1", statement="Sensor A is continuously available", confidence=0.40),
        ],
        outcome=Outcome(status="DEGRADED", summary="Coverage gap emerged.", metrics={"coverage": 0.68}),
        evidence=[EvidenceRef(id="EV-2", uri="memory://ev-2", weight=0.95)],
        tags={"C-UAS", "coverage"},
        entities=["Sensor-A", "Sector-1"],
        metadata={"weather": "heavy-rain"},
    )
    return prior, current


def main() -> None:
    parser = argparse.ArgumentParser(prog="deepsigma-contrast")
    sub = parser.add_subparsers(dest="command", required=True)

    compare = sub.add_parser("compare", help="Compare prior and current episode JSON files.")
    compare.add_argument("prior")
    compare.add_argument("current")
    compare.add_argument("--cerpa", action="store_true", help="Also emit a CERPA handoff.")

    sub.add_parser("demo", help="Run the built-in deterministic demonstration.")

    args = parser.parse_args()

    if args.command == "compare":
        prior = _load(args.prior)
        current = _load(args.current)
    else:
        prior, current = _demo()

    result = ContrastEngine().compare(current_episode=current, prior_episode=prior)
    payload = {"contrast": result.to_dict()}
    if getattr(args, "cerpa", False):
        payload["cerpa"] = to_cerpa_handoff(result).to_dict()
    print(json.dumps(payload, indent=2, sort_keys=True, default=str))


if __name__ == "__main__":
    main()
