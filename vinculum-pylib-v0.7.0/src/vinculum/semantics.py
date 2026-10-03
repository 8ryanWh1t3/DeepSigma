from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import math
import re
from typing import Any, Iterable, Mapping, Sequence

from .models import ObjectType, VinculumObject


class ReconciliationStatus(str, Enum):
    NO_COMPARISON = "NO_COMPARISON"
    ALIGNED = "ALIGNED"
    CONFLICT = "CONFLICT"
    MIXED = "MIXED"
    UNRESOLVED = "UNRESOLVED"


@dataclass(frozen=True)
class MeaningRule:
    """Deterministic lexical meaning rule.

    A MeaningRule does not assert that arbitrary prose is true. It states that a
    recognized phrase has a canonical machine-comparable meaning under this
    registry. Rules are explicit and inspectable; callers can replace/extend the
    registry without changing the core engine.
    """

    id: str
    label: str
    pattern: re.Pattern[str]
    dimension: str
    operator: str
    value: float
    unit: str | None = None
    confidence: float = 1.0
    tolerance_abs: float = 0.0
    priority: int = 100
    note: str = ""

    @classmethod
    def compile(
        cls,
        *,
        id: str,
        label: str,
        pattern: str,
        dimension: str,
        operator: str,
        value: float,
        unit: str | None = None,
        confidence: float = 1.0,
        tolerance_abs: float = 0.0,
        priority: int = 100,
        note: str = "",
    ) -> "MeaningRule":
        return cls(
            id=id,
            label=label,
            pattern=re.compile(pattern, re.IGNORECASE | re.MULTILINE),
            dimension=dimension,
            operator=operator,
            value=float(value),
            unit=unit,
            confidence=max(0.0, min(1.0, float(confidence))),
            tolerance_abs=max(0.0, float(tolerance_abs)),
            priority=int(priority),
            note=note,
        )


DEFAULT_MEANING_RULES: tuple[MeaningRule, ...] = (
    MeaningRule.compile(
        id="SEM_BAKERS_DOZEN",
        label="baker's dozen",
        pattern=r"\bbaker(?:['’]s|s)?\s+dozen\b",
        dimension="count",
        operator="eq",
        value=13,
        unit="count",
        confidence=1.0,
        priority=10,
        note="Canonical English quantity: a baker's dozen is thirteen.",
    ),
    MeaningRule.compile(
        id="SEM_HALF_DOZEN",
        label="half-dozen",
        pattern=r"\b(?:half[-\s]?dozen|half\s+a\s+dozen)\b",
        dimension="count",
        operator="eq",
        value=6,
        unit="count",
        confidence=1.0,
        priority=20,
        note="Canonical quantity: half a dozen is six.",
    ),
    MeaningRule.compile(
        id="SEM_DOZEN",
        label="dozen",
        pattern=r"\b(?:a\s+)?dozen\b",
        dimension="count",
        operator="eq",
        value=12,
        unit="count",
        confidence=1.0,
        priority=50,
        note="Canonical quantity: a dozen is twelve.",
    ),
    MeaningRule.compile(
        id="SEM_PAIR",
        label="pair",
        pattern=r"\b(?:a\s+)?pair\b",
        dimension="count",
        operator="eq",
        value=2,
        unit="count",
        confidence=0.98,
        priority=60,
        note="Canonical count meaning of pair; confidence is slightly below 1 to allow non-count idioms.",
    ),
)


@dataclass(frozen=True)
class SemanticFact:
    fact_id: str
    source_object_id: str
    source_kind: str  # semantic | record
    dimension: str
    operator: str
    value: float
    unit: str | None
    confidence: float
    tolerance_abs: float = 0.0
    concept_key: str | None = None
    phrase: str = ""
    path: str = ""
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "fact_id": self.fact_id,
            "source_object_id": self.source_object_id,
            "source_kind": self.source_kind,
            "dimension": self.dimension,
            "operator": self.operator,
            "value": self.value,
            "unit": self.unit,
            "confidence": self.confidence,
            "semantic_determinization_strength": self.confidence if self.source_kind == "semantic" else None,
            "deterministic_defense_strength": self.confidence if self.source_kind == "record" else None,
            "probabilistic_contamination": (1.0 - self.confidence) if self.source_kind == "record" else None,
            "tolerance_abs": self.tolerance_abs,
            "concept_key": self.concept_key,
            "phrase": self.phrase,
            "path": self.path,
            "note": self.note,
        }


