from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Pattern


@dataclass(frozen=True)
class SignalRule:
    id: str
    channel: str
    label: str
    pattern: Pattern[str]
    weight: float
    max_count: int = 5
    note: str = ""


def _r(rule_id: str, channel: str, label: str, pattern: str, weight: float, max_count: int = 5, note: str = "") -> SignalRule:
    return SignalRule(rule_id, channel, label, re.compile(pattern, re.IGNORECASE | re.MULTILINE), weight, max_count, note)


LANGUAGE_RULES: tuple[SignalRule, ...] = (
    _r("P_HEDGE", "P", "Hedge / modal uncertainty", r"\b(?:may|might|could|possibly|perhaps|maybe)\b", 0.55),
    _r("P_LIKELIHOOD", "P", "Likelihood language", r"\b(?:likely|unlikely|probably|probable|plausible|chance|odds)\b", 0.70),
    _r("P_APPEARANCE", "P", "Appearance / inference language", r"\b(?:appears?|seems?|suggests?|indicates?|implies?)\b", 0.55),
    _r("P_APPROX", "P", "Approximation language", r"\b(?:about|around|roughly|approximately|estimated|estimate)\b|[≈~]", 0.75),
    _r("P_ASSUMPTION", "P", "Assumption marker", r"\b(?:assume|assumes|assumed|assuming|assumption|presumably)\b", 0.70),
    _r("P_UNCERTAIN", "P", "Explicit uncertainty / ambiguity", r"\b(?:uncertain|uncertainty|unknown|unclear|ambiguous|indeterminate|unresolved)\b", 0.90),
    _r("P_GENERALIZER", "P", "Generalization / frequency qualifier", r"\b(?:generally|typically|often|sometimes|usually|commonly|mostly)\b", 0.45),
    _r("P_OPINION", "P", "Belief / opinion marker", r"\b(?:believe|belief|think|opinion|view|judgment)\b", 0.50),
    _r("D_DEFINITION", "D", "Explicit definition", r"\b(?:is defined as|defined as|shall mean|means|definition:)\b", 1.15),
    _r("D_MANDATE", "D", "Normative constraint", r"\b(?:must|shall|required to|prohibited|may not|will not)\b", 0.85),
    _r("D_BOUND", "D", "Quantified bound", r"\b(?:at least|at most|no more than|no less than|exactly|within|between)\b[^\n.;]{0,50}\b\d+(?:\.\d+)?\b", 1.10),
    _r("D_IDENTIFIER", "D", "Stable identifier / URI / hash", r"https?://\S+|urn:[^\s]+|\b(?:[A-Z]{2,}[A-Z0-9]*[-_]\d+[A-Z0-9_-]*|[A-Z]{2,}\d{2,}[A-Z0-9_-]*)\b|\b[a-f0-9]{32,64}\b", 0.75),
    _r("D_ISO_DATE", "D", "Explicit date/time", r"\b\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2}(?::\d{2})?)?\b", 0.70),
    _r("D_NUMBER_UNIT", "D", "Quantified value with unit", r"\b\d+(?:\.\d+)?\s?(?:%|ms|s|sec|seconds?|min|minutes?|hours?|days?|mm|cm|m|meters?|km|kilometers?|in|inches?|ft|feet|kg|g|lb|lbs|GB|MB|TB|Hz|kHz|MHz|GHz)\b", 0.75),
    _r("D_LOGIC", "D", "Formal logical relation", r"(?:⇔|⇒|∀|∃|∧|∨|¬|\bif and only if\b|\biff\b)", 1.00),
    _r("D_RELATION", "D", "Explicit relationship/operator", r"(?:->|→|<-|←|=>|:=|\bsubject\b.+\bpredicate\b.+\bobject\b)", 0.65),
    _r("D_SEMANTIC", "D", "RDF/SKOS/OWL semantic anchor", r"\b(?:rdf|rdfs|skos|owl|shacl):[A-Za-z_][\w-]*", 1.00),
    _r("D_CITATION", "D", "Citation / evidence anchor", r"\[[0-9]{1,3}\]|\bdoi:\s*10\.\d{4,9}/\S+|\bsource:\s*\S+", 0.55),
)


MATH_RULES: tuple[SignalRule, ...] = (
    _r("D_EQUALITY", "D", "Exact equality", r"(?<![<>!≈~])=(?!=)", 1.25, 8),
    _r("D_INEQUALITY", "D", "Exact inequality/bound", r"(?:<=|>=|≤|≥|(?<![<>=])<(?![=>])|(?<![<>=])>(?![=>]))", 0.80, 8),
    _r("D_ARITH", "D", "Arithmetic structure", r"(?:\d|[A-Za-z])\s*(?:\+|-|\*|/|×|÷|\^|\*\*)\s*(?:\d|[A-Za-z])", 0.65, 8),
    _r("D_FUNCTION", "D", "Formal function / operator", r"\b(?:sin|cos|tan|log|ln|sqrt|sum|mean|median|min|max)\s*\(|[∑∫√]", 0.70, 6),
    _r("D_RATIO", "D", "Exact ratio / fraction", r"\b\d+\s*/\s*\d+\b", 0.55, 6),
    _r("D_UNIT", "D", "Explicit unit", r"\b\d+(?:\.\d+)?\s?(?:mm|cm|m|km|in|ft|kg|g|lb|ms|s|Hz|kHz|MHz|GHz|%)\b", 0.55, 6),
    _r("P_APPROX", "P", "Approximate equality", r"(?:≈|≃|≅|(?<!\w)~(?!=))", 1.10, 8),
    _r("P_PLUS_MINUS", "P", "Measurement uncertainty", r"±|\+/-", 1.15, 6),
    _r("P_CONFIDENCE", "P", "Confidence / probability", r"\b(?:confidence|probability|probable|likelihood|p\s*=|Pr\s*\(|P\s*\()", 0.90, 6),
    _r("P_DISTRIBUTION", "P", "Stochastic / distribution construct", r"\b(?:random|stochastic|distribution|normal|gaussian|poisson|variance|standard deviation|std\.?)\b", 0.75, 6),
    _r("P_ESTIMATE", "P", "Estimate / expected value", r"\b(?:estimate|estimated|expected|approximately|approximation|error margin|uncertainty)\b", 0.80, 6),
)


@dataclass(frozen=True)
class ScoringConfig:
    language_baseline_p: float = 0.45
    language_baseline_d: float = 0.15
    math_baseline_p: float = 0.05
    math_baseline_d: float = 0.65
    structured_baseline_p: float = 0.15
    structured_baseline_d: float = 0.45
    ttl_baseline_p: float = 0.05
    ttl_baseline_d: float = 0.75
    signal_scale: float = 3.0
    boundary_low: float = 40.0
    boundary_high: float = 60.0
    minimum_coverage: float = 0.15
    aggregate_parent_overlay_weight: float = 0.0
    ttl_graph_overlay_weight: float = 2.0
