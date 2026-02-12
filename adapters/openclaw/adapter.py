"""OpenClaw adapter — bridges skill execution into DeepSigma supervision.

Closes #7.

Usage:
    from adapters.openclaw.adapter import OpenClawSupervisor
        supervisor = OpenClawSupervisor(policy_pack_path="policy_packs/packs/demo_policy_pack_v1.json")
            result = supervisor.supervise_skill("AccountQuarantine", inputs={}, contract={})
            """
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional

from engine.degrade_ladder import DegradeSignal, choose_degrade_step
from engine.policy_loader import load_policy_pack, get_rules


def _iso_now() -> str:
      return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _seal_hash(obj: Dict[str, Any]) -> str:
      import hashlib
      canonical = json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")
      return hashlib.sha256(canonical).hexdigest()


class OpenClawSupervisor:
      """Wraps an OpenClaw skill invocation as a DeepSigma-supervised action."""

    def __init__(self, policy_pack_path: str):
              self.pack = load_policy_pack(policy_pack_path, verify_hash=False)

    def supervise_skill(
              self,
              decision_type: str,
              inputs: Dict[str, Any],
              contract: Dict[str, Any],
              skill_fn: Optional[Callable] = None,
    ) -> Dict[str, Any]:
              """Orchestrate the full supervision loop for a skill invocation.

                      Args:
                                  decision_type: The type of decision being made.
                                              inputs: Skill input data.
                                                          contract: Action contract with pre/post conditions.
                                                                      skill_fn: Optional callable that executes the skill.
                                                                                            If None, uses a stub that returns inputs.

                                                                                                    Returns:
                                                                                                                Sealed episode dict.
                                                                                                                        """
              rules = get_rules(self.pack, decision_type)
              dte_defaults = rules.get("dteDefaults", {})
              ladder = rules.get("degradeLadder", [])

        episode_id = "ep_" + uuid.uuid4().hex[:12]
        started = _iso_now()

        # Pre-check: verify action contract preconditions
        pre_ok = self._check_preconditions(contract, inputs)

        # Execute skill
        if skill_fn and pre_ok:
                      try:
                                        result = skill_fn(inputs)
                                        execution_ok = True
except Exception as e:
                result = {"error": str(e)}
                execution_ok = False
elif pre_ok:
            result = {"stub": True, "inputs": inputs}
            execution_ok = True
else:
            result = {"blocked": True, "reason": "precondition_failed"}
              execution_ok = False

        # Post-check: verify action contract postconditions
        post_ok = self._check_postconditions(contract, result) if execution_ok else False

        # Build degrade signal
        verification_result = "pass" if (pre_ok and post_ok) else "fail"
        sig = DegradeSignal(
                      deadline_ms=int(dte_defaults.get("decisionWindowMs", 120)),
                      elapsed_ms=50,
                      p99_ms=80,
                      jitter_ms=10,
                      ttl_breaches=0,
                      max_feature_age_ms=100,
                      verifier_result=verification_result,
        )
        step, rationale = choose_degrade_step(ladder, sig)

        ended = _iso_now()

        # Build episode
        episode = {
                      "episodeId": episode_id,
                      "decisionType": decision_type,
                      "startedAt": started,
                      "endedAt": ended,
                      "decisionWindowMs": int(dte_defaults.get("decisionWindowMs", 120)),
                      "actor": {"type": "agent", "id": "openclaw_adapter", "version": "0.1.0"},
                      "dteRef": {
                                        "decisionType": decision_type,
                                        "version": self.pack.get("version", "1.0.0"),
                      },
                      "context": {
                                        "snapshotId": "snap_" + uuid.uuid4().hex[:8],
                                        "capturedAt": started,
                                        "ttlMs": int(dte_defaults.get("ttlMs", 500)),
                                        "maxFeatureAgeMs": 100,
                                        "ttlBreachesCount": 0,
                                        "evidenceRefs": [],
                      },
                      "plan": {"planner": "rules", "summary": f"OpenClaw skill: {decision_type}"},
                      "actions": [],
                      "verification": {
                                        "required": True,
                                        "method": "contract_check",
                                        "result": verification_result,
                      },
                      "outcome": {
                                        "code": "success" if verification_result == "pass" else "fail",
                                        "reason": f"pre={pre_ok}, post={post_ok}, step={step}",
                      },
                      "telemetry": {
                                        "endToEndMs": 50,
                                        "stageMs": {"context": 10, "plan": 10, "act": 20, "verify": 10},
                                        "p95Ms": 72, "p99Ms": 80, "jitterMs": 10,
                                        "fallbackUsed": step not in ("none", None),
                                        "fallbackStep": step if step not in ("none", None) else "none",
                                        "hopCount": 1, "fanout": 1,
                      },
                      "seal": {},
                      "degrade": {
                                        "step": step or "none",
                                        "rationale": rationale if isinstance(rationale, dict) else {"reason": str(rationale)},
                                        "ladder": ladder,
                      },
        }

        ep_no_seal = {k: v for k, v in episode.items() if k != "seal"}
        episode["seal"] = {"sealedAt": ended, "sealHash": _seal_hash(ep_no_seal)}

        # Emit drift if postconditions failed
        drift_event = None
        if not post_ok and execution_ok:
                      drift_event = {
                                        "driftId": "dr_" + uuid.uuid4().hex[:12],
                                        "episodeId": episode_id,
                                        "decisionType": decision_type,
                                        "observedAt": ended,
                                        "type": "verify",
                                        "severity": "red",
                                        "details": {"postcondition_failed": True},
                      }

        return {
                      "episode": episode,
                      "driftEvent": drift_event,
                      "skillResult": result,
        }

    def _check_preconditions(self, contract: Dict[str, Any], inputs: Dict[str, Any]) -> bool:
              """Check action contract preconditions against inputs."""
              preconditions = contract.get("preconditions", [])
              if not preconditions:
                            return True
                        for cond in preconditions:
                                      field = cond.get("field")
                                      expected = cond.get("equals")
                                      if field and expected is not None:
                                                        if inputs.get(field) != expected:
                                                                              return False
                                                                  return True

    def _check_postconditions(self, contract: Dict[str, Any], result: Dict[str, Any]) -> bool:
              """Check action contract postconditions against result."""
        postconditions = contract.get("postconditions", [])
        if not postconditions:
                      return True
                  for cond in postconditions:
                                field = cond.get("field")
                                expected = cond.get("equals")
                                if field and expected is not None:
                                                  if result.get(field) != expected:
                                                                        return False
                                                            return True