@dataclass(frozen=True)
class ComparisonResult:
    semantic_fact_id: str
    record_fact_id: str
    dimension: str
    semantic_value: float
    record_value: float
    operator: str
    unit: str | None
    status: str
    aligned: bool
    delta: float
    normalized_delta: float
    alignment_score: float
    semantic_determinization_strength: float
    deterministic_defense_strength: float
    probabilistic_contamination: float
    raw_conflict_strength: float
    conflict_strength: float
    rationale: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "semantic_fact_id": self.semantic_fact_id,
            "record_fact_id": self.record_fact_id,
            "dimension": self.dimension,
            "semantic_value": self.semantic_value,
            "record_value": self.record_value,
            "operator": self.operator,
            "unit": self.unit,
            "status": self.status,
            "aligned": self.aligned,
            "delta": self.delta,
            "normalized_delta": self.normalized_delta,
            "alignment_score": self.alignment_score,
            "semantic_determinization_strength": self.semantic_determinization_strength,
            "deterministic_defense_strength": self.deterministic_defense_strength,
            "probabilistic_contamination": self.probabilistic_contamination,
            "raw_conflict_strength": self.raw_conflict_strength,
            "conflict_strength": self.conflict_strength,
            "raw_collision_strength": self.raw_conflict_strength,
            "collision_strength": self.conflict_strength,
            "rationale": self.rationale,
        }


@dataclass(frozen=True)
class ReconciliationSummary:
    status: ReconciliationStatus
    semantic_record_tension: float
    comparison_coverage: float
    max_conflict_strength: float = 0.0
    semantic_determinization_strength: float | None = None
    deterministic_defense_strength: float | None = None
    probabilistic_contamination: float | None = None
    semantic_facts: tuple[SemanticFact, ...] = ()
    record_facts: tuple[SemanticFact, ...] = ()
    comparisons: tuple[ComparisonResult, ...] = ()
    unresolved: tuple[str, ...] = ()

    @property
    def has_comparison(self) -> bool:
        return bool(self.comparisons)

    def to_dict(self) -> dict[str, Any]:
        primary = None
        if self.comparisons:
            ranked = sorted(self.comparisons, key=lambda c: (-c.conflict_strength, -c.alignment_score, c.semantic_fact_id, c.record_fact_id))
            primary = ranked[0].to_dict()
        return {
            "status": self.status.value,
            "semantic_record_tension": self.semantic_record_tension,
            "comparison_coverage": self.comparison_coverage,
            "max_conflict_strength": self.max_conflict_strength,
            "semantic_determinization_strength": self.semantic_determinization_strength,
            "deterministic_defense_strength": self.deterministic_defense_strength,
            "probabilistic_contamination": self.probabilistic_contamination,
            "primary_comparison": primary,
            "semantic_facts": [f.to_dict() for f in self.semantic_facts],
            "record_facts": [f.to_dict() for f in self.record_facts],
            "comparisons": [c.to_dict() for c in self.comparisons],
            "unresolved": list(self.unresolved),
        }


class MeaningRegistry:
    def __init__(self, rules: Iterable[MeaningRule] = DEFAULT_MEANING_RULES) -> None:
        self.rules = tuple(sorted(tuple(rules), key=lambda r: (r.priority, r.id)))

    @classmethod
    def default(cls) -> "MeaningRegistry":
        return cls(DEFAULT_MEANING_RULES)

    def with_rule(self, rule: MeaningRule) -> "MeaningRegistry":
        return MeaningRegistry(self.rules + (rule,))

    def resolve_text(self, text: str, *, object_id: str, path: str = "") -> tuple[SemanticFact, ...]:
        """Resolve non-overlapping canonical phrase meanings in deterministic priority order."""
        if not text:
            return ()
        occupied: list[tuple[int, int]] = []
        out: list[SemanticFact] = []
        for rule in self.rules:
            for idx, match in enumerate(rule.pattern.finditer(text), 1):
                span = match.span()
                if any(not (span[1] <= a or span[0] >= b) for a, b in occupied):
                    continue
                occupied.append(span)
                out.append(
                    SemanticFact(
                        fact_id=f"{object_id}:sem:{rule.id}:{span[0]}:{span[1]}",
                        source_object_id=object_id,
                        source_kind="semantic",
                        dimension=rule.dimension,
                        operator=rule.operator,
                        value=rule.value,
                        unit=rule.unit,
                        confidence=rule.confidence,
                        tolerance_abs=rule.tolerance_abs,
                        concept_key=rule.id,
                        phrase=match.group(0),
                        path=path,
                        note=rule.note,
                    )
                )
        out.sort(key=lambda f: (f.path, f.fact_id))
        return tuple(out)


