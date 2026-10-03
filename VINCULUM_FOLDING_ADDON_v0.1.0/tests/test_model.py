import copy
import dataclasses
import json
import pytest
from vinculum_folding import FoldEpisode, FoldError, Lens, unassessed_lenses
from vinculum_folding.model import canonical, exact_number, strict_json, timestamp


def test_snapshot_is_lossless_and_immutable(episode, data):
    original = episode.digest
    ep = FoldEpisode(data)
    data["nodes"][0]["value"]["start"] = None
    assert ep.digest == original
    ep.to_dict()["nodes"].clear()
    assert ep.digest == original
    with pytest.raises(dataclasses.FrozenInstanceError): ep._json = "{}"


def test_roundtrip(episode):
    assert FoldEpisode(strict_json(canonical(episode.to_dict()))) == episode


@pytest.mark.parametrize("field,value", [("schema", "wrong"), ("revision", True), ("revision", 0),
    ("revision", 1.5), ("episode_id", ""), ("mission_id", " "), ("title", None),
    ("previous_digest", "f" * 64), ("nodes", {}), ("folds", None), ("evidence", "x")])
def test_invalid_top_level(data, field, value):
    data[field] = value
    with pytest.raises(FoldError): FoldEpisode(data)


@pytest.mark.parametrize("where", ["top", "node", "value", "fold", "lens", "evidence", "cerpa", "artifact"])
def test_unknown_fields_rejected(data, where):
    targets = {"top": data, "node": data["nodes"][0], "value": data["nodes"][0]["value"],
        "fold": data["folds"][0], "lens": data["folds"][0]["jit"][0],
        "evidence": data["evidence"][0], "cerpa": data["cerpa_links"][0], "artifact": data["artifact_links"][0]}
    targets[where]["truth_score"] = 1
    with pytest.raises(FoldError): FoldEpisode(data)


@pytest.mark.parametrize("collection", ["nodes", "folds", "evidence", "cerpa_links", "artifact_links"])
def test_duplicate_identity(data, collection):
    data[collection].append(copy.deepcopy(data[collection][0]))
    with pytest.raises(FoldError): FoldEpisode(data)


@pytest.mark.parametrize("bad", ["2026-10-03", "10:00", "2026-10-03T10:00:00", "2026-99-03T10:00:00Z", "2026-10-03T25:00:00Z"])
def test_naive_invalid_time_rejected(bad):
    with pytest.raises(FoldError): timestamp(bad)


def test_timezone_equivalence():
    assert timestamp("2026-10-03T10:00:00-04:00") == timestamp("2026-10-03T14:00:00Z")


def test_reversed_time(data):
    data["nodes"][0]["value"]["end"] = "2026-10-03T09:00:00-04:00"
    with pytest.raises(FoldError): FoldEpisode(data)


@pytest.mark.parametrize("value", [True, 1.2, "NaN", "Infinity", "1/0", "1e9999", "__import__('os')", "1" * 300])
def test_invalid_exact_number(value):
    with pytest.raises(FoldError): exact_number(value)


@pytest.mark.parametrize("value", ["1/3", "3.00", 3, "-1.25", "2e3"])
def test_exact_number_preserved(data, value):
    q = data["nodes"][2]["value"]["quantity"]
    q["lower"] = q["upper"] = value
    ep = FoldEpisode(data)
    assert ep.to_dict()["nodes"][2]["value"]["quantity"]["lower"] == value


@pytest.mark.parametrize("q", [dict(lower="4", upper="3", lower_inclusive=True, upper_inclusive=True),
    dict(lower=None, upper=None, lower_inclusive=True, upper_inclusive=True),
    dict(lower="3", upper="3", lower_inclusive=False, upper_inclusive=True),
    dict(lower="3", upper="3", lower_inclusive=1, upper_inclusive=True)])
def test_bad_numeric_ranges(data, q):
    data["nodes"][2]["value"]["quantity"] = q
    with pytest.raises(FoldError): FoldEpisode(data)


def test_null_quantity_is_valid_unknown(data):
    data["nodes"][2]["value"]["quantity"] = None
    assert FoldEpisode(data).to_dict()["nodes"][2]["value"]["quantity"] is None


def test_dangling_sources(data):
    data["nodes"][0]["source_ids"] = ["MISSING"]
    with pytest.raises(FoldError): FoldEpisode(data)


def test_dangling_fold(data):
    data["folds"][0]["to_node"] = "MISSING"
    with pytest.raises(FoldError): FoldEpisode(data)


def test_self_fold(data):
    data["folds"][0]["to_node"] = data["folds"][0]["from_node"]
    with pytest.raises(FoldError): FoldEpisode(data)


def test_all_four_jit_lenses_mandatory(data):
    data["folds"][0]["jit"].pop()
    with pytest.raises(FoldError): FoldEpisode(data)


def test_duplicate_jit(data):
    data["folds"][0]["jit"][1] = copy.deepcopy(data["folds"][0]["jit"][0])
    with pytest.raises(FoldError): FoldEpisode(data)


def test_jit_labels_not_generic_stages():
    assert [x["lens"] for x in unassessed_lenses()] == [x.value for x in Lens]
    a, b = unassessed_lenses(), unassessed_lenses()
    a[0]["evidence_ids"].append("x")
    assert not b[0]["evidence_ids"]


@pytest.mark.parametrize("missing", ["assessor", "evidence_ids"])
def test_claimed_support_needs_attribution_and_references(data, missing):
    entry = data["folds"][-1]["jit"][-1]
    entry[missing] = None if missing == "assessor" else []
    with pytest.raises(FoldError): FoldEpisode(data)


def test_awareness_preserves_epa(data):
    del data["folds"][-1]["jit"][2]["context"]["potency"]
    with pytest.raises(FoldError): FoldEpisode(data)


@pytest.mark.parametrize("payload", ['{"x":1,"x":2}', '{"x":NaN}', '{"x":Infinity}', '{"x":-Infinity}', '[['])
def test_strict_json(payload):
    with pytest.raises(FoldError): strict_json(payload)


def test_nested_json_limit():
    x = None
    for _ in range(65): x = [x]
    with pytest.raises(FoldError): canonical(x)


def test_revision_lineage(episode):
    next_ = episode.revise(recorded_at="2026-10-03T11:00:00-04:00", title="reviewed")
    assert next_.revision == 2
    assert next_.to_dict()["previous_digest"] == episode.digest
    assert episode.revision == 1


@pytest.mark.parametrize("field", ["episode_id", "mission_id", "previous_digest", "revision", "schema"])
def test_revision_cannot_reassign_identity(episode, field):
    with pytest.raises(FoldError): episode.revise(recorded_at="2026-10-03T11:00:00-04:00", **{field: "bad"})


@pytest.mark.parametrize("value", [[], {}, True, None, 3])
def test_wrong_type_fold_endpoint_is_a_validation_error(data, value):
    data["folds"][0]["from_node"] = value
    with pytest.raises(FoldError): FoldEpisode(data)
