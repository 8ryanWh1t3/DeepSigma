from __future__ import annotations

import json
from math import exp
import re
from typing import Any, Iterable

from rdflib import BNode, Literal, URIRef
from rdflib.namespace import OWL, RDF, RDFS, SKOS

from .config import LANGUAGE_RULES, MATH_RULES, ScoringConfig, SignalRule
from .formulas import clamp01
from .models import ScoreMode, Signal, VinculumObject




_RELIABILITY_RE = re.compile(
    r"\b(?:sensor\s+confidence|measurement\s+confidence|record\s+confidence|confidence|reliability|certainty)\b"
    r"\s*(?::|=|is)?\s*(?P<value>\d+(?:\.\d+)?)\s*(?P<pct>%)?",
    re.IGNORECASE,
)


def _normalize_reliability(value: float, percent_mark: bool = False) -> float | None:
    value = float(value)
    if percent_mark or 1.0 < value <= 100.0:
        value /= 100.0
    if 0.0 <= value <= 1.0:
        return value
    return None


def _explicit_reliability(text: str) -> float | None:
    values: list[float] = []
    for m in _RELIABILITY_RE.finditer(text):
        v = _normalize_reliability(float(m.group("value")), bool(m.group("pct")))
        if v is not None:
            values.append(v)
    # Natural prose commonly places the number before the qualifier: "80% confidence".
    reverse = re.compile(
        r"(?P<value>\d+(?:\.\d+)?)\s*(?P<pct>%)?\s*"
        r"(?:sensor\s+confidence|measurement\s+confidence|record\s+confidence|confidence|reliability|certainty)\b",
        re.IGNORECASE,
    )
    for m in reverse.finditer(text):
        v = _normalize_reliability(float(m.group("value")), bool(m.group("pct")))
        if v is not None:
            values.append(v)
    return min(values) if values else None


def _saturate(baseline: float, evidence: float, scale: float) -> float:
    if evidence <= 0:
        return clamp01(baseline)
    return clamp01(baseline + (1.0 - baseline) * (1.0 - exp(-evidence / max(scale, 1e-9))))


def _match_rules(text: str, rules: Iterable[SignalRule]) -> tuple[float, float, tuple[Signal, ...], tuple[Signal, ...]]:
    p_sum = d_sum = 0.0
    ps: list[Signal] = []
    ds: list[Signal] = []
    for rule in rules:
        matches = list(rule.pattern.finditer(text))
        if not matches:
            continue
        count = min(len(matches), rule.max_count)
        examples = tuple(m.group(0)[:120] for m in matches[:3])
        sig = Signal(rule.id, rule.channel, rule.label, rule.weight, count, examples, rule.note)
        if rule.channel == "P":
            p_sum += sig.contribution
            ps.append(sig)
        else:
            d_sum += sig.contribution
            ds.append(sig)
    ps.sort(key=lambda s: (-s.contribution, s.id))
    ds.sort(key=lambda s: (-s.contribution, s.id))
    return p_sum, d_sum, tuple(ps), tuple(ds)


def score_language(text: str, config: ScoringConfig) -> tuple[float, float, float, tuple[Signal, ...], tuple[Signal, ...], tuple[str, ...], dict[str, Any]]:
    stripped = text.strip()
    if not stripped:
        return 0.0, 0.0, 0.0, (), (), ("empty language object",), {}
    p_sum, d_sum, ps, ds = _match_rules(stripped, LANGUAGE_RULES)
    P = _saturate(config.language_baseline_p, p_sum, config.signal_scale)
    D = _saturate(config.language_baseline_d, d_sum, config.signal_scale)
    meta = {"characters": len(stripped), "tokens": len(re.findall(r"\S+", stripped)), "signal_P": p_sum, "signal_D": d_sum}
    return P, D, 1.0, ps, ds, (), meta


