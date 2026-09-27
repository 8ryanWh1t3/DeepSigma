from pyaltcog import AltCogEngine, DiscoverySurface, EvidenceItem, MaturityState, Prediction


def test_archive_preserves_and_reactivates():
    e = AltCogEngine()
    s = e.capture_friction(
        stream_id="S", surface=DiscoverySurface.REPEATED_EXCEPTION,
        statement="identity reset after handoff", source="log", strength=0.8,
        tags=["identity", "handoff"], detected_at="2026-01-01T00:00:00+00:00",
    )
    cl = e.cluster([s], created_at="2026-01-01T00:01:00+00:00")[0]
    c = e.create_candidate(
        cluster=cl, dominant_model="noise", hypothesis="handoff creates reset",
        prediction=Prediction(variable="rate", dominant_expected="flat", alternative_expected="rise"),
        evidence=[EvidenceItem(id="E", statement="one signal", source="log", confidence=0.9)],
        mission_relevance=0.9, owner="team", revisit_trigger="handoff reset",
        created_at="2026-01-01T00:02:00+00:00",
    )
    e.score(c)
    c, monitor = e.archive(c, reason="not enough cycles", archived_at="2026-01-01T00:03:00+00:00")
    assert c.maturity == MaturityState.AC8_ARCHIVED_WITH_TRIGGER

    s2 = e.capture_friction(
        stream_id="S", surface=DiscoverySurface.REPEATED_EXCEPTION,
        statement="new handoff reset observed", source="log", strength=0.9,
        tags=["handoff", "reset"], detected_at="2026-01-02T00:00:00+00:00",
    )
    c, monitor, hits = e.reactivate(c, monitor, [s2], reactivated_at="2026-01-02T00:01:00+00:00")
    assert c.maturity == MaturityState.AC4_ALTERNATIVE_HYPOTHESIS
    assert hits
    assert not monitor.active
