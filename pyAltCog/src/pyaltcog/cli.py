from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .clustering import cluster_signals
from .engine import AltCogEngine
from .models import (
    AltCogCandidatePacket,
    AlternativeKind,
    CandidateScore,
    DiscoverySurface,
    EvidenceItem,
    FrictionSignalRecord,
    MaturityState,
    Prediction,
)
from .scoring import score_candidate
from .serde import load_json, to_primitive


def _signal_from_dict(d: dict[str, Any]) -> FrictionSignalRecord:
    return FrictionSignalRecord(
        id=d["id"],
        stream_id=d["stream_id"],
        surface=DiscoverySurface(d["surface"]),
        statement=d["statement"],
        source=d.get("source", ""),
        detected_at=d.get("detected_at", ""),
        maturity=MaturityState(d.get("maturity", "AC1")),
        strength=float(d.get("strength", 0.5)),
        tags=list(d.get("tags", [])),
        domain=d.get("domain", ""),
        metadata=dict(d.get("metadata", {})),
    )


def _candidate_from_dict(d: dict[str, Any]) -> AltCogCandidatePacket:
    predictions = [Prediction(**p) for p in d.get("predictions", [])]
    evidence = [EvidenceItem(**e) for e in d.get("evidence", [])]
    return AltCogCandidatePacket(
        id=d["id"],
        stream_id=d["stream_id"],
        cluster_id=d["cluster_id"],
        dominant_model=d["dominant_model"],
        hypothesis=d["hypothesis"],
        created_at=d["created_at"],
        kind=AlternativeKind(d.get("kind", "structural")),
        maturity=MaturityState(d.get("maturity", "AC4")),
        signal_ids=list(d.get("signal_ids", [])),
        evidence=evidence,
        predictions=predictions,
        falsification_conditions=list(d.get("falsification_conditions", [])),
        mission_relevance=float(d.get("mission_relevance", 0.0)),
        owner=d.get("owner", ""),
        revisit_trigger=d.get("revisit_trigger", ""),
        metadata=dict(d.get("metadata", {})),
    )


def cmd_demo(_: argparse.Namespace) -> int:
    engine = AltCogEngine()
    s1 = engine.capture_friction(
        stream_id="DEMO-01",
        surface=DiscoverySurface.OUTCOME_MISMATCH,
        statement="Expected track continuity; identity reset after handoff.",
        source="demo-log",
        strength=0.8,
        tags=["track", "identity", "handoff"],
        domain="C-UAS",
    )
    s2 = engine.capture_friction(
        stream_id="DEMO-01",
        surface=DiscoverySurface.REPEATED_EXCEPTION,
        statement="A second identity reset occurred after the same handoff condition.",
        source="demo-log",
        strength=0.85,
        tags=["identity", "handoff", "reset"],
        domain="C-UAS",
    )
    cluster = engine.cluster([s1, s2], min_similarity=0.10)[0]
    evidence = EvidenceItem(
        id="EVID-DEMO-1",
        statement="Two independent handoff events produced the same reset pattern.",
        source="demo-log",
        confidence=0.9,
    )
    candidate = engine.create_candidate(
        cluster=cluster,
        dominant_model="Identity resets are random sensor noise.",
        hypothesis="Identity resets correlate with a recurring handoff condition.",
        prediction=Prediction(
            variable="reset_rate_after_handoff",
            dominant_expected="no systematic increase",
            alternative_expected="measurable increase",
        ),
        evidence=[evidence],
        mission_relevance=0.9,
        owner="BLUE-TEAM",
        revisit_trigger="next handoff event",
    )
    candidate = engine.score(candidate)
    candidate = engine.promote_if_ready(candidate)
    out = {
        "candidate": to_primitive(candidate),
        "plan": to_primitive(engine.plan(candidate)),
        "ledger_verified": engine.ledger.verify(),
    }
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0


def cmd_cluster(args: argparse.Namespace) -> int:
    raw = load_json(args.path)
    signals = [_signal_from_dict(d) for d in raw]
    clusters = cluster_signals(signals, min_similarity=args.min_similarity, created_at="")
    print(json.dumps(to_primitive(clusters), indent=2, sort_keys=True))
    return 0


def cmd_score(args: argparse.Namespace) -> int:
    d = load_json(args.path)
    candidate = _candidate_from_dict(d)
    candidate.score = score_candidate(candidate)
    print(json.dumps(to_primitive(candidate), indent=2, sort_keys=True))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="pyaltcog", description="Deep Sigma AltCogOps runtime library")
    sub = p.add_subparsers(dest="command", required=True)

    demo = sub.add_parser("demo", help="run a deterministic end-to-end AltCog demo")
    demo.set_defaults(func=cmd_demo)

    cluster = sub.add_parser("cluster", help="cluster FSR JSON records")
    cluster.add_argument("path", type=Path)
    cluster.add_argument("--min-similarity", type=float, default=0.25)
    cluster.set_defaults(func=cmd_cluster)

    score = sub.add_parser("score", help="score an ACP JSON document")
    score.add_argument("path", type=Path)
    score.set_defaults(func=cmd_score)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