def score_math(text: str, config: ScoringConfig) -> tuple[float, float, float, tuple[Signal, ...], tuple[Signal, ...], tuple[str, ...], dict[str, Any]]:
    stripped = text.strip()
    if not stripped:
        return 0.0, 0.0, 0.0, (), (), ("empty math object",), {}
    p_sum, d_sum, ps, ds = _match_rules(stripped, MATH_RULES)
    math_markers = len(re.findall(r"[=<>≤≥+*/^∑∫√≈±]|\b\d+(?:\.\d+)?\b", stripped))
    coverage = min(1.0, math_markers / 3.0) if math_markers else 0.10
    P = _saturate(config.math_baseline_p, p_sum, config.signal_scale)
    D_base = config.math_baseline_d if math_markers else 0.10
    D_raw = _saturate(D_base, d_sum, config.signal_scale)

    # Second-order math model: probabilistic features do not merely add P; they
    # weaken the numeric side's defense of determinism. Explicit confidence /
    # reliability wins when present. Otherwise uncertainty signals derive U_D.
    explicit_reliability = _explicit_reliability(stripped)
    if explicit_reliability is not None:
        defense = explicit_reliability
        defense_source = "explicit"
    else:
        contamination = 1.0 - exp(-p_sum / max(config.math_uncertainty_scale, 1e-9)) if p_sum > 0 else 0.0
        defense = 1.0 - contamination
        defense_source = "derived_from_math_uncertainty_signals"
    defense = clamp01(defense)
    contamination = 1.0 - defense
    D = clamp01(D_raw * defense)

    unresolved = () if math_markers else ("no formal mathematical structure detected",)
    meta = {
        "characters": len(stripped),
        "math_markers": math_markers,
        "signal_P": p_sum,
        "signal_D": d_sum,
        "raw_deterministic_strength": D_raw,
        "deterministic_defense_strength": defense,
        "probabilistic_contamination": contamination,
        "deterministic_defense_source": defense_source,
    }
    return P, D, coverage, ps, ds, unresolved, meta


def score_structured(content: Any, config: ScoringConfig) -> tuple[float, float, float, tuple[Signal, ...], tuple[Signal, ...], tuple[str, ...], dict[str, Any]]:
    if content is None:
        return 0.0, 0.0, 0.0, (), (), ("null structured object",), {}
    values: list[Any] = []
    nulls = 0
    scalars = 0
    numeric = 0
    strings = 0

    def walk(v: Any) -> None:
        nonlocal nulls, scalars, numeric, strings
        if isinstance(v, dict):
            for k in sorted(v):
                walk(v[k])
        elif isinstance(v, (list, tuple)):
            for x in v:
                walk(x)
        else:
            values.append(v)
            scalars += 1
            if v is None:
                nulls += 1
            elif isinstance(v, (int, float)) and not isinstance(v, bool):
                numeric += 1
            elif isinstance(v, str):
                strings += 1

    walk(content)
    if scalars == 0:
        return 0.0, 0.0, 0.0, (), (), ("structured object has no scalar values",), {}
    p_e = (nulls / scalars) * 2.0
    d_e = (numeric / scalars) * 1.5 + (1.0 - nulls / scalars) * 1.0
    P = _saturate(config.structured_baseline_p, p_e, config.signal_scale)
    D = _saturate(config.structured_baseline_d, d_e, config.signal_scale)
    ps = () if nulls == 0 else (Signal("P_NULLS", "P", "Missing/null structured values", 1.0, nulls, (), "Nulls increase unresolved pressure."),)
    ds_list: list[Signal] = [Signal("D_SCHEMA", "D", "Typed structured fields", 0.5, max(1, scalars - nulls), (), "Explicit typed structure increases determinism.")]
    if numeric:
        ds_list.append(Signal("D_NUMERIC", "D", "Numeric values", 0.5, numeric))
    coverage = 1.0 - (nulls / scalars)
    meta = {"scalar_count": scalars, "null_count": nulls, "numeric_count": numeric, "string_count": strings}
    unresolved = (f"{nulls} null values",) if nulls else ()
    return P, D, coverage, ps, tuple(ds_list), unresolved, meta


