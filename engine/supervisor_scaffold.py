"""Supervisor Scaffold: Policy Pack → Degrade Ladder → Episode stamping

Demonstrates:
- load policy pack
- choose degrade step based on runtime signals
- stamp DecisionEpisode with policyPackId/version/hash and degrade rationale
"""

from __future__ import annotations
import json
from dataclasses import asdict
from typing import Any, Dict

from engine.policy_loader import load_policy_pack, get_rules
from engine.degrade_ladder import DegradeSignal, choose_degrade_step

def apply_policy_and_degrade(decision_type: str, policy_pack_path: str, signals: DegradeSignal):
    pack = load_policy_pack(policy_pack_path)
    rules = get_rules(pack, decision_type)
    ladder = rules.get("degradeLadder", [])
    step, rationale = choose_degrade_step(ladder, signals)

    policy_ref = {
        "policyPackId": pack.get("policyPackId"),
        "policyPackVersion": pack.get("version"),
        "policyPackHash": pack.get("policyPackHash"),
    }

    degrade = {
        "step": step,
        "rationale": rationale,
        "signals": asdict(signals),
        "ladder": ladder,
    }
    return policy_ref, degrade

def stamp_episode(episode: Dict[str, Any], policy_ref: Dict[str, Any], degrade: Dict[str, Any]) -> Dict[str, Any]:
    episode.setdefault("policy", {})
    episode["policy"].update(policy_ref)
    episode.setdefault("degrade", {})
    episode["degrade"].update(degrade)
    return episode

if __name__ == "__main__":
    signals = DegradeSignal(
        deadline_ms=120,
        elapsed_ms=95,
        p99_ms=160,
        jitter_ms=70,
        ttl_breaches=0,
        max_feature_age_ms=180,
        verifier_result="pass",
    )
    policy_ref, degrade = apply_policy_and_degrade("AccountQuarantine", "policy_packs/packs/demo_policy_pack_v1.json", signals)
    episode = {"episodeId":"demo","decisionType":"AccountQuarantine"}
    print(json.dumps(stamp_episode(episode, policy_ref, degrade), indent=2))
