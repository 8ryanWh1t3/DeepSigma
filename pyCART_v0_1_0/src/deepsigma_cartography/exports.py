"""Offline JSON, JSONL, CSV, and RDF statement projections. No graphic renderer."""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any
from urllib.parse import quote

from .assessment import Assessment
from .atlas import Atlas, MapView
from .util import ValidationError, canonical_json, parse_json

BASE = "urn:deep-sigma:cartography:"
RDF = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
RDFS = "http://www.w3.org/2000/01/rdf-schema#"
XSD = "http://www.w3.org/2001/XMLSchema#"


def write_json(value: Any, path: str | Path) -> Path:
    path = Path(path)
    path.write_text(canonical_json(value) + "\n", encoding="utf-8")
    return path


def export_jsonl(atlas: Atlas, path: str | Path) -> Path:
    metadata = {k: v for k, v in atlas.to_dict().items() if k not in ("nodes", "edges", "evidence", "predicates")}
    records = [{"record_type": "atlas", "payload": metadata}]
    for name in ("nodes", "edges", "evidence", "predicates"):
        records.extend({"record_type": name, "payload": row.to_dict()} for row in getattr(atlas, name))
    path = Path(path)
    path.write_text("".join(canonical_json(row) + "\n" for row in records), encoding="utf-8")
    return path


def import_jsonl(path: str | Path) -> Atlas:
    metadata = None
    records: dict[str, list] = {name: [] for name in ("nodes", "edges", "evidence", "predicates")}
    with Path(path).open(encoding="utf-8") as stream:
        for line_no, line in enumerate(stream, 1):
            if not line.strip():
                continue
            row = parse_json(line)
            if not isinstance(row, dict) or set(row) != {"record_type", "payload"}:
                raise ValidationError(f"Invalid JSONL envelope at line {line_no}")
            kind = row["record_type"]
            if kind == "atlas":
                if metadata is not None:
                    raise ValidationError("Duplicate atlas header")
                metadata = row["payload"]
            elif kind in records:
                records[kind].append(row["payload"])
            else:
                raise ValidationError(f"Unknown JSONL record type at line {line_no}")
    if not isinstance(metadata, dict) or set(metadata) & records.keys():
        raise ValidationError("Missing or invalid atlas header")
    return Atlas.from_dict({**metadata, **records})


def spreadsheet_text(value: Any) -> Any:
    """Neutralize formula-leading literal text. Canonical JSON keeps original bytes."""
    if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@")):
        return "'" + value
    return value


def export_csv(atlas: Atlas, directory: str | Path) -> Path:
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    for name, fields in (
        ("nodes", ("id", "label", "kind", "layer", "scope", "status", "confidence", "evidence_ids", "valid_from", "valid_to", "review_due", "attributes")),
        ("edges", ("id", "source", "predicate", "target", "status", "confidence", "evidence_ids", "valid_from", "valid_to", "attributes")),
        ("evidence", ("id", "source", "locator", "sha256", "valid_from", "valid_to", "attributes")),
        ("predicates", ("id", "label", "description", "dependency", "source_kinds", "target_kinds", "evidence_relation")),
    ):
        with (directory / f"{name}.csv").open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            for record in getattr(atlas, name):
                row = record.to_dict()
                writer.writerow({k: spreadsheet_text(canonical_json(v) if isinstance(v, (dict, list)) else v)
                                 for k, v in row.items()})
    write_json({"atlas_id": atlas.id, "atlas_fingerprint": atlas.fingerprint,
                "notice": "CSV is a spreadsheet-safe projection. Formula-leading strings have an apostrophe prefix. atlas.json is lossless."},
               directory / "manifest.json")
    atlas.save(directory / "atlas.json")
    return directory


def _iri(kind: str, value: str) -> str:
    return BASE + kind + ":" + quote(value, safe="")


def jsonld_document(view: MapView) -> dict[str, Any]:
    """Reify relationships: assertions/inferences do NOT become bare factual triples."""
    graph: list[dict[str, Any]] = []
    for node in view.nodes:
        row = {"@id": _iri("node", node.id), "@type": "c:Node", "c:id": node.id,
               "rdfs:label": node.label, "c:kind": node.kind, "c:layer": node.layer,
               "c:scope": node.scope, "c:status": node.status.value,
               "c:recordJSON": canonical_json(node)}
        if node.confidence is not None:
            row["c:confidence"] = node.confidence
        graph.append(row)
    for edge in view.edges:
        graph.append({"@id": _iri("edge", edge.id), "@type": "rdf:Statement", "c:id": edge.id,
                      "rdf:subject": {"@id": _iri("node", edge.source)},
                      "rdf:predicate": {"@id": _iri("predicate", edge.predicate)},
                      "rdf:object": {"@id": _iri("node", edge.target)},
                      "c:status": edge.status.value, "c:recordJSON": canonical_json(edge)})
    for evidence in view.atlas.evidence:
        graph.append({"@id": _iri("evidence", evidence.id), "@type": "c:Evidence", "c:id": evidence.id,
                      "c:source": evidence.source, "c:recordJSON": canonical_json(evidence)})
    for predicate in view.atlas.predicates:
        graph.append({"@id": _iri("predicate", predicate.id), "@type": "c:Predicate", "c:id": predicate.id,
                      "rdfs:label": predicate.label, "c:definition": predicate.description,
                      "c:dependency": predicate.dependency, "c:recordJSON": canonical_json(predicate)})
    graph.append({"@id": _iri("view", view.fingerprint), "@type": "c:MapView",
                  "c:asOf": {"@value": view.as_of, "@type": "xsd:dateTime"},
                  "c:authority": "not_evaluated", "c:viewJSON": canonical_json(view)})
    return {"@context": {"c": BASE, "rdf": RDF, "rdfs": RDFS, "xsd": XSD}, "@graph": graph}


def export_jsonld(view: MapView, path: str | Path) -> Path:
    return write_json(jsonld_document(view), path)


def export_ntriples(view: MapView, path: str | Path) -> Path:
    """Export the same reified graph without a runtime RDF-library dependency."""
    document = jsonld_document(view)
    context = document["@context"]

    def expand(value: str) -> str:
        prefix, sep, tail = value.partition(":")
        return context[prefix] + tail if sep and prefix in context else value

    def literal(value: Any) -> str:
        if isinstance(value, dict):
            return json.dumps(value["@value"], ensure_ascii=False) + "^^<" + expand(value["@type"]) + ">"
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return json.dumps(str(value)) + "^^<" + XSD + "double>"
        return json.dumps(value, ensure_ascii=False)

    triples = []
    for row in document["@graph"]:
        subject = "<" + row["@id"] + ">"
        for key, value in row.items():
            if key == "@id":
                continue
            predicate = RDF + "type" if key == "@type" else expand(key)
            if key == "@type":
                obj = "<" + expand(value) + ">"
            elif isinstance(value, dict) and "@id" in value:
                obj = "<" + value["@id"] + ">"
            else:
                obj = literal(value)
            triples.append(f"{subject} <{predicate}> {obj} .")
    path = Path(path)
    path.write_text("\n".join(sorted(triples)) + "\n", encoding="utf-8")
    return path


def export_assessment(assessment: Assessment, path: str | Path) -> Path:
    return write_json(assessment, path)
