import pytest
from dataclasses import replace
from fractions import Fraction
from vinculum import *
from vinculum.demos import bakers_dozen, demonstration_scope, declared_support
from vinculum.math import compare_ranges
from vinculum.utils import number, number_text

@pytest.mark.parametrize('side', ['L', 'M'])
@pytest.mark.parametrize('order', [1, 2, 3, 4, 5, 6])
def test_each_side_has_both_channels_at_every_order(side, order):
    n = Representation('n', side, order, 'e', 'p', pd=PDProfile(.8, .9, 'declared'))
    assert n.pd.probabilistic == .8 and n.pd.deterministic == .9
    assert n.pd.vector()['assessed']

@pytest.mark.parametrize('p,d', [(0, 0), (None, .5), (.5, None), (None, None)])
def test_unassessed_channels_do_not_invent_equilibrium(p, d):
    assert PDProfile(p, d).vector()['balance'] is None

@pytest.mark.parametrize('bad', [-.01, 1.01, 95, float('nan'), float('inf'), True])
def test_invalid_scores_rejected(bad):
    with pytest.raises(ValueError): PDProfile(bad, 1)

@pytest.mark.parametrize('bad', ['NaN', 'Infinity', '-Infinity', True, '1/0', '1e99999'])
def test_invalid_numbers_rejected(bad):
    with pytest.raises(ValueError): number(bad)

@pytest.mark.parametrize('literal', ['0', '-1', '13', '0.1', '0.0001', '1/3', '0.125', '-0.04'])
def test_exact_numeric_roundtrip(literal):
    assert number(number_text(number(literal))) == number(literal)

@pytest.mark.parametrize('args', [(None, None), (2, 1), (1, 1, False, True)])
def test_invalid_ranges(args):
    with pytest.raises(ValueError): NumericRange(*args)

def test_negative_tolerance():
    with pytest.raises(ValueError): NumericRange.around(1, -1)

def test_open_boundary_violation_has_zero_distance_but_real_conflict():
    state, d, raw = compare_ranges(NumericRange.constraint('gt', 50), NumericRange.point(50), Fraction(100))
    assert state is PairStatus.CONFLICT and d['boundary_gap'] == '0' and raw == 100

def test_uncertainty_interval_is_partial_not_a_fabricated_probability():
    state, d, raw = compare_ranges(NumericRange.point(0), NumericRange(0, 1))
    assert state is PairStatus.PARTIAL and raw is None

def test_observation_within_expected_bounds():
    state, _, raw = compare_ranges(NumericRange(0, 30), NumericRange(10, 20))
    assert state is PairStatus.ALIGNED and raw == 0

def test_missing_defense_is_not_one():
    node = measurement(id='n', entity='e', concept='p', value=1, unit='count', scope=demonstration_scope())
    assert node.support.assess()['strength'] is None

def test_factor_gaps_are_not_dropped():
    s = SupportProfile((SupportFactor('a', .9, 'test'), SupportFactor('b', None, 'unknown', order=3)))
    assert s.assess()['strength'] is None and s.assess()['coverage'] == .5

def test_repeated_dependency_factors_do_not_multiply():
    s = SupportProfile(tuple(SupportFactor(str(i), .9, 'same evidence', dependency_group='one') for i in range(5)))
    assert s.assess()['strength'] == .9 and s.assess()['dependency_groups'] == 1

def test_naive_time_rejected():
    with pytest.raises(ValueError): TimeWindow.instant('2026-10-02T12:00:00')

def test_timezone_normalization():
    assert TimeWindow.instant('2026-10-02T12:00:00Z') == TimeWindow.instant('2026-10-02T08:00:00-04:00')

def test_context_type_cannot_enter_scoring():
    with pytest.raises(TypeError): PairGraph().add_node(NarrativeContext.deep_sigma())

def test_profile_types_validated():
    with pytest.raises(TypeError): Representation('x', 'L', 1, 'e', 'c', pd={})

def test_calibration_is_explicit_not_confidence_times_a_magic_factor():
    r = beta_calibration(72, 100)
    assert r['posterior_mean'] == pytest.approx(73/102)
    assert r['data_available']
    assert not beta_calibration(0, 0)['data_available']
