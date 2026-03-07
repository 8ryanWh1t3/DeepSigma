"""Tests for core.model_exchange.evaluator — multi-adapter evaluation."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC_ROOT = _REPO_ROOT / "src"
if str(_SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(_SRC_ROOT))

from core.model_exchange.evaluator import evaluate_results  # noqa: E402
from core.model_exchange.consensus import (  # noqa: E402
    agreement_score,
    claim_overlap_score,
    reasoning_overlap_score,
)
from core.model_exchange.contradiction import (  # noqa: E402
    contradiction_score,
    detect_claim_contradictions,
)
from core.model_exchange.confidence import (  # noqa: E402
    aggregate_confidence,
    downweight_for_contradictions,
    score_evidence_coverage,
)
from core.model_exchange.ttl import (  # noqa: E402
    compute_claim_ttl_seconds,
    ttl_from_packet,
)
from core.model_exchange.models import (  # noqa: E402
    CandidateClaim,
    ContradictionRecord,
    EvaluationResult,
    ModelMeta,
    ReasoningResult,
    ReasoningStep,
)
from core.model_exchange.adapters.mock_adapter import MockAdapter  # noqa: E402
from core.model_exchange.adapters.apex_adapter import ApexAdapter  # noqa: E402


def _sample_packet():
    return {
        "request_id": "REQ-EVAL-001",
        "topic": "test",
        "question": "Is the system healthy?",
        "evidence": ["ev-1"],
    }


def _make_result(adapter_name="test", claims=None, confidence=0.8):
    return ReasoningResult(
        request_id="REQ-001",
        adapter_name=adapter_name,
        claims=claims or [
            CandidateClaim(
                claim_id="C-1",
                text="System is healthy",
                claim_type="inference",
                confidence=0.8,
                citations=["ev-1"],
            )
        ],
        reasoning=[
            ReasoningStep(step_id="S-1", kind="observation", text="Checking health"),
        ],
        confidence=confidence,
        citations=["ev-1"],
        contradictions=[],
        model_meta=ModelMeta(
            provider="local", model="test", adapter_name=adapter_name
        ),
    )


# -- Evaluator --


class TestEvaluateResults:
    def test_empty_results(self):
        ev = evaluate_results([])
        assert ev.recommended_escalation == "reject"
        assert ev.drift_likelihood == 1.0

    def test_single_result(self):
        ev = evaluate_results([_make_result()])
        assert isinstance(ev, EvaluationResult)
        assert 0 <= ev.agreement_score <= 1
        assert 0 <= ev.contradiction_score <= 1
        assert 0 <= ev.drift_likelihood <= 1

    def test_two_agreeing_results(self):
        r1 = _make_result(adapter_name="a")
        r2 = _make_result(adapter_name="b")
        ev = evaluate_results([r1, r2])
        assert ev.agreement_score > 0.5
        assert ev.contradiction_score == 0.0

    def test_scores_bounded(self):
        mock = MockAdapter()
        apex = ApexAdapter()
        r1 = mock.reason(_sample_packet())
        r2 = apex.reason(_sample_packet())
        ev = evaluate_results([r1, r2])
        for score in [
            ev.agreement_score,
            ev.contradiction_score,
            ev.novelty_score,
            ev.evidence_coverage_score,
            ev.drift_likelihood,
        ]:
            assert 0 <= score <= 1

    def test_escalation_accept_for_drafting(self):
        r1 = _make_result(adapter_name="a")
        r2 = _make_result(adapter_name="b")
        ev = evaluate_results([r1, r2])
        assert ev.recommended_escalation == "accept-for-drafting"

    def test_high_contradiction_triggers_authority_review(self):
        r1 = _make_result(
            adapter_name="a",
            claims=[
                CandidateClaim(
                    claim_id="C-1",
                    text="The system is safe and secure and compliant",
                    claim_type="fact",
                    confidence=0.9,
                    citations=["ev-1"],
                )
            ],
        )
        r2 = _make_result(
            adapter_name="b",
            claims=[
                CandidateClaim(
                    claim_id="C-2",
                    text="The system is unsafe and insecure and noncompliant",
                    claim_type="fact",
                    confidence=0.9,
                    citations=["ev-1"],
                )
            ],
        )
        ev = evaluate_results([r1, r2])
        assert ev.contradiction_score > 0
        assert ev.recommended_escalation in ("authority-review", "human-review")

    def test_no_claims_triggers_reject(self):
        r = ReasoningResult(
            request_id="REQ-001",
            adapter_name="empty",
            claims=[],
            reasoning=[],
            confidence=0.0,
            citations=[],
            contradictions=[],
            model_meta=ModelMeta(
                provider="local", model="test", adapter_name="empty"
            ),
        )
        ev = evaluate_results([r])
        assert ev.recommended_escalation == "reject"

    def test_to_dict_serializable(self):
        ev = evaluate_results([_make_result()])
        d = ev.to_dict()
        assert "requestId" in d
        assert "agreementScore" in d
        assert "recommendedEscalation" in d


# -- Consensus --


class TestConsensus:
    def test_claim_overlap_single(self):
        assert claim_overlap_score([_make_result()]) == 1.0

    def test_claim_overlap_identical(self):
        r1 = _make_result(adapter_name="a")
        r2 = _make_result(adapter_name="b")
        score = claim_overlap_score([r1, r2])
        assert score == 1.0

    def test_reasoning_overlap_single(self):
        assert reasoning_overlap_score([_make_result()]) == 1.0

    def test_agreement_score_bounded(self):
        r1 = _make_result(adapter_name="a")
        r2 = _make_result(adapter_name="b")
        score = agreement_score([r1, r2])
        assert 0 <= score <= 1


# -- Contradiction --


class TestContradiction:
    def test_no_contradictions(self):
        r1 = _make_result(adapter_name="a")
        r2 = _make_result(adapter_name="b")
        records = detect_claim_contradictions([r1, r2])
        assert len(records) == 0

    def test_polarity_contradiction(self):
        r1 = _make_result(
            adapter_name="a",
            claims=[
                CandidateClaim(
                    claim_id="C-1",
                    text="The deployment is safe and secure",
                    claim_type="fact",
                    confidence=0.9,
                )
            ],
        )
        r2 = _make_result(
            adapter_name="b",
            claims=[
                CandidateClaim(
                    claim_id="C-2",
                    text="The deployment is unsafe and insecure",
                    claim_type="fact",
                    confidence=0.9,
                )
            ],
        )
        records = detect_claim_contradictions([r1, r2])
        assert len(records) >= 1
        assert records[0].severity in ("low", "medium", "high")

    def test_contradiction_score_bounded(self):
        score = contradiction_score([_make_result()])
        assert 0 <= score <= 1


# -- Confidence --


class TestConfidence:
    def test_aggregate_empty(self):
        assert aggregate_confidence([]) == 0.0

    def test_aggregate_single(self):
        r = _make_result(confidence=0.8)
        assert aggregate_confidence([r]) == 0.8

    def test_downweight(self):
        assert downweight_for_contradictions(0.9, 0.0) == 0.9
        assert downweight_for_contradictions(0.9, 1.0) == pytest.approx(0.45)

    def test_evidence_coverage_all_cited(self):
        r = _make_result()
        assert score_evidence_coverage([r]) == 1.0

    def test_evidence_coverage_none_cited(self):
        r = _make_result(
            claims=[
                CandidateClaim(
                    claim_id="C-1",
                    text="uncited claim",
                    claim_type="inference",
                    confidence=0.5,
                )
            ]
        )
        assert score_evidence_coverage([r]) == 0.0


# -- TTL --


class TestTTL:
    def test_ttl_from_packet_present(self):
        assert ttl_from_packet({"ttl": 3600}) == "3600"

    def test_ttl_from_packet_absent(self):
        assert ttl_from_packet({}) is None

    def test_compute_ttl_int(self):
        assert compute_claim_ttl_seconds({"ttl": 3600}) == 3600

    def test_compute_ttl_string(self):
        assert compute_claim_ttl_seconds({"ttl": "7200"}) == 7200

    def test_compute_ttl_absent(self):
        assert compute_claim_ttl_seconds({}) is None

    def test_compute_ttl_zero(self):
        assert compute_claim_ttl_seconds({"ttl": 0}) is None


# -- Models --


class TestModels:
    def test_normalized_confidence_clamped(self):
        r = _make_result(confidence=1.5)
        assert r.normalized_confidence() == 1.0
        r2 = _make_result(confidence=-0.5)
        assert r2.normalized_confidence() == 0.0

    def test_has_high_severity_contradictions(self):
        r = _make_result()
        assert r.has_high_severity_contradictions() is False

    def test_claims_by_type(self):
        r = _make_result()
        inferences = r.claims_by_type("inference")
        assert len(inferences) == 1
        assert r.claims_by_type("risk") == []

    def test_reasoning_result_to_dict(self):
        r = _make_result()
        d = r.to_dict()
        assert d["adapterName"] == "test"
        assert len(d["claims"]) == 1

    def test_candidate_claim_to_dict(self):
        c = CandidateClaim(
            claim_id="C-1",
            text="test",
            claim_type="fact",
            confidence=0.9,
            citations=["ev-1"],
            ttl_seconds=3600,
        )
        d = c.to_dict()
        assert d["claimId"] == "C-1"
        assert d["ttlSeconds"] == 3600

    def test_model_meta_to_dict(self):
        m = ModelMeta(
            provider="local",
            model="test",
            adapter_name="test",
            version="1.0",
        )
        d = m.to_dict()
        assert d["provider"] == "local"
        assert d["version"] == "1.0"
