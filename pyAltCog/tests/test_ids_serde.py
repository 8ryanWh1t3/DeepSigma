from pyaltcog.ids import stable_hash, stable_id
from pyaltcog.models import DiscoverySurface, FrictionSignalRecord, MaturityState
from pyaltcog.serde import canonical_json, to_primitive


def test_stable_hash_order_independent_for_dicts():
    assert stable_hash({"a": 1, "b": 2}) == stable_hash({"b": 2, "a": 1})


def test_stable_id_prefix():
    assert stable_id("ACP", {"x": 1}).startswith("ACP-")


def test_enum_serialization():
    obj = FrictionSignalRecord(
        id="x", stream_id="s", surface=DiscoverySurface.OUTCOME_MISMATCH,
        statement="mismatch", source="src", detected_at="t",
        maturity=MaturityState.AC2_WEAK_SIGNAL,
    )
    p = to_primitive(obj)
    assert p["surface"] == "outcome_mismatch"
    assert p["maturity"] == "AC2"


def test_canonical_json_deterministic():
    assert canonical_json({"z": [2, 1], "a": True}) == canonical_json({"a": True, "z": [2, 1]})
