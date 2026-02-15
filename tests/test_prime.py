"""
Tests for PRIME Threshold Gate
==============================
Unit tests covering verdict logic, scoring, edge cases,
and escalation triggers.
"""

import time
import pytest

from coherence_ops.prime import (
    PRIMEGate,
    PRIMEConfig,
    PRIMEContext,
    TruthInvariant,
    ReasoningInvariant,
    MemoryInvariant,
    Verdict,
    ConfidenceBand,
)


# ── Fixtures ──


@pytest.fixture
def gate():
    """Default PRIME gate."""
    return PRIMEGate()


@pytest.fixture
def high_confidence_context():
    """Context that should produce APPROVE."""
    return PRIMEContext(
        truth=TruthInvariant(
            claim="System is operating within parameters",
            evidence=["metric A nominal", "metric B nominal"],
            sources=["monitoring_v2"],
            confidence=ConfidenceBand.HIGH,
        ),
        reasoning=ReasoningInvariant(
            facts=["CPU at 45%", "Memory at 62%", "No alerts"],
            interpretations=["System healthy"],
        ),
        memory=MemoryInvariant(
            seal_id="seal-001",
            version=3,
            lineage=["abc123", "def456"],
        ),
        coherence_score=0.85,
        temperature=0.2,
    )


@pytest.fixture
def low_confidence_context():
    """Context that should produce DEFER or ESCALATE."""
    return PRIMEContext(
        truth=TruthInvariant(
            claim="Deployment is safe",
            confidence=ConfidenceBand.LOW,
        ),
        reasoning=ReasoningInvariant(
            interpretations=["Seems fine", "No obvious issues"],
        ),
        coherence_score=0.3,
        temperature=0.5,
    )


@pytest.fixture
def contested_context():
    """Context with conflicting evidence."""
    return PRIMEContext(
        truth=TruthInvariant(
            claim="Budget allocation is optimal",
            evidence=["Q3 projections positive"],
            disconfirmers=["Q2 overspend detected", "Audit flagged variance"],
            confidence=ConfidenceBand.CONTESTED,
        ),
        reasoning=ReasoningInvariant(
            facts=["Budget is 2M"],
            interpretations=["Allocation seems right"],
            assumptions=[{"statement": "Market stays stable", "expires_at": time.time() + 3600}],
        ),
        coherence_score=0.5,
        temperature=0.4,
    )


# ── Verdict Tests ──


class TestVerdicts:
    def test_approve_high_confidence(self, gate, high_confidence_context):
        result = gate.evaluate(high_confidence_context)
        assert result.verdict == Verdict.APPROVE
        assert result.confidence > 0.6

    def test_defer_low_confidence(self, gate, low_confidence_context):
        result = gate.evaluate(low_confidence_context)
        assert result.verdict in (Verdict.DEFER, Verdict.ESCALATE)
        assert result.confidence < 0.5

    def test_escalate_contested(self, gate, contested_context):
        result = gate.evaluate(contested_context)
        assert result.verdict in (Verdict.DEFER, Verdict.ESCALATE)
        assert len(result.escalation_factors) > 0

    def test_escalate_on_high_temperature(self, gate):
        ctx = PRIMEContext(
            truth=TruthInvariant(
                claim="Test claim",
                confidence=ConfidenceBand.HIGH,
                evidence=["ev1"],
            ),
            reasoning=ReasoningInvariant(facts=["fact1"]),
            coherence_score=0.9,
            temperature=0.95,
        )
        result = gate.evaluate(ctx)
        assert result.verdict == Verdict.ESCALATE
        assert any("temperature" in f for f in result.escalation_factors)

    def test_escalate_missing_seal(self):
        config = PRIMEConfig(require_seal=True)
        gate = PRIMEGate(config)
        ctx = PRIMEContext(
            truth=TruthInvariant(claim="Test", confidence=ConfidenceBand.HIGH, evidence=["e"]),
            reasoning=ReasoningInvariant(facts=["f"]),
            memory=MemoryInvariant(),  # no seal_id
            coherence_score=0.9,
        )
        result = gate.evaluate(ctx)
        assert result.verdict == Verdict.ESCALATE
        assert any("missing_seal" in f for f in result.escalation_factors)


# ── Scoring Tests ──


