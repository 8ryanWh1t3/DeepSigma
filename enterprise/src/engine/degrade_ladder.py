"""Degrade Ladder Engine (Scaffold)

Turns 'degrade ladder' from a concept into executable selection logic.

Inputs:
- DTE budgets / P95/P99 / jitter
- TTL breach counts / maxFeatureAgeMs
- verifier results (pass/fail/inconclusive)
- policy pack ladder (ordered steps)

Output:
- selected degrade step (e.g., cache_bundle, rules_only, hitl, abstain)
- rationale (machine-readable)

This is intentionally small and vendor-neutral.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, List, Tuple

@dataclass
class DegradeSignal:
    deadline_ms: int
    elapsed_ms: int
    p99_ms: int
    jitter_ms: int
    ttl_breaches: int
    max_feature_age_ms: int
    verifier_result: str  # pass/fail/inconclusive/na

def choose_degrade_step(ladder: List[str], s: DegradeSignal) -> Tuple[str, Dict[str, Any]]:
    # Hard gates first
    if s.ttl_breaches > 0 or s.max_feature_age_ms > 500:
        step = "abstain" if "abstain" in ladder else ladder[-1]
        return step, {"reason": "freshness_gate", "ttl_breaches": s.ttl_breaches, "max_feature_age_ms": s.max_feature_age_ms}

    if s.verifier_result in ("fail", "inconclusive"):
        step = "hitl" if "hitl" in ladder else ladder[-1]
        return step, {"reason": "verification_gate", "verifier_result": s.verifier_result}

    # Time pressure gate: if we are close to deadline or tail is heavy, degrade upward
    remaining = max(0, s.deadline_ms - s.elapsed_ms)
    if remaining < 30 or s.p99_ms > s.deadline_ms or s.jitter_ms > 50:
        for preferred in ("cache_bundle", "rules_only"):
            if preferred in ladder:
                return preferred, {"reason": "time_pressure", "remaining_ms": remaining, "p99_ms": s.p99_ms, "jitter_ms": s.jitter_ms}

    # Default: no degrade
    return "none", {"reason": "within_envelope", "remaining_ms": remaining}
