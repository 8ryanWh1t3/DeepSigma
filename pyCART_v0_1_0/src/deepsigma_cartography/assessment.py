"""Bounded RESONATOR-oriented structural checks. No natural-language truth inference."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from .atlas import MapView
from .models import CoverageRequirement, Status, active
from .navigation import dependency_cycles
from .util import Record, ValidationError, digest, freeze, instant, strings


@dataclass(frozen=True)
class Finding(Record):
    id: str
    code: str
    severity: str
    subject_ids: tuple[str, ...]
    detail: str
    recommendation: str


@dataclass(frozen=True)
class Assessment(Record):
    view_fingerprint: str
    as_of: str
    findings: tuple[Finding, ...]
    metrics: Mapping[str, Any] = field(default_factory=dict)
    rule_set: str = "cartography.structural/1"
    interpretation: str = "Checks cover this recorded map only; no truth, compliance, or operational-readiness certification."

    def __post_init__(self) -> None:
        object.__setattr__(self, "metrics", freeze(self.metrics))

    @property
    def fingerprint(self) -> str:
        return digest(self)


def assess(view: MapView, *, requirements: tuple[CoverageRequirement, ...] = (),
           evidence_required_kinds: tuple[str, ...] = ("claim", "assumption", "decision"),
           authority_required_kinds: tuple[str, ...] = ("decision", "patch", "apply")) -> Assessment:
    """Find recorded gaps. A missing link is not proof of missing real-world authority."""
    if not isinstance(view, MapView):
        raise ValidationError("Assessment requires a MapView")
    if not isinstance(requirements, (list, tuple)) or not all(isinstance(r, CoverageRequirement) for r in requirements):
        raise ValidationError("requirements must contain CoverageRequirement records")
    evidence_required_kinds = strings(evidence_required_kinds, "evidence_required_kinds")
    authority_required_kinds = strings(authority_required_kinds, "authority_required_kinds")
    findings: list[Finding] = []
    outgoing: dict[str, list] = {n.id: [] for n in view.nodes}
    incident: dict[str, list] = {n.id: [] for n in view.nodes}
    for edge in view.edges:
        outgoing[edge.source].append(edge)
        incident[edge.source].append(edge)
        incident[edge.target].append(edge)
    fp = view.fingerprint

    def add(code: str, ids: tuple[str, ...], detail: str, recommendation: str,
            severity: str = "warning") -> None:
        ids = tuple(sorted(ids))
        fid = "finding:" + digest([fp, code, ids, detail])[:24]
        findings.append(Finding(fid, code, severity, ids, detail, recommendation))

    eligible = {Status.OBSERVED, Status.ASSERTED}
    evidence_needed = evidence_linked = authority_needed = authority_linked = 0
    for node in view.nodes:
        if node.kind in evidence_required_kinds:
            evidence_needed += 1
            refs = set(node.evidence_ids)
            # One-hop declared evidence relationships only. A support chain is not proof.
            for edge in incident[node.id]:
                predicate = view.atlas._predicates[edge.predicate]
                is_supported = ((predicate.dependency == "forward" and edge.source == node.id) or
                                (predicate.dependency == "reverse" and edge.target == node.id))
                if predicate.evidence_relation and is_supported and edge.status in eligible:
                    refs.update(edge.evidence_ids)
                    other = edge.target if edge.source == node.id else edge.source
                    supporter = view.node(other)
                    if supporter.status in eligible:
                        refs.update(supporter.evidence_ids)
            live = {eid for eid in refs if active(view.atlas._evidence[eid], view.as_of)}
            if live:
                evidence_linked += 1
            else:
                add("EVIDENCE_GAP", (node.id,), "No currently valid recorded evidence reference in the defined one-hop scope.",
                    "Attach or refresh source-located evidence; do not infer that the claim is false.")
        if node.kind in authority_required_kinds:
            authority_needed += 1
            references = [e for e in outgoing[node.id] if e.predicate == "authorized_by" and
                          e.status in eligible and view.node(e.target).status in eligible]
            if references:
                authority_linked += 1
            else:
                add("AUTHORITY_GAP", (node.id,), "No active asserted/observed authority reference in this map.",
                    "Resolve the governing authority with the host authority service; this module cannot grant it.")
        if node.review_due and instant(node.review_due) <= instant(view.as_of):
            add("TEMPORAL_GAP", (node.id,), f"Review is due at {node.review_due}.",
                "Review the recorded assumption or claim against current evidence.")
        if not incident[node.id]:
            add("SEMANTIC_ORPHAN", (node.id,), "Node has no incident relationship in this view.",
                "Confirm whether isolation is intended or a mapping gap.", "info")
        if node.status in (Status.INFERRED, Status.UNKNOWN):
            add("UNCERTAINTY", (node.id,), f"Node is explicitly {node.status.value}; confidence is not silently supplied.",
                "Preserve this status until evidence and human review justify a change.", "info")
    for edge in view.edges:
        if edge.predicate in ("contradicts", "claim_contradicts"):
            add("CONTRADICTION_RECORDED", (edge.source, edge.target, edge.id),
                f"A {edge.status.value} contradiction relationship is recorded.",
                "Review both representations in context; this check did not infer their logical inconsistency.")
        if not edge.evidence_ids:
            add("PROVENANCE_GAP", (edge.id,), "The relationship has no direct evidence reference.",
                "Record the provenance of this relationship, not only of its endpoints.", "info")
        if edge.status in (Status.UNKNOWN, Status.INFERRED):
            add("UNCERTAINTY", (edge.id,), f"Relationship is explicitly {edge.status.value}.",
                "Treat this as declared uncertainty rather than an established dependency.", "info")
    for cycle in dependency_cycles(view):
        add("DEPENDENCY_CYCLE", cycle, "A strongly connected component exists among declared dependencies.",
            "Check for circular support or an intentional feedback loop; a cycle alone is not invalidity.")
    covered = 0
    for req in requirements:
        view.node(req.subject_id)
        if req.predicate not in view.atlas._predicates:
            raise ValidationError(f"Unknown required predicate: {req.predicate}")
        targets = {e.target for e in outgoing[req.subject_id] if e.predicate == req.predicate and
                   e.status in eligible and view.node(e.target).status in eligible and
                   (req.target_kind is None or view.node(e.target).kind == req.target_kind)}
        if len(targets) >= req.minimum:
            covered += 1
        else:
            add("COVERAGE_GAP", (req.subject_id,),
                f"Expected at least {req.minimum} distinct {req.predicate} target(s) of kind {req.target_kind or '*'}; recorded {len(targets)}.",
                "Investigate the explicitly declared mapping requirement.")
    metrics = {
        "node_count": len(view.nodes), "edge_count": len(view.edges),
        "evidence_required_nodes": evidence_needed, "nodes_with_live_evidence_reference": evidence_linked,
        "recorded_evidence_coverage": evidence_linked / evidence_needed if evidence_needed else None,
        "authority_required_nodes": authority_needed, "nodes_with_authority_reference": authority_linked,
        "recorded_authority_reference_coverage": authority_linked / authority_needed if authority_needed else None,
        "requirements_evaluated": len(requirements), "requirements_satisfied": covered,
        "requirement_coverage": covered / len(requirements) if requirements else None,
        "finding_count": len(findings),
    }
    return Assessment(fp, view.as_of, tuple(sorted(findings, key=lambda f: (f.code, f.subject_ids, f.id))), metrics)
