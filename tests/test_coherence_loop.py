"""Tests for core.coherence_loop — five-primitive coherence orchestrator."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC_ROOT = _REPO_ROOT / "src"
if str(_SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(_SRC_ROOT))

from core.coherence_loop import (  # noqa: E402
    CoherenceLoopResult,
    CoherenceStep,
    StepRecord,
    run_coherence_loop,
)
from core.primitive_envelope import PrimitiveEnvelope  # noqa: E402
from core.primitives import PrimitiveType  # noqa: E402


def _aligned_claim():
    """Claim payload that will align with the event (no drift)."""
    return {
        "id": "CLM-001",
        "text": "System latency is within SLA",
        "domain": "ops",
        "source": "monitor",
        "timestamp": "2026-03-01T10:00:00Z",
        "assumptions": ["Latency under 200ms"],
    }


def _aligned_event():
    """Event payload that aligns with the claim."""
    return {
        "id": "EVT-001",
        "text": "Latency measured at 150ms",
        "domain": "ops",
        "source": "apm",
        "timestamp": "2026-03-01T10:05:00Z",
        "observed_state": {"status": "healthy"},
    }


def _drifting_claim():
    """Claim payload that will cause drift detection."""
    return {
        "id": "CLM-002",
        "text": "System is compliant",
        "domain": "compliance",
        "source": "audit",
        "timestamp": "2026-03-01T10:00:00Z",
        "assumptions": ["All checks pass"],
    }


def _drifting_event():
    """Event payload that contradicts the claim."""
    return {
        "id": "EVT-002",
        "text": "Compliance check failed for policy X",
        "domain": "compliance",
        "source": "scanner",
        "timestamp": "2026-03-01T10:05:00Z",
        "observed_state": {"status": "failed"},
        "metadata": {"violation": True, "violation_detail": "Policy X breached"},
    }


# ── CoherenceStep enum ─────────────────────────────────────────


class TestCoherenceStep:
    def test_has_five_members(self):
        assert len(CoherenceStep) == 5

    def test_values_match_primitive_types(self):
        for step in CoherenceStep:
            assert step.value in {p.value for p in PrimitiveType}


# ── Aligned loop (no drift) ────────────────────────────────────


class TestAlignedLoop:
    def test_returns_coherence_loop_result(self):
        result = run_coherence_loop(_aligned_claim(), _aligned_event())
        assert isinstance(result, CoherenceLoopResult)

    def test_completed(self):
        result = run_coherence_loop(_aligned_claim(), _aligned_event())
        assert result.completed is True

    def test_halted_at_is_none(self):
        result = run_coherence_loop(_aligned_claim(), _aligned_event())
        assert result.halted_at is None

    def test_has_three_steps_when_aligned(self):
        result = run_coherence_loop(_aligned_claim(), _aligned_event())
        # CLAIM, EVENT, REVIEW — no PATCH or APPLY when aligned
        assert len(result.steps) == 3

    def test_step_order_claim_event_review(self):
        result = run_coherence_loop(_aligned_claim(), _aligned_event())
        assert result.steps[0].step == CoherenceStep.CLAIM
        assert result.steps[1].step == CoherenceStep.EVENT
        assert result.steps[2].step == CoherenceStep.REVIEW

    def test_each_step_has_envelope(self):
        result = run_coherence_loop(_aligned_claim(), _aligned_event())
        for step in result.steps:
            assert isinstance(step.envelope, PrimitiveEnvelope)

    def test_loop_id_format(self):
        result = run_coherence_loop(_aligned_claim(), _aligned_event())
        assert result.loop_id.startswith("LOOP-")


# ── Drifting loop (full 5 steps) ───────────────────────────────


class TestDriftingLoop:
    def test_has_five_steps_when_drifting(self):
        result = run_coherence_loop(_drifting_claim(), _drifting_event())
        assert len(result.steps) == 5

    def test_step_order_full(self):
        result = run_coherence_loop(_drifting_claim(), _drifting_event())
        expected = [
            CoherenceStep.CLAIM,
            CoherenceStep.EVENT,
            CoherenceStep.REVIEW,
            CoherenceStep.PATCH,
            CoherenceStep.APPLY,
        ]
        actual = [s.step for s in result.steps]
        assert actual == expected

    def test_completed(self):
        result = run_coherence_loop(_drifting_claim(), _drifting_event())
        assert result.completed is True

    def test_review_notes_contain_verdict(self):
        result = run_coherence_loop(_drifting_claim(), _drifting_event())
        review_step = result.steps[2]
        assert any("verdict=" in n for n in review_step.notes)

    def test_apply_notes_contain_success(self):
        result = run_coherence_loop(_drifting_claim(), _drifting_event())
        apply_step = result.steps[4]
        assert any("success=" in n for n in apply_step.notes)


# ── Duration tracking ──────────────────────────────────────────


class TestDuration:
    def test_durations_non_negative(self):
        result = run_coherence_loop(_aligned_claim(), _aligned_event())
        for step in result.steps:
            assert step.duration_ms >= 0


# ── Serialisation ──────────────────────────────────────────────


class TestSerialization:
    def test_to_dict_keys(self):
        result = run_coherence_loop(_aligned_claim(), _aligned_event())
        d = result.to_dict()
        assert "loopId" in d
        assert "steps" in d
        assert "completed" in d

    def test_step_record_to_dict(self):
        result = run_coherence_loop(_aligned_claim(), _aligned_event())
        step_d = result.steps[0].to_dict()
        assert "step" in step_d
        assert "envelope" in step_d
        assert "durationMs" in step_d
        assert "notes" in step_d
