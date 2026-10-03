"""Read-only adapter to the source-inspected VINCULUM 0.7.0 serialization API.

Copies .to_dict() and .scenario.to_dict(); never calls evaluate, apply or export,
never monkey-patches the host, and never reclassifies its selected-pair outcomes.
"""
from __future__ import annotations

from typing import Any, Protocol

from .model import (FoldEpisode, FoldError, PAIR_STATES, canonical, digest,
                    episode_template, fields, identifier, sha, strict_json,
                    unassessed_lenses)

HOST_SCHEMA = "vinculum.folding.host/1"
HOST_VERSION = "0.7.0"
SOURCE_COMMIT = "6c4dd7ebacda4c3eb2cb505224c28348410bd05e"


class Serializable(Protocol):
    def to_dict(self) -> dict[str, Any]: ...


class PipelineLike(Serializable, Protocol):
    scenario: Serializable


def _host_parts(capture):
    fields(capture, {"schema", "host_version", "scenario", "pipeline", "content_sha256"},
           {"schema", "host_version", "scenario", "pipeline", "content_sha256"}, "host capture")
    if capture["schema"] != HOST_SCHEMA or capture["host_version"] != HOST_VERSION:
        raise FoldError("host capture requires the inspected VINCULUM 0.7.0 contract")
    scenario, pipeline = capture["scenario"], capture["pipeline"]
    if type(scenario) is not dict or scenario.get("schema") != "vinculum.crossorder.scenario/1":
        raise FoldError("host scenario schema is unsupported")
    if type(pipeline) is not dict or pipeline.get("schema") != "vinculum.pipeline.result/1" or pipeline.get("engine_version") != HOST_VERSION:
        raise FoldError("host pipeline result schema/version is unsupported")
    report = pipeline.get("report")
    if type(report) is not dict or report.get("schema") != "vinculum.crossorder.report/1" or report.get("engine_version") != HOST_VERSION:
        raise FoldError("host report schema/version is unsupported")
    if report.get("graph_id") != scenario.get("id"):
        raise FoldError("host graph identity mismatch")
    sha(capture["content_sha256"], "host content hash")
    if capture["content_sha256"] != digest({"scenario": scenario, "pipeline": pipeline}):
        raise FoldError("host capture content hash mismatch")

    def index(items, key, name):
        if type(items) is not list:
            raise FoldError(f"host {name} must be an array")
        result = {}
        for item in items:
            if type(item) is not dict:
                raise FoldError(f"host {name} item must be an object")
            identifier(item.get(key), f"host {name} identity")
            if item[key] in result:
                raise FoldError(f"duplicate host {name} identity")
            result[item[key]] = item
        return result

    reps = index(scenario.get("representations", []), "id", "representation")
    reported_reps = index(report.get("representations", []), "id", "reported representation")
    if canonical(reps) != canonical(reported_reps):
        raise FoldError("host scenario/report representations do not match")
    pairs = index(scenario.get("pairs", []), "id", "pair")
    results = index(report.get("pairs", []), "pair_id", "pair result")
    if set(pairs) != set(results):
        raise FoldError("host selected pairs and evaluated pair IDs differ")
    for key, pair in pairs.items():
        if pair.get("left_id") not in reps or pair.get("right_id") not in reps:
            raise FoldError("host pair has missing representation")
        if results[key].get("status") not in PAIR_STATES:
            raise FoldError("unsupported host pair state; do not silently remap it")
    return scenario, pipeline, reps, pairs, results


def validate_capture(capture, nodes, folds):
    _, _, reps, pairs, _ = _host_parts(capture)
    node_map = {}
    for node in nodes:
        rid = node.get("host_representation_id")
        if rid is None:
            continue
        if rid not in reps or rid in node_map:
            raise FoldError("host representation missing or projected twice")
        node_map[rid] = node["id"]
        rep = reps[rid]
        expected = "WORDS" if rep.get("side") == "L" else "NUMBERS" if rep.get("side") == "M" else None
        if node["aspect"] != expected:
            raise FoldError("host L/M side must remain independent of the time sidecar")
        if sorted(node["source_ids"]) != sorted(rep.get("source_ids", [])):
            raise FoldError("host source references changed in projection")
        if expected == "WORDS":
            if node["value"]["text"] != rep.get("text", "") or node["value"]["definition_id"] != rep.get("definition_id"):
                raise FoldError("host wording or definition identity changed")
        else:
            for key in ("quantity", "unit", "concept", "method"):
                if canonical(node["value"][key]) != canonical(rep.get(key)):
                    raise FoldError(f"host numeric {key} changed in projection")
    if set(node_map) != set(reps):
        raise FoldError("host representations must all survive the fold")
    seen = set()
    for fold in folds:
        pid = fold.get("host_pair_id")
        if pid is None:
            continue
        if pid not in pairs or pid in seen:
            raise FoldError("host pair missing or projected twice")
        seen.add(pid)
        pair = pairs[pid]
        if fold["relation"] != "SELECTED_PAIR" or fold["from_node"] != node_map[pair["left_id"]] or fold["to_node"] != node_map[pair["right_id"]]:
            raise FoldError("host pairing direction or endpoint changed")
    if seen != set(pairs):
        raise FoldError("selected host pairs must all survive the fold")


