#!/usr/bin/env python3
"""Enhanced replay harness with degrade ladder re-execution. Closes #12.

Replays a sealed episode through the degrade ladder to verify
decision reproducibility and supports what-if analysis with
alternative policy packs.

Usage:
    python tools/replay_episode.py --episode data/ep_001.json
    python tools/replay_episode.py --episode data/ep_001.json --policy-pack packs/alt.json
    python tools/replay_episode.py --episode data/ep_001.json --output report.json
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict

from engine.degrade_ladder import DegradeSignal, choose_degrade_step
from engine.policy_loader import load_policy_pack, get_rules


def _reconstruct_signal(episode: Dict[str, Any]) -> DegradeSignal:
    """Reconstruct a DegradeSignal from episode telemetry."""
    telemetry = episode.get("telemetry", {})
    context = episode.get("context", {})
    verification = episode.get("verification", {})

    return DegradeSignal(
        deadline_ms=episode.get("decisionWindowMs", 120),
        elapsed_ms=int(telemetry.get("endToEndMs", 0)),
        p99_ms=int(telemetry.get("stageMs", {}).get("act", 80)),
        jitter_ms=int(telemetry.get("stageMs", {}).get("verify", 10)),
        ttl_breaches=int(context.get("ttlBreaches", 0)),
        max_feature_age_ms=int(context.get("maxFeatureAgeMs", 100)),
        verifier_result=verification.get("result", "pass"),
    )


def _get_ladder(episode: Dict[str, Any], policy_pack: Dict[str, Any] = None) -> list:
    """Get the degrade ladder from episode or policy pack."""
    if policy_pack:
        decision_type = episode.get("decisionType", "")
        rules = get_rules(policy_pack, decision_type)
        if "degradeLadder" in rules:
            return rules["degradeLadder"]

    # Fall back to ladder recorded in the episode
    degrade = episode.get("degrade", {})
    return degrade.get("ladder", [])


def _get_recorded_step(episode: Dict[str, Any]) -> str:
    """Get the degrade step that was recorded in the episode."""
    degrade = episode.get("degrade", {})
    return degrade.get("step", "none")


def _determine_outcome(
    episode: Dict[str, Any],
    verification_result: str,
    degrade_step: str,
) -> str:
    """Determine what the outcome code should be."""
    if verification_result == "pass" and degrade_step in ("none", None):
        return "success"
    if verification_result == "pass":
        return "partial"
    if verification_result == "fail":
        return "fail"
    if degrade_step == "abstain":
        return "abstain"
    if degrade_step == "bypass":
        return "bypassed"
    return "partial"


def replay_episode(
    episode: Dict[str, Any],
    policy_pack: Dict[str, Any] = None,
) -> Dict[str, Any]:
    """Replay an episode and return a step-level report."""
    signal = _reconstruct_signal(episode)
    ladder = _get_ladder(episode, policy_pack)
    recorded_step = _get_recorded_step(episode)

    # Re-run degrade ladder
    replayed_step, rationale = choose_degrade_step(ladder, signal)

    # Compare with recorded
    match = replayed_step == recorded_step
    verification = episode.get("verification", {})
    verification_result = verification.get("result", "pass")

    replayed_outcome = _determine_outcome(episode, verification_result, replayed_step)
    recorded_outcome = episode.get("outcome", {}).get("code", "unknown")

    return {
        "episodeId": episode.get("episodeId"),
        "decisionType": episode.get("decisionType"),
        "recorded": {
            "degradeStep": recorded_step,
            "outcomeCode": recorded_outcome,
        },
        "replayed": {
            "degradeStep": replayed_step,
            "outcomeCode": replayed_outcome,
            "rationale": rationale,
        },
        "match": match,
        "outcomeMatch": replayed_outcome == recorded_outcome,
        "signal": {
            "deadline_ms": signal.deadline_ms,
            "elapsed_ms": signal.elapsed_ms,
            "p99_ms": signal.p99_ms,
            "jitter_ms": signal.jitter_ms,
            "ttl_breaches": signal.ttl_breaches,
            "max_feature_age_ms": signal.max_feature_age_ms,
            "verifier_result": signal.verifier_result,
        },
        "ladder": ladder,
        "policyPackUsed": "custom" if policy_pack else "episode",
    }


def main():
    ap = argparse.ArgumentParser(description="Replay a sealed episode through the degrade ladder")
    ap.add_argument("--episode", required=True, help="Path to sealed episode JSON")
    ap.add_argument("--policy-pack", help="Optional alternative policy pack for what-if")
    ap.add_argument("--output", help="Path to write JSON report")
    args = ap.parse_args()

    episode = json.loads(Path(args.episode).read_text(encoding="utf-8"))

    policy_pack = None
    if args.policy_pack:
        policy_pack = load_policy_pack(args.policy_pack, verify_hash=False)

    report = replay_episode(episode, policy_pack)
    output = json.dumps(report, indent=2)

    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
        print(f"Replay report written to {args.output}")
    else:
        print(output)


if __name__ == "__main__":
    main()
