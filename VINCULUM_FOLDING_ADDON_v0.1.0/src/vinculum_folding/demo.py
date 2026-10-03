"""Synthetic inspection fixture, not live operational data."""
from __future__ import annotations

import hashlib

from .model import FoldEpisode, episode_template, unassessed_lenses

OBSERVATION = "At 10:00, the inspection recorded three defects."
SUMMARY = "Only three defects existed."


def inspection_demo() -> FoldEpisode:
    data = episode_template(episode_id="EP-INSPECTION-001", mission_id="DEMO-MISSION",
                            title="Recorded defects versus exhaustive claim",
                            recorded_at="2026-10-03T10:10:00-04:00")
    data["evidence"] = [
        {"id": "EV-OBSERVATION", "locator": "synthetic://inspection/log#L1",
         "sha256": hashlib.sha256(OBSERVATION.encode()).hexdigest(),
         "root_id": "SYNTHETIC-INSPECTION", "description": "Synthetic observation wording; hash covers UTF-8 text without newline"},
        {"id": "EV-SUMMARY", "locator": "synthetic://inspection/summary#L1",
         "sha256": hashlib.sha256(SUMMARY.encode()).hexdigest(),
         "root_id": "SYNTHETIC-INSPECTION", "description": "Derived wording shares a declared evidence root; not independent corroboration"},
    ]
    data["nodes"] = [
        {"id": "time", "aspect": "TIME", "value": {"start": "2026-10-03T10:00:00-04:00", "end": None,
         "basis": "Illustrative event time, distinct from recorded_at"}, "source_ids": ["EV-OBSERVATION"],
         "ontological_grade": "GRADE_2_BIVECTOR", "referent_id": "INSPECTION-001"},
        {"id": "observation", "aspect": "WORDS", "value": {"text": OBSERVATION, "scope": "RECORDED",
         "definition_id": "DEMO-DEFECT-v1"}, "source_ids": ["EV-OBSERVATION"],
         "ontological_grade": "GRADE_2_BIVECTOR", "referent_id": "INSPECTION-001"},
        {"id": "count", "aspect": "NUMBERS", "value": {"quantity": {"lower": "3", "upper": "3",
         "lower_inclusive": True, "upper_inclusive": True}, "unit": "count", "concept": "recorded_defects",
         "method": "synthetic inspection record"}, "source_ids": ["EV-OBSERVATION"],
         "ontological_grade": "GRADE_2_BIVECTOR", "referent_id": "INSPECTION-001"},
        {"id": "summary", "aspect": "WORDS", "value": {"text": SUMMARY, "scope": "EXHAUSTIVE",
         "definition_id": "DEMO-DEFECT-v1"}, "source_ids": ["EV-SUMMARY"],
         "ontological_grade": "GRADE_2_BIVECTOR", "referent_id": "INSPECTION-001"},
    ]
    for id_, source, target, relation, rationale in [
        ("time-context", "time", "observation", "ASPECT_OF", "Time locates this recorded inspection"),
        ("recorded-count", "count", "observation", "ASPECT_OF", "Count quantifies what the inspection recorded"),
        ("summary-derivation", "summary", "observation", "DERIVED_FROM", "Derived summary widens the observation's declared scope"),
    ]:
        data["folds"].append({"id": id_, "from_node": source, "to_node": target, "relation": relation,
            "rationale": rationale, "evidence_ids": ["EV-OBSERVATION"], "jit": unassessed_lenses()})
    jit = data["folds"][-1]["jit"]
    for entry in jit:
        entry["assessor"] = "DEMO-REVIEWER"
        entry["evidence_ids"] = ["EV-OBSERVATION", "EV-SUMMARY"]
    jit[0].update(state="CHALLENGED", rationale="The qualifier 'only' introduces an exhaustive claim absent from the observation.")
    jit[1].update(state="INDETERMINATE", rationale="The fixture supplies no complete inspection coverage or detection-sensitivity evidence.")
    jit[2].update(state="CHALLENGED", rationale="The broader wording can suggest closure the source did not establish.",
                  context={"evaluation": "Appears conclusive", "potency": "Sounds comprehensive",
                           "activity": "May discourage further review", "viewpoint": "Synthetic report reader, not an assessed person"})
    jit[3].update(state="SUPPORTED", rationale="Both inputs are representations of an inspection, not the whole physical situation.")
    data["cerpa_links"] = [{"stage": "REVIEW", "record_id": "REVIEW-DEMO-001", "locator": "synthetic://cerpa/review/001", "sha256": None}]
    data["artifact_links"] = [{"kind": "DLR", "record_id": "DLR-DEMO-001", "locator": "synthetic://memory/dlr/001", "sha256": None}]
    return FoldEpisode(data)
