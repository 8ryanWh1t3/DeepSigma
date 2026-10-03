from vinculum_folding import FoldEpisode, FoldError, audit, compare, project, review_input, unfold
import pytest


def test_scope_expansion_is_a_review_not_a_truth_verdict(episode):
    result = audit(episode)
    findings = [x for x in result.findings if x.code == "SCOPE_EXPANSION_REVIEW"]
    assert len(findings) == 1
    assert "not proof" in findings[0].message
    assert result.declared_evidence_roots == ("SYNTHETIC-INSPECTION",)
    assert dict(result.aspect_counts) == {"TIME": 1, "WORDS": 2, "NUMBERS": 1}


def test_no_lexical_scope_inference(data):
    data["nodes"][-1]["value"]["scope"] = "UNSPECIFIED"
    result = audit(FoldEpisode(data))
    assert not any(x.code == "SCOPE_EXPANSION_REVIEW" for x in result.findings)


def test_project_read_only_and_no_truth_score(episode):
    view = project(episode)
    assert view["read_only"] is True
    assert "truth_score" not in view
    assert view["audit"]["automatic_actions"] == 0
    assert len(view["lenses"]) == 4
    assert {a["kind"] for a in view["artifact_links"]} == {"DLR"}


def test_unfold_returns_sources_jit_and_original_text(episode):
    result = unfold(episode, "summary-derivation")
    assert len(result["evidence"]) == 2
    assert len(result["fold"]["jit"]) == 4
    assert {n["id"] for n in result["nodes"]} == {"summary", "observation"}
    with pytest.raises(FoldError): unfold(episode, "missing")


def test_missing_data_not_invented(data):
    data["nodes"][0]["value"]["start"] = None
    data["nodes"][2]["value"]["quantity"] = None
    data["nodes"][2]["value"]["unit"] = None
    data["nodes"][2]["source_ids"] = []
    data["evidence"][0]["locator"] = None
    data["evidence"][0]["sha256"] = None
    result = audit(FoldEpisode(data))
    codes = {x.code for x in result.findings}
    assert {"TIME_UNSPECIFIED", "QUANTITY_UNKNOWN", "UNIT_UNSPECIFIED", "EVIDENCE_MISSING", "SOURCE_LOCATOR_MISSING", "SOURCE_HASH_UNPINNED", "JIT_EVIDENCE_UNLOCATED"} <= codes


def test_draft_review_not_apply(episode):
    result = review_input(episode)
    assert result["requested_stage"] == "REVIEW"
    assert result["disposition"] == "DRAFT_REVIEW_INPUT"
    assert result["automatic_actions"] == 0


def test_apply_link_is_not_success(data):
    data["cerpa_links"].append({"stage": "APPLY", "record_id": "A1", "locator": "synthetic://apply", "sha256": None})
    result = project(FoldEpisode(data))
    assert "success" not in result
    assert "APPLY is not proof" in result["boundary"]


def test_revision_diff(episode):
    data = episode.to_dict()
    data["nodes"][-1]["value"]["scope"] = "RECORDED"
    next_ = episode.revise(recorded_at="2026-10-03T11:00:00Z", nodes=data["nodes"])
    diff = compare(episode, next_)
    assert diff["direct_successor"]
    assert diff["changes"]["nodes"]["changed"] == ["summary"]


def test_other_episode_not_revision(episode, data):
    data["episode_id"] = "OTHER"
    with pytest.raises(FoldError): compare(episode, FoldEpisode(data))


@pytest.mark.parametrize("second, expected", [
    ("2026-10-03T09:00:00-04:00", "TEMPORAL_ORDER_CONFLICT"),
    ("2026-10-03T10:00:00-04:00", "TEMPORAL_ORDER_CONFLICT"),
    ("2026-10-03T11:00:00-04:00", None)])
def test_temporal_check(data, second, expected):
    import copy
    node = copy.deepcopy(data["nodes"][0]); node["id"] = "time2"; node["value"]["start"] = second
    data["nodes"].append(node)
    data["folds"][0].update(to_node="time2", relation="PRECEDES")
    codes = {x.code for x in audit(FoldEpisode(data)).findings}
    if expected: assert expected in codes
    else: assert not any(x.startswith("TEMPORAL_") for x in codes)


def test_revision_diff_includes_metadata_and_record_links(episode):
    after = episode.revise(recorded_at="2026-10-03T16:00:00Z", title="New title", cerpa_links=[])
    result = compare(episode, after)
    assert set(result["metadata_changes"]) == {"title", "recorded_at", "cerpa_links"}
    assert not result["host_capture_changed"]
