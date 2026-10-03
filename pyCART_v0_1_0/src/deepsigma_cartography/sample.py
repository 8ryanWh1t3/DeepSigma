"""Explicitly invoked synthetic administrative-review example; no real asset data."""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any

from .adapters import cerpa_review, patch_proposals, vinculum_projection
from .assessment import assess
from .atlas import Atlas
from .editions import EditionStore, compare
from .exports import export_csv, export_jsonl, export_jsonld, export_ntriples, write_json
from .folding import fold
from .models import Edge, Evidence, Node, Status
from .navigation import impact, trace
from .util import ValidationError

AS_OF = "2026-10-03T12:00:00Z"


def sample_atlas() -> Atlas:
    """A synthetic evidence-refresh scenario; none of its labels are operational facts."""
    evidence = (
        Evidence("ev:scenario", "synthetic://cartography/example", "Explicit synthetic scenario authored for tests"),
        Evidence("ev:report", "synthetic://cartography/review-report", "Synthetic review report, section 2",
                 valid_from="2026-09-01T00:00:00Z", valid_to="2026-10-02T00:00:00Z"),
    )
    nodes = (
        Node("mission:readiness", "Prepare a readiness review", "mission", layer="mission"),
        Node("capability:intake", "Evidence intake process", "capability", layer="operations"),
        Node("claim:current", "The assessment has current evidence", "claim", layer="meaning"),
        Node("evidence:report", "Recorded review report", "evidence", layer="evidence", evidence_ids=("ev:report",)),
        Node("assumption:standard", "Review standard remains applicable", "assumption", layer="meaning",
             evidence_ids=("ev:scenario",), review_due="2026-10-01T00:00:00Z"),
        Node("policy:review", "Review procedure", "policy", layer="policy"),
        Node("authority:reviewer", "Designated review role", "authority", layer="authority"),
        Node("decision:publish", "Proposed assessment publication", "decision", layer="decisions", evidence_ids=("ev:scenario",)),
        Node("event:review", "Review window opened", "event", layer="events", status=Status.OBSERVED, evidence_ids=("ev:scenario",)),
        Node("claim:unknown", "Additional source coverage is unknown", "claim", layer="meaning", status=Status.UNKNOWN),
    )
    edges = (
        Edge("edge:01", "mission:readiness", "requires", "capability:intake", evidence_ids=("ev:scenario",)),
        Edge("edge:02", "capability:intake", "depends_on", "claim:current", evidence_ids=("ev:scenario",)),
        Edge("edge:03", "claim:current", "supported_by", "evidence:report", evidence_ids=("ev:report",)),
        Edge("edge:04", "claim:current", "depends_on", "assumption:standard", evidence_ids=("ev:scenario",)),
        Edge("edge:05", "decision:publish", "depends_on", "claim:current", evidence_ids=("ev:scenario",)),
        Edge("edge:06", "decision:publish", "implements", "policy:review", evidence_ids=("ev:scenario",)),
        Edge("edge:07", "policy:review", "authorized_by", "authority:reviewer", evidence_ids=("ev:scenario",)),
        Edge("edge:08", "event:review", "relates_to", "decision:publish", evidence_ids=("ev:scenario",)),
    )
    return Atlas("atlas:synthetic-review", "Synthetic administrative review | DEEP SIGMA CARTOGRAPHY",
                 nodes, edges, evidence, attributes={"synthetic": True, "purpose": "demonstration only", "episode_id": "episode:synthetic-review"})


def sample_candidate(baseline: Atlas) -> Atlas:
    """Build a proposed revision locally, not an authorized operational change."""
    evidence = tuple(replace(e, valid_to="2026-11-01T00:00:00Z") if e.id == "ev:report" else e for e in baseline.evidence)
    nodes = tuple(replace(n, review_due="2026-11-01T00:00:00Z") if n.id == "assumption:standard" else n for n in baseline.nodes)
    edge = Edge("edge:09", "decision:publish", "authorized_by", "authority:reviewer", evidence_ids=("ev:scenario",))
    return replace(baseline, nodes=nodes, evidence=evidence, edges=baseline.edges + (edge,),
                   attributes={**baseline.attributes, "revision_status": "PROPOSED_NOT_AUTHORIZED"})


def run_demo(directory: str | Path, *, xlsx: bool = False) -> dict[str, Any]:
    output = Path(directory)
    if output.exists() and any(output.iterdir()):
        raise ValidationError("Demo output directory must be new or empty; existing artifacts are not overwritten")
    output.mkdir(parents=True, exist_ok=True)
    baseline = sample_atlas()
    candidate = sample_candidate(baseline)
    view = baseline.view(as_of=AS_OF)
    report = assess(view)
    baseline.save(output / "baseline.json")
    candidate.save(output / "candidate.json")
    write_json(report, output / "assessment.json")
    route = trace(view, "mission:readiness", "evidence:report")
    write_json(route, output / "route.json")
    write_json(impact(view, "evidence:report"), output / "impact.json")
    write_json(fold(view, by="layer"), output / "folded.json")
    write_json(compare(baseline, candidate), output / "diff.json")
    write_json(vinculum_projection(view, report), output / "vinculum_projection.json")
    review = cerpa_review(view, report, claim_id="claim:current", event_id="event:review", domain="synthetic-review")
    write_json(review, output / "cerpa_review_draft.json")
    write_json(patch_proposals(report, review_id=review["id"], domain="synthetic-review"), output / "cerpa_patch_drafts.json")
    export_jsonl(baseline, output / "atlas.jsonl")
    export_csv(baseline, output / "csv")
    export_jsonld(view, output / "atlas.jsonld")
    export_ntriples(view, output / "atlas.nt")
    with EditionStore.create(output / "editions.sqlite3", atlas_id=baseline.id) as store:
        first = store.append(baseline, recorded_at=AS_OF, expected_parent=None)
        second = store.append(candidate, recorded_at="2026-10-03T12:01:00Z", expected_parent=first.edition_hash)
        head = store.verify(expected_head=second.edition_hash)
    if xlsx:
        from .workbook import export_workbook
        export_workbook(view, output / "cartography.xlsx", report)
    result = {"synthetic": True, "nodes": len(baseline.nodes), "edges": len(baseline.edges),
              "findings": len(report.findings), "route_hops": len(route.steps),
              "candidate_findings": len(assess(candidate.view(as_of=AS_OF)).findings),
              "editions": 2, "head_sha256": head, "authority": "not_evaluated", "output": str(output)}
    write_json(result, output / "demo_result.json")
    return result
