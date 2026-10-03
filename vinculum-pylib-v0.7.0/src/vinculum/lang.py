"""Bounded phrase/constraint resolution. No claim to unrestricted language understanding."""
from __future__ import annotations
from dataclasses import dataclass
import re
from typing import Any
from .core import (NumericRange, PDProfile, Representation, Scope, Side, SupportFactor, SupportProfile)
from .utils import identifier, unit_score


@dataclass(frozen=True)
class NumericMeaningRule:
    id: str
    pattern: str
    concept: str
    unit: str
    quantity: NumericRange
    basis: str
    semantic_strength: float | None = None

    def __post_init__(self):
        for k in ('id', 'pattern', 'concept', 'unit', 'basis'):
            identifier(getattr(self, k), k)
        re.compile(self.pattern)
        object.__setattr__(self, 'semantic_strength', unit_score(self.semantic_strength, 'semantic strength'))


@dataclass(frozen=True)
class Resolution:
    status: str
    quantity: NumericRange | None
    concept: str | None
    unit: str | None
    rule_id: str | None
    basis: str
    semantic_strength: float | None
    alternatives: tuple[str, ...] = ()


class SemanticRegistry:
    """Rules full-match a segment. Ambiguous matches never silently select a winner.

    Caller-authored regex rules are trusted configuration. Domain phrases such as
    'airspace clear' require an explicitly supplied numeric concept and scope.
    """
    def __init__(self, rules=()):
        self._rules = []
        for rule in rules:
            self.register(rule)

    def register(self, rule: NumericMeaningRule):
        if not isinstance(rule, NumericMeaningRule) or any(r.id == rule.id for r in self._rules):
            raise ValueError('invalid or duplicate semantic rule')
        self._rules.append(rule)
        return self

    @classmethod
    def default(cls):
        return cls([
            NumericMeaningRule('bakers-dozen-v1', r"(?:the order is (?:a )?)?baker['’]s dozen", 'item_count', 'count',
                               NumericRange.point(13), 'explicit starter lexicon: baker’s dozen = thirteen', 1.0),
            NumericMeaningRule('dozen-v1', r'(?:a )?dozen', 'item_count', 'count', NumericRange.point(12),
                               'explicit starter lexicon: dozen = twelve', 1.0),
            NumericMeaningRule('half-dozen-v1', r'(?:a )?half[- ]dozen', 'item_count', 'count', NumericRange.point(6),
                               'explicit starter lexicon: half-dozen = six', 1.0),
            NumericMeaningRule('pair-v1', r'(?:a )?pair', 'item_count', 'count', NumericRange.point(2),
                               'explicit starter count sense of pair; caller supplies item scope', 1.0),
            NumericMeaningRule('majority-v1', r'(?:a )?majority', 'share', '%', NumericRange.constraint('gt', 50),
                               'strict majority of the explicitly scoped denominator', 1.0),
        ])

    def resolve(self, text: str, *, concept: str | None = None) -> Resolution:
        if not isinstance(text, str) or len(text) > 100000:
            raise ValueError('segment must be a string of at most 100,000 characters')
        segment = text.strip().rstrip('.!?').strip()
        matches = [r for r in self._rules if re.fullmatch(r.pattern, segment, re.IGNORECASE)]
        if concept is not None:
            matches = [r for r in matches if r.concept == concept]
        if len(matches) > 1:
            return Resolution('UNRESOLVED', None, concept, None, None, 'ambiguous registered meanings', None,
                              tuple(r.id for r in matches))
        if matches:
            r = matches[0]
            return Resolution('RESOLVED', r.quantity, r.concept, r.unit, r.id, r.basis, r.semantic_strength)
        # One intentionally narrow compositional grammar; bounds require a named concept.
        within = re.fullmatch(r'within\s+(\d+(?:\.\d+)?)\s+(seconds?|minutes?|hours?|days?)', segment, re.I)
        if within and concept:
            unit = {'second': 's', 'minute': 'min', 'hour': 'h', 'day': 'day'}[within[2].lower().rstrip('s')]
            return Resolution('RESOLVED', NumericRange(0, within[1]), concept, unit, 'within-duration-v1',
                              'elapsed duration from a caller-defined origin, nonnegative and at most the bound', 1.0)
        return Resolution('UNRESOLVED', None, concept, None, None,
                          'no unambiguous registered numeric meaning; qualifiers and negation are not discarded', None)

    def representation(self, text: str, *, id: str, entity: str, scope: Scope,
                       order: int = 1, concept: str | None = None, source_ids=(), pd=None) -> Representation:
        r = self.resolve(text, concept=concept)
        support = SupportProfile((SupportFactor('semantic_mapping', r.semantic_strength, r.basis,
                                               source_id=r.rule_id, kind='declared'),))
        return Representation(id, Side.LANGUAGE, order, entity, r.concept, r.quantity, r.unit, scope, text,
                              pd or PDProfile(), support, tuple(source_ids), definition_id=r.rule_id)

    def document(self, text: str, *, id: str, entity: str, scope: Scope, concept: str | None = None):
        """Segment a document without guessing reference resolution or dropping unknown clauses."""
        segments = [s.strip() for s in re.split(r'(?<=[.!?])\s+|\n+', text) if s.strip()]
        return tuple(self.representation(s, id=f'{id}:clause:{i}', entity=entity, scope=scope,
                                         concept=concept, source_ids=(id,)) for i, s in enumerate(segments, 1))


def measurement(*, id: str, entity: str, concept: str, value: Any = None, interval: NumericRange | None = None,
                unit: str, scope: Scope, order: int = 1, defense: float | None = None,
                defense_basis: str = 'numeric defense not assessed', source_ids=(), pd: PDProfile | None = None,
                depends_on=(), method=None) -> Representation:
    """Numeric adapter: missing defense remains missing, never an implicit 1.0."""
    if value is not None and interval is not None:
        raise ValueError('supply a value or interval, not both')
    quantity = interval if interval is not None else (None if value is None else NumericRange.point(value))
    return Representation(id, Side.MATHEMATICS, order, entity, concept, quantity, unit, scope,
                          text='' if value is None else str(value), pd=pd or PDProfile(),
                          support=SupportProfile((SupportFactor('numeric_defense', defense, defense_basis,
                                                                 source_id=source_ids[0] if source_ids else None),)),
                          source_ids=tuple(source_ids), depends_on=tuple(depends_on), method=method)
