"""Real-host smoke test. A skip is NOT a passed host integration result."""
import importlib.util
import pytest

pytestmark = pytest.mark.skipif(importlib.util.find_spec("vinculum") is None,
                                reason="actual VINCULUM host package unavailable in this build runtime")


def test_real_pipeline_capture_is_non_mutating():
    from vinculum import VinculumPipeline
    from vinculum_folding import from_pipeline, host_pair_results
    from vinculum_folding.model import canonical
    job = {"schema": "vinculum.pipeline.job/1", "id": "FOLD-HOST-SMOKE",
           "scenario": {"schema": "vinculum.crossorder.scenario/1", "id": "FOLD-HOST-SMOKE",
            "representations": [
                {"id": "L1", "side": "L", "order": 1, "entity": "inspection", "concept": "defect_count",
                 "quantity": {"lower": "3", "upper": "3"}, "unit": "count", "text": "three recorded defects",
                 "scope": {"timeless": True}},
                {"id": "M1", "side": "M", "order": 1, "entity": "inspection", "concept": "defect_count",
                 "quantity": {"lower": "3", "upper": "3"}, "unit": "count", "text": "3",
                 "scope": {"timeless": True}}],
            "pairs": [{"id": "P1", "left_id": "L1", "right_id": "M1", "rationale": "explicit smoke-test pair"}]}}
    run = VinculumPipeline().run(job)
    before = canonical({"result": run.to_dict(), "scenario": run.scenario.to_dict()})
    ep = from_pipeline(run, episode_id="EP-SMOKE", mission_id="DEMO", title="Host API smoke test",
                       recorded_at="2026-10-03T16:00:00Z")
    after = canonical({"result": run.to_dict(), "scenario": run.scenario.to_dict()})
    assert before == after
    assert host_pair_results(ep)["P1"]["status"] == run.report.pairs[0].status.value
