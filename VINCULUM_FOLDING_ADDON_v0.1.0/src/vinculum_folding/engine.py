"""Non-scoring checks and read-only UI projections. No general NLP is implied."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from .adapter import host_pair_results
from .model import BOUNDARY, LENS_LABELS, VERSION, FoldEpisode, FoldError, timestamp


@dataclass(frozen=True)
class Finding:
    code: str
    target_id: str
    message: str
    basis: str


@dataclass(frozen=True)
class Audit:
    episode_id: str
    revision: int
    episode_digest: str
    findings: tuple[Finding, ...]
    aspect_counts: tuple[tuple[str, int], ...]
    lens_counts: tuple[tuple[str, int, int], ...]
    declared_evidence_roots: tuple[str, ...]
    unknown_evidence_roots: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {"schema": "vinculum.folding.audit/1", "addon_version": VERSION,
                "episode_id": self.episode_id, "revision": self.revision,
                "episode_digest": self.episode_digest,
                "findings": [asdict(f) for f in self.findings],
                "aspect_counts": [list(x) for x in self.aspect_counts],
                "lens_counts": [list(x) for x in self.lens_counts],
                "declared_evidence_roots": list(self.declared_evidence_roots),
                "unknown_evidence_roots": list(self.unknown_evidence_roots),
                "boundary": BOUNDARY,
                "density_note": "Root IDs are caller-declared grouping labels, not proof of independent exposure.",
                "automatic_actions": 0}


def audit(episode: FoldEpisode) -> Audit:
    data = episode.to_dict()
    nodes = {n["id"]: n for n in data["nodes"]}
    evidence = {e["id"]: e for e in data["evidence"]}
    findings: list[Finding] = []

    def add(code, target, message, basis):
        findings.append(Finding(code, target, message, basis))

    for ev in data["evidence"]:
        if ev["locator"] is None:
            add("SOURCE_LOCATOR_MISSING", ev["id"], "Original evidence location is not supplied.", "registered metadata")
        if ev["sha256"] is None:
            add("SOURCE_HASH_UNPINNED", ev["id"], "No source-content hash is recorded; source bytes were not checked by this add-on.", "registered metadata")
    for node in data["nodes"]:
        if not node["source_ids"]:
            add("EVIDENCE_MISSING", node["id"], "Aspect has no linked source evidence.", "explicit source references")
        if node["ontological_grade"] == "UNSPECIFIED":
            add("ONTOLOGY_UNSPECIFIED", node["id"], "Grade-1/Grade-2 classification has not been attributed.", "declared JIT category")
        value = node["value"]
        if node["aspect"] == "TIME" and value["start"] is None:
            add("TIME_UNSPECIFIED", node["id"], "Event/scope time remains unknown.", "explicit time value")
        if node["aspect"] == "NUMBERS":
            if value["quantity"] is None:
                add("QUANTITY_UNKNOWN", node["id"], "Unknown quantity is not zero.", "explicit numeric value")
            if value["unit"] is None:
                add("UNIT_UNSPECIFIED", node["id"], "Measurement unit is not stated.", "explicit numeric metadata")
    for fold in data["folds"]:
        for assessment in fold["jit"]:
            state, lens = assessment["state"], assessment["lens"]
            if state == "UNASSESSED":
                add("JIT_UNASSESSED", fold["id"], LENS_LABELS[lens] + " has not been assessed.", lens)
            elif state in {"SUPPORTED", "CHALLENGED"}:
                incomplete = [sid for sid in assessment["evidence_ids"] if evidence[sid]["locator"] is None]
                if incomplete:
                    add("JIT_EVIDENCE_UNLOCATED", fold["id"], "Assessment cites sources without locators: " + ", ".join(incomplete), lens)
        a, b = nodes[fold["from_node"]], nodes[fold["to_node"]]
        if fold["relation"] == "DERIVED_FROM" and a["aspect"] == b["aspect"] == "WORDS":
            if a["value"]["scope"] == "EXHAUSTIVE" and b["value"]["scope"] == "RECORDED":
                add("SCOPE_EXPANSION_REVIEW", fold["id"],
                    "An exhaustive claim is derived from a recorded observation. Additional coverage evidence is required; this is not proof the claim is false.",
                    "explicit RECORDED → EXHAUSTIVE scope annotations; no free-text inference")
        if fold["relation"] == "PRECEDES":
            if a["aspect"] != "TIME" or b["aspect"] != "TIME":
                add("TEMPORAL_TYPE_UNRESOLVED", fold["id"], "PRECEDES requires two explicit TIME aspects.", "declared temporal relation")
            elif a["value"]["start"] is None or b["value"]["start"] is None:
                add("TEMPORAL_ORDER_UNRESOLVED", fold["id"], "A time endpoint is missing.", "declared temporal relation")
            else:
                aa = timestamp(a["value"]["start"])
                ab = timestamp(a["value"]["end"] or a["value"]["start"])
                ba = timestamp(b["value"]["start"])
                bb = timestamp(b["value"]["end"] or b["value"]["start"])
                if aa >= bb:
                    add("TEMPORAL_ORDER_CONFLICT", fold["id"], "Strictly-before relation conflicts with the declared intervals.", "explicit timestamp comparison")
                elif ab >= ba:
                    add("TEMPORAL_ORDER_UNRESOLVED", fold["id"], "Overlapping/touching intervals do not establish strict precedence.", "explicit timestamp comparison")
    aspect_counts = tuple((a, sum(n["aspect"] == a for n in nodes.values())) for a in ("TIME", "WORDS", "NUMBERS"))
    for name, count in aspect_counts:
        if count == 0:
            add("ASPECT_ABSENT", data["episode_id"], f"No {name} aspect is recorded. No value was invented.", "aspect inventory")
    roots = tuple(sorted({e["root_id"] for e in evidence.values() if e["root_id"] is not None}))
    unknown = tuple(sorted(e["id"] for e in evidence.values() if e["root_id"] is None))
    lens_counts = tuple((lens, sum(a["lens"] == lens and a["state"] != "UNASSESSED"
                                 for f in data["folds"] for a in f["jit"]), len(data["folds"])) for lens in LENS_LABELS)
    return Audit(data["episode_id"], data["revision"], episode.digest,
                 tuple(sorted(findings, key=lambda x: (x.target_id, x.code, x.basis))),
                 aspect_counts, lens_counts, roots, unknown)


def project(episode: FoldEpisode) -> dict[str, Any]:
    """A view-model for the single-canvas inspector, not the canvas implementation."""
    data = episode.to_dict()
    return {"schema": "vinculum.folding.view/1", "addon_version": VERSION,
            "episode_id": data["episode_id"], "revision": data["revision"],
            "mission_id": data["mission_id"], "title": data["title"],
            "episode_digest": episode.digest, "workspace": "VINCULUM",
            "read_only": True, "nodes": data["nodes"], "folds": data["folds"],
            "external_links": data["external_links"], "evidence": data["evidence"],
            "lenses": [{"id": k, "label": v} for k, v in LENS_LABELS.items()],
            "host_pair_results": host_pair_results(episode),
            "audit": audit(episode).to_dict(),
            "cerpa_links": data["cerpa_links"], "artifact_links": data["artifact_links"],
            "studio_boundary": "Draft preparation belongs to Studio/host; this view grants no write or APPLY authority.",
            "boundary": BOUNDARY}


def unfold(episode: FoldEpisode, fold_id: str) -> dict[str, Any]:
    """Recover both aspect values, their source references, JIT and exact host result."""
    data = episode.to_dict()
    fold = next((f for f in data["folds"] if f["id"] == fold_id), None)
    if fold is None:
        raise FoldError(f"unknown fold: {fold_id}")
    nodes = [n for n in data["nodes"] if n["id"] in {fold["from_node"], fold["to_node"]}]
    source_ids = set(fold["evidence_ids"])
    for node in nodes:
        source_ids.update(node["source_ids"])
    for assessment in fold["jit"]:
        source_ids.update(assessment["evidence_ids"])
    return {"schema": "vinculum.folding.unfold/1", "episode_id": data["episode_id"],
            "revision": data["revision"], "episode_digest": episode.digest,
            "fold": fold, "nodes": nodes,
            "evidence": [e for e in data["evidence"] if e["id"] in source_ids],
            "host_pair_result": host_pair_results(episode).get(fold.get("host_pair_id")),
            "boundary": BOUNDARY}


def compare(before: FoldEpisode, after: FoldEpisode) -> dict[str, Any]:
    """Compare recorded revisions without deciding which interpretation is true."""
    a, b = before.to_dict(), after.to_dict()
    if a["episode_id"] != b["episode_id"] or a["mission_id"] != b["mission_id"]:
        raise FoldError("revision comparison requires the same episode and mission identity")
    changes = {}
    for name in ("nodes", "folds", "evidence", "external_links"):
        aa, bb = {x["id"]: x for x in a[name]}, {x["id"]: x for x in b[name]}
        changes[name] = {"added": sorted(bb.keys() - aa.keys()), "removed": sorted(aa.keys() - bb.keys()),
                         "changed": sorted(k for k in aa.keys() & bb.keys() if aa[k] != bb[k])}
    return {"schema": "vinculum.folding.diff/1", "episode_id": a["episode_id"],
            "before_digest": before.digest, "after_digest": after.digest,
            "direct_successor": b["revision"] == a["revision"] + 1 and b["previous_digest"] == before.digest,
            "changes": changes,
            "metadata_changes": [key for key in ("title", "recorded_at", "cerpa_links", "artifact_links") if a[key] != b[key]],
            "host_capture_changed": a.get("host_capture") != b.get("host_capture"),
            "boundary": BOUNDARY}


def review_input(episode: FoldEpisode) -> dict[str, Any]:
    """Non-executing handoff; no auto-CERPA transition or operational task dispatch."""
    return {"schema": "vinculum.folding.review_input/1", "episode_id": episode.episode_id,
            "revision": episode.revision, "episode_digest": episode.digest,
            "requested_stage": "REVIEW", "disposition": "DRAFT_REVIEW_INPUT",
            "findings": [asdict(f) for f in audit(episode).findings],
            "automatic_actions": 0, "boundary": BOUNDARY}