_RECORD_KEY_DIMENSIONS: Mapping[str, tuple[str, str | None]] = {
    "qty": ("count", "count"),
    "quantity": ("count", "count"),
    "count": ("count", "count"),
    "itemcount": ("count", "count"),
    "itemscount": ("count", "count"),
    "numberofitems": ("count", "count"),
    "totalitems": ("count", "count"),
    "units": ("count", "count"),
    "unitcount": ("count", "count"),
}

_LABEL_KEYS = ("item", "name", "description", "product", "label", "term", "subject", "metric", "title")


def _norm_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


def _as_number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        if math.isfinite(float(value)):
            return float(value)
        return None
    if isinstance(value, str):
        m = re.fullmatch(r"\s*[-+]?\d+(?:\.\d+)?\s*", value)
        if m:
            try:
                return float(value)
            except ValueError:
                return None
    return None




_RECORD_DEFENSE_KEYS = (
    "deterministicdefense",
    "recordconfidence",
    "sensorconfidence",
    "measurementconfidence",
    "reliability",
    "confidence",
    "certainty",
    "qualityscore",
)


def _as_strength(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, str):
        raw = value.strip()
        pct = raw.endswith("%")
        if pct:
            raw = raw[:-1].strip()
        try:
            number = float(raw)
        except ValueError:
            return None
        if pct or 1.0 < number <= 100.0:
            number /= 100.0
    elif isinstance(value, (int, float)):
        number = float(value)
        if 1.0 < number <= 100.0:
            number /= 100.0
    else:
        return None
    if math.isfinite(number) and 0.0 <= number <= 1.0:
        return number
    return None


def _record_defense_from_mapping(value: Mapping[str, Any]) -> float:
    candidates: list[float] = []
    for key, child in value.items():
        if _norm_key(str(key)) in _RECORD_DEFENSE_KEYS:
            strength = _as_strength(child)
            if strength is not None:
                candidates.append(strength)
    # Conservative when multiple quality indicators disagree: the weakest defense wins.
    return min(candidates) if candidates else 1.0


_TEXT_DEFENSE_RE = re.compile(
    r"\b(?:sensor\s+confidence|measurement\s+confidence|record\s+confidence|confidence|reliability|certainty)\b"
    r"\s*(?::|=|is)?\s*(?P<value>\d+(?:\.\d+)?)\s*(?P<pct>%)?",
    re.IGNORECASE,
)


def _record_defense_from_text(text: str) -> float | None:
    candidates: list[float] = []
    for m in _TEXT_DEFENSE_RE.finditer(text):
        raw = m.group("value") + ("%" if m.group("pct") else "")
        strength = _as_strength(raw)
        if strength is not None:
            candidates.append(strength)
    reverse = re.compile(
        r"(?P<value>\d+(?:\.\d+)?)\s*(?P<pct>%)?\s*"
        r"(?:sensor\s+confidence|measurement\s+confidence|record\s+confidence|confidence|reliability|certainty)\b",
        re.IGNORECASE,
    )
    for m in reverse.finditer(text):
        raw = m.group("value") + ("%" if m.group("pct") else "")
        strength = _as_strength(raw)
        if strength is not None:
            candidates.append(strength)
    return min(candidates) if candidates else None

def _concept_from_label(label: str, registry: MeaningRegistry, object_id: str, path: str) -> str | None:
    resolved = registry.resolve_text(label, object_id=object_id, path=path)
    if len(resolved) == 1:
        return resolved[0].concept_key
    return None


