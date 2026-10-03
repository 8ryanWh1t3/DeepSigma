import copy
import pytest
from vinculum_folding.demo import inspection_demo

@pytest.fixture
def episode():
    return inspection_demo()

@pytest.fixture
def data(episode):
    return episode.to_dict()

@pytest.fixture
def host_run():
    """Synthetic serialization-contract fixture, NOT execution of the host engine."""
    reps = []
    for rid, side in [("L1", "L"), ("M1", "M")]:
        reps.append({"id": rid, "side": side, "order": 7 if side == "L" else 2,
            "entity": "INSPECTION", "concept": "recorded_defects",
            "quantity": {"lower": "3", "upper": "3", "lower_inclusive": True, "upper_inclusive": True},
            "unit": "count", "scope": {"scope_id": "S", "window": {
                "start": "2026-10-03T10:00:00-04:00", "end": "2026-10-03T10:01:00-04:00"}},
            "text": "three recorded defects" if side == "L" else "3", "method": "inspection",
            "pd": {"probabilistic": 0.4, "deterministic": 0.7, "basis": "synthetic descriptors"},
            "support": {"factors": []}, "source_ids": ["S1"], "depends_on": [],
            "material": True, "definition_id": "D1"})
    scenario = {"schema": "vinculum.crossorder.scenario/1", "id": "GRAPH-1",
        "representations": reps,
        "pairs": [{"id": "P1", "left_id": "L1", "right_id": "M1", "rationale": "explicit selection",
                   "hinge_orders": [1, 2, 3, 4, 5], "hinge_states": []}],
        "groups": [], "policy": {}, "units": [], "transformations": [], "context": None}
    pipeline = {"schema": "vinculum.pipeline.result/1", "engine_version": "0.7.0",
        "job_fingerprint": "a" * 64, "ontology_fingerprint": "b" * 64,
        "report": {"schema": "vinculum.crossorder.report/1", "engine_version": "0.7.0",
            "graph_id": "GRAPH-1", "representations": copy.deepcopy(reps),
            "pairs": [{"pair_id": "P1", "status": "ALIGNED", "raw_collision_score": 0,
                       "supported_collision_score": None, "discrepancy": "0"}],
            "summary": {"status": "ALIGNED", "selected_pairs": 1}, "matrix": {}, "groups": {}, "contract": {}},
        "sources": [{"id": "S1", "sha256": "c" * 64, "uri": "synthetic://inspection"}],
        "codec_reports": [], "stage_trace": [], "findings": [], "warnings": []}
    class Serializer:
        def __init__(self, payload): self.payload = payload
        def to_dict(self): return self.payload  # deliberately returns alias: adapter must copy
    class Run(Serializer):
        def __init__(self):
            super().__init__(pipeline)
            self.scenario = Serializer(scenario)
        def evaluate(self): raise AssertionError("add-on must not re-evaluate host")
        def export(self, *_): raise AssertionError("add-on must not export or mutate host")
    return Run()
