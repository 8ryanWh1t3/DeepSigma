import pytest

from pyaltcog.lifecycle import LifecycleError, can_transition, transition
from pyaltcog.models import AltCogCandidatePacket, MaturityState


def candidate(state=MaturityState.AC4_ALTERNATIVE_HYPOTHESIS):
    return AltCogCandidatePacket(
        id="ACP-1", stream_id="S", cluster_id="ECC-1", dominant_model="D",
        hypothesis="H", created_at="t", maturity=state,
    )


def test_ac4_to_ac5_allowed():
    c = candidate()
    transition(c, MaturityState.AC5_SCORED_ALTERNATIVE)
    assert c.maturity == MaturityState.AC5_SCORED_ALTERNATIVE


def test_skipping_ac4_to_ac6_blocked():
    with pytest.raises(LifecycleError):
        transition(candidate(), MaturityState.AC6_OPERATIONAL_ALTERNATIVE)


def test_ac8_can_reactivate_to_ac4():
    c = candidate(MaturityState.AC8_ARCHIVED_WITH_TRIGGER)
    transition(c, MaturityState.AC4_ALTERNATIVE_HYPOTHESIS)
    assert c.maturity == MaturityState.AC4_ALTERNATIVE_HYPOTHESIS


def test_ac7_can_archive():
    assert can_transition(MaturityState.AC7_PROMOTED_MODEL, MaturityState.AC8_ARCHIVED_WITH_TRIGGER)
