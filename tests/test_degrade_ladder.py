"""Tests for engine/degrade_ladder.py — Issue #3."""
import pytest
from engine.degrade_ladder import DegradeSignal, choose_degrade_step


LADDER = ["cache_bundle", "rules_only", "hitl", "abstain"]


def _signal(**overrides) -> DegradeSignal:
      """Build a DegradeSignal with sane defaults; override any field."""
      defaults = dict(
          deadline_ms=120,
          elapsed_ms=50,
          p99_ms=80,
          jitter_ms=10,
          ttl_breaches=0,
          max_feature_age_ms=100,
          verifier_result="pass",
      )
      defaults.update(overrides)
      return DegradeSignal(**defaults)


# ---- Freshness gate ----

def test_ttl_breaches_trigger_abstain():
      step, rationale = choose_degrade_step(LADDER, _signal(ttl_breaches=1))
      assert step == "abstain"
      assert rationale["reason"] == "freshness_gate"


def test_high_feature_age_triggers_abstain():
      step, rationale = choose_degrade_step(LADDER, _signal(max_feature_age_ms=600))
      assert step == "abstain"
      assert rationale["reason"] == "freshness_gate"


def test_freshness_gate_uses_last_step_when_abstain_not_in_ladder():
      ladder = ["cache_bundle", "rules_only"]
      step, _ = choose_degrade_step(ladder, _signal(ttl_breaches=2))
      assert step == "rules_only"  # last in ladder


# ---- Verification gate ----

def test_verification_fail_triggers_hitl():
      step, rationale = choose_degrade_step(LADDER, _signal(verifier_result="fail"))
      assert step == "hitl"
      assert rationale["reason"] == "verification_gate"


def test_verification_inconclusive_triggers_hitl():
      step, rationale = choose_degrade_step(LADDER, _signal(verifier_result="inconclusive"))
      assert step == "hitl"
      assert rationale["reason"] == "verification_gate"


def test_verification_gate_uses_last_step_when_hitl_not_in_ladder():
      ladder = ["cache_bundle", "rules_only"]
      step, _ = choose_degrade_step(ladder, _signal(verifier_result="fail"))
      assert step == "rules_only"


# ---- Time pressure gate ----

def test_low_remaining_time_triggers_cache_bundle():
      step, rationale = choose_degrade_step(
                LADDER, _signal(deadline_ms=100, elapsed_ms=80)
      )
      assert step == "cache_bundle"
      assert rationale["reason"] == "time_pressure"


def test_p99_exceeding_deadline_triggers_degrade():
      step, rationale = choose_degrade_step(
                LADDER, _signal(p99_ms=200, deadline_ms=120)
      )
      assert step == "cache_bundle"
      assert rationale["reason"] == "time_pressure"


def test_high_jitter_triggers_degrade():
      step, rationale = choose_degrade_step(
                LADDER, _signal(jitter_ms=60)
      )
      assert step == "cache_bundle"
      assert rationale["reason"] == "time_pressure"


# ---- Happy path ----

def test_within_envelope_returns_none():
      step, rationale = choose_degrade_step(LADDER, _signal())
      assert step == "none"
      assert rationale["reason"] == "within_envelope"


def test_within_envelope_has_remaining_ms():
      _, rationale = choose_degrade_step(LADDER, _signal(deadline_ms=200, elapsed_ms=50))
      assert rationale["remaining_ms"] == 150


# ---- Edge cases ----

def test_empty_ladder_freshness_gate():
      """Empty ladder should still work for gates that use ladder[-1]."""
      # With empty ladder, ladder[-1] would fail, but ttl_breaches > 0
      # checks 'abstain' in ladder first, so falls to ladder[-1].
      # This tests robustness — if ladder is empty we expect an IndexError.
      with pytest.raises(IndexError):
                choose_degrade_step([], _signal(ttl_breaches=1))


def test_signal_dataclass_fields():
      sig = _signal()
      assert sig.deadline_ms == 120
      assert sig.verifier_result == "pass"
