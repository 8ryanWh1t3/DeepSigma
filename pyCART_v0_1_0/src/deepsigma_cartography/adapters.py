"""Explicit integration boundaries. No vendor connection or autonomous APPLY."""
from __future__ import annotations

from collections import Counter
from typing import Any, Mapping

from .assessment import Assessment
from .atlas import Atlas, MapView
from .models import DEFAULT_PREDICATES, Edge, Evidence, Node, Predicate
from .util import ValidationError, canonical_json, digest, file_sha256, parse_json, text


def from_memory_graph(source: Any, *, atlas_id: str, title: str) -> Atlas:
    """Read the inspected DeepSigma 2.1.2 MemoryGraph.to_json() format.

    Also accepts its decoded mapping or JSON text. Unknown relation kinds are
    preserved in the legend with NO dependency semantics, never guessed.
    Original properties/timestamps remain in source_record; no confidence rescaling.
    """
    if hasattr(source, "to_json"):
        source = source.to_json()
    if isinstance(source, str):
        source = parse_json(source)
    if not isinstance(source, Mapping) or set(source) != {"nodes", "edges"}:
        raise ValidationError("Expected the MemoryGraph nodes/edges export")
    if not isinstance(source["nodes"], (list, tuple)) or not isinstance(source["edges"], (list, tuple)):
        raise ValidationError("MemoryGraph nodes and edges must be arrays")
    nodes, edges, evidence = [], [], []
    definitions = {p.id: p for p in DEFAULT_PREDICATES}
    declared = {
        "claim_depends_on": ("forward", False), "claim_supports": ("reverse", True),
        "claim_evidence": ("forward", True), "claim_source": ("forward", True),
        "claim_contradicts": ("none", False), "claim_supersedes": ("none", False),
    }
    counts: Counter = Counter()
    try:
        for row in source["nodes"]:
            ref_ids = ()
            if row["kind"] == "evidence" and row.get("label"):
                ref_id = "source-ref:" + digest(row["node_id"])[:24]
                evidence.append(Evidence(ref_id, row["label"], attributes={"adapter": "MemoryGraph", "source_node_id": row["node_id"], "verification": "not_performed"}))
                ref_ids = (ref_id,)
            nodes.append(Node(row["node_id"], row.get("label") or row["node_id"], row["kind"],
                              layer="memory", evidence_ids=ref_ids, attributes={"source_record": row}))
        for row in sorted(source["edges"], key=canonical_json):
            kind = row["kind"]
            if kind not in definitions:
                orientation, is_evidence = declared.get(kind, ("none", False))
                definitions[kind] = Predicate(kind, kind, "Preserved MemoryGraph relation. Only explicitly mapped dependency semantics apply.",
                                              orientation, evidence_relation=is_evidence)
            key = digest(row)
            counts[key] += 1
            edges.append(Edge(f"mg-edge:{key[:24]}:{counts[key]}", row["source_id"], kind, row["target_id"],
                              attributes={"source_record": row}))
    except (TypeError, KeyError) as exc:
        raise ValidationError(f"Invalid MemoryGraph record: {exc}") from exc
    return Atlas(atlas_id, title, tuple(nodes), tuple(edges), tuple(evidence), tuple(definitions.values()),
                 {"adapter": "DeepSigma MemoryGraph 2.1.2 snapshot contract", "source_digest": digest(source),
                  "authority_verification": "not_performed"})


def verify_evidence_file(evidence: Evidence, path: str) -> dict[str, Any]:
    """Check an explicit local file. Never fetch a URL or treat a digest as truth."""
    if evidence.sha256 is None:
        raise ValidationError("Evidence has no pinned SHA-256; verification cannot be claimed")
    observed = file_sha256(path)
    return {"evidence_id": evidence.id, "expected_sha256": evidence.sha256,
            "actual_sha256": observed, "matches": observed == evidence.sha256,
            "interpretation": "Byte identity only; factual validity and authority were not evaluated."}


def _bound(view: MapView, assessment: Assessment) -> None:
    if assessment.view_fingerprint != view.fingerprint or assessment.as_of != view.as_of:
        raise ValidationError("Assessment belongs to a different map view")


def vinculum_projection(view: MapView, assessment: Assessment | None = None) -> dict[str, Any]:
    """Proposed read-only interchange contract, NOT an installed VINCULUM plug-in."""
    if assessment is not None:
        _bound(view, assessment)
    return {"schema": "deepsigma.cartography.vinculum-projection/1", "read_only": True,
            "authority": "not_evaluated", "view_fingerprint": view.fingerprint,
            "map": view.to_dict(), "assessment": assessment.to_dict() if assessment else None,
            "integration_status": "interchange_contract_only"}


def cerpa_review(view: MapView, assessment: Assessment, *, claim_id: str, event_id: str,
                 domain: str) -> dict[str, Any]:
    """Draft compatible with the inspected core.cerpa.models.Review constructor.

    Finding a gap in one map does not establish temporal drift or adjudicate truth.
    The returned draft deliberately says drift_detected=False with an explicit
    not_evaluated qualifier. Host review/authority workflow must decide disposition.
    """
    _bound(view, assessment)
    text(domain, "domain")
    if view.node(claim_id).kind != "claim" or view.node(event_id).kind != "event":
        raise ValidationError("claim_id/event_id must identify a claim and an event")
    rid = "review:" + digest([assessment.fingerprint, claim_id, event_id, domain])[:24]
    related = sorted({s for f in assessment.findings for s in f.subject_ids})
    return {"id": rid, "claim_id": claim_id, "event_id": event_id, "domain": domain,
            "timestamp": view.as_of, "verdict": "STRUCTURAL_REVIEW_DRAFT",
            "rationale": f"{len(assessment.findings)} structural finding(s) across the recorded view; human evaluation required.",
            "drift_detected": False, "source": "deepsigma-cartography",
            "provenance": [{"view_sha256": view.fingerprint, "assessment_sha256": assessment.fingerprint}],
            "related_ids": related,
            "metadata": {"status": "PROPOSED", "scope": "entire_map_view", "drift_status": "not_evaluated",
                         "authority": "not_evaluated", "findings": [f.to_dict() for f in assessment.findings]}}


def patch_proposals(assessment: Assessment, *, review_id: str, domain: str) -> tuple[dict[str, Any], ...]:
    """Draft core.cerpa.models.Patch-shaped requests. Never mutates an atlas."""
    text(review_id, "review_id")
    text(domain, "domain")
    return tuple({"id": "patch:" + digest([review_id, domain, f.id])[:24], "review_id": review_id,
                  "domain": domain, "timestamp": assessment.as_of, "action": "request_review",
                  "target": f.subject_ids[0], "description": f.recommendation,
                  "source": "deepsigma-cartography", "related_ids": list(f.subject_ids),
                  "metadata": {"status": "PROPOSED", "finding_id": f.id, "authority": "not_evaluated",
                               "base_view_sha256": assessment.view_fingerprint}}
                 for f in assessment.findings)
