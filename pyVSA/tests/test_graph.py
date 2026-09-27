from deep_sigma_vsa import VoiceSemanticAdapter


def test_graph_projection_contains_evidence_edge():
    packet = VoiceSemanticAdapter().from_transcript("We should review the plan.")
    graph = packet.to_pathfinder_payload()
    assert any(edge["predicate"] == "supportedBy" for edge in graph["edges"])


def test_turtle_contains_claim():
    packet = VoiceSemanticAdapter().from_transcript("Coverage is sufficient.")
    ttl = packet.to_turtle()
    assert "ds:Claim" in ttl
    assert "Coverage is sufficient." in ttl
