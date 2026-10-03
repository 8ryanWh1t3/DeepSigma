from dataclasses import replace
import pytest
from vinculum import Representation,Side,NumericRange,Scope,PairGraph,HingeEvaluator,PairPlanner,PairingPlan

S=Scope('x','cookies','order','line',timeless=True)
def node(id,side='L',order=1,value=13,**kwargs):
    args=dict(id=id,side=side,order=order,entity='x',concept='count',quantity=NumericRange.point(value),unit='count',scope=S)
    args.update(kwargs);return Representation(**args)

def graph(*nodes):
    g=PairGraph('g')
    for n in nodes:g.add_node(n)
    return g

def auto(**kwargs):return PairingPlan('auto',policy_id='exact-v1',basis='test-only explicit complete one-to-one mapping',**kwargs)

def test_auto_unique_across_order():
    g=graph(node('L','L',1),node('M','M',4,value=12))
    a=PairPlanner().apply(g,auto())
    assert len(a.selected_pair_ids)==1
    r=g.evaluate().pairs[0]
    assert (r.language_order,r.mathematics_order)==(1,4)
    assert r.status.value=='CONFLICT'
    assert r.supported_collision_score is None # exact metadata does not invent match probability

@pytest.mark.parametrize('side',['L','M'])
def test_global_ambiguity_both_endpoints(side):
    nodes=[node('L','L'),node('M','M'),node('extra',side)]
    g=graph(*nodes);a=PairPlanner().apply(g,auto())
    assert len(g.pairs)==0
    assert len(a.deferred_candidate_ids)==2
    assert all(c.ambiguous for c in a.candidates)

def test_guided_ambiguity_explicitly_selected():
    g=graph(node('L'),node('M1','M'),node('M2','M'))
    a=PairPlanner().apply(g,PairingPlan('guided',choices=(('L','M2'),),basis='analyst selected second record'))
    assert len(g.pairs)==1 and next(iter(g.pairs.values())).right_id=='M2'
    assert len(a.deferred_candidate_ids)==1

def test_guided_reject_is_atomic():
    g=graph(node('L'),node('M','M'))
    with pytest.raises(ValueError):PairPlanner().apply(g,PairingPlan('guided',choices=(('L','M'),('bad','id'))))
    assert len(g.pairs)==0

def test_manual_bad_is_atomic():
    g=graph(node('L'),node('M','M'))
    with pytest.raises(ValueError):PairPlanner().apply(g,PairingPlan('manual',choices=(('L','M'),('bad','id'))))
    assert len(g.pairs)==0

@pytest.mark.parametrize('change',[{'entity':'other'},{'concept':'other'},{'unit':'m'},{'scope':replace(S,population='other')},{'scope':replace(S,timeless=False)}])
def test_incompatible_not_autopaired(change):
    g=graph(node('L'),node('M','M',**change));a=PairPlanner().apply(g,auto())
    assert not g.pairs

def test_missing_scope_deferred_not_dropped():
    g=graph(node('L'),node('M','M',scope=replace(S,denominator=None)))
    a=PairPlanner().apply(g,auto())
    assert not g.pairs
    assert a.candidates[0].state=='UNRESOLVED'
    assert 'denominator' in a.candidates[0].pending

@pytest.mark.parametrize('value',[13,12,0,999])
def test_pair_matching_does_not_depend_on_agreement(value):
    g=graph(node('L'),node('M','M',value=value));a=PairPlanner().apply(g,auto())
    assert len(g.pairs)==1 and a.candidates[0].metadata_coverage==1

def test_unknown_numeric_value_can_be_paired_but_not_scored():
    g=graph(node('L',quantity=None),node('M','M'))
    PairPlanner().apply(g,auto())
    assert g.evaluate().pairs[0].status.value=='UNRESOLVED'

def test_manual_unpaired_no_collision():
    g=graph(node('L'),node('M','M'))
    a=PairPlanner().apply(g,PairingPlan())
    assert not g.pairs and len(a.unmatched_node_ids)==2
    assert g.evaluate().summary['max_raw_collision_score'] is None

def test_order_filter():
    g=graph(node('L1'),node('L2',order=2),node('M','M'))
    a=PairPlanner().apply(g,auto(language_orders=(2,)))
    assert len(g.pairs)==1 and next(iter(g.pairs.values())).left_id=='L2'

def test_candidate_budget():
    g=graph(node('L'),node('M1','M'),node('M2','M'))
    with pytest.raises(ValueError):PairPlanner().apply(g,auto(max_candidates=1))
    assert not g.pairs

def test_auto_requires_named_policy():
    with pytest.raises(ValueError):PairingPlan('auto')
    with pytest.raises(ValueError):PairingPlan('auto',policy_id='name')

def test_all_25_slots_are_possible_not_automatic():
    nn=[node('L'+str(i),'L',i) for i in range(1,6)]+[node('M'+str(j),'M',j) for j in range(1,6)]
    g=graph(*nn);a=PairPlanner().apply(g,auto())
    assert len(a.candidates)==25 and len(g.pairs)==0
    PairPlanner().apply(g,PairingPlan('guided',choices=tuple((f'L{i}',f'M{j}')for i in range(1,6)for j in range(1,6))))
    assert g.evaluate().matrix['evaluated_order_slots']==25

def test_permutation_independent_matching():
    a=graph(node('L'),node('M1','M'),node('M2','M'))
    b=graph(node('M2','M'),node('L'),node('M1','M'))
    assert PairPlanner().apply(a,auto()).to_dict()==PairPlanner().apply(b,auto()).to_dict()

def test_declared_alignment_support_is_not_inferred():
    g=graph(node('L'),node('M','M'))
    a=PairPlanner().apply(g,auto(alignment_support=.8,alignment_basis='declared example contract coefficient'))
    assert next(iter(g.pairs.values())).alignment_support==.8
    with pytest.raises(ValueError):auto(alignment_support=.8)
