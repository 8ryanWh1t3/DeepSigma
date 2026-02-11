#!/usr/bin/env python3
"""Run a supervised decision (Scaffold)

One command that:
- loads a Policy Pack
- applies DTE defaults
- chooses degrade step (Degrade Ladder)
- optionally runs a verifier stub
- emits a sealed DecisionEpisode JSON
- emits a DriftEvent JSON when warranted

Usage:
  python tools/run_supervised.py \
    --decisionType AccountQuarantine \
    --policy policy_packs/packs/demo_policy_pack_v1.json \
    --telemetry endToEndMs=95 p99Ms=160 jitterMs=70 \
    --context ttlBreachesCount=0 maxFeatureAgeMs=180 \
    --verification pass \
    --out episodes_out

Notes:
- This is vendor-neutral and uses stubs for tool/action/verify.
- Replace stubs with adapters (LangChain/Foundry/Power Platform/MCP).
"""

from __future__ import annotations

import argparse
import json
import uuid
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Dict

from engine.policy_loader import load_policy_pack, get_rules
from engine.degrade_ladder import DegradeSignal, choose_degrade_step

def iso_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00","Z")

def parse_kv(items: list[str]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for s in items:
        if "=" not in s:
            continue
        k, v = s.split("=", 1)
        # best-effort numeric parsing
        if v.isdigit():
            out[k] = int(v)
        else:
            try:
                out[k] = float(v)
            except:
                out[k] = v
    return out

def seal_hash(obj: Dict[str, Any]) -> str:
    import hashlib
    canonical = json.dumps(obj, sort_keys=True, separators=(",",":")).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--decisionType", required=True)
    ap.add_argument("--policy", required=True, help="Path to policy pack JSON")
    ap.add_argument("--telemetry", nargs="*", default=[], help="k=v pairs (endToEndMs, p99Ms, jitterMs)")
    ap.add_argument("--context", nargs="*", default=[], help="k=v pairs (ttlBreachesCount, maxFeatureAgeMs)")
    ap.add_argument("--verification", default="na", choices=["pass","fail","inconclusive","na"])
    ap.add_argument("--out", default="episodes_out", help="Output directory")
    args = ap.parse_args()

    pack = load_policy_pack(args.policy)
    rules = get_rules(pack, args.decisionType)
    dte_defaults = rules.get("dteDefaults", {})

    telemetry = parse_kv(args.telemetry)
    context = parse_kv(args.context)

    decision_window = int(dte_defaults.get("decisionWindowMs", 120))
    elapsed = int(telemetry.get("endToEndMs", 0))
    p99 = int(telemetry.get("p99Ms", 0))
    jitter = int(telemetry.get("jitterMs", 0))
    ttl_breaches = int(context.get("ttlBreachesCount", 0))
    max_age = int(context.get("maxFeatureAgeMs", 0))

    ladder = rules.get("degradeLadder", [])

    sig = DegradeSignal(
        deadline_ms=decision_window,
        elapsed_ms=elapsed,
        p99_ms=p99,
        jitter_ms=jitter,
        ttl_breaches=ttl_breaches,
        max_feature_age_ms=max_age,
        verifier_result=args.verification,
    )
    step, rationale = choose_degrade_step(ladder, sig)

    episode_id = "ep_" + uuid.uuid4().hex[:12]
    started = iso_now()
    ended = iso_now()

    episode: Dict[str, Any] = {
        "episodeId": episode_id,
        "decisionType": args.decisionType,
        "startedAt": started,
        "endedAt": ended,
        "decisionWindowMs": decision_window,
        "policy": {
            "policyPackId": pack.get("policyPackId"),
            "policyPackVersion": pack.get("version"),
            "policyPackHash": pack.get("policyPackHash"),
        },
        "telemetry": telemetry,
        "context": {**dte_defaults, **context},
        "verification": {"result": args.verification},
        "degrade": {"step": step, "rationale": rationale, "ladder": ladder},
        "outcome": {"code": "ok" if args.verification == "pass" else "needs_review"},
    }

    # Seal (exclude seal)
    ep_no_seal = {k:v for k,v in episode.items() if k != "seal"}
    episode["seal"] = {"sealedAt": ended, "sealHash": seal_hash(ep_no_seal)}

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    ep_path = out_dir / f"{episode_id}.json"
    ep_path.write_text(json.dumps(episode, indent=2), encoding="utf-8")

    # Drift heuristics (scaffold)
    drift = None
    if step not in ("none", None) and step != "none":
        drift = {"type": "fallback", "severity": "yellow", "details": {"degradeStep": step, "rationale": rationale}}
    if ttl_breaches > 0 or max_age > int(dte_defaults.get("maxFeatureAgeMs", 200)):
        drift = {"type": "freshness", "severity": "red", "details": {"ttlBreachesCount": ttl_breaches, "maxFeatureAgeMs": max_age}}
    if args.verification in ("fail", "inconclusive"):
        drift = {"type": "verify", "severity": "red", "details": {"result": args.verification}}
    if p99 and p99 > decision_window:
        drift = {"type": "time", "severity": "yellow", "details": {"p99Ms": p99, "decisionWindowMs": decision_window}}

    if drift:
        drift_event = {
            "driftId": "dr_" + uuid.uuid4().hex[:12],
            "episodeId": episode_id,
            "decisionType": args.decisionType,
            "observedAt": ended,
            "drift": drift,
            "fingerprint": seal_hash({"decisionType": args.decisionType, **drift}),
            "policy": episode["policy"],
        }
        drift_path = out_dir / f"{episode_id}.drift.json"
        drift_path.write_text(json.dumps(drift_event, indent=2), encoding="utf-8")

    print(str(ep_path))

if __name__ == "__main__":
    main()
