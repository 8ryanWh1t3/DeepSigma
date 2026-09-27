import pytest

from pyaltcog import AltCogEngine, DiscoverySurface, EvidenceItem, MaturityState, Prediction


def make_operational(engine: AltCogEngine):
    s1 = engine.capture_friction(
        stream_id="S", surface=DiscoverySurface.OUTCOME_MISMATCH,
        statement="identity reset after handoff", source="log", strength=0.9,
        tags=["identity", "handoff"], domain="C-UAS",
        detected_at="2026-01-01T00:00:00+00:00",
    )
    s2 = engine.capture_friction(
        stream_id="S", surface=DiscoverySurface.REPEATED_EXCEPTION,
        statement="repeated identity reset following handoff", source="log", strength=0.9,
        tags=["identity", "handoff"], domain="C-UAS",
        detected_at="2026-01-01T00:01:00+00:00",
    )
    cluster = engine.cluster([s1, s2], min_similarity=0.1, created_at="2026-01-01T00:02:00+00:00")[0]
    c = engine.create_candidate(
        cluster=cluster,
        dominant_model="random noise",
        hypothesis="handoff mechanism",
        prediction=Prediction(variable="rate", dominant_expected="flat", alternative_expected="rise"),
        evidence=[EvidenceItem(id="E", statement="repeat", source="log", confidence=0.95)],
        mission_relevance=0.9,
        owner="owner",
        revisit_trigger="next handoff",
        created_at="2026-01-01T00:03:00+00:00",
    )
    engine.score(c)
    engine.promote_if_ready(c)
    return c


def test_end_to_end_promotes_to_ac6():
    e = AltCogEngine()
    c = make_operational(e)
    assert c.maturity == MaturityState.AC6_OPERATIONAL_ALTERNATIVE
    assert e.ledger.verify()


def test_plan_builds_request():
    e = AltCogEngine()
    c = make_operational(e)
    plan = e.plan(c)
    assert len(plan.requests) == 1
    assert plan.requests[0].variable == "rate"


def test_validation_can_promote_ac7():
    e = AltCogEngine()
    c = make_operational(e)
    e.validate(c, verdict="alternative_supported", rationale="observed rise", confidence=0.9)
    assert c.maturity == MaturityState.AC7_PROMOTED_MODEL


def test_validation_can_archive_ac8():
    e = AltCogEngine()
    c = make_operational(e)
    e.validate(c, verdict="dominant_supported", rationale="flat rate", confidence=0.9)
    assert c.maturity == MaturityState.AC8_ARCHIVED_WITH_TRIGGER


def test_inconclusive_stays_ac6():
    e = AltCogEngine()
    c = make_operational(e)
    e.validate(c, verdict="inconclusive", rationale="mixed", confidence=0.4)
    assert c.maturity == MaturityState.AC6_OPERATIONAL_ALTERNATIVE


def test_validation_requires_ac6():
    e = AltCogEngine()
    s = e.capture_friction(stream_id="S", surface=DiscoverySurface.OUTCOME_MISMATCH,
                           statement="x", source="log", detected_at="t")
    cl = e.cluster([s], created_at="t")[0]
    c = e.create_candidate(cluster=cl, dominant_model="d", hypothesis="h", created_at="t")
    with pytest.raises(ValueError):
        e.validate(c, verdict="inconclusive", rationale="x")


def test_residual_creates_rer_and_signal():
    e = AltCogEngine()
    rer, signal = e.capture_residual(
        stream_id="S", dominant_model="D", observed="10", explained="8", residual="2 unexplained",
        source="lab", detected_at="2026-01-01T00:00:00+00:00",
    )
    assert rer.signal_id == signal.id
    assert signal.surface == DiscoverySurface.RESIDUAL_EVIDENCE


def test_promotion_blockers_are_recorded():
    e = AltCogEngine()
    s = e.capture_friction(stream_id="S", surface=DiscoverySurface.OUTCOME_MISMATCH,
                           statement="x", source="log", detected_at="t")
    cl = e.cluster([s], created_at="t")[0]
    c = e.create_candidate(cluster=cl, dominant_model="D", hypothesis="H", created_at="t")
    e.score(c)
    e.promote_if_ready(c)
    assert c.maturity == MaturityState.AC5_SCORED_ALTERNATIVE
    assert c.metadata["promotion_blockers"]