def _extract_record_facts_from_mapping(
    value: Any,
    *,
    object_id: str,
    registry: MeaningRegistry,
    path: str = "$",
) -> list[SemanticFact]:
    out: list[SemanticFact] = []
    if isinstance(value, dict):
        label_parts = [str(value[k]) for k in _LABEL_KEYS if k in value and isinstance(value[k], str)]
        label = " | ".join(label_parts)
        label_concept = _concept_from_label(label, registry, object_id, path) if label else None
        local_defense = _record_defense_from_mapping(value)
        for key, child in value.items():
            nkey = _norm_key(str(key))
            child_path = f"{path}.{key}"
            if nkey in _RECORD_KEY_DIMENSIONS:
                number = _as_number(child)
                if number is not None:
                    dimension, unit = _RECORD_KEY_DIMENSIONS[nkey]
                    out.append(
                        SemanticFact(
                            fact_id=f"{object_id}:record:{child_path}",
                            source_object_id=object_id,
                            source_kind="record",
                            dimension=dimension,
                            operator="eq",
                            value=number,
                            unit=unit,
                            confidence=local_defense,
                            tolerance_abs=0.0,
                            concept_key=label_concept,
                            phrase=label or str(key),
                            path=child_path,
                            note=(f"Explicit structured numeric field '{key}'. "
                                  f"Deterministic defense R_D={local_defense:.3f}."),
                        )
                    )
            out.extend(_extract_record_facts_from_mapping(child, object_id=object_id, registry=registry, path=child_path))
    elif isinstance(value, (list, tuple)):
        for idx, child in enumerate(value):
            out.extend(_extract_record_facts_from_mapping(child, object_id=object_id, registry=registry, path=f"{path}[{idx}]"))
    return out


_TEXT_RECORD_RE = re.compile(
    r"(?P<label>(?:baker(?:['’]s|s)?\s+dozen|half[-\s]?dozen|dozen|pair)[^\n]{0,80}?)?"
    r"\b(?P<key>qty|quantity|count|total\s+items?|item\s+count|unit\s+count|units?)\b\s*(?::|=)?\s*(?P<value>[-+]?\d+(?:\.\d+)?)\b",
    re.IGNORECASE,
)

_TTL_QUANTITY_RE = re.compile(
    r"(?:[A-Za-z_][\w.-]*:)?(?P<key>qty|quantity|count|totalItems|itemCount|unitCount|units)\b\s+(?P<value>[-+]?\d+(?:\.\d+)?)\b",
    re.IGNORECASE,
)


def _extract_record_facts_from_text(text: str, *, object_id: str, registry: MeaningRegistry, path: str = "$") -> list[SemanticFact]:
    out: list[SemanticFact] = []
    for idx, m in enumerate(_TEXT_RECORD_RE.finditer(text), 1):
        value = float(m.group("value"))
        label = (m.group("label") or "").strip()
        context_start = text.rfind("\n", 0, m.start()) + 1
        context_end = text.find("\n", m.end())
        if context_end < 0:
            context_end = len(text)
        context = text[context_start:context_end].strip()
        concept = _concept_from_label(label or context, registry, object_id, path)
        local_defense = _record_defense_from_text(context) or 1.0
        out.append(
            SemanticFact(
                fact_id=f"{object_id}:text-record:{m.start()}:{m.end()}",
                source_object_id=object_id,
                source_kind="record",
                dimension="count",
                operator="eq",
                value=value,
                unit="count",
                confidence=local_defense,
                tolerance_abs=0.0,
                concept_key=concept,
                phrase=context or m.group(0),
                path=path,
                note=(f"Explicit text record field '{m.group('key')}'. "
                      f"Deterministic defense R_D={local_defense:.3f}."),
            )
        )
    # Turtle frequently expresses an unquoted numeric object after a predicate.
    for m in _TTL_QUANTITY_RE.finditer(text):
        span_id = f"{object_id}:ttl-record:{m.start()}:{m.end()}"
        if any(f.fact_id == span_id for f in out):
            continue
        out.append(
            SemanticFact(
                fact_id=span_id,
                source_object_id=object_id,
                source_kind="record",
                dimension="count",
                operator="eq",
                value=float(m.group("value")),
                unit="count",
                confidence=1.0,
                tolerance_abs=0.0,
                concept_key=None,
                phrase=m.group(0),
                path=path,
                note=f"Explicit Turtle-like numeric predicate '{m.group('key')}'.",
            )
        )
    global_defense = _record_defense_from_text(text)
    if global_defense is not None and len(out) == 1 and abs(out[0].confidence - 1.0) < 1e-12:
        from dataclasses import replace
        out[0] = replace(
            out[0],
            confidence=global_defense,
            note=out[0].note + f" Global deterministic defense R_D={global_defense:.3f}.",
        )
    return out


