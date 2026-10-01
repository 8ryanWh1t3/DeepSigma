from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
from typing import Any, Iterable

from rdflib import BNode, Graph, Literal, URIRef

from .models import ObjectType, ScoreMode, VinculumObject


def stable_id(prefix: str, content: Any) -> str:
    if isinstance(content, str):
        raw = content
    else:
        raw = json.dumps(content, sort_keys=True, separators=(",", ":"), default=str)
    return f"{prefix}-{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:12]}"


def _as_object_type(value: str | ObjectType) -> ObjectType:
    return value if isinstance(value, ObjectType) else ObjectType(value)


def _as_mode(value: str | ScoreMode) -> ScoreMode:
    return value if isinstance(value, ScoreMode) else ScoreMode(value)


def ingest_text(
    text: str,
    *,
    object_type: str | ObjectType = ObjectType.CLAIM,
    object_id: str | None = None,
    mode: str | ScoreMode = ScoreMode.AUTO,
    weight: float = 1.0,
    decompose: bool = True,
) -> VinculumObject:
    typ = _as_object_type(object_type)
    smode = _as_mode(mode)
    oid = object_id or stable_id(typ.value, text)

    if typ is ObjectType.TTL_GRAPH:
        return ingest_ttl(text, object_id=oid, weight=weight)

    children: tuple[VinculumObject, ...] = ()
    if decompose and typ in {ObjectType.DOCUMENT, ObjectType.POLICY, ObjectType.CORPUS}:
        parts = [p.strip() for p in re.split(r"\n\s*\n+", text) if p.strip()]
        if len(parts) > 1:
            child_type = ObjectType.PARAGRAPH if typ is not ObjectType.CORPUS else ObjectType.DOCUMENT
            children = tuple(
                ingest_text(p, object_type=child_type, object_id=f"{oid}:{i+1}", mode=smode, weight=max(1.0, len(p.split())), decompose=False)
                for i, p in enumerate(parts)
            )
    return VinculumObject(oid, typ, text, smode, weight, {}, children)


def ingest_ttl(text: str, *, object_id: str | None = None, weight: float = 1.0) -> VinculumObject:
    oid = object_id or stable_id("ttl", text)
    graph = Graph()
    parse_error = ""
    children: list[VinculumObject] = []
    parsed = False
    try:
        graph.parse(data=text, format="turtle")
        parsed = True
        triples = sorted(graph, key=lambda t: tuple(str(x) for x in t))
        for idx, (s, p, o) in enumerate(triples, 1):
            content = f"{s.n3(graph.namespace_manager)} {p.n3(graph.namespace_manager)} {o.n3(graph.namespace_manager)} ."
            md = {
                "subject": str(s),
                "predicate": str(p),
                "object": str(o),
                "subject_kind": type(s).__name__,
                "predicate_kind": type(p).__name__,
                "object_kind": type(o).__name__,
                "datatype": str(o.datatype) if isinstance(o, Literal) and o.datatype else None,
                "language": o.language if isinstance(o, Literal) else None,
            }
            children.append(VinculumObject(f"{oid}:triple:{idx}", ObjectType.RDF_TRIPLE, content, ScoreMode.TTL, 1.0, md, ()))
    except Exception as exc:  # rdflib surfaces several parser exception types
        parse_error = f"{type(exc).__name__}: {exc}"
        # fallback statements allow partial visibility without pretending parse success
        statements = [s.strip() + "." for s in re.split(r"\.\s*(?=(?:[^\"]*\"[^\"]*\")*[^\"]*$)", text) if s.strip() and not s.lstrip().startswith("@prefix")]
        for idx, stmt in enumerate(statements[:500], 1):
            children.append(VinculumObject(f"{oid}:fallback:{idx}", ObjectType.CLAIM, stmt, ScoreMode.LANGUAGE, 1.0, {"ttl_fallback": True}, ()))

    bnodes = 0
    if parsed:
        bnodes = len({n for triple in graph for n in triple if isinstance(n, BNode)})
    prefix_count = len(re.findall(r"(?:@prefix|\bPREFIX)\s+", text, re.IGNORECASE))
    meta = {
        "parsed": parsed,
        "parse_error": parse_error,
        "triple_count": len(graph) if parsed else len(children),
        "blank_nodes": bnodes,
        "prefix_count": prefix_count,
    }
    return VinculumObject(oid, ObjectType.TTL_GRAPH, text, ScoreMode.TTL, weight, meta, tuple(children))


def ingest_mapping(
    data: Any,
    *,
    object_type: str | ObjectType = ObjectType.EPISODE,
    object_id: str | None = None,
    mode: str | ScoreMode = ScoreMode.AUTO,
    weight: float = 1.0,
) -> VinculumObject:
    typ = _as_object_type(object_type)
    smode = _as_mode(mode)
    oid = object_id or stable_id(typ.value, data)
    children: list[VinculumObject] = []

    if typ is ObjectType.EPISODE and isinstance(data, dict):
        key_types = {
            "claims": ObjectType.CLAIM,
            "events": ObjectType.GENERIC,
            "decisions": ObjectType.DECISION,
            "observations": ObjectType.SENSOR_OBSERVATION,
            "model_outputs": ObjectType.MODEL_OUTPUT,
        }
        for key, child_type in key_types.items():
            values = data.get(key, [])
            if not isinstance(values, list):
                values = [values]
            for idx, value in enumerate(values, 1):
                if isinstance(value, str):
                    child = ingest_text(value, object_type=child_type, object_id=f"{oid}:{key}:{idx}", mode=ScoreMode.AUTO, decompose=False)
                else:
                    child = VinculumObject(f"{oid}:{key}:{idx}", child_type, value, ScoreMode.STRUCTURED, 1.0, {"episode_key": key}, ())
                children.append(child)
    elif typ in {ObjectType.DATASET, ObjectType.CORPUS} and isinstance(data, list):
        child_type = ObjectType.DATA_ROW if typ is ObjectType.DATASET else ObjectType.GENERIC
        for idx, value in enumerate(data, 1):
            if isinstance(value, str):
                children.append(ingest_text(value, object_type=child_type, object_id=f"{oid}:{idx}", mode=ScoreMode.AUTO, decompose=False))
            else:
                children.append(VinculumObject(f"{oid}:{idx}", child_type, value, ScoreMode.STRUCTURED, 1.0, {}, ()))

    return VinculumObject(oid, typ, data, smode, weight, {}, tuple(children))


def ingest_file(path: str | Path, *, object_type: str | ObjectType | None = None, mode: str | ScoreMode = ScoreMode.AUTO) -> VinculumObject:
    p = Path(path)
    suffix = p.suffix.lower()
    if suffix in {".ttl", ".turtle"}:
        return ingest_ttl(p.read_text(encoding="utf-8"), object_id=p.name)
    if suffix == ".json":
        data = json.loads(p.read_text(encoding="utf-8"))
        typ = ObjectType.DATASET if isinstance(data, list) else ObjectType.EPISODE
        if object_type is not None:
            typ = _as_object_type(object_type)
        return ingest_mapping(data, object_type=typ, object_id=p.name, mode=mode)
    text = p.read_text(encoding="utf-8")
    typ = _as_object_type(object_type) if object_type is not None else ObjectType.DOCUMENT
    return ingest_text(text, object_type=typ, object_id=p.name, mode=mode)
