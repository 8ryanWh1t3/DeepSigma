from deep_sigma_vsa import VoiceSemanticAdapter


def test_cerpa_candidate_view():
    packet = VoiceSemanticAdapter().from_transcript("We may need another sensor.")
    rows = packet.to_cerpa_candidates()
    assert rows[0]["cerpa_stage"] == "Claim"
    assert rows[0]["next"] == "Review"


def test_composer_never_auto_authoritative():
    packet = VoiceSemanticAdapter().from_transcript("This shall become policy.")
    candidate = packet.to_composer_candidates()[0]
    assert candidate["authority_status"] == "candidate"
    assert candidate["requires_human_review"] is True