def _local_name(uri: str) -> str:
    return re.split(r"[#/:]", uri)[-1]


def _extract_rdf_record_fact(obj: VinculumObject, registry: MeaningRegistry, defense_by_subject: Mapping[str, float] | None = None) -> list[SemanticFact]:
    if obj.object_type is not ObjectType.RDF_TRIPLE:
        return []
    predicate = str(obj.metadata.get("predicate", ""))
    local = _norm_key(_local_name(predicate))
    if local not in _RECORD_KEY_DIMENSIONS:
        return []
    number = _as_number(obj.metadata.get("object"))
    if number is None:
        return []
    dimension, unit = _RECORD_KEY_DIMENSIONS[local]
    subject = str(obj.metadata.get("subject", ""))
    defense = (defense_by_subject or {}).get(subject, 1.0)
    return [
        SemanticFact(
            fact_id=f"{obj.object_id}:rdf-record",
            source_object_id=obj.object_id,
            source_kind="record",
            dimension=dimension,
            operator="eq",
            value=number,
            unit=unit,
            confidence=defense,
            tolerance_abs=0.0,
            concept_key=None,
            phrase=str(obj.content),
            path="rdf",
            note=(f"Numeric RDF object on predicate '{_local_name(predicate)}'. "
                  f"Deterministic defense R_D={defense:.3f}."),
        )
    ]


def collect_semantic_and_record_facts(obj: VinculumObject, registry: MeaningRegistry) -> tuple[tuple[SemanticFact, ...], tuple[SemanticFact, ...]]:
    semantic: list[SemanticFact] = []
    records: list[SemanticFact] = []
    rdf_defense_by_subject: dict[str, float] = {}

    def collect_rdf_defense(node: VinculumObject) -> None:
        if node.object_type is ObjectType.RDF_TRIPLE:
            predicate = str(node.metadata.get("predicate", ""))
            local = _norm_key(_local_name(predicate))
            if local in _RECORD_DEFENSE_KEYS:
                strength = _as_strength(node.metadata.get("object"))
                subject = str(node.metadata.get("subject", ""))
                if strength is not None and subject:
                    prior = rdf_defense_by_subject.get(subject, 1.0)
                    rdf_defense_by_subject[subject] = min(prior, strength)
        for child in node.children:
            collect_rdf_defense(child)

    collect_rdf_defense(obj)
    seen_sem: set[tuple[str, str, float, str]] = set()
    seen_rec: set[tuple[str, str, float, str]] = set()

    def add_sem(facts: Iterable[SemanticFact]) -> None:
        for f in facts:
            key = (f.concept_key or f.source_object_id, f.dimension, f.value, f.unit or "")
            if key not in seen_sem:
                seen_sem.add(key)
                semantic.append(f)

    def add_rec(facts: Iterable[SemanticFact]) -> None:
        for f in facts:
            key = (f.source_object_id, f.dimension, f.value, f.path)
            if key not in seen_rec:
                seen_rec.add(key)
                records.append(f)

    def walk(node: VinculumObject, path: str) -> None:
        if isinstance(node.content, str):
            add_sem(registry.resolve_text(node.content, object_id=node.object_id, path=path))
            if node.object_type is not ObjectType.TTL_GRAPH:
                add_rec(_extract_record_facts_from_text(node.content, object_id=node.object_id, registry=registry, path=path))
        elif isinstance(node.content, (dict, list, tuple)):
            add_rec(_extract_record_facts_from_mapping(node.content, object_id=node.object_id, registry=registry, path=path))
            # String values inside structured data can carry canonical semantic labels.
            def strings(v: Any, p: str) -> None:
                if isinstance(v, dict):
                    for k, x in v.items():
                        strings(x, f"{p}.{k}")
                elif isinstance(v, (list, tuple)):
                    for i, x in enumerate(v):
                        strings(x, f"{p}[{i}]")
                elif isinstance(v, str):
                    add_sem(registry.resolve_text(v, object_id=node.object_id, path=p))
            strings(node.content, path)
        add_rec(_extract_rdf_record_fact(node, registry, rdf_defense_by_subject))
        has_content = not (node.content is None or node.content == "" or node.content == {} or node.content == [] or node.content == ())
        # Normal ingesters retain child source material in the parent content, so rescanning
        # children would duplicate the same fact. Turtle is the exception: parsed RDF
        # triples carry predicate/object structure not recoverable from raw-text scanning.
        if node.object_type is ObjectType.TTL_GRAPH or not has_content:
            for idx, child in enumerate(node.children):
                walk(child, f"{path}.children[{idx}]")

    walk(obj, "$")
    semantic.sort(key=lambda f: (f.dimension, f.source_object_id, f.path, f.fact_id))
    records.sort(key=lambda f: (f.dimension, f.source_object_id, f.path, f.fact_id))
    return tuple(semantic), tuple(records)


