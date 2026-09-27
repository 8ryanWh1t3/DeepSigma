from __future__ import annotations

import json
from typing import Iterable

from .models import SemanticPacket

NS = "https://deepsigma.example/vsa/"


def iri(local_id: str) -> str:
    return f"<{NS}{local_id}>"


def literal(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def to_rdf_triples(packet: SemanticPacket) -> list[tuple[str, str, str]]:
    triples: list[tuple[str, str, str]] = []
    p = iri(packet.packet_id)
    triples.extend(
        [
            (p, "rdf:type", "ds:SemanticPacket"),
            (p, "ds:sourceId", literal(packet.transcript.source_id)),
            (p, "ds:authorityStatus", literal(packet.governance.authority_status.value)),
        ]
    )

    for evidence in packet.evidence:
        e = iri(evidence.id)
        triples.extend(
            [
                (e, "rdf:type", "ds:Evidence"),
                (e, "ds:text", literal(evidence.text)),
                (e, "ds:sourceId", literal(evidence.provenance.source_id)),
                (e, "ds:confidence", literal(str(evidence.confidence.value))),
                (p, "ds:contains", e),
            ]
        )

    for claim in packet.claims:
        c = iri(claim.id)
        triples.extend(
            [
                (c, "rdf:type", "ds:Claim"),
                (c, "ds:text", literal(claim.text)),
                (c, "ds:modality", literal(claim.modality.value)),
                (c, "ds:confidence", literal(str(claim.confidence.value))),
                (c, "ds:authorityStatus", literal(claim.authority_status.value)),
                (p, "ds:contains", c),
            ]
        )
        for evidence_id in claim.evidence_ids:
            triples.append((c, "ds:supportedBy", iri(evidence_id)))

    for assumption in packet.assumptions:
        a = iri(assumption.id)
        triples.extend(
            [
                (a, "rdf:type", "ds:Assumption"),
                (a, "ds:text", literal(assumption.statement)),
                (a, "ds:confidence", literal(str(assumption.confidence.value))),
                (p, "ds:contains", a),
            ]
        )
        for evidence_id in assumption.evidence_ids:
            triples.append((a, "ds:supportedBy", iri(evidence_id)))

    for event in packet.events:
        ev = iri(event.id)
        triples.extend(
            [
                (ev, "rdf:type", "ds:Event"),
                (ev, "ds:eventType", literal(event.event_type)),
                (ev, "ds:description", literal(event.description)),
                (p, "ds:contains", ev),
            ]
        )

    for intent in packet.intents:
        i = iri(intent.id)
        triples.extend(
            [
                (i, "rdf:type", "ds:Intent"),
                (i, "ds:goal", literal(intent.goal)),
                (p, "ds:contains", i),
            ]
        )

    for entity in packet.entities:
        en = iri(entity.id)
        triples.extend(
            [
                (en, "rdf:type", "ds:Entity"),
                (en, "ds:name", literal(entity.name)),
                (en, "ds:entityType", literal(entity.entity_type)),
                (p, "ds:contains", en),
            ]
        )

    for rel in packet.relationships:
        triples.append((iri(rel.source_id), f"ds:{rel.predicate}", iri(rel.target_id)))

    return triples


def triples_to_turtle(triples: Iterable[tuple[str, str, str]]) -> str:
    header = (
        "@prefix ds: <https://deepsigma.example/vsa/schema#> .\n"
        "@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .\n\n"
    )
    return header + "\n".join(f"{s} {p} {o} ." for s, p, o in triples) + "\n"


def to_resonator_payload(packet: SemanticPacket) -> dict:
    return {
        "packet_id": packet.packet_id,
        "mode": "semantic_input",
        "authority_status": packet.governance.authority_status.value,
        "claims": [
            {
                "id": c.id,
                "text": c.text,
                "confidence": c.confidence.value,
                "modality": c.modality.value,
                "negated": c.negated,
                "evidence_ids": list(c.evidence_ids),
            }
            for c in packet.claims
        ],
        "assumptions": [
            {
                "id": a.id,
                "statement": a.statement,
                "confidence": a.confidence.value,
                "evidence_ids": list(a.evidence_ids),
            }
            for a in packet.assumptions
        ],
        "events": [
            {
                "id": e.id,
                "type": e.event_type,
                "description": e.description,
                "confidence": e.confidence.value,
                "evidence_ids": list(e.evidence_ids),
            }
            for e in packet.events
        ],
    }


def to_pathfinder_payload(packet: SemanticPacket) -> dict:
    nodes: list[dict] = []
    edges: list[dict] = []

    for obj_type, items in (
        ("Claim", packet.claims),
        ("Assumption", packet.assumptions),
        ("Event", packet.events),
        ("Intent", packet.intents),
        ("Entity", packet.entities),
        ("Evidence", packet.evidence),
    ):
        for item in items:
            label = getattr(item, "text", None) or getattr(item, "statement", None) or getattr(
                item, "description", None
            ) or getattr(item, "goal", None) or getattr(item, "name", None)
            nodes.append({"id": item.id, "type": obj_type, "label": label})

    for claim in packet.claims:
        for evidence_id in claim.evidence_ids:
            edges.append(
                {
                    "source": claim.id,
                    "predicate": "supportedBy",
                    "target": evidence_id,
                    "authority_status": claim.authority_status.value,
                }
            )
    for rel in packet.relationships:
        edges.append(
            {
                "source": rel.source_id,
                "predicate": rel.predicate,
                "target": rel.target_id,
                "confidence": rel.confidence.value,
                "authority_status": rel.authority_status.value,
            }
        )

    return {"packet_id": packet.packet_id, "nodes": nodes, "edges": edges}


def to_composer_candidates(packet: SemanticPacket) -> list[dict]:
    return [
        {
            "source": "VSA",
            "candidate_type": "clause",
            "semantic_object_id": claim.id,
            "text": claim.text,
            "modality": claim.modality.value,
            "confidence": claim.confidence.value,
            "evidence_ids": list(claim.evidence_ids),
            "authority_status": "candidate",
            "requires_human_review": True,
        }
        for claim in packet.claims
    ]


def to_cerpa_candidates(packet: SemanticPacket) -> list[dict]:
    return [
        {
            "cerpa_stage": "Claim",
            "claim_id": claim.id,
            "text": claim.text,
            "confidence": claim.confidence.value,
            "modality": claim.modality.value,
            "evidence_ids": list(claim.evidence_ids),
            "authority_status": claim.authority_status.value,
            "next": "Review",
        }
        for claim in packet.claims
    ]
