from __future__ import annotations

import hashlib
import re
import unicodedata
from rdflib import Graph
from rdflib.compare import to_canonical_graph


def normalize_text(value: str | None) -> str:
    if not value:
        return ""
    value = unicodedata.normalize("NFKC", value).casefold().strip()
    value = re.sub(r"[_\-/]+", " ", value)
    value = re.sub(r"[^\w\s]", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def local_name(uri: str) -> str:
    if "#" in uri:
        return uri.rsplit("#", 1)[-1]
    return uri.rstrip("/").rsplit("/", 1)[-1]


def namespace_of(uri: str) -> str:
    if "#" in uri:
        return uri.rsplit("#", 1)[0] + "#"
    if "/" in uri:
        return uri.rsplit("/", 1)[0] + "/"
    return uri


def graph_fingerprint(graph: Graph) -> str:
    """Stable graph fingerprint, including graphs that contain RDF blank-node structures."""
    canonical = to_canonical_graph(graph)
    rows = sorted(f"{s.n3()} {p.n3()} {o.n3()} ." for s, p, o in canonical)
    return hashlib.sha256("\n".join(rows).encode("utf-8")).hexdigest()


def hash_text(*values: str) -> str:
    return hashlib.sha256("\u241f".join(values).encode("utf-8")).hexdigest()