def _parent_path(path: str) -> str:
    if path in {"", "$", "rdf"}:
        return path
    if "." in path:
        return path.rsplit(".", 1)[0]
    if "[" in path:
        return path.rsplit("[", 1)[0]
    return path


def _alignment_score(sem: SemanticFact, rec: SemanticFact, sem_count: int, rec_count: int) -> float:
    if sem.dimension != rec.dimension:
        return 0.0
    if sem.concept_key and rec.concept_key and sem.concept_key == rec.concept_key:
        return 1.0
    # Same object is not enough: a claim and an unrelated receipt can coexist in one
    # episode. Require a shared local container/path before treating proximity as identity.
    if sem.source_object_id == rec.source_object_id and _parent_path(sem.path) == _parent_path(rec.path):
        return 0.85
    # Conservative singleton fallback: only compare when there is one plausible fact on each side.
    if sem_count == 1 and rec_count == 1:
        return 0.70
    return 0.0


def _satisfies(sem: SemanticFact, record_value: float) -> tuple[bool, float, float, str]:
    delta = record_value - sem.value
    denom = max(abs(sem.value), 1.0)
    norm = min(1.0, abs(delta) / denom)
    tol = sem.tolerance_abs
    op = sem.operator
    if op == "eq":
        ok = abs(delta) <= tol + 1e-12
    elif op == "gt":
        ok = record_value > sem.value
    elif op == "gte":
        ok = record_value >= sem.value
    elif op == "lt":
        ok = record_value < sem.value
    elif op == "lte":
        ok = record_value <= sem.value
    else:
        return False, delta, norm, f"unsupported semantic operator {op!r}"
    rationale = f"record {record_value:g} {'satisfies' if ok else 'violates'} semantic {op} {sem.value:g}"
    return ok, delta, norm, rationale


