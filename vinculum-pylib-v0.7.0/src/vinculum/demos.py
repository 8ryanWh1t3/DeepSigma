"""Explicitly invoked, synthetic fixtures. Never loaded as operational facts by default."""
from __future__ import annotations
from dataclasses import replace
from .core import (NumericRange, PDProfile, Representation, Scope, Side, SupportFactor, SupportProfile, TimeWindow)
from .context import NarrativeContext
from .codec import Transformation
from .hinge import HingePolicy
from .lang import SemanticRegistry, measurement
from .math import UnitRegistry
from .matrix import ObjectGroup, PairGraph
from .serialization import Scenario


def demonstration_scope(id='SYNTHETIC-TRANSACTION'):
    return Scope(scope_id=id, population='items in this transaction', denominator='one transaction',
                 granularity='transaction', timeless=True, definition_version='demo/v1')


def declared_support(value, name='representation_support', order=2):
    return SupportProfile((SupportFactor(name, value, 'synthetic demonstration coefficient; not an empirical probability',
                                         order=order, kind='assumed'),))


def bakers_dozen(observed=12, defense=.99):
    scope = demonstration_scope('SYNTHETIC-BAKERY-ORDER')
    g = PairGraph('BAKERS-DOZEN-SYNTHETIC')
    l = SemanticRegistry.default().representation("baker's dozen", id='L-order', entity='order-1', scope=scope,
                                                 source_ids=('order-label',), pd=PDProfile(0, 1, 'explicitly defined count sense'))
    m = measurement(id='M-receipt', entity='order-1', concept='item_count', value=observed, unit='count',
                    scope=scope, defense=defense, defense_basis='synthetic fixture; record is not a physical recount',
                    source_ids=('receipt-line',), pd=PDProfile(.1, .9, 'declared mixed representation'))
    g.add_node(l).add_node(m).add_pair(l.id, m.id, id='BAKERY', rationale='same explicitly scoped order line',
                                    alignment_support=1, alignment_basis='fixture identity contract')
    g.add_group(ObjectGroup('claim-1', 'claim', (l.id, m.id)))
    g.add_group(ObjectGroup('episode-1', 'episode', children=('claim-1',)))
    return Scenario(g, HingePolicy(), UnitRegistry.default())


def codec_stress():
    g = PairGraph('SYNTHETIC-CODEC-LIMIT-TEST')
    scope = Scope(scope_id='sector-bravo/demo', population='aircraft in the declared sector',
                  denominator='one declared sector', granularity='sector aggregate', location='synthetic-sector',
                  definition_version='demo/v1', window=TimeWindow('2026-10-02T14:31:30Z', '2026-10-02T14:32:00Z'))
    def add(id, side, order, concept, value, unit='count', text='', p=.1, d=.9, strength=.9, interval=None,
            source='synthetic-source', material=True, deps=()):
        node = Representation(id, side, order, 'SYNTHETIC-SECTOR', concept,
                              interval or NumericRange.point(value), unit, scope, text,
                              PDProfile(p, d, 'synthetic explicit P/D descriptors at this order'),
                              declared_support(strength), (source,), deps, material=material)
        g.add_node(node)
        return id
    add('M1-detections', 'M', 1, 'detected_track_count', 0, text='No tracks were detected in this 30-second window.', strength=.99)
    add('M2-count-interval', 'M', 2, 'detected_track_count', None, interval=NumericRange(0, 1),
        text='Possible count under the declared interval model is between 0 and 1.', p=.8, d=.9, strength=.42)
    add('M3-hit-rate', 'M', 3, 'validation_hit_rate', 72, '%', 'The fixture validation hit rate is 72%.', strength=.9)
    add('M3-trial-count', 'M', 3, 'validation_case_count', 100, text='100 fixture validation cases.', strength=1)
    add('M4-coverage', 'M', 4, 'observed_coverage', 60, '%', 'Sensor coverage was 60%.', strength=.98)
    add('M1-age', 'M', 1, 'record_age', 90, 's', 'Age field is 90 seconds in this fixture.', strength=1)
    add('M5-source-count', 'M', 5, 'independent_source_count', 1, text='Two displays trace to one declared source root.', strength=1)
    add('L1-detections', 'L', 1, 'detected_track_count', 0, text='No tracks were detected.', p=0, d=1, strength=.99, source='generated-summary')
    add('L1-coverage', 'L', 1, 'observed_coverage', 100, '%', 'The entire sector was observed.', p=0, d=1, strength=1, source='generated-summary')
    add('L1-presence', 'L', 1, 'aircraft_present_count', 0, text='No aircraft were present.', p=.1, d=.9, strength=.95, source='generated-summary')
    add('L2-confidence', 'L', 2, 'validation_hit_rate', None, '%', 'At least 95% in the declared validation metric.',
        interval=NumericRange.constraint('ge', 95), strength=.95, source='generated-summary')
    add('L2-coverage-bound', 'L', 2, 'observed_coverage', None, '%', 'At least half the sector was observed.',
        interval=NumericRange.constraint('ge', 50), strength=1, source='generated-summary')
    add('L3-trial-count', 'L', 3, 'validation_case_count', 100, text='The description is supported by 100 cases.', strength=1)
    add('L4-age-limit', 'L', 4, 'record_age', None, 's', 'The snapshot is at most 30 seconds old.',
        interval=NumericRange(0, 30), strength=1)
    add('L5-sources', 'L', 5, 'independent_source_count', 2, text='Two independent sources corroborate this.', strength=1)
    cases = [
        ('zero-preserved', 'L1-detections', 'M1-detections'),
        ('uncertain-count', 'L1-detections', 'M2-count-interval'),
        ('coverage-overclaim', 'L1-coverage', 'M4-coverage'),
        ('unsupported-absence', 'L1-presence', 'M1-detections'),
        ('confidence-overclaim', 'L2-confidence', 'M3-hit-rate'),
        ('qualified-coverage', 'L2-coverage-bound', 'M4-coverage'),
        ('support-case-count', 'L3-trial-count', 'M3-trial-count'),
        ('freshness-claim', 'L4-age-limit', 'M1-age'),
        ('dependence-overclaim', 'L5-sources', 'M5-source-count'),
    ]
    for id, l, m in cases:
        g.add_pair(l, m, id=id, rationale='explicit synthetic test pairing; applicability must be checked',
                   alignment_support=1, alignment_basis='fixture-provided pairing, not learned confidence')
    codec_members = ('M1-detections', 'M4-coverage', 'L1-detections', 'L1-coverage', 'L1-presence')
    g.add_group(ObjectGroup('codec-episode', 'episode', codec_members))
    g.add_group(ObjectGroup('analysis-document', 'document', tuple(g.nodes), children=('codec-episode',)))
    g.add_group(ObjectGroup('corpus', 'corpus', children=('analysis-document',)))
    g.context = NarrativeContext.deep_sigma()
    tx = Transformation('SUMMARY-TRANSFORM', ('M1-detections', 'M4-coverage'),
                        ('L1-detections', 'L1-coverage', 'L1-presence'),
                        'Source: zero detections, 60% coverage. Summary: entire sector observed, no aircraft present.')
    return Scenario(g, HingePolicy(), UnitRegistry.default(), (tx,))


def same_number_different_defense():
    """Two separate, same-scope demonstrations. The value 1 is never scaled to .42."""
    outcomes = []
    for defense in (.99, .42):
        s = bakers_dozen(observed=12, defense=defense)
        outcomes.append(s.evaluate())
    return tuple(outcomes)