class TestScoring:
    def test_truth_score_high(self, gate):
        truth = TruthInvariant(
            claim="Verified claim",
            evidence=["e1", "e2"],
            confidence=ConfidenceBand.HIGH,
        )
        score = gate._score_truth(truth)
        assert score >= 0.9

    def test_truth_score_empty_claim(self, gate):
        truth = TruthInvariant(claim="")
        assert gate._score_truth(truth) == 0.0

    def test_truth_score_contested(self, gate):
        truth = TruthInvariant(
            claim="Disputed claim",
            evidence=["e1"],
            disconfirmers=["d1", "d2"],
            confidence=ConfidenceBand.CONTESTED,
        )
        score = gate._score_truth(truth)
        assert score < 0.4

    def test_reasoning_score_all_facts(self, gate):
        reasoning = ReasoningInvariant(
            facts=["f1", "f2", "f3"],
            interpretations=[],
        )
        score = gate._score_reasoning(reasoning)
        assert score == 1.0

    def test_reasoning_score_empty(self, gate):
        reasoning = ReasoningInvariant()
        assert gate._score_reasoning(reasoning) == 0.0

    def test_reasoning_score_with_assumptions(self, gate):
        reasoning = ReasoningInvariant(
            facts=["f1"],
            interpretations=["i1"],
            assumptions=[
                {"statement": f"a{i}", "expires_at": time.time() + 3600}
                for i in range(6)
            ],
        )
        score = gate._score_reasoning(reasoning)
        assert score < 0.5  # penalty for many assumptions

    def test_memory_score_full(self, gate):
        memory = MemoryInvariant(
            seal_id="seal-abc",
            version=5,
            lineage=["h1", "h2", "h3"],
        )
        score = gate._score_memory(memory)
        assert score >= 0.9

    def test_memory_score_minimal(self, gate):
        memory = MemoryInvariant()
        score = gate._score_memory(memory)
        assert score == 0.5


# ── Config Tests ──


class TestConfig:
    def test_default_config_valid(self):
        config = PRIMEConfig()
        assert config.validate() == []

    def test_invalid_thresholds(self):
        config = PRIMEConfig(approve_threshold=0.3, defer_threshold=0.5)
        issues = config.validate()
        assert len(issues) > 0
        assert "approve_threshold" in issues[0]

    def test_invalid_ratios(self):
        config = PRIMEConfig(min_evidence_ratio=1.5)
        issues = config.validate()
        assert len(issues) > 0

    def test_custom_config(self):
        config = PRIMEConfig(
            approve_threshold=0.9,
            defer_threshold=0.6,
            temperature_ceiling=0.5,
            require_seal=True,
            contested_claim_policy="escalate",
        )
        gate = PRIMEGate(config)
        assert gate.config.approve_threshold == 0.9
        assert gate.config.require_seal is True


# ── Lineage Tests ──


class TestLineage:
    def test_verdict_has_lineage(self, gate, high_confidence_context):
        result = gate.evaluate(high_confidence_context)
        assert "gate_version" in result.lineage
        assert "context_hash" in result.lineage
        assert result.lineage["gate_version"] == "1.0.0"

    def test_verdict_to_dict(self, gate, high_confidence_context):
        result = gate.evaluate(high_confidence_context)
        d = result.to_dict()
        assert d["verdict"] == "APPROVE"
        assert isinstance(d["lineage"], dict)

    def test_memory_patch_lineage(self):
        mem = MemoryInvariant(seal_id="s1")
        mem.apply_patch({"description": "initial fix"})
        assert mem.version == 2
        assert len(mem.lineage) == 1
        mem.apply_patch({"description": "follow-up"})
        assert mem.version == 3
        assert len(mem.lineage) == 2


# ── Edge Cases ──


class TestEdgeCases:
    def test_empty_context(self, gate):
        result = gate.evaluate(PRIMEContext())
        assert result.verdict in (Verdict.DEFER, Verdict.ESCALATE)

    def test_expired_assumptions_trigger(self, gate):
        ctx = PRIMEContext(
            truth=TruthInvariant(claim="Test", confidence=ConfidenceBand.HIGH, evidence=["e"]),
            reasoning=ReasoningInvariant(
                facts=["f1"],
                assumptions=[
                    {"statement": f"exp{i}", "expires_at": time.time() - 100}
                    for i in range(5)
                ],
            ),
            coherence_score=0.8,
        )
        result = gate.evaluate(ctx)
        assert any("expired_assumptions" in f for f in result.escalation_factors)

    def test_contested_escalate_policy(self):
        config = PRIMEConfig(contested_claim_policy="escalate")
        gate = PRIMEGate(config)
        ctx = PRIMEContext(
            truth=TruthInvariant(
                claim="Disputed",
                evidence=["e1"],
                disconfirmers=["d1"],
                confidence=ConfidenceBand.CONTESTED,
            ),
            reasoning=ReasoningInvariant(facts=["f1"]),
            coherence_score=0.7,
        )
        result = gate.evaluate(ctx)
        assert result.verdict == Verdict.ESCALATE
        assert any("contested_claim" in f for f in result.escalation_factors)
