from pyaltcog.models import AltCogCandidatePacket, EvidenceItem, Prediction
from pyaltcog.scoring import PromotionPolicy, operational_readiness, score_candidate


def complete_candidate():
    return AltCogCandidatePacket(
        id="ACP-1", stream_id="S", cluster_id="ECC-1", dominant_model="random noise",
        hypothesis="handoff mechanism", created_at="t", signal_ids=["FSR-1"],
        evidence=[EvidenceItem(id="E1", statement="repeat", source="log", confidence=0.9)],
        predictions=[Prediction(variable="rate", dominant_expected="flat", alternative_expected="rise")],
        falsification_conditions=["rate remains flat"], mission_relevance=0.9,
        owner="team", revisit_trigger="next event",
    )


def test_complete_candidate_scores_high():
    c = complete_candidate()
    score = score_candidate(c)
    assert score.total >= 0.7
    assert score.evidence == 0.9


def test_missing_evidence_blocks_operational():
    c = complete_candidate()
    c.evidence = []
    c.score = score_candidate(c)
    ready, reasons = operational_readiness(c)
    assert not ready
    assert "evidence confidence below threshold" in reasons


def test_missing_owner_blocks_operational():
    c = complete_candidate()
    c.owner = ""
    c.score = score_candidate(c)
    ready, reasons = operational_readiness(c)
    assert not ready
    assert "owner missing" in reasons


def test_same_prediction_not_discriminating():
    c = complete_candidate()
    c.predictions = [Prediction(variable="x", dominant_expected="same", alternative_expected="same")]
    c.score = score_candidate(c)
    ready, reasons = operational_readiness(c)
    assert not ready
    assert "prediction does not discriminate" in reasons


def test_custom_threshold_can_block():
    c = complete_candidate()
    c.score = score_candidate(c)
    ready, _ = operational_readiness(c, PromotionPolicy(minimum_total=0.99))
    assert not ready
