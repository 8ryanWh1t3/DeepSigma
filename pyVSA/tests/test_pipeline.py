from deep_sigma_vsa import AuthorityStatus, Modality, VoiceSemanticAdapter


def test_probable_concern_stays_candidate():
    packet = VoiceSemanticAdapter().from_transcript(
        "We can probably cover the eastern sector, but I am concerned about a gap.",
        speaker_id="cmdr",
    )
    assert len(packet.claims) == 1
    claim = packet.claims[0]
    assert claim.modality == Modality.PROBABLE
    assert claim.authority_status == AuthorityStatus.CANDIDATE
    assert packet.governance.human_review_required is True
    assert len(packet.events) == 1
    assert packet.events[0].event_type == "risk_signal"


def test_required_language():
    packet = VoiceSemanticAdapter().from_transcript("The team must validate the sensor coverage.")
    assert packet.claims[0].modality == Modality.REQUIRED


def test_empty_transcript_rejected():
    try:
        VoiceSemanticAdapter().from_transcript("   ")
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError")
