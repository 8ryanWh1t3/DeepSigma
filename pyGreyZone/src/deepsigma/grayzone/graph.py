"""Portable graph projections; RDF triples assert only recorded relationships."""

from __future__ import annotations

import json
from urllib.parse import quote

from .schema import Assessment


def graph_json(assessment: Assessment) -> dict[str, object]:
    nodes = ([{"id": e.id, "type": "event", "kind": e.kind} for e in assessment.events]
             + [{"id": h.id, "type": "hypothesis", "status": h.status} for h in assessment.hypotheses])
    edges = ([{"source": x.left, "target": x.right, "type": "related_observation",
               "score": x.score, "reasons": list(x.reasons)} for x in assessment.links]
             + [{"source": h.id, "target": eid, "type": "supported_by"}
                for h in assessment.hypotheses for eid in h.event_ids])
    records: dict[str, dict[str, str]] = {}
    for event in assessment.events:
        for source in event.sources:
            record_node = "record:" + source.source_id + ":" + source.record_id
            records[record_node] = {"id": record_node, "type": "source_record",
                                    "sha256": source.sha256, "lineage_group": source.independent_group,
                                    "locator": source.locator}
            edges.append({"source": event.id, "target": record_node, "type": "derived_from"})
    nodes += [records[key] for key in sorted(records)]
    return {"nodes": nodes, "edges": edges}


def _uri(kind: str, identifier: str) -> str:
    return f"<urn:deepsigma:grayzone:{kind}:{quote(identifier, safe='')}>"


def ntriples(assessment: Assessment) -> str:
    """Small N-Triples export that can be mapped to local RDF/SKOS ontologies."""
    predicate = "<urn:deepsigma:grayzone:predicate:"
    lines: list[str] = []
    for event in assessment.events:
        subject = _uri("event", event.id)
        lines.append(f'{subject} {predicate}kind> {json.dumps(event.kind, ensure_ascii=False)} .')
        for source in event.sources:
            record = _uri("record", source.source_id + ":" + source.record_id)
            lines.append(f'{subject} {predicate}record> {record} .')
            lines.append(f'{record} {predicate}sha256> "{source.sha256}" .')
    for hypothesis in assessment.hypotheses:
        subject = _uri("hypothesis", hypothesis.id)
        for event_id in hypothesis.event_ids:
            lines.append(f'{subject} {predicate}supportedBy> {_uri("event", event_id)} .')
    return "\n".join(lines) + ("\n" if lines else "")