def from_pipeline(run: PipelineLike, *, episode_id: str, mission_id: str,
                  title: str, recorded_at: str) -> FoldEpisode:
    """Capture a pipeline run as a sidecar episode. No host re-evaluation occurs.

    Time is projected only from an explicitly declared host Scope.window.
    No source independence, exhaustive scope or ontological grade is inferred.
    """
    try:
        scenario = strict_json(canonical(run.scenario.to_dict()))
        pipeline = strict_json(canonical(run.to_dict()))
    except AttributeError as exc:
        raise FoldError("adapter requires run.to_dict() and run.scenario.to_dict()") from exc
    capture = {"schema": HOST_SCHEMA, "host_version": HOST_VERSION,
               "scenario": scenario, "pipeline": pipeline,
               "content_sha256": digest({"scenario": scenario, "pipeline": pipeline})}
    _, _, reps, pairs, _ = _host_parts(capture)
    data = episode_template(episode_id=episode_id, mission_id=mission_id,
                            title=title, recorded_at=recorded_at)
    registered = {}
    for source in pipeline.get("sources", []):
        if type(source) is not dict or type(source.get("id")) is not str:
            raise FoldError("invalid host source metadata")
        if source["id"] in registered:
            raise FoldError("duplicate host source id")
        registered[source["id"]] = source
    all_sources = set(registered)
    for rep in reps.values():
        all_sources.update(rep.get("source_ids", []))
    for sid in sorted(all_sources):
        source = registered.get(sid, {})
        data["evidence"].append({"id": sid, "locator": source.get("locator") or source.get("uri"),
            "sha256": source.get("sha256"), "root_id": None,
            "description": "Imported host source metadata; not authenticated" if sid in registered
                           else "Host reference not registered; evidence remains unresolved"})
    for rid, rep in sorted(reps.items()):
        if rep.get("side") not in {"L", "M"}:
            raise FoldError("unknown host side")
        aspect = "WORDS" if rep["side"] == "L" else "NUMBERS"
        value = ({"text": rep.get("text", ""), "scope": "UNSPECIFIED", "definition_id": rep.get("definition_id")}
                 if aspect == "WORDS" else {k: rep.get(k) for k in ("quantity", "unit", "concept", "method")})
        node_id = f"r/{rid}"
        sources = list(rep.get("source_ids", []))
        data["nodes"].append({"id": node_id, "aspect": aspect, "value": value,
            "source_ids": sources, "ontological_grade": "UNSPECIFIED",
            "referent_id": rep.get("entity"), "host_representation_id": rid})
        window = (rep.get("scope") or {}).get("window")
        if window is not None:
            tid = f"t/{rid}"
            data["nodes"].append({"id": tid, "aspect": "TIME",
                "value": {"start": window["start"], "end": window["end"],
                          "basis": "Declared host scope window; not inferred event time"},
                "source_ids": sources, "ontological_grade": "UNSPECIFIED", "referent_id": rep.get("entity")})
            data["folds"].append({"id": f"time-of/{rid}", "from_node": tid,
                "to_node": node_id, "relation": "ASPECT_OF",
                "rationale": "Projects the existing representation's declared temporal scope",
                "evidence_ids": sources, "jit": unassessed_lenses()})
        for i, dependency in enumerate(rep.get("depends_on", [])):
            # A missing dependency remains in the exact host snapshot; do not fabricate its node.
            if dependency in reps:
                data["folds"].append({"id": f"dep/{rid}/{i}", "from_node": node_id,
                    "to_node": f"r/{dependency}", "relation": "DEPENDS_ON",
                    "rationale": "Declared host representation dependency",
                    "evidence_ids": [], "jit": unassessed_lenses()})
    for pid, pair in sorted(pairs.items()):
        data["folds"].append({"id": f"p/{pid}", "from_node": f"r/{pair['left_id']}",
            "to_node": f"r/{pair['right_id']}", "relation": "SELECTED_PAIR",
            "rationale": pair["rationale"], "evidence_ids": [],
            "jit": unassessed_lenses(), "host_pair_id": pid})
    data["host_capture"] = capture
    return FoldEpisode(data)


def host_pair_results(episode: FoldEpisode) -> dict[str, dict]:
    """Exact copied host results, separate from JIT and folding audit findings."""
    capture = episode.to_dict().get("host_capture")
    return {} if capture is None else _host_parts(capture)[4]
