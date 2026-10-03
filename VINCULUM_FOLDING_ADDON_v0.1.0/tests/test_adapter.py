import copy
import pytest
from vinculum_folding import FoldEpisode, FoldError, from_pipeline, host_pair_results, project
from vinculum_folding.model import canonical, digest


def capture(run):
    return from_pipeline(run, episode_id="EP-HOST", mission_id="M1", title="Host capture",
                         recorded_at="2026-10-03T15:00:00Z")


def test_host_contract_preserves_snapshot_and_does_not_mutate(host_run):
    a, b = copy.deepcopy(host_run.to_dict()), copy.deepcopy(host_run.scenario.to_dict())
    ep = capture(host_run)
    assert host_run.to_dict() == a and host_run.scenario.to_dict() == b
    kept = ep.to_dict()["host_capture"]
    assert kept["pipeline"] == a and kept["scenario"] == b
    assert len(ep.to_dict()["nodes"]) == 4  # two existing reps + their explicit windows
    host_run.payload["report"]["pairs"][0]["status"] = "CONFLICT"
    assert host_pair_results(ep)["P1"]["status"] == "ALIGNED"
    assert kept["scenario"]["representations"][0]["order"] == 7
    assert kept["scenario"]["representations"][0]["pd"]["deterministic"] == .7


@pytest.mark.parametrize("status", ["ALIGNED", "PARTIAL", "CONFLICT", "UNRESOLVED", "NOT_COMPARABLE"])
def test_five_host_states_are_not_collapsed(host_run, status):
    host_run.payload["report"]["pairs"][0]["status"] = status
    ep = capture(host_run)
    assert project(ep)["host_pair_results"]["P1"]["status"] == status


def test_no_inferred_time_or_ontological_grade(host_run):
    for collection in [host_run.scenario.payload["representations"], host_run.payload["report"]["representations"]]:
        for r in collection: r["scope"] = {"timeless": True}
    ep = capture(host_run)
    assert not any(n["aspect"] == "TIME" for n in ep.to_dict()["nodes"])
    assert all(n["ontological_grade"] == "UNSPECIFIED" for n in ep.to_dict()["nodes"])


def test_missing_host_sources_stay_missing(host_run):
    host_run.payload["sources"] = []
    ep = capture(host_run)
    ev = ep.to_dict()["evidence"][0]
    assert ev["locator"] is None and ev["sha256"] is None
    assert "unresolved" in ev["description"]


def test_unpaired_host_node_no_invented_result(host_run):
    host_run.scenario.payload["pairs"] = []
    host_run.payload["report"]["pairs"] = []
    ep = capture(host_run)
    assert not host_pair_results(ep)
    assert not any(f["relation"] == "SELECTED_PAIR" for f in ep.to_dict()["folds"])


@pytest.mark.parametrize("which", ["pipeline", "scenario", "report", "version", "pair_status", "graph_id"])
def test_incompatible_contract_rejected(host_run, which):
    if which == "pipeline": host_run.payload["schema"] = "vinculum.pipeline/1"
    elif which == "scenario": host_run.scenario.payload["schema"] = "wrong"
    elif which == "report": host_run.payload["report"]["schema"] = "wrong"
    elif which == "version": host_run.payload["engine_version"] = "0.8.0"
    elif which == "pair_status": host_run.payload["report"]["pairs"][0]["status"] = "TRUE"
    else: host_run.payload["report"]["graph_id"] = "OTHER"
    with pytest.raises(FoldError): capture(host_run)


def test_mismatched_host_result(host_run):
    host_run.payload["report"]["pairs"] = []
    with pytest.raises(FoldError): capture(host_run)


def test_mismatched_host_representation(host_run):
    host_run.payload["report"]["representations"][0]["text"] = "changed"
    with pytest.raises(FoldError): capture(host_run)


def test_host_capture_hash_tamper(host_run):
    data = capture(host_run).to_dict()
    data["host_capture"]["pipeline"]["report"]["pairs"][0]["status"] = "CONFLICT"
    with pytest.raises(FoldError): FoldEpisode(data)


@pytest.mark.parametrize("change", ["omit_node", "omit_pair", "number", "text", "side", "sources", "endpoint"])
def test_host_projection_is_lossless(host_run, change):
    data = capture(host_run).to_dict()
    node = next(n for n in data["nodes"] if n.get("host_representation_id") == "M1")
    word = next(n for n in data["nodes"] if n.get("host_representation_id") == "L1")
    if change == "omit_node": data["nodes"].remove(node)
    elif change == "omit_pair": data["folds"] = [f for f in data["folds"] if f.get("host_pair_id") is None]
    elif change == "number": node["value"]["quantity"]["upper"] = "4"
    elif change == "text": word["value"]["text"] = "something else"
    elif change == "side": node["aspect"] = "WORDS"; node["value"] = word["value"]
    elif change == "sources": node["source_ids"] = []
    else:
        f = next(f for f in data["folds"] if f.get("host_pair_id"))
        f["from_node"], f["to_node"] = f["to_node"], f["from_node"]
    with pytest.raises(FoldError): FoldEpisode(data)
