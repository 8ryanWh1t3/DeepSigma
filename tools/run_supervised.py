#!/usr/bin/env python3
"""Run a supervised decision — schema-compliant output.

Produces a sealed DecisionEpisode JSON that conforms to
specs/episode.schema.json and optionally a DriftEvent JSON
conforming to specs/drift.schema.json. Closes #1, #2.

Usage:
    python tools/run_supervised.py \
        --decisionType AccountQuarantine \
        --policy policy_packs/packs/demo_policy_pack_v1.json \
        --telemetry endToEndMs=95 p99Ms=160 jitterMs=70 \
        --context ttlBreachesCount=0 maxFeatureAgeMs=180 \
        --verification pass \
        --out episodes_out
"""
from __future__ import annotations

import sys
from pathlib import Path

# Ensure the project root is on sys.path so engine.* imports work
# without requiring PYTHONPATH=. to be set manually.
_REPO_ROOT = str(Path(__file__).resolve().parents[1])
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import argparse
import json
import uuid
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Dict

from engine.policy_loader import load_policy_pack, get_rules
from engine.degrade_ladder import DegradeSignal, choose_degrade_step


def iso_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_kv(items: list[str]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for s in items:
        if "=" not in s:
            continue
        k, v = s.split("=", 1)
        if v.isdigit():
            out[k] = int(v)
        else:
            try:
                out[k] = float(v)
            except ValueError:
                out[k] = v
    return out


def seal_hash(obj: Dict[str, Any]) -> str:
    import hashlib
    canonical = json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _outcome_code(verification_result: str, degrade_step: str) -> str:
    """Map verification + degrade state to a schema-valid outcome code."""
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--decisionType", required=True)
    ap.add_argument("--policy", required=True, help="Path to policy pack JSON")
    ap.add_argument(
        "--telemetry", nargs="*", default=[],
        help="k=v pairs (endToEndMs, p99Ms, jitterMs)",
    )
    ap.add_argument(
        "--context", nargs="*", default=[],
        help="k=v pairs (ttlBreachesCount, maxFeatureAgeMs)",
    )
    ap.add_argument(
        "--verification", default="na",
        choices=["pass", "fail", "inconclusive", "na"],
    )
    ap.add_argument("--out", default="episodes_out", help="Output directory")
    args = ap.parse_args()

    pack = load_policy_pack(args.policy)
    rules = get_rules(pack, args.decisionType)
    dte_defaults = rules.get("dteDefaults", {})

    telemetry_kv = parse_kv(args.telemetry)
    context_kv = parse_kv(args.context)

    decision_window = int(dte_defaults.get("decisionWindowMs", 120))
    elapsed = int(telemetry_kv.get("endToEndMs", 0))
    p99 = int(telemetry_kv.get("p99Ms", 0))
    jitter = int(telemetry_kv.get("jitterMs", 0))
    ttl_breaches = int(context_kv.get("ttlBreachesCount", 0))
    max_age = int(context_kv.get("maxFeatureAgeMs", 0))
    ttl_ms = int(dte_defaults.get("ttlMs", 500))
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
    snapshot_id = "snap_" + uuid.uuid4().hex[:8]
    fallback_used = step not in ("none", None)

    # Build schema-compliant episode (specs/episode.schema.json)
    episode: Dict[str, Any] = {
        "episodeId": episode_id,
        "decisionType": args.decisionType,
        "startedAt": started,
        "endedAt": ended,
        "decisionWindowMs": decision_window,
        "actor": {
            "type": "agent",
            "id": "run_supervised_cli",
            "version": "0.2.0",
        },
        "dteRef": {
            "decisionType": args.decisionType,
            "version": pack.get("version", "1.0.0"),
            "policyPackHash": pack.get("policyPackHash", ""),
        },
        "context": {
            "snapshotId": snapshot_id,
            "capturedAt": started,
            "ttlMs": ttl_ms,
            "maxFeatureAgeMs": max_age,
            "ttlBreachesCount": ttl_breaches,
            "evidenceRefs": [],
        },
        "plan": {
            "planner": "rules",
            "summary": f"Degrade ladder evaluation for {args.decisionType}",
        },
        "actions": [],
        "verification": {
            "required": args.verification != "na",
            "method": "stub" if args.verification != "na" else "none",
            "result": args.verification,
        },
        "outcome": {
            "code": _outcome_code(args.verification, step),
            "reason": f"degrade_step={step}",
        },
        "telemetry": {
            "endToEndMs": elapsed,
            "stageMs": {
                "context": max(1, elapsed // 4),
                "plan": max(1, elapsed // 4),
                "act": max(1, elapsed // 4),
                "verify": max(1, elapsed // 4),
            },
            "p95Ms": int(telemetry_kv.get("p95Ms", int(p99 * 0.9))),
            "p99Ms": p99,
            "jitterMs": jitter,
            "fallbackUsed": fallback_used,
            "fallbackStep": step if fallback_used else "none",
            "hopCount": 1,
            "fanout": 1,
        },
        "seal": {},  # placeholder, filled below
        "policy": {
            "policyPackId": pack.get("policyPackId", ""),
            "policyPackVersion": pack.get("version", ""),
            "policyPackHash": pack.get("policyPackHash", ""),
        },
        "degrade": {
            "step": step if step else "none",
            "rationale": rationale if isinstance(rationale, dict) else {"reason": str(rationale)},
            "ladder": ladder,
        },
    }

    # Compute seal over everything except the seal field itself
    ep_no_seal = {k: v for k, v in episode.items() if k != "seal"}
    episode["seal"] = {"sealedAt": ended, "sealHash": seal_hash(ep_no_seal)}

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    ep_path = out_dir / f"{episode_id}.json"
    ep_path.write_text(json.dumps(episode, indent=2), encoding="utf-8")

    # --- Drift events (schema-compliant: specs/drift.schema.json) ---
    drift_type = None
    drift_severity = "yellow"
    drift_details: Dict[str, Any] = {}

    if step not in ("none", None):
        drift_type = "fallback"
        drift_severity = "yellow"
        drift_details = {"degradeStep": step, "rationale": str(rationale)}

    if ttl_breaches > 0 or max_age > int(dte_defaults.get("maxFeatureAgeMs", 200)):
        drift_type = "freshness"
        drift_severity = "red"
        drift_details = {"ttlBreachesCount": ttl_breaches, "maxFeatureAgeMs": max_age}

    if args.verification in ("fail", "inconclusive"):
        drift_type = "verify"
        drift_severity = "red"
        drift_details = {"result": args.verification}

    if p99 and p99 > decision_window:
        drift_type = "time"
        drift_severity = "yellow"
        drift_details = {"p99Ms": p99, "decisionWindowMs": decision_window}

    if drift_type:
        drift_event = {
            "driftId": "dr_" + uuid.uuid4().hex[:12],
            "episodeId": episode_id,
            "decisionType": args.decisionType,
            "observedAt": ended,
            "type": drift_type,
            "severity": drift_severity,
            "details": drift_details,
            "fingerprint": seal_hash({
                "decisionType": args.decisionType,
                "type": drift_type,
                **drift_details,
            }),
            "patchHint": f"Review {drift_type} drift for {args.decisionType}",
        }
        drift_path = out_dir / f"{episode_id}.drift.json"
        drift_path.write_text(json.dumps(drift_event, indent=2), encoding="utf-8")

    print(str(ep_path))


if __name__ == "__main__":
    main()
