#!/usr/bin/env python3
"""Enhanced Replay Harness — re-runs degrade ladder logic.

Closes #12.

Reconstructs DegradeSignal from each episode's recorded telemetry/context,
re-runs choose_degrade_step(), and compares the replayed decision against
the recorded decision.

Usage:
    # Replay with original policy pack
        python tools/replay_episode.py examples/episodes/01_success.json

            # Replay with alternate policy pack (what-if)
                python tools/replay_episode.py examples/episodes/01_success.json \
        --policy-pack policy_packs/packs/demo_policy_pack_v1.json

            # Output structured JSON report
                python tools/replay_episode.py examples/episodes/01_success.json \
        --output replay_report.json
        """
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from engine.degrade_ladder import DegradeSignal, choose_degrade_step
from engine.policy_loader import load_policy_pack, get_rules


def iso_now() -> str:
      return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _reconstruct_signal(episode: Dict[str, Any]) -> DegradeSignal:
      """Reconstruct a DegradeSignal from the episode's recorded data."""
      telemetry = episode.get("telemetry", {})
      context = episode.get("context", {})
      verification = episode.get("verification", {})

    return DegradeSignal(
              deadline_ms=episode.get("decisionWindowMs", 120),
              elapsed_ms=int(telemetry.get("endToEndMs", 0)),
              p99_ms=int(telemetry.get("p99Ms", 0)),
              jitter_ms=int(telemetry.get("jitterMs", 0)),
              ttl_breaches=int(context.get("ttlBreachesCount", 0)),
              max_feature_age_ms=int(context.get("maxFeatureAgeMs", 0)),
              verifier_result=verification.get("result", "na"),
    )


def _get_recorded_step(episode: Dict[str, Any]) -> Optional[str]:
      """Extract the recorded degrade step from the episode."""
      degrade = episode.get("degrade", {})
      return degrade.get("step")


def _get_ladder(episode: Dict[str, Any], policy_pack: Optional[Dict[str, Any]] = None) -> List[str]:
      """Get the degrade ladder, either from the episode or a policy pack override."""
      if policy_pack:
                decision_type = episode.get("decisionType", "")
                rules = get_rules(policy_pack, decision_type)
                ladder = rules.get("degradeLadder", [])
                if ladder:
                              return ladder

            # Fall back to ladder recorded in the episode
            degrade = episode.get("degrade", {})
    return degrade.get("ladder", [])


def replay_episode(
      episode: Dict[str, Any],
      policy_pack: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
      """Replay an episode and return a step-level report."""
    signal = _reconstruct_signal(episode)
    ladder = _get_ladder(episode, policy_pack)
    recorded_step = _get_recorded_step(episode)

    replayed_step, replayed_rationale = choose_degrade_step(ladder, signal)

    match = recorded_step == replayed_step
    return {
              "episodeId": episode.get("episodeId"),
              "decisionType": episode.get("decisionType"),
              "recordedStep": recorded_step,
              "replayedStep": replayed_step,
              "replayedRationale": replayed_rationale,
              "match": match,
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
    }


def main():
      ap = argparse.ArgumentParser(description="Replay a sealed episode through the degrade ladder")
      ap.add_argument("episode", help="Path to episode JSON file")
      ap.add_argument("--policy-pack", help="Override policy pack (what-if analysis)")
      ap.add_argument("--output", help="Write JSON report to file instead of stdout")
      args = ap.parse_args()

    episode = json.loads(Path(args.episode).read_text(encoding="utf-8"))

    policy_pack = None
    if args.policy_pack:
              policy_pack = load_policy_pack(args.policy_pack, verify_hash=False)

    step_result = replay_episode(episode, policy_pack)

    report = {
              "replayAt": iso_now(),
              "mode": "what-if" if args.policy_pack else "audit",
              "policyPackOverride": args.policy_pack,
              "steps": [step_result],
              "verdict": "PASS" if step_result["match"] else "MISMATCH",
              "summary": (
                            f"Replayed episode {step_result['episodeId']}: "
                            f"recorded={step_result['recordedStep']}, replayed={step_result['replayedStep']} "
                            f"-> {'MATCH' if step_result['match'] else 'MISMATCH'}"
              ),
    }

    output = json.dumps(report, indent=2)

    if args.output:
              Path(args.output).write_text(output, encoding="utf-8")
              print(f"Replay report written to {args.output}")
else:
          print(output)


if __name__ == "__main__":
      main()