def reconcile_object(obj: VinculumObject, registry: MeaningRegistry | None = None) -> ReconciliationSummary:
    registry = registry or MeaningRegistry.default()
    semantic, records = collect_semantic_and_record_facts(obj, registry)
    if not semantic and not records:
        return ReconciliationSummary(
            status=ReconciliationStatus.NO_COMPARISON,
            semantic_record_tension=0.0,
            comparison_coverage=0.0,
            max_conflict_strength=0.0,
        )
    if not semantic or not records:
        missing = "record fact" if semantic else "semantic fact"
        return ReconciliationSummary(
            status=ReconciliationStatus.UNRESOLVED,
            semantic_record_tension=0.0,
            comparison_coverage=0.0,
            max_conflict_strength=0.0,
            semantic_determinization_strength=(sum(f.confidence for f in semantic) / len(semantic)) if semantic else None,
            deterministic_defense_strength=(sum(f.confidence for f in records) / len(records)) if records else None,
            probabilistic_contamination=(1.0 - (sum(f.confidence for f in records) / len(records))) if records else None,
            semantic_facts=semantic,
            record_facts=records,
            comparisons=(),
            unresolved=(f"no comparable {missing} found",),
        )

    comparisons: list[ComparisonResult] = []
    used_records: set[str] = set()
    paired_semantics: set[str] = set()

    for sem in semantic:
        candidates: list[tuple[float, SemanticFact]] = []
        same_dim_sem = sum(1 for x in semantic if x.dimension == sem.dimension)
        same_dim_rec = sum(1 for x in records if x.dimension == sem.dimension)
        for rec in records:
            if rec.fact_id in used_records:
                continue
            score = _alignment_score(sem, rec, same_dim_sem, same_dim_rec)
            if score > 0:
                candidates.append((score, rec))
        if not candidates:
            continue
        candidates.sort(key=lambda x: (-x[0], x[1].fact_id))
        alignment, rec = candidates[0]
        ok, delta, norm, rationale = _satisfies(sem, rec.value)
        # Exact semantic mismatches are categorical conflicts; magnitude is still retained as normalized_delta.
        if ok:
            raw_conflict = 0.0
            conflict = 0.0
            status = "MATCH"
        else:
            base = 1.0 if sem.operator == "eq" and sem.tolerance_abs == 0 else max(0.25, norm)
            raw_conflict = max(0.0, min(1.0, base * alignment))
            conflict = max(0.0, min(1.0, raw_conflict * sem.confidence * rec.confidence))
            status = "CONFLICT"
        comparisons.append(
            ComparisonResult(
                semantic_fact_id=sem.fact_id,
                record_fact_id=rec.fact_id,
                dimension=sem.dimension,
                semantic_value=sem.value,
                record_value=rec.value,
                operator=sem.operator,
                unit=sem.unit or rec.unit,
                status=status,
                aligned=ok,
                delta=delta,
                normalized_delta=norm,
                alignment_score=alignment,
                semantic_determinization_strength=sem.confidence,
                deterministic_defense_strength=rec.confidence,
                probabilistic_contamination=1.0 - rec.confidence,
                raw_conflict_strength=raw_conflict,
                conflict_strength=conflict,
                rationale=rationale,
            )
        )
        used_records.add(rec.fact_id)
        paired_semantics.add(sem.fact_id)

    if not comparisons:
        return ReconciliationSummary(
            status=ReconciliationStatus.UNRESOLVED,
            semantic_record_tension=0.0,
            comparison_coverage=0.0,
            max_conflict_strength=0.0,
            semantic_determinization_strength=sum(f.confidence for f in semantic) / len(semantic),
            deterministic_defense_strength=sum(f.confidence for f in records) / len(records),
            probabilistic_contamination=1.0 - (sum(f.confidence for f in records) / len(records)),
            semantic_facts=semantic,
            record_facts=records,
            comparisons=(),
            unresolved=("semantic and record facts were present but could not be aligned safely",),
        )

    conflicts = [c for c in comparisons if c.status == "CONFLICT"]
    matches = [c for c in comparisons if c.status == "MATCH"]
    if conflicts and matches:
        status = ReconciliationStatus.MIXED
    elif conflicts:
        status = ReconciliationStatus.CONFLICT
    else:
        status = ReconciliationStatus.ALIGNED

    tension = sum(c.conflict_strength for c in comparisons) / max(len(comparisons), 1)
    max_conflict = max((c.conflict_strength for c in comparisons), default=0.0)
    comparable_semantic = len({f.fact_id for f in semantic if any(r.dimension == f.dimension for r in records)})
    coverage = len(paired_semantics) / max(comparable_semantic, 1)
    unresolved: list[str] = []
    unpaired = comparable_semantic - len(paired_semantics)
    if unpaired > 0:
        unresolved.append(f"{unpaired} comparable semantic facts were not safely paired")

    semantic_strength = sum(c.semantic_determinization_strength for c in comparisons) / len(comparisons)
    record_defense = sum(c.deterministic_defense_strength for c in comparisons) / len(comparisons)
    return ReconciliationSummary(
        status=status,
        semantic_record_tension=max(0.0, min(1.0, tension)),
        comparison_coverage=max(0.0, min(1.0, coverage)),
        max_conflict_strength=max(0.0, min(1.0, max_conflict)),
        semantic_determinization_strength=max(0.0, min(1.0, semantic_strength)),
        deterministic_defense_strength=max(0.0, min(1.0, record_defense)),
        probabilistic_contamination=max(0.0, min(1.0, 1.0 - record_defense)),
        semantic_facts=semantic,
        record_facts=records,
        comparisons=tuple(comparisons),
        unresolved=tuple(unresolved),
    )
