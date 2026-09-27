from pyaltcog.adapters import to_cerpa, to_dko, to_franops, to_intelops, to_pathfinder, to_reops, to_resonator
from pyaltcog.models import AltCogCandidatePacket, MaturityState, Prediction


def candidate():
    return AltCogCandidatePacket(
        id="ACP-1", stream_id="S", cluster_id="ECC-1", dominant_model="D", hypothesis="H",
        created_at="t", maturity=MaturityState.AC6_OPERATIONAL_ALTERNATIVE,
        signal_ids=["FSR-1"], predictions=[Prediction("x", "a", "b")],
        owner="O", revisit_trigger="R",
    )


def test_projections_have_identity():
    c = candidate()
    assert to_cerpa(c)["review"]["candidate_id"] == "ACP-1"
    assert to_dko(c)["identity"] == "ACP-1"
    assert to_resonator(c)["candidate_id"] == "ACP-1"
    assert any(e["object"] == "ACP-1" for e in to_pathfinder(c))
    assert to_intelops(c)["claim"] == "H"
    assert to_reops(c)["candidate_id"] == "ACP-1"
    assert to_franops(c)["canon_change_candidate"] == "ACP-1"
