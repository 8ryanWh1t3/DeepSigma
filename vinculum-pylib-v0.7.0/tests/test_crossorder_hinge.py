from dataclasses import replace
import pytest
from vinculum import *
from vinculum.demos import bakers_dozen, demonstration_scope, declared_support


def evaluate_nodes(left=None, right=None, policy=None, spec=None):
    f = bakers_dozen()
    l, r = f.graph.nodes['L-order'], f.graph.nodes['M-receipt']
    l, r = left or l, right or r
    spec = spec or PairSpec('p', l.id, r.id, 'test pair', alignment_support=1, alignment_basis='test')
    return HingeEvaluator(policy).evaluate(l, r, spec)


def test_bakers_exact_discrepancy():
    r = evaluate_nodes()
    assert r.status is PairStatus.CONFLICT and r.discrepancy['signed_delta'] == '-1'
    assert r.raw_collision_score == 100 and r.supported_collision_score == 99


def test_equal_pd_balance_is_not_a_collision():
    for count, status in [(12, PairStatus.CONFLICT), (13, PairStatus.ALIGNED)]:
        fixture = bakers_dozen(count)
        assert fixture.evaluate().pairs[0].status is status


def test_weak_defense_does_not_erase_disagreement_or_scale_the_number():
    strong, weak = (bakers_dozen(12, d).evaluate().pairs[0] for d in [.99, .42])
    assert strong.status is weak.status is PairStatus.CONFLICT
    assert strong.discrepancy == weak.discrepancy
    assert strong.raw_collision_score == weak.raw_collision_score == 100
    assert weak.supported_collision_score == 42


def test_zero_support_still_not_alignment():
    r = bakers_dozen(12, 0).evaluate().pairs[0]
    assert r.status is PairStatus.CONFLICT and r.raw_collision_score == 100
    assert r.supported_collision_score == 0


def test_unknown_support_has_no_fake_zero_score():
    r = bakers_dozen(12, None).evaluate().pairs[0]
    assert r.status is PairStatus.CONFLICT and r.supported_collision_score is None


@pytest.mark.parametrize('field', ['entity', 'concept', 'unit'])
def test_mismatched_identity_or_dimension_not_conflict(field):
    n = bakers_dozen().graph.nodes['M-receipt']
    value = 's' if field == 'unit' else 'different'
    r = evaluate_nodes(right=replace(n, **{field: value}))
    assert r.status is PairStatus.NOT_COMPARABLE
    assert r.raw_collision_score is None and r.discrepancy['signed_delta'] is None


@pytest.mark.parametrize('field', ['population', 'denominator', 'granularity', 'location', 'definition_version', 'scope_id'])
def test_scope_mismatch_not_compared(field):
    n = bakers_dozen().graph.nodes['M-receipt']
    # Both sides need supplied location to demonstrate mismatch (missing is unknown).
    l = bakers_dozen().graph.nodes['L-order']
    if field == 'location': l = replace(l, scope=replace(l.scope, location='a'))
    r = evaluate_nodes(left=l, right=replace(n, scope=replace(n.scope, **{field:'different'})))
    assert r.status is PairStatus.NOT_COMPARABLE


def test_missing_scope_unresolved_not_compared():
    n = bakers_dozen().graph.nodes['M-receipt']
    r = evaluate_nodes(right=replace(n, scope=replace(n.scope, population=None)))
    assert r.status is PairStatus.UNRESOLVED and r.raw_collision_score is None


def test_mandatory_checks_cannot_be_disabled_by_order_selection():
    n = bakers_dozen().graph.nodes['M-receipt']
    n = replace(n, scope=replace(n.scope, scope_id='different'))
    r = evaluate_nodes(right=n, spec=PairSpec('p','L-order','M-receipt','test', hinge_orders=(1,)))
    assert r.status is PairStatus.NOT_COMPARABLE and 4 in r.hinge_orders


def test_missing_numeric_meaning_unresolved():
    l = replace(bakers_dozen().graph.nodes['L-order'], quantity=None)
    assert evaluate_nodes(left=l).status is PairStatus.UNRESOLVED


def test_exact_unit_normalization():
    l, r = bakers_dozen().graph.nodes.values()
    l = replace(l, concept='length', quantity=NumericRange.point(82), unit='ft')
    r = replace(r, concept='length', quantity=NumericRange.point(984), unit='in')
    assert evaluate_nodes(l,r).status is PairStatus.ALIGNED
    assert evaluate_nodes(l,replace(r,quantity=NumericRange.point(82))).status is PairStatus.CONFLICT


def test_affine_unit_normalization():
    l,r = bakers_dozen().graph.nodes.values()
    l = replace(l,concept='temperature',quantity=NumericRange.point(0),unit='C')
    r = replace(r,concept='temperature',quantity=NumericRange.point(32),unit='F')
    assert evaluate_nodes(l,r).status is PairStatus.ALIGNED


def test_unknown_unit_is_unresolved():
    n = replace(bakers_dozen().graph.nodes['M-receipt'], unit='unknown-unit')
    assert evaluate_nodes(right=n).status is PairStatus.UNRESOLVED


def test_different_windows_do_not_compare_aggregates():
    l,r = bakers_dozen().graph.nodes.values()
    l=replace(l,scope=replace(l.scope,timeless=False,window=TimeWindow('2026-10-02T12:00Z','2026-10-02T12:01Z')))
    r=replace(r,scope=replace(r.scope,timeless=False,window=TimeWindow('2026-10-02T12:00Z','2026-10-02T12:02Z')))
    assert evaluate_nodes(l,r).status is PairStatus.NOT_COMPARABLE


def test_stale_data_is_unresolved_under_an_explicit_clock():
    l,r = bakers_dozen().graph.nodes.values()
    w=TimeWindow.instant('2026-10-02T12:00Z')
    l=replace(l,scope=replace(l.scope,timeless=False,window=w))
    r=replace(r,scope=replace(r.scope,timeless=False,window=w))
    r=evaluate_nodes(l,r,HingePolicy(max_age_seconds=30,as_of='2026-10-02T12:01Z'))
    assert r.status is PairStatus.UNRESOLVED


def test_product_aggregation_needs_explicit_basis():
    with pytest.raises(ValueError): HingePolicy(support_aggregation='product')
    r=evaluate_nodes(policy=HingePolicy(support_aggregation='product',product_basis='declared heuristic only'))
    assert r.supported_collision_score == pytest.approx(99)


def test_hinge_extensions_add_restrictions():
    f=bakers_dozen(); l,r=f.graph.nodes.values(); p=next(iter(f.graph.pairs.values()))
    ev=HingeEvaluator().register_check('o6',lambda *_: HingeCheck('additional',6,CheckState.UNKNOWN,'test missing assumption'))
    result=ev.evaluate(l,r,p)
    assert result.status is PairStatus.UNRESOLVED and 6 in result.hinge_orders


def test_extension_error_does_not_pass():
    f=bakers_dozen(); l,r=f.graph.nodes.values(); p=next(iter(f.graph.pairs.values()))
    def error(*_): raise RuntimeError('failed check')
    result=HingeEvaluator().register_check('error',error).evaluate(l,r,p)
    assert result.status is PairStatus.UNRESOLVED
