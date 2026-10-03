"""Strict, lossless, immutable episode snapshots. No claim here is an authorization.

The origami vocabulary describes recorded representations, not physical folding,
physical time reversal, or an automatically optimized mathematical maximum.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from fractions import Fraction
from pathlib import Path
from typing import Any, Mapping

VERSION = "0.1.0"
SCHEMA = "vinculum.folding.episode/1"
MAX_BYTES = 8_000_000
MAX_NODES = 10_000
MAX_FOLDS = 20_000
MAX_TEXT = 100_000
MAX_DEPTH = 60


class FoldError(ValueError):
    """Invalid or inconsistent folding data, never a negative truth verdict."""


class Aspect(str, Enum):
    TIME = "TIME"
    WORDS = "WORDS"
    NUMBERS = "NUMBERS"


class Lens(str, Enum):
    LEGACY_OF_PRECISION = "LEGACY_OF_PRECISION"
    DENSITY_OF_EXPOSURE = "DENSITY_OF_EXPOSURE"
    MATRIX_OF_AWARENESS = "MATRIX_OF_AWARENESS"
    ONTOLOGICAL_GRADE = "ONTOLOGICAL_GRADE"


class AssessmentState(str, Enum):
    UNASSESSED = "UNASSESSED"
    SUPPORTED = "SUPPORTED"
    CHALLENGED = "CHALLENGED"
    INDETERMINATE = "INDETERMINATE"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class OntologicalGrade(str, Enum):
    # User-defined JIT categories, not geometric calculations or truth ranks.
    UNSPECIFIED = "UNSPECIFIED"
    GRADE_1_VECTOR = "GRADE_1_VECTOR"
    GRADE_2_BIVECTOR = "GRADE_2_BIVECTOR"


LENS_LABELS = {
    Lens.LEGACY_OF_PRECISION.value: "Legacy of Precision",
    Lens.DENSITY_OF_EXPOSURE.value: "Density of Exposure",
    Lens.MATRIX_OF_AWARENESS.value: "Matrix of Awareness",
    Lens.ONTOLOGICAL_GRADE.value: "Ontological Grade",
}
RELATIONS = {"RELATED_TO", "ASPECT_OF", "DERIVED_FROM", "DEPENDS_ON",
             "COUNTERFOLD", "PRECEDES", "SELECTED_PAIR"}
PAIR_STATES = {"ALIGNED", "PARTIAL", "CONFLICT", "UNRESOLVED", "NOT_COMPARABLE"}
CERPA_STAGES = ("CLAIM", "EVENT", "REVIEW", "PATCH", "APPLY")
ARTIFACT_KINDS = {"DLR", "RS", "DS", "MG"}
BOUNDARY = (
    "Inspection is not authorization. JIT states are attributed assessments, not "
    "truth scores. Hashes identify recorded content, not factual truth or trusted "
    "authority. APPLY is not proof of successful outcome."
)


def _walk_json(value: Any, depth: int = 0) -> None:
    if depth > MAX_DEPTH:
        raise FoldError("JSON nesting exceeds the folding limit")
    if value is None or type(value) in (bool, int):
        return
    if type(value) is float:
        if value != value or abs(value) == float("inf"):
            raise FoldError("nonfinite JSON number")
        return
    if type(value) is str:
        if len(value) > MAX_TEXT:
            raise FoldError("JSON string exceeds the folding text limit")
        return
    if type(value) is list:
        if len(value) > 100_000:
            raise FoldError("JSON array exceeds the folding limit")
        for item in value:
            _walk_json(item, depth + 1)
        return
    if type(value) is dict:
        if len(value) > 100_000 or any(type(k) is not str for k in value):
            raise FoldError("JSON object requires bounded string keys")
        for k, item in value.items():
            _walk_json(k, depth + 1)
            _walk_json(item, depth + 1)
        return
    raise FoldError(f"unsupported JSON value: {type(value).__name__}")


def canonical(value: Any) -> str:
    """Deterministic JSON; preserves array order and exact numeric strings."""
    try:
        _walk_json(value)
        text = json.dumps(value, ensure_ascii=False, sort_keys=True,
                          separators=(",", ":"), allow_nan=False)
        if len(text.encode("utf-8")) > MAX_BYTES:
            raise FoldError("snapshot exceeds byte limit")
        return text
    except (TypeError, OverflowError, RecursionError, UnicodeError) as exc:
        raise FoldError("value cannot be represented as bounded UTF-8 JSON") from exc


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def strict_json(text: str) -> Any:
    if type(text) is not str or len(text.encode("utf-8")) > MAX_BYTES:
        raise FoldError("JSON input exceeds byte limit or is not text")

    def pairs(items):
        obj = {}
        for key, value in items:
            if key in obj:
                raise FoldError(f"duplicate JSON key: {key}")
            obj[key] = value
        return obj

    def constant(value):
        raise FoldError(f"nonfinite JSON literal: {value}")

    try:
        result = json.loads(text, object_pairs_hook=pairs, parse_constant=constant)
        canonical(result)
        return result
    except (json.JSONDecodeError, RecursionError, UnicodeError) as exc:
        raise FoldError("invalid JSON input") from exc


def load_json(path: str | Path) -> Any:
    with Path(path).open("rb") as stream:
        raw = stream.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise FoldError("input file exceeds byte limit")
    try:
        return strict_json(raw.decode("utf-8"))
    except UnicodeError as exc:
        raise FoldError("input must be UTF-8") from exc


def text(value: Any, name: str, *, empty: bool = False, limit: int = MAX_TEXT) -> str:
    if type(value) is not str or len(value) > limit or (not empty and not value.strip()):
        raise FoldError(f"{name}: expected {'a' if empty else 'a nonempty'} bounded string")
    return value


def identifier(value: Any, name: str = "id") -> str:
    value = text(value, name, limit=512)
    if any(ord(c) < 32 for c in value):
        raise FoldError(f"{name}: control characters are not permitted")
    return value


def timestamp(value: Any, name: str = "timestamp") -> datetime:
    value = text(value, name, limit=80)
    # Explicit timezone mandatory; do not infer the user's/local machine's zone.
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})", value):
        raise FoldError(f"{name}: require ISO timestamp with explicit Z or UTC offset")
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.utcoffset() is None:
            raise ValueError("naive")
        return dt
    except ValueError as exc:
        raise FoldError(f"{name}: invalid timestamp") from exc


def sha(value: Any, name: str = "sha256", *, nullable: bool = False) -> None:
    if value is None and nullable:
        return
    if type(value) is not str or not re.fullmatch("[0-9a-f]{64}", value):
        raise FoldError(f"{name}: expected lowercase SHA-256 hex")


def fields(obj: Any, allowed: set[str], required: set[str], name: str) -> None:
    if type(obj) is not dict:
        raise FoldError(f"{name}: expected object")
    extra, missing = set(obj) - allowed, required - set(obj)
    if extra or missing:
        raise FoldError(f"{name}: unknown={sorted(extra)}, missing={sorted(missing)}")


def enum(value: Any, choices: set[str], name: str) -> None:
    if type(value) is not str or value not in choices:
        raise FoldError(f"{name}: invalid value {value!r}")


def array(value: Any, name: str, *, limit: int = MAX_FOLDS) -> list:
    if type(value) is not list or len(value) > limit:
        raise FoldError(f"{name}: expected bounded array")
    return value


def ids(value: Any, name: str, known: set[str] | None = None) -> None:
    array(value, name)
    for item in value:
        identifier(item, name)
    if len(set(value)) != len(value):
        raise FoldError(f"{name}: duplicate references")
    if known is not None and not set(value) <= known:
        raise FoldError(f"{name}: dangling references {sorted(set(value) - known)}")


def exact_number(value: Any) -> Fraction:
    # A string preserves 1/3 and stated decimal precision. Floats/bools are refused.
    if type(value) is int:
        if len(str(abs(value))) > 128:
            raise FoldError("numeric integer exceeds digit limit")
        return Fraction(value)
    if type(value) is not str or len(value) > 260:
        raise FoldError("exact numbers require bounded integer or numeric string")
    if not re.fullmatch(r"[+-]?\d{1,128}(?:/\d{1,128}|(?:\.\d{1,128})?(?:[eE][+-]?\d{1,3})?)?", value):
        raise FoldError("invalid bounded exact number")
    try:
        return Fraction(value)
    except (ValueError, ZeroDivisionError) as exc:
        raise FoldError("invalid exact numeric value") from exc


def unassessed_lenses() -> list[dict[str, Any]]:
    """Fresh four-lens collection; callers never share mutable default state."""
    return [{"lens": lens.value, "state": "UNASSESSED", "rationale": "Not assessed",
             "assessor": None, "evidence_ids": [], "context": {}}
            for lens in Lens]


def validate_lenses(items: Any, evidence_ids: set[str]) -> None:
    array(items, "jit", limit=4)
    if len(items) != 4:
        raise FoldError("every fold requires exactly the four named JIT lenses")
    seen = set()
    for item in items:
        fields(item, {"lens", "state", "rationale", "assessor", "evidence_ids", "context"},
               {"lens", "state", "rationale", "assessor", "evidence_ids", "context"}, "JIT assessment")
        enum(item["lens"], set(LENS_LABELS), "JIT lens")
        if item["lens"] in seen:
            raise FoldError("duplicate JIT lens")
        seen.add(item["lens"])
        enum(item["state"], {v.value for v in AssessmentState}, "JIT state")
        text(item["rationale"], "JIT rationale")
        if item["assessor"] is not None:
            identifier(item["assessor"], "assessor attribution")
        if item["state"] != "UNASSESSED" and item["assessor"] is None:
            raise FoldError("assessed JIT state requires assessor attribution")
        ids(item["evidence_ids"], "JIT evidence", evidence_ids)
        if item["state"] in {"SUPPORTED", "CHALLENGED"} and not item["evidence_ids"]:
            raise FoldError("supported/challenged assessment requires evidence references")
        allowed = ({"evaluation", "potency", "activity", "viewpoint"}
                   if item["lens"] == Lens.MATRIX_OF_AWARENESS.value else {"note"})
        fields(item["context"], allowed, set(), "lens context")
        for key, value in item["context"].items():
            text(value, key)
        if item["lens"] == Lens.MATRIX_OF_AWARENESS.value and item["state"] in {"SUPPORTED", "CHALLENGED"}:
            if not {"evaluation", "potency", "activity", "viewpoint"} <= item["context"].keys():
                raise FoldError("Matrix of Awareness requires Evaluation, Potency, Activity and viewpoint")


def validate_episode(data: dict[str, Any]) -> None:
    allowed = {"schema", "episode_id", "revision", "mission_id", "title", "recorded_at",
               "previous_digest", "evidence", "nodes", "folds", "external_links",
               "cerpa_links", "artifact_links", "host_capture"}
    fields(data, allowed, allowed - {"host_capture"}, "episode")
    if data["schema"] != SCHEMA:
        raise FoldError(f"expected {SCHEMA}")
    for key in ("episode_id", "mission_id"):
        identifier(data[key], key)
    text(data["title"], "title")
    timestamp(data["recorded_at"], "recorded_at")
    if type(data["revision"]) is not int or data["revision"] < 1:
        raise FoldError("revision must be a positive integer, not a boolean")
    sha(data["previous_digest"], "previous_digest", nullable=True)
    if (data["revision"] == 1) != (data["previous_digest"] is None):
        raise FoldError("revision 1 has no predecessor; every later revision requires one")

    evidence_ids = set()
    for ev in array(data["evidence"], "evidence", limit=MAX_NODES):
        fields(ev, {"id", "locator", "sha256", "root_id", "description"},
               {"id", "locator", "sha256", "root_id", "description"}, "evidence")
        identifier(ev["id"])
        if ev["id"] in evidence_ids:
            raise FoldError("duplicate evidence id")
        evidence_ids.add(ev["id"])
        for key in ("locator", "root_id"):
            if ev[key] is not None:
                text(ev[key], key)
        text(ev["description"], "evidence description", empty=True)
        sha(ev["sha256"], nullable=True)

    node_ids = set()
    for node in array(data["nodes"], "nodes", limit=MAX_NODES):
        fields(node, {"id", "aspect", "value", "source_ids", "ontological_grade", "referent_id", "host_representation_id"},
               {"id", "aspect", "value", "source_ids", "ontological_grade", "referent_id"}, "aspect node")
        identifier(node["id"])
        if node["id"] in node_ids:
            raise FoldError("duplicate node id")
        node_ids.add(node["id"])
        enum(node["aspect"], {x.value for x in Aspect}, "aspect")
        enum(node["ontological_grade"], {x.value for x in OntologicalGrade}, "ontological grade")
        for key in ("referent_id", "host_representation_id"):
            if node.get(key) is not None:
                identifier(node[key], key)
        ids(node["source_ids"], "node source_ids", evidence_ids)
        value = node["value"]
        if node["aspect"] == "TIME":
            fields(value, {"start", "end", "basis"}, {"start", "end", "basis"}, "time value")
            text(value["basis"], "temporal basis")
            if value["start"] is None and value["end"] is not None:
                raise FoldError("time end cannot exist without a start")
            if value["start"] is not None:
                start = timestamp(value["start"], "time start")
                if value["end"] is not None and timestamp(value["end"], "time end") < start:
                    raise FoldError("reversed time interval")
        elif node["aspect"] == "WORDS":
            fields(value, {"text", "scope", "definition_id"}, {"text", "scope", "definition_id"}, "words value")
            text(value["text"], "words text", empty=True)
            enum(value["scope"], {"UNSPECIFIED", "RECORDED", "EXHAUSTIVE"}, "claim scope")
            if value["definition_id"] is not None:
                identifier(value["definition_id"], "definition_id")
        else:
            fields(value, {"quantity", "unit", "concept", "method"}, {"quantity", "unit", "concept", "method"}, "numbers value")
            for key in ("unit", "concept", "method"):
                if value[key] is not None:
                    identifier(value[key], key)
            q = value["quantity"]
            if q is not None:
                fields(q, {"lower", "upper", "lower_inclusive", "upper_inclusive"},
                       {"lower", "upper", "lower_inclusive", "upper_inclusive"}, "quantity")
                if any(type(q[k]) is not bool for k in ("lower_inclusive", "upper_inclusive")):
                    raise FoldError("range inclusivity must be boolean")
                lo = exact_number(q["lower"]) if q["lower"] is not None else None
                hi = exact_number(q["upper"]) if q["upper"] is not None else None
                if lo is None and hi is None:
                    raise FoldError("use quantity=null for unknown, not an unconstrained range")
                if lo is not None and hi is not None and (lo > hi or (lo == hi and not (q["lower_inclusive"] and q["upper_inclusive"]))):
                    raise FoldError("empty or reversed numeric interval")

    fold_ids = set()
    for fold in array(data["folds"], "folds"):
        fields(fold, {"id", "from_node", "to_node", "relation", "rationale", "evidence_ids", "jit", "host_pair_id"},
               {"id", "from_node", "to_node", "relation", "rationale", "evidence_ids", "jit"}, "fold")
        identifier(fold["id"])
        if fold["id"] in fold_ids or fold["id"] in node_ids:
            raise FoldError("fold ID must be unique and distinct from node IDs")
        fold_ids.add(fold["id"])
        for key in ("from_node", "to_node"):
            identifier(fold[key], key)
            if fold[key] not in node_ids:
                raise FoldError("fold has dangling node reference")
        if fold["from_node"] == fold["to_node"]:
            raise FoldError("a fold must relate distinct nodes")
        enum(fold["relation"], RELATIONS, "fold relation")
        text(fold["rationale"], "fold rationale")
        ids(fold["evidence_ids"], "fold evidence", evidence_ids)
        validate_lenses(fold["jit"], evidence_ids)
        if fold.get("host_pair_id") is not None:
            identifier(fold["host_pair_id"], "host_pair_id")
            if fold["relation"] != "SELECTED_PAIR":
                raise FoldError("host pair references must retain SELECTED_PAIR relation")

    external_ids = set()
    for link in array(data["external_links"], "external_links"):
        fields(link, {"id", "from_node", "to_episode_id", "to_revision", "to_node", "relation", "rationale"},
               {"id", "from_node", "to_episode_id", "to_revision", "to_node", "relation", "rationale"}, "external link")
        for key in ("id", "from_node", "to_episode_id", "to_node"):
            identifier(link[key], key)
        if link["id"] in external_ids or link["id"] in fold_ids or link["id"] in node_ids:
            raise FoldError("external link ID collision")
        external_ids.add(link["id"])
        if link["from_node"] not in node_ids:
            raise FoldError("external link source is missing")
        if type(link["to_revision"]) is not int or link["to_revision"] < 1:
            raise FoldError("cross-episode references must pin a positive revision")
        enum(link["relation"], RELATIONS - {"SELECTED_PAIR"}, "external relation")
        text(link["rationale"], "external rationale")

    for collection, field_name, choices in (("cerpa_links", "stage", set(CERPA_STAGES)),
                                              ("artifact_links", "kind", ARTIFACT_KINDS)):
        seen = set()
        for item in array(data[collection], collection):
            fields(item, {field_name, "record_id", "locator", "sha256"},
                   {field_name, "record_id", "locator", "sha256"}, collection)
            enum(item[field_name], choices, field_name)
            identifier(item["record_id"], "record_id")
            text(item["locator"], "record locator")
            sha(item["sha256"], nullable=True)
            key = (item[field_name], item["record_id"])
            if key in seen:
                raise FoldError(f"duplicate {collection} reference")
            seen.add(key)

    capture = data.get("host_capture")
    if capture is not None:
        from .adapter import validate_capture
        validate_capture(capture, data["nodes"], data["folds"])
    elif any(n.get("host_representation_id") is not None for n in data["nodes"]) or any(f.get("host_pair_id") is not None for f in data["folds"]):
        raise FoldError("host object references require a retained host snapshot")


@dataclass(frozen=True, init=False)
class FoldEpisode:
    """Immutable, validated snapshot; returned dictionaries are independent copies."""
    _json: str

    def __init__(self, data: Mapping[str, Any]):
        if not isinstance(data, Mapping):
            raise FoldError("episode must be a mapping")
        encoded = canonical(dict(data))
        normalized = strict_json(encoded)
        validate_episode(normalized)
        object.__setattr__(self, "_json", encoded)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "FoldEpisode":
        return cls(data)

    @classmethod
    def load(cls, path: str | Path) -> "FoldEpisode":
        return cls(load_json(path))

    def to_dict(self) -> dict[str, Any]:
        return json.loads(self._json)

    @property
    def digest(self) -> str:
        return hashlib.sha256(self._json.encode("utf-8")).hexdigest()

    @property
    def episode_id(self) -> str:
        return self.to_dict()["episode_id"]

    @property
    def revision(self) -> int:
        return self.to_dict()["revision"]

    def revise(self, *, recorded_at: str, **changes: Any) -> "FoldEpisode":
        """Prepare a new draft snapshot, never overwrite or authorize the prior one."""
        forbidden = {"schema", "episode_id", "revision", "previous_digest", "mission_id"}
        if set(changes) & forbidden:
            raise FoldError("revision cannot reassign identity, mission or lineage")
        data = self.to_dict()
        data.update(changes)
        data.update(revision=self.revision + 1, previous_digest=self.digest, recorded_at=recorded_at)
        return FoldEpisode(data)


def episode_template(*, episode_id: str, mission_id: str, title: str, recorded_at: str) -> dict[str, Any]:
    return {"schema": SCHEMA, "episode_id": episode_id, "revision": 1,
            "mission_id": mission_id, "title": title, "recorded_at": recorded_at,
            "previous_digest": None, "evidence": [], "nodes": [], "folds": [],
            "external_links": [], "cerpa_links": [], "artifact_links": []}