def score_ttl_triple(obj: VinculumObject, config: ScoringConfig) -> tuple[float, float, float, tuple[Signal, ...], tuple[Signal, ...], tuple[str, ...], dict[str, Any]]:
    m = dict(obj.metadata)
    s_kind = m.get("subject_kind", "")
    p_kind = m.get("predicate_kind", "")
    o_kind = m.get("object_kind", "")
    datatype = m.get("datatype")
    lang = m.get("language")
    predicate = m.get("predicate", "")
    P = config.ttl_baseline_p
    D = config.ttl_baseline_d
    ps: list[Signal] = []
    ds: list[Signal] = []

    if s_kind == "URIRef":
        ds.append(Signal("D_URI_SUBJECT", "D", "IRI subject", 0.25, 1))
        D += 0.06
    elif s_kind == "BNode":
        ps.append(Signal("P_BNODE_SUBJECT", "P", "Blank-node subject", 0.35, 1, (), "Blank nodes reduce stable identity."))
        P += 0.14

    if p_kind == "URIRef":
        ds.append(Signal("D_URI_PREDICATE", "D", "IRI predicate", 0.35, 1))
        D += 0.08

    if o_kind == "URIRef":
        ds.append(Signal("D_URI_OBJECT", "D", "IRI object", 0.25, 1))
        D += 0.06
    elif o_kind == "BNode":
        ps.append(Signal("P_BNODE_OBJECT", "P", "Blank-node object", 0.30, 1))
        P += 0.12
    elif o_kind == "Literal":
        if datatype:
            ds.append(Signal("D_TYPED_LITERAL", "D", "Typed literal", 0.30, 1))
            D += 0.08
        else:
            ps.append(Signal("P_PLAIN_LITERAL", "P", "Untyped natural-language literal", 0.20, 1))
            P += 0.07
        if lang:
            ps.append(Signal("P_LANG_LITERAL", "P", "Language-tagged literal", 0.15, 1))
            P += 0.04

    if any(ns in str(predicate) for ns in (str(RDF), str(RDFS), str(OWL), str(SKOS))):
        ds.append(Signal("D_VOCAB_PREDICATE", "D", "Standard semantic vocabulary predicate", 0.30, 1))
        D += 0.07

    return clamp01(P), clamp01(D), 1.0, tuple(ps), tuple(ds), (), {"subject_kind": s_kind, "predicate_kind": p_kind, "object_kind": o_kind, "datatype": datatype, "language": lang}


def score_ttl_graph(obj: VinculumObject, config: ScoringConfig) -> tuple[float, float, float, tuple[Signal, ...], tuple[Signal, ...], tuple[str, ...], dict[str, Any]]:
    m = dict(obj.metadata)
    parsed = bool(m.get("parsed", False))
    triple_count = int(m.get("triple_count", 0) or 0)
    bnodes = int(m.get("blank_nodes", 0) or 0)
    parse_error = str(m.get("parse_error", "") or "")
    if not parsed:
        ps = (Signal("P_PARSE_FAILURE", "P", "Turtle parse failure", 1.5, 1, (), parse_error),)
        return 0.85, 0.10, 0.35, ps, (), ("TTL graph did not parse cleanly",), {"parse_error": parse_error, "triple_count": triple_count}
    P = config.ttl_baseline_p + min(0.35, (bnodes / max(triple_count, 1)) * 0.35)
    D = config.ttl_baseline_d + min(0.20, triple_count / 1000.0)
    ds = [Signal("D_TTL_PARSE", "D", "Valid Turtle parse", 1.0, 1)]
    if triple_count:
        ds.append(Signal("D_TRIPLE_GRAPH", "D", "Explicit RDF triples", 0.25, min(triple_count, 20)))
    ps: list[Signal] = []
    if bnodes:
        ps.append(Signal("P_BNODES", "P", "Blank-node identity", 0.15, min(bnodes, 20)))
    return clamp01(P), clamp01(D), 1.0, tuple(ps), tuple(ds), (), {"triple_count": triple_count, "blank_nodes": bnodes, "prefix_count": m.get("prefix_count", 0)}


def detect_mode(text: str) -> ScoreMode:
    sample = text.strip()
    if re.search(r"(?:@prefix\s+|\bPREFIX\s+|\brdf:type\b|\b(?:owl|rdfs|skos):[\w-]+)", sample, re.IGNORECASE):
        return ScoreMode.TTL
    math_markers = len(re.findall(r"[=<>≤≥+*/^∑∫√≈±]|\b\d+(?:\.\d+)?\b", sample))
    math_words = bool(re.search(r"\b(?:equation|formula|variance|probability|derivative|integral|matrix)\b", sample, re.IGNORECASE))
    alpha_words = len(re.findall(r"\b[A-Za-z]{3,}\b", sample))
    if math_markers >= 3 and (math_words or math_markers >= max(3, alpha_words // 2)):
        return ScoreMode.MATH
    return ScoreMode.LANGUAGE
